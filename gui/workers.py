"""Background tasks used by the GUI to keep the Qt event loop responsive."""
from __future__ import annotations

import csv
import os
import re
import tempfile
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from PIL import Image, UnidentifiedImageError
from PyQt5.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

import config
from database import crud

VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".webm")


class WorkerSignals(QObject):
    result = pyqtSignal(object)
    error = pyqtSignal(str)
    finished = pyqtSignal(object)


class FunctionWorker(QRunnable):
    """Run a callable in QThreadPool and report results through Qt signals."""

    def __init__(self, function, *args, **kwargs):
        super().__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.job_id = id(self)
        self.signals = WorkerSignals()
        # Keep the Python wrapper alive until the GUI receives ``finished``.
        self.setAutoDelete(False)

    @pyqtSlot()
    def run(self):
        try:
            self.signals.result.emit(self.function(*self.args, **self.kwargs))
        except Exception as exc:  # UI receives a safe, non-secret-bearing error.
            self.signals.error.emit(type(exc).__name__)
        finally:
            self.signals.finished.emit(self.job_id)


def clean_filename(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    name = re.sub(r"\[.*?\]|\(.*?\)", "", name)
    name = name.replace("_", " ").replace(".", " ")
    return re.sub(r"\s+", " ", name).strip()


def scan_folder_task(folder: str) -> dict:
    """Scan a directory tree, consolidate legacy duplicates, and import new paths."""
    merged_rows = crud.merge_duplicate_file_paths()
    for old_id, kept_id in merged_rows:
        old_cache = Path(config.CACHE_DIR) / f"{old_id}.jpg"
        kept_cache = Path(config.CACHE_DIR) / f"{kept_id}.jpg"
        try:
            if old_cache.is_file():
                if not kept_cache.exists():
                    os.replace(old_cache, kept_cache)
                else:
                    old_cache.unlink(missing_ok=True)
        except OSError:
            # DB metadata is still consolidated; stale cache files are harmless.
            pass

    records = []
    walk_errors = []

    def record_error(error):
        walk_errors.append(str(error))

    for root, _dirs, files in os.walk(folder, onerror=record_error):
        for filename in files:
            if filename.lower().endswith(VIDEO_EXTENSIONS):
                full_path = os.path.abspath(os.path.join(root, filename))
                records.append({
                    "name": clean_filename(filename),
                    "type": "local",
                    "status": "want",
                    "file_path": full_path,
                })

    added = crud.add_titles_bulk(records)
    return {
        "found": len(records),
        "added": added,
        "merged_duplicates": len(merged_rows),
        "walk_errors": len(walk_errors),
    }


def search_tmdb_task(query: str, api_key: str) -> list[dict]:
    url = "https://api.themoviedb.org/3/search/multi"
    try:
        response = requests.get(
            url,
            params={"api_key": api_key, "query": query},
            timeout=(4, 12),
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise RuntimeError("TMDB request failed") from exc

    results = payload.get("results", [])
    # The multi-search endpoint also returns people; this app catalogues
    # movies and TV shows only.
    return [item for item in results if item.get("media_type") in ("movie", "tv")][:10]


def _year_from_result(result: dict):
    date_value = result.get("first_air_date") or result.get("release_date") or ""
    try:
        return int(date_value[:4]) if len(date_value) >= 4 else None
    except (TypeError, ValueError):
        return None


def download_posters_task(result: dict, title_ids: list[int]) -> dict:
    """Download one validated TMDB poster and apply its metadata to selected rows."""
    poster_path = result.get("poster_path")
    year = _year_from_result(result)
    poster_url = None

    if poster_path:
        # Never accept an arbitrary URL supplied by a result object.
        if not isinstance(poster_path, str) or not poster_path.startswith("/") or ".." in poster_path:
            raise RuntimeError("Invalid poster path")
        poster_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
        parsed = urlparse(poster_url)
        if parsed.scheme != "https" or parsed.hostname != "image.tmdb.org":
            raise RuntimeError("Untrusted poster host")

        try:
            with requests.get(
                poster_url,
                headers={"User-Agent": "CineTrack/1.0"},
                timeout=(4, 12),
                stream=True,
            ) as response:
                response.raise_for_status()
                declared_size = int(response.headers.get("Content-Length") or 0)
                max_size = 15 * 1024 * 1024
                if declared_size > max_size:
                    raise RuntimeError("Poster file is too large")
                payload = bytearray()
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    if chunk:
                        payload.extend(chunk)
                        if len(payload) > max_size:
                            raise RuntimeError("Poster file is too large")
            image_bytes = bytes(payload)
            with Image.open(BytesIO(image_bytes)) as probe:
                probe.verify()
            with Image.open(BytesIO(image_bytes)) as source:
                image = source.convert("RGB")
                image.thumbnail((1200, 1800), Image.Resampling.LANCZOS)
        except (requests.RequestException, UnidentifiedImageError, OSError, ValueError) as exc:
            raise RuntimeError("Poster download or image decoding failed") from exc

        os.makedirs(config.CACHE_DIR, exist_ok=True)
        for title_id in title_ids:
            target = Path(config.CACHE_DIR) / f"{int(title_id)}.jpg"
            fd, temp_name = tempfile.mkstemp(prefix=f"{int(title_id)}_", suffix=".jpg.tmp", dir=config.CACHE_DIR)
            os.close(fd)
            try:
                image.save(temp_name, format="JPEG", quality=90, optimize=True)
                os.replace(temp_name, target)
            finally:
                try:
                    if os.path.exists(temp_name):
                        os.remove(temp_name)
                except OSError:
                    pass

    updated = 0
    for title_id in title_ids:
        if crud.update_title_info(title_id, year=year, poster_url=poster_url):
            updated += 1
    return {"updated": updated, "poster_saved": bool(poster_url)}



def export_csv_task(file_path: str) -> int:
    """Write the library atomically in the background, preserving old exports."""
    target = Path(file_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    titles = crud.get_all_titles()
    fd, temporary_path = tempfile.mkstemp(
        prefix=f"{target.stem}_", suffix=".csv.tmp", dir=str(target.parent)
    )
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Name", "Year", "Type", "Status", "File Path"])
            for title in titles:
                writer.writerow([title.name, title.year, title.type, title.status, title.file_path])
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, target)
    except Exception:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise
    return len(titles)


def qbittorrent_task(settings: dict, password: str) -> list[str]:
    """Fetch torrent status with network timeouts; caller runs this off the UI thread."""
    import qbittorrentapi

    client = qbittorrentapi.Client(
        host=settings.get("qbit_host", "localhost"),
        port=int(settings.get("qbit_port", 8080)),
        username=settings.get("qbit_user", "admin"),
        password=password,
        REQUESTS_ARGS={"timeout": (3, 8)},
        DISABLE_LOGGING_DEBUG_OUTPUT=True,
    )
    try:
        torrents = client.torrents_info()
        return [
            f"[{round(float(torrent.progress) * 100, 1)}%] {torrent.name}"
            for torrent in torrents[:10]
        ]
    finally:
        try:
            client.auth_log_out()
        except Exception:
            pass
