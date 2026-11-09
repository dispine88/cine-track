# CineTrack

**CineTrack** is a powerful, locally-hosted media library manager built with Python and PyQt5. It is designed for movie and anime enthusiasts who want to keep their local files organized, visually appealing, and easily accessible.

![CineTrack Screenshot](image.png)

## Features
- **Smart Local Scanning:** Automatically scans folders for video files (`.mkv`, `.mp4`, `.avi`, `.webm`) and cleans up filenames.
- **TMDB Integration:** Fetches official movie/show posters and release years directly from The Movie Database.
- **qBittorrent Support:** Connects to your local qBittorrent client to track active downloads (optional).
- **Custom Modern UI:** A fully custom, frameless dark-mode interface with QSS styling.
- **Multilingual:** Full support for English and Russian languages.
- **Built-in Player:** Double-click any movie to instantly play it (via MPV on Linux or default player on Windows).
- **Setup Wizard:** A smooth onboarding process to configure your API key, language, and torrent client.

## Security & Architecture
- **Secure Secrets:** API keys and passwords are encrypted and stored in your OS's native credential manager (via Python `keyring`), never in plain-text files.
- **Modular Codebase:** Clean MVC-like structure (`gui/`, `database/`, `config.py`) for maximum maintainability.
- **Path Validation:** Strict checks prevent arbitrary code execution when launching video files.

## Tech Stack
- **Language:** Python 3.10+
- **GUI:** PyQt5 (Qt5)
- **Database:** SQLite + SQLAlchemy
- **Security:** Keyring, Python-dotenv
- **Installer:** Inno Setup (Windows)

## Installation (Windows)
1. Go to the [Releases](https://github.com/dispine88/cine-track/releases) page.
2. Download the latest `CineTrack_Setup.exe`.
3. Run the installer and launch the app.
4. Follow the Setup Wizard *(You will need a free TMDB API key to fetch posters)*.

### Linux (General: Ubuntu, Arch, Fedora, etc.)
*Note: Make sure you have Python 3.10+, `pip`, and `mpv` installed on your system. Also, ensure you have a Secret Service provider (like `gnome-keyring` or `kwallet`) running for the secure keyring storage to work.*

1. Clone the repository:
    ```bash
    git clone https://github.com/dispine88/cine-track.git
    cd cine-track
    ```
2. Create a virtual environment and install dependencies:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```
3. Run the application:
    ```bash
    python main.py
    ```
4. (Optional) Create a desktop shortcut:
    ```bash
    chmod +x install.sh
    ./install.sh
    ```

### ❄️ NixOS
1. Clone the repository:
    ```bash
    git clone https://github.com/dispine88/cine-track.git
    cd cine-track
    ```
2. Run inside the Nix environment:
    ```bash
    nix-shell --run "python main.py"
    ```
3. (Optional) Install the desktop shortcut:
    ```bash
    chmod +x install.sh
    ./install.sh
    ```

## License
This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

---
*Made with love for cinema and code.*