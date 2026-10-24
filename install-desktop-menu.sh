#!/usr/bin/env bash
# Adds MormorsFilDammsugare to the KDE Plasma Application Menu on SteamOS Desktop
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
MENU_ENTRY="$HOME/.local/share/applications/mormors-fildammsugare.desktop"

mkdir -p "$(dirname "$MENU_ENTRY")"
cat > "$MENU_ENTRY" <<DESKTOP
[Desktop Entry]
Type=Application
Name=MormorsFilDammsugare
Comment=Native Linux Backup Triage & File Vacuum Suite
Exec="$DIR/mormor" gui
Icon=utilities-file-archiver
Terminal=false
Categories=Utility;Archiving;System;
DESKTOP

chmod +x "$MENU_ENTRY"
echo "✓ Installed application menu entry at: $MENU_ENTRY"
echo "You can now launch MormorsFilDammsugare from the KDE Application Launcher!"
