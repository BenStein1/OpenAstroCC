#!/usr/bin/env bash
# Build an x86_64 OpenAstroCC AppImage from the source checkout.
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
    --paths "$root/tools" \
    --hidden-import a50_setup \
    --add-data "$root/presets:presets" \
    --add-data "$root/docs/THIRD_PARTY_NOTICES.md:docs" \
    --add-data "$root/LICENSE:licenses" \
    --add-data "$root/licenses:licenses" \
    --distpath "$root/dist/pyinstaller" \
    --workpath "$root/build/pyinstaller" \
    --specpath "$root/build" \
    "$root/tools/a50_gui.py"

# PyInstaller includes Qt xcb but misses optional system XCB libraries on
# minimal distributions (AppImageHub Xvfb/Ubuntu 22.04, for example).
python3 scripts/bundle_qt_xcb.py "$root/dist/pyinstaller/astro-a50-linux/_internal"

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
# AppImageLauncher on some desktops intercepts appimagetool itself and
# fails to read modern zstd-compressed AppImages. Suppress the integration UI;
# if the binfmt hook still prevents launch, extract via unsquashfs and run the
# extracted AppRun directly. Neither path modifies system AppImageLauncher.
output="$root/dist/OpenAstroCC-x86_64.AppImage"
if ! ARCH=x86_64 APPIMAGELAUNCHER_DISABLE=1 APPIMAGE_EXTRACT_AND_RUN=1 \
    "$tool" "$appdir" "$output"; then
    echo "AppImageLauncher may be intercepting appimagetool; trying extracted fallback." >&2
    if ! command -v unsquashfs >/dev/null 2>&1; then
        echo "Please install squashfs-tools (unsquashfs) to use the no-launcher fallback." >&2
        exit 2
    fi
    extracted="$root/build/appimagetool-extracted"
    offset="$(python3 scripts/appimage_offset.py "$tool")"
    rm -rf "$extracted"
    mkdir -p "$extracted"
    unsquashfs -no-progress -d "$extracted" -o "$offset" "$tool"
    if [ ! -x "$extracted/AppRun" ]; then
        echo "Extracted appimagetool has no executable AppRun." >&2
        exit 2
    fi
    APPDIR="$extracted" ARCH=x86_64 "$extracted/AppRun" "$appdir" "$output"
fi
test -s "$output"
(cd "$root/dist" && sha256sum OpenAstroCC-x86_64.AppImage > OpenAstroCC-x86_64.AppImage.sha256)
printf 'AppImage built at %s\n' "$output"
