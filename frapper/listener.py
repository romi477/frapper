# python3

from time import sleep

import requests
from redis import Redis

from parser import process_bin_data


def read(client):

    for complex_key in client.scan_iter():
        complex_key = complex_key.decode()
        print(complex_key)
        bin_data = client.get(complex_key)
        meta_id, message_id, message_date = complex_key.split('_', maxsplit=2)
        kw = dict(
            meta_id=meta_id,
            message_date=message_date,
            message_id=int(message_id),
        )
        result = process_bin_data(bin_data, **kw)
        print(result)
        client.delete(complex_key)


if __name__ == '__main__':
    redis_cli = Redis(host='localhost', port=6379)

    while True:
        sleep(5)
        print('Run listener')
        read(redis_cli)
