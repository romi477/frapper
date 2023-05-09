# python3

import re
import json
import requests

from redis import Redis

from telethon.sync import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto

from tools import DATETIME_FORMAT
from settings import (
    FRAPPER_ID,
    PHRASE_PL_ID,
    TG_API_HASH,
    TG_API_ID,
    BOT_TOKEN,
    API_URL,
)

HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'TelegramBot/0.1.0',
}


redis_cli = Redis(host='localhost', port=6379)
bot = TelegramClient('frapper_bot', TG_API_ID, TG_API_HASH)


@bot.on(events.NewMessage(chats=[PHRASE_PL_ID]))
async def handler_new_message(event):
    print('New item in channel')

    message = event.message
    if not isinstance(message.media, MessageMediaPhoto):
        print('Not photo!')
        return False

    data = {
        'phrase_meta': [{
            'channel_id': PHRASE_PL_ID,
            'message_id': (message_id := message.id),
            'message_date': (message_date := message.date.strftime(DATETIME_FORMAT)),
        }],
    }
    response = requests.post(f'{API_URL}/phrase-meta/', json=data, headers=HEADERS)
    if not response.ok:
        print(f'Response status: {response.status_code}')
        return False

    jdata = response.json()
    if not (record_list := jdata['phrase_meta']):
        print('Empty response')
        return False

    redis_key = f"{record_list[0]['id']}_{message_id}_{message_date}"
    print(redis_key)

    bin_data = await event.download_media(file=bytes)
    redis_cli.set(redis_key, bin_data)

    return True


@bot.on(events.NewMessage(pattern='/c'))
async def handler_new_message_count(event):
    print('Call Count')

    def is_number(string):
        return bool(re.match(r'^\d+$', string))

    query = event.message.message
    query_split = query.split()

    is_bad_request = False
    target = query_split[-1]

    if len(query_split) == 1:
        target = 3
    elif len(query_split) > 2:
        is_bad_request = True
    elif not is_number(target):
        is_bad_request = True

    if is_bad_request:
        return await event.reply('Bad Query!')

    data = _fetch_data('fetch-count', count=target)

    if not data:
        return await event.reply('Not Found!')

    for message in data:
        response = _prepare_response(message)
        await event.respond(response, parse_mode='html')

    return True


@bot.on(events.NewMessage(pattern='/f'))
async def handler_new_message_target(event):
    print('Call Find')
    query = event.message.message
    query_split = query.split(maxsplit=1)

    if len(query_split) < 2:
        return await event.reply('Bad Query!')

    target = query_split[-1]
    data = _fetch_data('target-tag', tag=target)

    if not data:
        return await event.reply('Not Found!')

    for message in data:
        response = _prepare_response(message)
        await event.respond(response, parse_mode='html')

    return True


@bot.on(events.NewMessage(pattern='/t'))
async def handler_new_message_translate(event):
    print('Call Find')
    query = event.message.message
    query_split = query.split(maxsplit=1)

    if len(query_split) < 2:
        return await event.reply('Bad Query!')

    target = query_split[-1]
    data = _fetch_data('translate-tag', tag=target)

    if not data:
        return await event.reply('Not Found!')

    for message in data:
        response = _prepare_response(message)
        await event.respond(response, parse_mode='html')

    return True


def _fetch_data(url, **kwargs):
    response = requests.get(
        f'{API_URL}/phrase-pl/{url}',
        params=kwargs,
        headers=HEADERS,
    )
    data = response.content.decode('utf-8')
    jdata = json.loads(data)
    return jdata['messages']


def _prepare_response(message):
    entity_id, message_id, target, target_mask, translate, translate_mask = message

    target_ = _rebuild_string(target, target_mask)
    translate_ = _rebuild_string(translate, translate_mask)

    html_string = (
        f'{entity_id}\n\n\U00002139\t\t{target_}\n\n\U000021AA\t\t<i>{translate_}</i>'
    )
    return html_string


def _rebuild_string(sentence, mask):
    string = ''
    for action, word in zip(mask, sentence.split()):
        if int(action):
            word = f'<u>{word}</u>'
        string += (word + ' ')
    return string


if __name__ == '__main__':
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
