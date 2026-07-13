#!/usr/bin/env bash
# Build a DeskBuddy .deb package (Linux) from a PyInstaller binary.
# Usage:  bash scripts/build-deb.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$HERE"

APP="deskbuddy"
VERSION="$(grep -m1 '^version' pyproject.toml | sed -E 's/.*"([0-9.]+)".*/\1/')"
ARCH="$(dpkg --print-architecture 2>/dev/null || echo amd64)"
PKG="${APP}_${VERSION}_${ARCH}"

echo ">> building PyInstaller binary..."
pip install -q '.[packaging]' 2>/dev/null || true
pyinstaller scripts/deskbuddy.spec --noconfirm

echo ">> assembling $PKG.deb ..."
rm -rf "dist/$PKG"
mkdir -p "dist/$PKG/usr/bin" "dist/$PKG/DEBIAN" "dist/$PKG/usr/share/applications"

cp "dist/buddy" "dist/$PKG/usr/bin/buddy"
chmod 755 "dist/$PKG/usr/bin/buddy"

cat > "dist/$PKG/DEBIAN/control" <<EOF
Package: $APP
Version: $VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Depends: python3, ffmpeg
Maintainer: King Jethro Jerry <kingjethro999@users.noreply.github.com>
Description: DeskBuddy - Alexa for your PC.
 A voice-powered desktop companion you install from the terminal.
 Say the wake word and a styled GUI runs your computer hands-off.
EOF

cat > "dist/$PKG/usr/share/applications/deskbuddy.desktop" <<EOF
[Desktop Entry]
Name=DeskBuddy
Exec=buddy
Terminal=false
Type=Application
Categories=Utility;
EOF

dpkg-deb --build "dist/$PKG"
echo ">> done: dist/$PKG.deb"
