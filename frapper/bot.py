# python3

import logging

import requests
from redis import Redis

from telethon.sync import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto

from models import PhrasePlList, PhraseMetaList
from tools import prepare_redis_key, DATETIME_FORMAT
from settings import (
    PHRASE_PL_ID,
    TG_API_HASH,
    TG_API_ID,
    BOT_TOKEN,
    MAIN_HOST,
    REDIS_DB,
    REDIS_PORT,
    HEADERS
)
from settings import log_format, log_dir

TARGET_EMOJI = '\U00002139'
TRANSLATE_EMOJI = '\U000021AA'

COMMAND_URL_MAPPING = {
    'c': 'fetch-count',
    's': 'fetch-slice',
    'l': 'fetch-tail',
    'f': 'target-tag',
    't': 'translate-tag',
}

log = logging.getLogger('frapper.bot')
handler = logging.FileHandler(f'{log_dir}/bot.log')
formatter = logging.Formatter(log_format)
handler.setFormatter(formatter)
log.addHandler(handler)

redis_client = Redis(host='localhost', port=REDIS_PORT, db=REDIS_DB)
bot = TelegramClient('frapper_bot', TG_API_ID, TG_API_HASH)


@bot.on(events.NewMessage(chats=[PHRASE_PL_ID]))
async def handler_new_message_pl(event):
    log.info('New item in channel.')

    message = event.message
    if not isinstance(message.media, MessageMediaPhoto):
        log.info('Item is not a picture.')
        return False

    data = {
        'phrase_meta': [{
            'channel_id': PHRASE_PL_ID,
            'message_id': (message_id := message.id),
            'message_date': (message_date := message.date.strftime(DATETIME_FORMAT)),
        }],
    }
    response = requests.post(f'{MAIN_HOST}/phrase-meta/', json=data, headers=HEADERS)
    log.info(f'Response status: {response.status_code}')

    if not response.ok:
        log.error(response.text)
        return False

    model = PhraseMetaList.parse_raw(response.text)

    if not len(getattr(model, model._table_name)):
        log.info('Empty response.')
        return False

    for item in model.scan():
        redis_key = prepare_redis_key(item.id, message_id, message_date)
        log.info(redis_key)

        bin_data = await event.download_media(file=bytes)
        redis_client.set(redis_key, bin_data)

    return True


@bot.on(events.NewMessage(pattern='/[csftl]'))
async def handler_client_query_pl(event):
    message = event.message.message
    key = message[1]
    log.info(message)

    is_valid, params = eval(f'_{key}_validator')(message)
    if not is_valid:
        return await event.reply('Bad Query!')

    api_url = f'{MAIN_HOST}/phrase-pl/{COMMAND_URL_MAPPING[key]}'
    response = requests.get(api_url, params=params, headers=HEADERS)

    if not response.ok:
        return await event.reply('Server Error!')

    model = PhrasePlList.parse_raw(response.text)

    if not (len_items := len(getattr(model, model._table_name))):
        return await event.reply('Not Found!')

    for index, item in enumerate(model.scan(), 1):
        html_string = _prepare_html(item, index, len_items)
        await event.respond(html_string, parse_mode='html')

    return True


def _prepare_html(item, index, count):
    target = _rebuild_string(item.target, item.target_mask)
    translate = _rebuild_string(item.translate, item.translate_mask)

    head = f'{item.id} ({index}/{count})'
    target_format = f'{TARGET_EMOJI}\t\t{target}'
    translate_format = f'{TRANSLATE_EMOJI}\t\t<i>{translate}</i>'

    return f'{head}\n\n{target_format}\n\n{translate_format}'


def _rebuild_string(sentence, mask):
    string = ''
    for flag, word in zip(mask, sentence.split()):
        if int(flag):
            word = f'<u>{word}</u>'
        string += f'{word} '
    return string


def _c_validator(query):
    is_valid = True
    query_split = query.split()
    target = query_split[-1]

    if len(query_split) == 1:
        target = 3
    elif len(query_split) > 2:
        is_valid = False
    elif not target.isdigit():
        is_valid = False

    return is_valid, dict(count=target)


def _l_validator(query):
    is_valid = True
    query_split = query.split()
    target = query_split[-1]

    if len(query_split) == 1:
        target = 3
    elif len(query_split) > 2:
        is_valid = False
    elif not target.isdigit():
        is_valid = False

    return is_valid, dict(count=target, tail=100)


def _s_validator(query):
    query_split = query.split(maxsplit=1)

    if len(query_split) < 2:
        return False, {}

    is_valid = True
    target_split = query_split[-1].split(':', maxsplit=1)

    since_id = target_split[0]
    count = target_split[-1] if len(target_split) == 2 else 10

    if not since_id.isdigit():
        is_valid = False
    if not count.isdigit():
        is_valid = False

    return is_valid, dict(since_id=since_id, count=count)


def _f_validator(query):
    query_split = query.split(maxsplit=1)

    if len(query_split) < 2:
        return False, {}

    return True, dict(tag=query_split[-1])


def _t_validator(query):
    return _f_validator(query)


if __name__ == '__main__':
    bot.start(bot_token=BOT_TOKEN)
    try:
        bot.run_until_disconnected()
    except KeyboardInterrupt:
        redis_client.close()
        raise
