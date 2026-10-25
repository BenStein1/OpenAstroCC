#!/usr/bin/env bash
# Build an x86_64 Astro A50 Linux AppImage from the source checkout.
# Requires Linux, Python 3.11+, PyQt6, PyInstaller, curl and appimagetool.
set -e
cd "$(dirname "$0")/.."
root="$PWD"
appdir="$root/dist/AppDir"
tool="$root/build/appimagetool-x86_64.AppImage"

if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
    echo "This build currently supports Linux x86_64 only." >&2
    exit 2
fi

python3 -c 'from PyQt6.QtWidgets import QApplication; import PyInstaller'
mkdir -p build dist
python3 -m PyInstaller \
    --noconfirm --clean --onedir --windowed \
    --contents-directory _internal \
    --name astro-a50-linux \
    --paths tools \
    --hidden-import a50_setup \
    --add-data presets:presets \
    --add-data docs/THIRD_PARTY_NOTICES.md:docs \
    --add-data LICENSE:licenses \
    --add-data licenses:licenses \
    --distpath dist/pyinstaller \
    --workpath build/pyinstaller \
    --specpath build \
    tools/a50_gui.py

rm -rf "$appdir"
mkdir -p "$appdir/usr/lib" "$appdir/usr/share/doc/astro-a50-linux" \
         "$appdir/usr/share/icons/hicolor/256x256/apps"
cp -a dist/pyinstaller/astro-a50-linux "$appdir/usr/lib/"
cp LICENSE "$appdir/usr/share/doc/astro-a50-linux/LICENSE"
cp docs/THIRD_PARTY_NOTICES.md "$appdir/usr/share/doc/astro-a50-linux/"
cp -a licenses "$appdir/usr/share/doc/astro-a50-linux/"
python3 scripts/collect_bundle_licenses.py "$appdir/usr/share/doc/astro-a50-linux/third-party"

# Render the same app icon the GUI already uses.
QT_QPA_PLATFORM=offscreen python3 - <<'PY'
import sys
sys.path.insert(0, "tools")
from PyQt6.QtWidgets import QApplication
from a50_gui import make_icon
app = QApplication([])
if not make_icon().pixmap(256, 256).save("dist/AppDir/usr/share/icons/hicolor/256x256/apps/astro-a50-linux.png"):
    raise RuntimeError("Could not render app icon")
PY

cp packaging/astro-a50-linux.desktop "$appdir/astro-a50-linux.desktop"
ln -s usr/share/icons/hicolor/256x256/apps/astro-a50-linux.png "$appdir/astro-a50-linux.png"
ln -s astro-a50-linux.png "$appdir/.DirIcon"

cat > "$appdir/AppRun" <<'APP_RUN'
#!/bin/sh
APPDIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
unset PYTHONHOME PYTHONPATH PYTHONUSERBASE QT_PLUGIN_PATH QT_QPA_PLATFORM_PLUGIN_PATH
exec "$APPDIR/usr/lib/astro-a50-linux/astro-a50-linux" "$@"
APP_RUN
chmod +x "$appdir/AppRun"
chmod +x "$appdir/usr/lib/astro-a50-linux/astro-a50-linux"

if [ -n "$APPIMAGETOOL" ]; then
    tool="$APPIMAGETOOL"
elif [ ! -f "$tool" ]; then
    curl -fL --retry 3 \
      https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage \
      -o "$tool"
    chmod +x "$tool"
fi
# AppImage bundling tool can run without FUSE in CI.
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 "$tool" "$appdir" \
    "$root/dist/Astro-A50-Linux-x86_64.AppImage"
sha256sum dist/Astro-A50-Linux-x86_64.AppImage > dist/Astro-A50-Linux-x86_64.AppImage.sha256
printf 'AppImage built at %s\n' "$root/dist/Astro-A50-Linux-x86_64.AppImage"
