#!/usr/bin/env bash
# Adds MormorsFilDammsugare to the KDE Plasma Application Menu on SteamOS Desktop
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
MENU_ENTRY="$HOME/.local/share/applications/mormors-fildammsugare.desktop"
ICON_DIR_256="$HOME/.local/share/icons/hicolor/256x256/apps"
ICON_DIR_SCALABLE="$HOME/.local/share/icons/hicolor/scalable/apps"

if [ "$1" = "--remove" ] || [ "$1" = "--uninstall" ]; then
    rm -f "$MENU_ENTRY"
    rm -f "$ICON_DIR_256/mormors-fildammsugare.png"
    rm -f "$ICON_DIR_SCALABLE/mormors-fildammsugare.svg"
    echo "✓ Removed MormorsFilDammsugare desktop entry and icons."
    exit 0
fi

# 1. Install application icons
mkdir -p "$ICON_DIR_256" "$ICON_DIR_SCALABLE"
if [ -f "$DIR/mormorsfildammsugare/gui/assets/mormors-fildammsugare.png" ]; then
    cp "$DIR/mormorsfildammsugare/gui/assets/mormors-fildammsugare.png" "$ICON_DIR_256/mormors-fildammsugare.png"
fi
if [ -f "$DIR/mormorsfildammsugare/gui/assets/mormors-fildammsugare.svg" ]; then
    cp "$DIR/mormorsfildammsugare/gui/assets/mormors-fildammsugare.svg" "$ICON_DIR_SCALABLE/mormors-fildammsugare.svg"
fi

# 2. Install desktop entry
mkdir -p "$(dirname "$MENU_ENTRY")"
cat > "$MENU_ENTRY" <<DESKTOP
[Desktop Entry]
Type=Application
Name=MormorsFilDammsugare
GenericName=Backup Triage & File Vacuum Suite
Comment=Extract, deduplicate, categorize, privacy-audit, and clean backup dumps
Exec="$DIR/mormor" gui
Icon=mormors-fildammsugare
Terminal=false
Categories=Utility;Archiving;System;Filesystem;
Keywords=backup;photos;sorter;deduplicate;documents;privacy;czkawka;cleaner;
StartupWMClass=MormorsFilDammsugare
DESKTOP

chmod +x "$MENU_ENTRY"

# 3. Refresh desktop databases if utilities exist
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
fi

echo "✓ Successfully installed MormorsFilDammsugare into KDE Plasma Application Launcher!"
echo "  • Desktop Entry: $MENU_ENTRY"
echo "  • Icon: $ICON_DIR_256/mormors-fildammsugare.png"
echo "You can now search for 'MormorsFilDammsugare' in the SteamOS start menu."
