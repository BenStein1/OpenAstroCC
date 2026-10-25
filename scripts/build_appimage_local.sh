#!/usr/bin/env bash
# One-command local AppImage build, without installing packages system-wide.
set -e
cd "$(dirname "$0")/.."
mkdir -p build
if [ ! -x build/appimage-venv/bin/python ]; then
    python3 -m venv build/appimage-venv
fi
build/appimage-venv/bin/python -m pip install \
    'PyQt6==6.9.1' 'pyinstaller==6.16.0'
PATH="$PWD/build/appimage-venv/bin:$PATH" bash scripts/build_appimage.sh
