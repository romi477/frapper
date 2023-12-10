# python3

import os
import json
import logging

from envparse import Env


with open('frapper/config.json', 'r') as f:
    config = json.loads(f.read())
    env_file_path = config.pop('env_file')

Env.read_envfile(env_file_path)
env = Env()

FRAPPER_ID = env.int('tg_frapper_id')
PHRASE_PL_ID = env.int('tg_phrase_pl_id')

TG_API_ID = env.int('tg_api_id')
TG_API_HASH = env.str('tg_api_hash')
BOT_TOKEN = env.str('frapper_bot_token')

MAIN_HOST = config.get('frapper_main_host', 'http://localhost:8000')
FRAPPER_DB = config.get('frapper_db', 'frapper.db')
REDIS_PORT = config.get('redis_port', 6379)
REDIS_DB = config.get('redis_db', 6379)

HEADERS = {
    'Content-Type': 'application/json',
    'User-Agent': 'TelegramBot/0.1.0',
}


log_format = '%(asctime)s %(name)s %(levelname)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=log_format)
log = logging.getLogger('frapper')

if not os.path.exists(log_dir := config['log_dir']):
    os.makedirs(log_dir)
