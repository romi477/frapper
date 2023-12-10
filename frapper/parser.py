# python3

import json
import sqlite3
import logging

from tools import (
    DONE,
    FrapperImage,
    split_image_from_tg_json,
    split_image_from_file_path,
    split_image_from_bin_data,
)
from settings import FRAPPER_DB, PHRASE_PL_ID
from settings import log_format, log_dir


log = logging.getLogger('frapper.parser')
handler = logging.FileHandler(f'{log_dir}/parser.log')
formatter = logging.Formatter(log_format)
handler.setFormatter(formatter)
log.addHandler(handler)


def process_chat_history(pth, count=None):
    with open(f'{pth}/result.json', encoding='utf-8') as f:
        data = json.load(f)

    index = int()
    conn = sqlite3.connect(FRAPPER_DB)

    for idx, jdata in enumerate(data['messages']):
        if jdata.get('type') != 'message':
            continue

        if count and idx > count:
            break

        meta_values = (
            DONE,
            PHRASE_PL_ID,
            jdata['id'],
            jdata['date'],
            False,
        )
        query = FrapperImage._get_save_meta_query()
        cursor_used = conn.execute(query, meta_values)
        conn.commit()

        jdata['meta_id'] = cursor_used.lastrowid
        record_list = split_image_from_tg_json(jdata, pth)

        if not record_list:
            log.info(f'Missed: {jdata}')

        for rec in record_list:
            index += 1
            rec.parse()
            result, msg = rec._save_sqlite_db(conn)

            values = [
                index,
                rec.state,
                rec.success,
                rec.get_metainfo(),
                rec.target_mask,
                rec.translate_mask,
            ]
            if not result:
                values.append(f'Skipped: {msg}')
                values.append(rec.target_string)
                values.append(rec.target_tag)

            log.info('; '.join(str(x) for x in values))

    conn.close()
    return data


def process_file(pth):
    rec_list = split_image_from_file_path(pth)
    [rec.parse() for rec in rec_list]
    return rec_list


def process_bin_data(bin_data, **kw):
    rec_list = split_image_from_bin_data(bin_data, **kw)
    [rec.parse() for rec in rec_list]
    return rec_list


if __name__ == '__main__':
    process_chat_history('/home/zorka/Downloads/Telegram Desktop/ChatExport_2023-06-04')
    # l = split_image_from_file_path('/opt/projects/frapper_app/photo_21@02-10-2022_22-53-00.jpg')
