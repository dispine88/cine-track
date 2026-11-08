# CineTrack

**CineTrack** is a local media library manager with TMDB and qBittorrent integration.

![CineTrack Screenshot](image.png)

## Features
- Scan local folders for movies and TV shows.
- Automatic poster and release year fetching from TMDB.
- qBittorrent Web UI integration for tracking downloads.
- Multilingual interface (RU/EN).
- Custom theme via QSS (supports any CSS styles).
- Built-in video playback (via MPV).

## Requirements
- **OS:** Linux (NixOS recommended, as the project uses shell.nix).
- **Nix package manager** (for automatic dependency installation).
- **MPV** (for video playback).
- **Python 3.10+** (installed automatically via Nix).

## Installation

1. Clone the repository:
    
    ```bash
    git clone https://github.com/dispine88/cine-track.git
    cd cine-track
    ```

2. Run the installer (it will create a shortcut in the app menu):
    
    ```bash
    ./install.sh
    ```

3. Create a .env file in the project folder and mandatory add your TMDB API key (https://www.themoviedb.org/):
    
    ```bash
    TMDB_API_KEY=your_key_here
    ```

4. Launch **CineTrack** from the app menu or via terminal:
    
    ```bash
    cinetrack
    ```

---
*Made with love for cinema and code.*