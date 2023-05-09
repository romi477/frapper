# python3

import logging
import sqlite3
from io import BytesIO
from copy import deepcopy
from datetime import datetime

import numpy as np
from PIL import Image
from pyocr import tesseract
from pyocr.builders import TextBuilder, WordBoxBuilder


PIXEL_SUM_V1 = 255 + 255 + 255
PIXEL_SUM_V2 = 243 + 247 + 250

MIN_HEIGHT = 140
TAG_OFFSET = 4
SPLIT_PIXEL_OFFSET = 7
THRES_HOLD_BLACK = 150
THRES_HOLD_TAG = 15
WHITE_SEPARATOR_COUNT = 3

IS_TRUE = '1'
IS_FALSE = '0'

BLACK_NUM = 0
WHITE_NUM = 255

TARGET_LANG = 'pol'

TO_DO = 'todo'
ERROR = 'error'
DONE = 'done'

R_RANGE = (245, 255)
G_RANGE = (245, 255)
B_RANGE = (212, 228)

DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

_logger = logging.getLogger(__name__)


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

    def perform(self):
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

    def parse(self):
        if self.state == TO_DO:
            self.perform()

        return dict(
            state=self.state,
            target_string=self.target_string,
            target_tag=self.target_tag,
            translate_string=self.translate_string,
            translate_tag=self.translate_tag,
            metadata=self.get_metainfo(),
        )

    def split_row_image(self):
        X, Y = self._image.size
        targer_image = translate_image = self._image

        gray_image = to_gray(self._image)
        split_index = find_split_index(gray_image)

        if not split_index:
            self._state = ERROR
        else:
            targer_image = self._image.crop((0, 0, X, split_index))
            translate_image = self._image.crop((0, split_index, X, Y))

        return targer_image, translate_image

    def get_metainfo(self, to_string=False):
        metadata = deepcopy(self.metadata)
        metadata.pop('meta_id', False)
        metadata.pop('message_id', False)
        metadata.pop('message_date', False)
        if to_string:
            return str(metadata)
        return metadata

    def save_sqlite_db(self, conn):
        values = (
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
        save_query = self._get_save_phrase_query()
        try:
            conn.execute(save_query, values)
        except sqlite3.IntegrityError as ex:
            return False, ex.args

        conn.commit()
        return True, ''

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

    @staticmethod
    def _get_save_phrase_query():
        query = """
            INSERT INTO phrase_pl (
                meta_id,
                state,
                active,
                target,
                target_tag,
                translate,
                translate_tag,
                target_mask,
                translate_mask,
                message_id,
                message_date,
                metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return query

    @staticmethod
    def _get_save_meta_query():
        query = """
            INSERT INTO phrase_meta (
                state,
                channel_id,
                message_id,
                message_date
            )
            VALUES (?, ?, ?, ?)
        """
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


def find_split_index(image):
    X, _ = image.size
    array = np.array(image)

    result, point = list(), list()
    candidate_list = [x / WHITE_NUM for x in (x.sum() for x in array)]

    for idx, array_x in enumerate(candidate_list, start=1):
        if int(array_x.sum()) == X:
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


def split_image(image, **kw):
    X, Y = image.size

    image_px = image.crop((SPLIT_PIXEL_OFFSET, 0, SPLIT_PIXEL_OFFSET + 1, Y))
    image_array = np.array(image_px)

    need_second = False
    candidate_list, point = list(), list()

    for idx, pixel in enumerate(image_array, start=1):
        print(pixel.sum())
        if int(pixel.sum()) == PIXEL_SUM_V1:
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
    candidate_filtered = [(x, y) for x, y in candidate_list if (y - x) > MIN_HEIGHT]

    for idx, (y1, y2) in enumerate(candidate_filtered, start=1):
        image_x = image.crop((0 + SPLIT_PIXEL_OFFSET, y1, X - SPLIT_PIXEL_OFFSET, y2))

        kw['file_index'] = idx
        kw['coordinates'] = (y1, y2)
        kw['threshold'] = list()
        kw['size'] = image_x.size

        record = FrapperImage(image_x, **kw)
        result.append(record)

    return result


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
    record_list = split_image(pil_image, **kw)
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
    record_list = split_image(pil_image, **kw)
    return record_list


def split_image_from_bin_data(bin_data, **kw):
    with Image.open(BytesIO(bin_data)) as pil_image:
        pil_image.load()

    record_list = split_image(pil_image, **kw)
    return record_list
