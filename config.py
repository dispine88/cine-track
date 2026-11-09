import os
import sys
import json
import keyring
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

SERVICE_NAME = "CineTrack"

TMDB_API_KEY = ""
QBIT_PASS = ""

if os.path.exists(SETTINGS_FILE):
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings_data = json.load(f)
            
        migrated = False
        
        if "tmdb_api_key" in settings_data and settings_data["tmdb_api_key"]:
            keyring.set_password(SERVICE_NAME, "tmdb_api_key", settings_data["tmdb_api_key"])
            del settings_data["tmdb_api_key"]
            migrated = True
            
        if "qbit_pass" in settings_data and settings_data["qbit_pass"]:
            keyring.set_password(SERVICE_NAME, "qbit_pass", settings_data["qbit_pass"])
            del settings_data["qbit_pass"]
            migrated = True
            
        if migrated:
            with open(SETTINGS_FILE, 'w') as f:
                json.dump(settings_data, f, indent=4)
            print("[KEYRING] Секреты успешно перенесены в системное хранилище.")
            
    except Exception as e:
        print(f"[KEYRING] Ошибка при миграции: {e}")

try:
    TMDB_API_KEY = keyring.get_password(SERVICE_NAME, "tmdb_api_key") or ""
    QBIT_PASS = keyring.get_password(SERVICE_NAME, "qbit_pass") or "adminadmin"
except Exception:
    pass

if not TMDB_API_KEY:
    load_dotenv(os.path.join(APP_DIR, '.env'))
    load_dotenv()
    TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

if not TMDB_API_KEY:
    print(f"\n[WARNING] API ключ TMDB не найден.")
    print(f"[WARNING] Пожалуйста, создайте файл .env по этому пути: {os.path.join(APP_DIR, '.env')}")
    print(f"[WARNING] И добавьте туда строку: TMDB_API_KEY=твой_ключ\n")