# CineTrack

**CineTrack** is a local media library manager with TMDB integration, built with Python and PyQt5.

![CineTrack Screenshot](image.png)

## Features
- Scan local folders for movies and TV shows.
- Automatic poster and release year fetching from TMDB.
- qBittorrent Web UI integration for tracking downloads.
- Multilingual interface (RU/EN).
- Custom frameless theme via QSS.
- Built-in video playback (via MPV).
- Built-in setup wizard for easy configuration.

## Tech Stack & Architecture
- **Language:** Python 3.10+
- **GUI:** PyQt5
- **Database:** SQLite + SQLAlchemy
- **Architecture:** Modular MVC-like structure (`gui/`, `database/`, `config.py`).

## Installation (Windows)
1. Go to the [Releases](https://github.com/dispine88/cine-track/releases) page.
2. Download the latest `CineTrack_Setup.exe`.
3. Run the installer and launch the app.
4. Follow the Setup Wizard to choose your language, enter your TMDB API key, and configure qBittorrent.

## Linux / NixOS (Dev Mode)
1. Clone the repository:
    ```bash
    git clone https://github.com/dispine88/cine-track.git
    cd cine-track
    ```
2. Run the installer:
    ```bash
    ./install.sh
    ```
3. Launch via terminal: 
    ```bash
    cinetrack
    ``` 
Or through app menu (API key will be requested on first launch).

---
*Made with love for cinema and code.*