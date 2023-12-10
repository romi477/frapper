# python3

import logging
from time import sleep

import requests
from redis import Redis

from tools import parse_redis_key
from parser import process_bin_data
from settings import MAIN_HOST, REDIS_PORT, REDIS_DB, HEADERS
from settings import log_format, log_dir


log = logging.getLogger('frapper.listener')
handler = logging.FileHandler(f'{log_dir}/listener.log')
formatter = logging.Formatter(log_format)
handler.setFormatter(formatter)
log.addHandler(handler)


def read_redis_db(client):

    for complex_key in client.scan_iter():
        complex_key = complex_key.decode()
        log.info(complex_key)
        meta_id, message_id, message_date = parse_redis_key(complex_key)
        kw = dict(
            meta_id=meta_id,
            message_date=message_date,
            message_id=int(message_id),
        )
        rec_list = process_bin_data(client.get(complex_key), **kw)

        if not rec_list:
            log.info(f'Missed records: {complex_key}. Bin data moved to DB=1')
            client.move(complex_key, 1)
            continue

        data = dict(phrase_pl=[x.to_dict() for x in rec_list])
        log.info(f'Post data for {complex_key}: {data}')
        response = requests.post(f'{MAIN_HOST}/phrase-pl/', json=data, headers=HEADERS)

        if (code := response.status_code) != 200:
            log.error(f'Response status: {code} ({complex_key}). Bin data moved to DB=1')
            log.error(response.text)
            client.move(complex_key, 1)
            continue

        log.info(response.json())
        client.delete(complex_key)


if __name__ == '__main__':
    redis_client = Redis(host='localhost', port=REDIS_PORT, db=REDIS_DB)

    while True:
        try:
            read_redis_db(redis_client)
        except KeyboardInterrupt:
            redis_client.close()
            raise
        else:
            sleep(5)
