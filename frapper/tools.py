# python3

import sqlite3
from io import BytesIO
from copy import deepcopy
from datetime import datetime

import numpy as np
from PIL import Image
from pyocr import tesseract
from pyocr.builders import TextBuilder, WordBoxBuilder

from models import PhrasePl, PhraseMeta


PIXEL_SUM_V1 = 255 + 255 + 255
PIXEL_SUM_V2 = 243 + 247 + 250  # images since 10.05.2023 because of the new design of Reverso
PIXEL_SUM_DATE = '2023-05-10T00:00:00'

TAG_OFFSET = 4
MIN_IMAGE_HEIGHT = 140

STANDARD_WIDTH = 1080
IMAGE_OFFSET_L = 32
IMAGE_OFFSET_R = 112
CUT_THE_ARROW_OFFSET = 73  # depends on IMAGE_OFFSET_L, sum = 105

THRES_HOLD_TAG = 15
THRES_HOLD_BLACK = 150
WHITE_SEPARATOR_COUNT = 3

BLACK_NUM = 0
WHITE_NUM = 255

R_RANGE = (245, 255)
G_RANGE = (245, 255)
B_RANGE = (212, 228)

IS_TRUE = '1'
IS_FALSE = '0'

TO_DO = 'todo'
ERROR = 'error'
DONE = 'done'

TARGET_LANG = 'pol'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


class FrapperImage:

    def __init__(self, pil_image, **kw):
        self._state = TO_DO
        self._image = pil_image
        self.metadata = kw

        target, translate = self.split_row_image()

        self.target_image = target
        self.translate_image = translate

        self._target_array = np.array(target)
        self._translate_array = np.array(translate)

        self.target_image_gray = to_gray(target)
        self.translate_image_gray = to_gray(translate)

        self.target_string = ''
        self.target_tag = ''
        self.target_mask = ''

        self.translate_string = ''
        self.translate_tag = ''
        self.translate_mask = ''

    def __repr__(self):
        return '<FrapperImage(%s)>' % self.metadata

    @property
    def state(self):
        return self._state

    @property
    def success(self):
        return all([
            self.state == DONE,
            self.target_string,
            self.target_tag,
            self.translate_string,
        ])

    def parse(self, verbose=False):
        result = self._parse()

        if verbose:
            return self.post_values()
        return result

    def _parse(self):
        if self.state == ERROR:
            return False  # Do the math

        self.parse_target_string()
        self.parse_target_tag()

        self.parse_translate_string()
        self.parse_translate_tag()

        self._state = DONE
        return True

    def parse_target_string(self):
        text = parse_text(self.target_image_gray)
        self.target_string = text
        return text

    def parse_translate_string(self):
        text = parse_text(self.translate_image_gray)
        self.translate_string = text
        return text

    def parse_target_tag(self):
        text, mask = self._parse_tag_text(self.target_image_gray, self._target_array)

        self.target_tag = text
        self.target_mask = mask
        return text

    def parse_translate_tag(self):
        text, mask = self._parse_tag_text(self.translate_image_gray, self._translate_array)

        self.translate_tag = text
        self.translate_mask = mask
        return text

    def split_row_image(self):
        width, height = self._image.size
        targer_image = translate_image = self._image

        gray_image = to_gray(self._image)
        split_height = find_split_height(gray_image)

        if not split_height:
            self._state = ERROR
        else:
            targer_image = self._image.crop((0, 0, width, split_height))
            translate_image = self._image.crop((CUT_THE_ARROW_OFFSET, split_height, width, height))

        return targer_image, translate_image

    def get_metainfo(self, to_string=False):
        metadata = deepcopy(self.metadata)
        metadata.pop('meta_id', False)
        metadata.pop('message_id', False)
        metadata.pop('message_date', False)
        if to_string:
            return str(metadata)
        return metadata        

    def to_dict(self):
        kwargs = dict(zip(self.post_keys(), self.post_values()))
        phrase_pl = PhrasePl(**kwargs)
        return phrase_pl.post_data()

    @staticmethod
    def post_keys():
        return PhrasePl.post_keys_cls()

    def post_values(self):
        _values = (
            self.metadata['meta_id'],
            self.state,
            self.success,
            self.target_string,
            self.target_tag,
            self.translate_string,
            self.translate_tag,
            self.target_mask,
            self.translate_mask,
            self.metadata['message_id'],
            self.metadata['message_date'],
            self.get_metainfo(to_string=True),
        )
        return _values

    def _save_sqlite_db(self, conn):
        query = self._get_save_phrase_query()
        values = self.post_values()

        try:
            cursor_used = conn.execute(query, values)
        except sqlite3.IntegrityError as ex:
            return False, ex.args

        conn.commit()
        return cursor_used.lastrowid, ''

    def _parse_tag_text(self, image, image_array):
        parse_result = list()
        threshold = list()
        box_list = parse_image_boxes(image)

        mask = list()
        for box in box_list:
            is_tag, value = self._is_tag(image_array, box.position)
            if is_tag:
                mask_value = IS_TRUE
                parse_result.append(box.content.rstrip(',.'))
            else:
                mask_value = IS_FALSE

            threshold.append(value)
            mask.append(mask_value)

        data = self.metadata['threshold']
        data.append(tuple(filter(None, threshold)))

        text = ' '.join(x.lower() for x in parse_result)
        text = text.replace('\n', ' ')

        return text, ''.join(mask)

    def _get_save_phrase_query(self):
        table = PhrasePl._table_name
        keys = PhrasePl.post_keys_cls()
        return self._build_insert_query(table, keys)

    def _get_save_meta_query(self):
        table = PhraseMeta._table_name
        keys = PhraseMeta.post_keys_cls()
        return self._build_insert_query(table, keys)

    @staticmethod
    def _build_insert_query(table, keys):
        args = (table, ', '.join(keys), ', '.join('?' for _ in keys))
        query = "INSERT INTO %s (%s) VALUES (%s)" % args
        return query

    def _is_tag(self, array, coordinates):
        ((x1, y1), (x2, _)) = coordinates
        array_slice = array[y1 - TAG_OFFSET][x1:x2]

        counter = int()
        for pixel in array_slice:
            if in_a_range(pixel):
                counter += 1

        value = 100 * counter / len(array_slice)
        return value >= THRES_HOLD_TAG, int(value)


