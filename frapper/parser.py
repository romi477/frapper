# python3

import json
import sqlite3

from tools import (
    DONE,
    FrapperImage,
    split_image_from_tg_json,
    split_image_from_file_path,
    split_image_from_bin_data,
)
from settings import FRAPPER_DB, PHRASE_PL_ID


def process_chat_history(pth, count=None):
    with open(f'{pth}/result.json', encoding='utf-8') as f:
        data = json.load(f)

    index = int()
    conn = sqlite3.connect(FRAPPER_DB)

    with open('frapp.log', 'w+', encoding='utf-8') as log_file:
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
            )
            query = FrapperImage._get_save_meta_query()
            cursor_used = conn.execute(query, meta_values)
            conn.commit()

            jdata['meta_id'] = cursor_used.lastrowid
            record_list = split_image_from_tg_json(jdata, pth)
            for rec in record_list:
                index += 1
                rec.perform()
                result, msg = rec.save_sqlite_db(conn)

                log_values = [
                    index,
                    rec.state,
                    rec.success,
                    rec.get_metainfo(),
                    rec.target_mask,
                    rec.translate_mask,
                ]
                if not result:
                    log_values.append(f'SKIPPED: {msg}')
                    log_values.append(rec.target_string)
                    log_values.append(rec.target_tag)

                print(*log_values, sep='; ')
                print(*log_values, sep='; ', file=log_file)

    conn.close()
    return data


def process_file(pth):
    rec_list = split_image_from_file_path(pth)
    return [rec.parse() for rec in rec_list]


def process_bin_data(bin_data, **kw):
    rec_list = split_image_from_bin_data(bin_data, **kw)
    return [rec.parse() for rec in rec_list]


if __name__ == '__main__':
    process_chat_history('/home/zorka/Downloads/Telegram Desktop/ChatExport_2023-05-09')

