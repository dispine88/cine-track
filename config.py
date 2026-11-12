"""Application paths, settings and secret loading for CineTrack."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import keyring
    from keyring.errors import PasswordDeleteError
except ImportError:  # Keep local database tools usable without the optional runtime extra.
    keyring = None

    class PasswordDeleteError(Exception):
        pass

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(*_args, **_kwargs):
        return False

SERVICE_NAME = "CineTrack"


def _application_dir() -> Path:
    if getattr(sys, "frozen", False):
        base = os.environ.get("APPDATA") or str(Path.home())
        return Path(base) / SERVICE_NAME
    return Path(__file__).resolve().parent


APP_DIR = _application_dir()
APP_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = APP_DIR / "settings.json"
CACHE_DIR = APP_DIR / ".cache_posters"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / "cinetrack.db"


def load_settings() -> dict[str, Any]:
    """Read settings; recover gracefully if the JSON file is malformed."""
    if not SETTINGS_FILE.exists():
        return {}
    try:
        with SETTINGS_FILE.open("r", encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data, dict):
            raise ValueError("Settings file must contain a JSON object")
        return data
    except (OSError, json.JSONDecodeError, ValueError):
        backup = SETTINGS_FILE.with_suffix(".json.corrupt")
        try:
            if backup.exists():
                backup.unlink()
            SETTINGS_FILE.replace(backup)
        except OSError:
            pass
        return {}


def save_settings(data: dict[str, Any]) -> None:
    """Atomically write non-secret settings to avoid truncated JSON files."""
    fd, temp_name = tempfile.mkstemp(prefix="settings_", suffix=".tmp", dir=APP_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, indent=4, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, SETTINGS_FILE)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def get_secret(name: str, default: str = "") -> str:
    try:
        return keyring.get_password(SERVICE_NAME, name) or default
    except Exception:
        return default


def set_secret(name: str, value: str) -> None:
    """Store a secret in Keyring, or remove it when an empty value is supplied."""
    if keyring is None:
        raise RuntimeError("The Keyring package is not installed")
    if value:
        keyring.set_password(SERVICE_NAME, name, value)
        return

    try:
        keyring.delete_password(SERVICE_NAME, name)
    except PasswordDeleteError:
        # The credential did not exist; this is already the desired state.
        pass


def reload_secrets() -> None:
    """Refresh module-level secrets after the user edits application settings."""
    global TMDB_API_KEY, QBIT_PASS

    settings = load_settings()
    allow_env_fallback = (
        not getattr(sys, "frozen", False)
        and not settings.get("tmdb_api_key_disabled", False)
    )
    env_key = os.getenv("TMDB_API_KEY", "") if allow_env_fallback else ""
    TMDB_API_KEY = get_secret("tmdb_api_key") or env_key
    QBIT_PASS = get_secret("qbit_pass")


def _migrate_legacy_secrets() -> None:
    """Move old plaintext secrets out of settings.json when Keyring is usable."""
    data = load_settings()
    changed = False
    for name in ("tmdb_api_key", "qbit_pass"):
        value = data.get(name)
        if value:
            try:
                keyring.set_password(SERVICE_NAME, name, str(value))
            except Exception:
                # Never remove a legacy value unless Keyring accepted it.
                continue
            data.pop(name, None)
            changed = True
    if changed:
        save_settings(data)


_migrate_legacy_secrets()

# Development fallback only. Packaged users should use the OS keyring.
if not getattr(sys, "frozen", False):
    load_dotenv(APP_DIR / ".env")

reload_secrets()
