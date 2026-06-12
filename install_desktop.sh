#!/bin/bash
# install_desktop.sh — Buat shortcut desktop untuk My AI CLI (Linux/GNOME/KDE)

DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_FILE="$HOME/.local/share/applications/my-ai-cli.desktop"
DESKTOP_DIR_FILE="$HOME/Desktop/my-ai-cli.desktop"

mkdir -p "$HOME/.local/share/applications"

cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=My AI CLI
Comment=AI Assistant dengan Live2D Avatar
Exec=bash -c "cd '$DIR' && ./run.sh"
Path=$DIR
Terminal=false
Icon=utilities-terminal
Categories=Utility;Development;
EOF

chmod +x "$DESKTOP_FILE"
chmod +x "$DIR/run.sh"

if [ -d "$HOME/Desktop" ]; then
    cp "$DESKTOP_FILE" "$DESKTOP_DIR_FILE"
    chmod +x "$DESKTOP_DIR_FILE"
    gio set "$DESKTOP_DIR_FILE" metadata::trusted true 2>/dev/null || true
fi

echo "✅ Shortcut dibuat:"
echo "   - $DESKTOP_FILE"
[ -f "$DESKTOP_DIR_FILE" ] && echo "   - $DESKTOP_DIR_FILE"
echo ""
echo "Sekarang 'My AI CLI' bisa dicari di menu aplikasi, atau klik 2x di Desktop."