def parse_image_boxes(image, convert_to_gray=False):
    if convert_to_gray:
        image = to_gray(image)
    word_boxes = tesseract.image_to_string(image, lang=TARGET_LANG, builder=WordBoxBuilder())
    return word_boxes


def parse_text(image, convert_to_gray=False):
    if convert_to_gray:
        image = to_gray(image)
    text = tesseract.image_to_string(image, lang=TARGET_LANG, builder=TextBuilder())
    text = text.replace('\n', ' ')
    return text


def to_gray(image):
    image_gray = image.convert('L')
    image_gray = image_gray.point(
        lambda x: WHITE_NUM if x > THRES_HOLD_BLACK else BLACK_NUM
    )
    return image_gray


def find_split_height(image):
    width, _ = image.size
    array = np.array(image)

    result, point = list(), list()
    candidate_list = [x / WHITE_NUM for x in (x.sum() for x in array)]

    for idx, array_x in enumerate(candidate_list, start=1):
        if int(array_x.sum()) == width:
            point.append(idx)
        else:
            if point:
                result.append(point)
            point = list()

    if point:
        point.append(idx)
        result.append(point)

    if len(result) < WHITE_SEPARATOR_COUNT:
        return False

    result_by_len = [len(x) for x in result][1:-1]
    index = result_by_len.index(max(result_by_len))

    suitable_list = result[index + 1]
    split_index = suitable_list[len(suitable_list) // 2]
    return split_index


def split_image_for_parse(image, **kw):
    width, height = image.size

    if width != STANDARD_WIDTH:
        new_height = int((height / width) * STANDARD_WIDTH)
        image = image.resize((STANDARD_WIDTH, new_height))
        width, height = image.size

    image_px = image.crop((IMAGE_OFFSET_L, 0, IMAGE_OFFSET_L + 1, height))
    image_array = np.array(image_px)

    need_second = False
    candidate_list, point = list(), list()

    pixel_sum = get_pixel_sum(kw['message_date'])

    for idx, pixel in enumerate(image_array, start=1):
        if int(pixel.sum()) == pixel_sum:
            if not need_second:
                point.append(idx)
                need_second = True
        else:
            if need_second:
                point.append(idx)
                candidate_list.append(point)
                need_second = False
                point = list()

    if need_second:
        point.append(idx)
        candidate_list.append(point)

    result = list()
    candidate_filtered = [(x, y) for x, y in candidate_list if (y - x) > MIN_IMAGE_HEIGHT]

    for idx, (y1, y2) in enumerate(candidate_filtered, start=1):
        image_x = image.crop((IMAGE_OFFSET_L, y1, width - IMAGE_OFFSET_R, y2))

        kw['size'] = image_x.size
        kw['y1_y2'] = (y1, y2)
        kw['threshold'] = list()
        kw['file_index'] = idx

        record = FrapperImage(image_x, **kw)
        result.append(record)

    return result


def get_pixel_sum(date_str):
    date = datetime.strptime(date_str, DATETIME_FORMAT)
    version_date = datetime.strptime(PIXEL_SUM_DATE, DATETIME_FORMAT)
    return PIXEL_SUM_V1 if date < version_date else PIXEL_SUM_V2


def in_a_range(pixel):
    a, b, c = pixel
    return all([a in range(*R_RANGE), b in range(*G_RANGE), c in range(*B_RANGE)])


def datetime_now():
    return datetime.now().strftime(DATETIME_FORMAT)


def split_image_from_file_path(pth):
    with Image.open(pth) as pil_image:
        pil_image.load()

    kw = dict(
        meta_id=False,
        message_id=100500,
        message_date=datetime_now(),
    )
    record_list = split_image_for_parse(pil_image, **kw)
    return record_list


def split_image_from_tg_json(jdata, suffix):
    pth = f'{suffix}/{jdata["photo"]}'

    with Image.open(pth) as pil_image:
        pil_image.load()

    kw = dict(
        meta_id=jdata['meta_id'],
        message_id=jdata['id'],
        message_date=jdata['date'],
    )
    record_list = split_image_for_parse(pil_image, **kw)
    return record_list


def split_image_from_bin_data(bin_data, **kw):
    with Image.open(BytesIO(bin_data)) as pil_image:
        pil_image.load()

    record_list = split_image_for_parse(pil_image, **kw)
    return record_list


def prepare_redis_key(meta_id, message_id, message_date):
    return f'{meta_id}_{message_id}_{message_date}'


def parse_redis_key(key):
    meta_id, message_id, message_date = key.split('_', maxsplit=2)
    return meta_id, message_id, message_date
