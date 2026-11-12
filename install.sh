#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_DIR="$HOME/.local/share/applications"
BIN_DIR="$HOME/.local/bin"
mkdir -p "$DESKTOP_DIR" "$BIN_DIR"

cat > "$BIN_DIR/cinetrack" <<LAUNCHER
#!/usr/bin/env bash
set -e
DIR="$DIR"
cd "\$DIR"
if [ -x "\$DIR/.venv/bin/python" ]; then
    exec "\$DIR/.venv/bin/python" "\$DIR/main.py" "\$@"
elif [ -e /etc/NIXOS ] && command -v nix-shell >/dev/null 2>&1; then
    exec nix-shell "\$DIR/shell.nix" --run "python '\$DIR/main.py'"
else
    exec python3 "\$DIR/main.py" "\$@"
fi
LAUNCHER
chmod +x "$BIN_DIR/cinetrack"

cat > "$DESKTOP_DIR/cinetrack.desktop" <<DESKTOP
[Desktop Entry]
Name=CineTrack
Comment=Local Media Tracker
Exec="$BIN_DIR/cinetrack"
Icon=video-x-generic
Terminal=false
Type=Application
Categories=AudioVideo;Player;
DESKTOP

echo "CineTrack launcher installed: $BIN_DIR/cinetrack"
