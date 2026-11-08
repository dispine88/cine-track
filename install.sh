#!/usr/bin/env bash

# absolute path to this script
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

DESKTOP_DIR="$HOME/.local/share/applications"
BIN_DIR="$HOME/.local/bin"

echo "Installing CineTrack in $DIR..."

# creating folders
mkdir -p "$DESKTOP_DIR"
mkdir -p "$BIN_DIR"

# 1. creating launch script
cat << LAUNCHER > "$BIN_DIR/cinetrack"
#!/usr/bin/env bash
cd "$DIR"
exec nix-shell --run "python main.py"
LAUNCHER

# making him executable
chmod +x "$BIN_DIR/cinetrack"

# 2. creating label (.desktop)
cat << DESKTOP > "$DESKTOP_DIR/cinetrack.desktop"
[Desktop Entry]
Name=CineTrack
Comment=Local Media Tracker
Exec=$BIN_DIR/cinetrack
Icon=video-x-generic
Terminal=false
Type=Application
Categories=AudioVideo;Player;
DESKTOP

echo "Success! CineTrack is added to your applications menu."
echo "You can also run it from the terminal with the command: cinetrack"
