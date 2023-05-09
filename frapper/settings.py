# python3

import json
from envparse import Env


with open('frapper/config.json', 'r') as f:
    config = json.loads(f.read())
    env_file_path = config.pop('env_file')

Env.read_envfile(env_file_path, **config)
env = Env()

FRAPPER_ID = env.int('tg_frapper_id')
PHRASE_PL_ID = env.int('tg_phrase_pl_id')

TG_API_ID = env.int('tg_api_id')
TG_API_HASH = env.str('tg_api_hash')
BOT_TOKEN = env.str('frapper_bot_token')

API_URL = env.str('frapper_api_url', default='http://localhost:8000')
FRAPPER_DB = env.str('frapper_db', default='frapper.db')
