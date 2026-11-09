import os
import sys
import json
from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    appdata = os.getenv('APPDATA')
    APP_DIR = os.path.join(appdata, "CineTrack")
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

os.makedirs(APP_DIR, exist_ok=True)

SETTINGS_FILE = os.path.join(APP_DIR, 'settings.json')
CACHE_DIR = os.path.join(APP_DIR, ".cache_posters")
os.makedirs(CACHE_DIR, exist_ok=True)

# 1. Пытаемся загрузить из .env (для разработки)
load_dotenv(os.path.join(APP_DIR, '.env'))
load_dotenv()

TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

# 2. Если есть settings.json, берем ключ оттуда (приоритет)
if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, 'r') as f:
            data = json.load(f)
            if data.get("tmdb_api_key"):
                TMDB_API_KEY = data["tmdb_api_key"]
    except Exception:
        pass