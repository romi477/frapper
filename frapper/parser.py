# python3

import json
import logging
import sqlite3
from io import BytesIO

import numpy as np
from PIL import Image
from pyocr import tesseract
from pyocr.builders import TextBuilder, WordBoxBuilder


_logger = logging.getLogger(__name__)

PIXEL_SUM = 765
MIN_HEIGHT = 140
TAG_OFFSET = 4
SPLIT_PIXEL_OFFSET = 7
THRES_HOLD_BLACK = 150
THRES_HOLD_TAG = 15
WHITE_SEPARATOR_COUNT = 3

BLACK_NUM = 0
WHITE_NUM = 255

TARGET_LANG = 'pol'

TO_DO = 'todo'
ERROR = 'error'
DONE = 'done'

R_RANGE = (245, 255)
G_RANGE = (245, 255)
B_RANGE = (212, 228)


class FrapperImage:

    def __init__(self, pil_image, **kw):
        self._state = TO_DO
        self._image = pil_image
        self.target_mask = ''
        self.translate_mask = ''
        self.metadata = kw

        target, translate = self._init_row_image()

        self.target_image = target
        self.translate_image = translate

        self._target_array = np.array(target)
        self._translate_array = np.array(translate)

        self.target_image_gray = to_gray(target)
        self.translate_image_gray = to_gray(translate)

        self.target_string = ''
        self.target_tag = ''
        self.translate_string = ''
        self.translate_tag = ''

    def __repr__(self):
        return '<FrapperImage(%s)>' % self.metadata

    @property
    def state(self):
        return self._state

    @property
    def status(self):
        return all([
            self.state == DONE,
            self.target_string,
            self.target_tag,
            self.translate_string,
            # self.translate_tag,
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
        result = list()
        threshold = list()
        box_list = parse_image_boxes(self.target_image_gray)

        mask = list()
        for box in box_list:
            is_tag, value = self._is_tag(self._target_array, box.position)
            if is_tag:
                mask_value = '1'
                result.append(box.content.rstrip(',.'))
            else:
                mask_value = '0'

            threshold.append(value)
            mask.append(mask_value)

        data = self.metadata['treshold']
        data.append(tuple(filter(None, threshold)))
        text = ' '.join(x.lower() for x in result)

        self.target_tag = text
        self.target_mask = ''.join(mask)
        return text

    def parse_translate_tag(self):
        result = list()
        threshold = list()
        box_list = parse_image_boxes(self.translate_image_gray)

        mask = list()
        for box in box_list:
            is_tag, value = self._is_tag(self._translate_array, box.position)
            if is_tag:
                mask_value = '1'
                result.append(box.content.rstrip(',.'))
            else:
                mask_value = '0'

            threshold.append(value)
            mask.append(mask_value)

        data = self.metadata['treshold']
        data.append(tuple(filter(None, threshold)))
        text = ' '.join(x.lower() for x in result)

        self.translate_tag = text
        self.translate_mask = ''.join(mask)
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
            metadata=self.metadata,
        )

    def save_target_gray(self, name):
        self.target_image_gray.save(name)

    def save_translate_gray(self, name):
        self.translate_image_gray.save(name)

    def save_db(self, conn):
        image = self._image
        X, Y = image.size

        buffer = BytesIO()
        image.save(buffer, format='JPEG')
        bin_data = buffer.getvalue()

        values = (
            self.metadata['id'],
            self.state,
            self.status,
            self.target_string,
            self.target_tag,
            self.translate_string,
            self.translate_tag,
            self.target_mask,
            self.translate_mask,
            self._get_metainfo(),
            X,
            Y,
            self.metadata['file_name'],
            self.metadata['file_index'],
            self.metadata['date'],
            bin_data
        )
        query = self._get_save_query()
        conn.execute(query, values)
        conn.commit()

    @staticmethod
    def _get_save_query():
        query = """
            INSERT INTO phrases (
                message_id,
                state,
                status,
                target,
                target_tag,
                translate,
                translate_tag,
                target_mask,
                translate_mask,
                metadata,
                width,
                height,
                file_name,
                file_index,
                file_date,
                bin_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        return query

    def _get_metainfo(self):
        meta_coord = self.metadata['coordinates']
        meta_treshold = self.metadata['treshold']
        return '{%s}' % f'crd: {meta_coord}, tsh: {meta_treshold}'

    def save_os(self):
        file_path = self.metadata['file_path']
        index = self.metadata['index']
        name, ext = file_path.rsplit('.', maxsplit=1)

        result_path = f'{name}-{index}.{ext}'
        target_path = f'{name}-{index}.target.{ext}'
        target_path_gray = f'{name}-{index}.target.gray.{ext}'
        translate_path = f'{name}-{index}.translate.{ext}'
        translate_path_gray = f'{name}-{index}.translate.gray.{ext}'

        self._image.save(result_path)
        self.target_image.save(target_path)
        self.target_image_gray.save(target_path_gray)
        self.translate_image.save(translate_path)
        self.translate_image_gray.save(translate_path_gray)
        _logger.info('Saved to OS: %s', self)

    def _is_tag(self, array, coordinates):
        ((x1, y1), (x2, _)) = coordinates
        array_slice = array[y1 - TAG_OFFSET][x1:x2]

        counter = int()
        for pixel in array_slice:
            if _in_a_range(pixel):
                counter += 1

        value = 100 * counter / len(array_slice)
        return value >= THRES_HOLD_TAG, int(value)

    def _init_row_image(self):
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


def from_file_path(pth):
    with Image.open(pth) as pil_image:
        pil_image.load()

    record_list = split_image(pil_image, file_path=pth)
    return record_list


def from_tg_json(jdata, suffix):
    pth = f'{suffix}/{jdata["photo"]}'

    with Image.open(pth) as pil_image:
        pil_image.load()

    kw = dict(
        id=jdata['id'],
        date=jdata['date'],
        date_unixtime=jdata['date_unixtime'],
        from_name=jdata['from'],
        from_id=jdata['from_id'],
        file_name=pth.rsplit('/', maxsplit=1)[-1],
    )

    record_list = split_image(pil_image, **kw)
    return record_list


def parse_image_boxes(image, convert_to_gray=False):
    if convert_to_gray:
        image = to_gray(image)
    word_boxes = tesseract.image_to_string(image, lang=TARGET_LANG, builder=WordBoxBuilder())
    return word_boxes


def parse_text(image, convert_to_gray=False):
    if convert_to_gray:
        image = to_gray(image)
    text = tesseract.image_to_string(image, lang=TARGET_LANG, builder=TextBuilder())
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

    result, point = [], []
    candidate_list = [x / WHITE_NUM for x in (x.sum() for x in array)]

    for idx, array_x in enumerate(candidate_list, start=1):
        if int(array_x.sum()) == X:
            point.append(idx)
        else:
            if point:
                result.append(point)
            point = []

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
    candidate_list, point = [], []

    for idx, pixel in enumerate(image_array, start=1):
        if int(pixel.sum()) == PIXEL_SUM:
            if not need_second:
                point.append(idx)
                need_second = True
        else:
            if need_second:
                point.append(idx)
                candidate_list.append(point)
                need_second = False
                point = []

    if need_second:
        point.append(idx)
        candidate_list.append(point)

    result = list()
    candidate_filtered = ((x, y) for x, y in candidate_list if (y - x) > MIN_HEIGHT)

    for idx, (y1, y2) in enumerate(candidate_filtered, start=1):
        image_x = image.crop((0 + SPLIT_PIXEL_OFFSET, y1, X - SPLIT_PIXEL_OFFSET, y2))

        kw['file_index'] = idx
        kw['coordinates'] = (y1, y2)
        kw['treshold'] = []

        record = FrapperImage(image_x, **kw)
        result.append(record)

    return result


def _in_a_range(pixel):
    a, b, c = pixel
    return all([a in range(*R_RANGE), b in range(*G_RANGE), c in range(*B_RANGE)])


def make_parse(count=None):
    sufix = '/home/zorka/Downloads/Telegram Desktop/ChatExport_2023-04-13'

    with open(f'{sufix}/result.json') as f:
        data = json.load(f)

    conn = sqlite3.connect('database.db')

    with open('frapp.log', 'w+') as flog:

        idx = int()
        for index, jdata in enumerate(data['messages']):
            if jdata.get('type') != 'message':
                continue
            if count and index > count:
                break

            record_list = from_tg_json(jdata, sufix)
            for rec in record_list:
                idx += 1
                rec.perform()
                rec.save_db(conn)
                print(idx, rec.state, rec.status, rec._get_metainfo(), rec.target_mask, rec.translate_mask, rec.metadata['file_name'], rec.metadata['file_index'], sep='; ', file=flog)
                print(idx, rec.state, rec.status, rec._get_metainfo(), rec.target_mask, rec.translate_mask, rec.metadata['file_name'], rec.metadata['file_index'], sep='; ')

    conn.close()
    return data


def make_parse_file(pth):
    rec_list = from_file_path(pth)
    for rec in rec_list:
        rec.perform()
    return rec_list


def make_info(pth):
    result = []
    rec_list = from_file_path(pth)
    for rec in rec_list:
        data = rec.parse()
        result.append(data)
    return result


if __name__ == '__main__':
    # make_parse()
    # r = make_info('/opt/projects/frapper_app/frapper_test/photo_232@23-10-2022_13-10-11.jpg')
    # rr = make_parse_file('/opt/projects/frapper_app/frapper_test/photo_232@23-10-2022_13-10-11.jpg')
# 
    # recs = from_file_path('/opt/projects/frapper_app/frapper_test/photo_232@23-10-2022_13-10-11.jpg')
    # r = recs[1]
    # res = r.parse()
    # print(res)

