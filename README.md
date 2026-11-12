# CineTrack

CineTrack is a local desktop media-library manager built with Python and PyQt5. It scans folders for video files, cleans filenames, searches TMDB for metadata and posters, and stores library metadata in SQLite.

![CineTrack Screenshot](image.png)

## Features

- Recursive scan of `.mkv`, `.mp4`, `.avi`, and `.webm` files.
- TMDB search for movie and TV metadata, with local poster cache.
- Compact Settings window for TMDB and qBittorrent credentials.
- Optional qBittorrent Web UI integration.
- RU/EN interface, custom dark theme, and playback through the system player.
- CSV export of the local library.
- SQLite storage with `titles`, `genres`, `title_genres`, and `reviews` tables.
- Keyring-backed storage for API keys and qBittorrent passwords.

## Architecture

```text
main.py              application entry point and first-run setup
gui/
  mainwindow.py      main window and user actions
  dialogs.py        first-run setup, search, input and message dialogs
  settings_dialog.py compact settings editor
  workers.py        scanning, TMDB, poster, CSV and qBittorrent tasks
database/
  db.py              SQLite connection, schema and version
  crud.py            parameterized CRUD operations
config.py            paths, JSON preferences and Keyring
style.qss            application theme
```

Folder scanning, TMDB requests, poster downloads, CSV export, and qBittorrent requests run in the Qt thread pool so the interface stays responsive. SQLite writes use transactions; connections enable foreign keys, a busy timeout, and WAL mode.

## Requirements

- Python 3.10+
- Packages in `requirements.txt`
- An operating-system credential manager supported by Keyring
- Optional: TMDB API key for remote metadata and posters
- Optional: qBittorrent Web UI for the integration

## Run from source

### Windows

```powershell
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
py main.py
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

MPV is used for playback on Linux when available; otherwise CineTrack falls back to `xdg-open`. The optional desktop launcher is installed with `chmod +x install.sh && ./install.sh`.

## Configuration and secrets

The first-run Setup Wizard collects initial preferences. After that, Settings edits the TMDB API key and qBittorrent host, port, username, and password in one window. Secret values are stored through Keyring; ordinary preferences are stored in `settings.json`. In a source checkout only, `config.py` can read `TMDB_API_KEY` from an ignored `.env` file. Do not commit `.env` or real API keys.

CineTrack remains usable without TMDB: local scanning, library storage, playback, and CSV export do not require an API key or network access.

## Tests

```bash
python -m compileall -q .
python -m unittest discover -s tests -v
```

## Build the Windows installer

Build on Windows; PyInstaller is not a cross-compiler.

1. Install Python 3.10+ and Inno Setup.
2. Run `build.bat`. It compiles the Python source, runs the SQLite tests, installs build dependencies, and creates `dist\\CineTrack`.
3. Run `build_setup.bat`, or open `installer.iss` in Inno Setup and compile it with F9. The installer is written to `Output`.

PyInstaller uses `onedir`; Inno Setup packages the entire directory, including the executable and its dependencies, into `Output\CineTrack_Setup.exe`. The installer script targets 64-bit Windows.

## License

MIT License. See [LICENSE](LICENSE).
