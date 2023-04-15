# python3

import re
import json
import requests

from telethon.sync import TelegramClient, events

from settings import (
    FRAPPER_ID,
    PHRASES_ID,
    TG_API_HASH,
    TG_API_ID,
    BOT_TOKEN,
    API_URL,
)


bot = TelegramClient('frapper_bot', TG_API_ID, TG_API_HASH)


@bot.on(events.NewMessage(chats=[PHRASES_ID]))
async def handler_new_message(event):
    print('New item in channel')
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
        await event.reply('Bad Query!')
        return

    api_url = f'{API_URL}/target_count/{target}'
    data = fetch_data(api_url)

    if not data:
        await event.reply('Not Found!')
        return

    for message in data:
        response = prepare_response(message)
        await event.respond(response, parse_mode='html')

    return True


@bot.on(events.NewMessage(pattern='/f'))
async def handler_new_message_target(event):
    print('Call Find')
    query = event.message.message
    query_split = query.split(maxsplit=1)

    if len(query_split) < 2:
        await event.reply('Bad Query!')
        return

    target = query_split[-1]

    uurl = f'{API_URL}/target/{target}'
    data = fetch_data(uurl)

    if not data:
        await event.reply('Not Found!')
        return

    for message in data:
        response = prepare_response(message)
        await event.respond(response, parse_mode='html')

    return True


@bot.on(events.NewMessage(pattern='/t'))
async def handler_new_message_translate(event):
    print('Call Find')
    query = event.message.message
    query_split = query.split(maxsplit=1)

    if len(query_split) < 2:
        await event.reply('Bad Query!')
        return

    target = query_split[-1]

    uurl = f'{API_URL}/target_translate/{target}'
    data = fetch_data(uurl)

    if not data:
        await event.reply('Not Found!')
        return

    for message in data:
        response = prepare_response(message)
        await event.respond(response, parse_mode='html')

    return True


def fetch_data(url):
    response = requests.get(url)
    data = response.content.decode('utf-8')
    jdata = json.loads(data)
    return jdata['messages']


def prepare_response(message):
    entity_id, message_id, target, target_mask, translate, translate_mask = message

    target_ = _rebuild_string(target, target_mask)
    translate_ = _rebuild_string(translate, translate_mask)
    html_string = (
        f'{entity_id}\n\n\U00002139\t\t{target_}\n\n\U000021AA\t\t<i>{translate_}</i>'
    )
    return html_string


def _rebuild_string(sentence, mask):
    target = ''
    for action, word in zip(mask, sentence.split()):
        if int(action):
            word = f'<u>{word}</u>'
        target += (word + ' ')
    return target


if __name__ == '__main__':
    bot.start(bot_token=BOT_TOKEN)
    bot.run_until_disconnected()
