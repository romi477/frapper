# python3

import json
from envparse import Env


with open('frapper/config.json', 'r') as f:
    config = json.loads(f.read())
    env_file_path = config.pop('env_file')

Env.read_envfile(env_file_path, **config)
env = Env()

FRAPPER_ID = env.int('TG_FRAPPER_ID')
PHRASES_ID = env.int('TG_PHRASES_ID')

TG_API_ID = env.int('TG_API_ID')
TG_API_HASH = env.str('TG_API_HASH')
BOT_TOKEN = env.str('FRAPPER_BOT_TOKEN')
API_URL = env.str('FRAPPER_API_URL', default='http://localhost:8000')
