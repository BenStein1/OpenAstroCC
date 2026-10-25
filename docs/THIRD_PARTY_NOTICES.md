# OpenAstroCC — licenses and third-party notices

**Copyright © 2026 Benjamin Conner and contributors.**

**OpenAstroCC application source code:** **GNU General Public License
version 3 only (GPL-3.0-only)**. The complete terms are in the repository's
[LICENSE](../LICENSE) and bundled as `licenses/LICENSE`. Source is available
at https://github.com/BenStein1/OpenAstroCC. The license permits copying,
modification and redistribution, including commercial uses, on its terms.
**There is no warranty or obligation to provide support.**

This unofficial project is not affiliated with or endorsed by Astro Gaming
or Logitech. Brand names are the property of their respective owners.

## Components in the Linux AppImage

The AppImage bundles the following dependencies. Their precise versions,
installed distribution names and verbatim wheel-provided copyright/license
files are included in
`usr/share/doc/astro-a50-linux/third-party/BUNDLED-COMPONENTS.md` and
neighboring directories **inside the AppImage**.

| Component | Copyright / attribution | License | Terms provided |
|---|---|---|---|
| **PyQt6** | © Riverbank Computing Limited | GPL-3.0-only (open-source edition) | Full application GPL-3.0-only text in `LICENSE`, plus wheel license files |
| **PyQt6-sip** | © Riverbank Computing Limited | GPL-3.0-only (open-source edition) | GPL-3.0-only and wheel license files |
| **Qt 6** (libraries and plugins bundled by the PyQt6-Qt6 wheel) | © The Qt Company Ltd. and individual Qt contributors | LGPL-3.0 / GPL-3.0 as applicable; some subcomponents have additional terms | `licenses/LGPL-3.0-only.txt`, `licenses/LICENSE`, plus Qt wheel license files |
| **Python 3** runtime/stdlib | © Python Software Foundation and contributors | Python Software Foundation License 2.0 and included historical licenses | `licenses/Python-2.0.txt` and upstream Python distribution license |
| **PyInstaller bootloader** | © PyInstaller Development Team, Giovanni Bajo and earlier contributors | GPL-2.0-or-later with Bootloader Exception | `licenses/PyInstaller-COPYING.txt` |
| **Qt's additional third-party libraries** | Their respective upstream contributors | Per-component terms listed in Qt license files | Verbatim Qt wheel license files included from the installed build packages |

**Qt LGPL compliance:** Qt is shipped as separate dynamically loaded shared
libraries inside the AppImage. Users can extract the AppImage
(`--appimage-extract`), inspect or replace these libraries and rebuild the
AppImage. This project does not prohibit reverse engineering needed to debug
changes to LGPL-covered Qt libraries. The application source and build scripts
are published in the linked repository.

Sources: [Riverbank PyQt license](https://www.riverbankcomputing.com/software/pyqt),
[Riverbank license FAQ](https://riverbankcomputing.com/commercial/license-faq),
[Qt licensing](https://doc.qt.io/qt-6/licensing.html),
[Python license](https://docs.python.org/3/license.html),
[PyInstaller license](https://pyinstaller.org/en/stable/license.html).

## Host services (not bundled into the AppImage)

- **PipeWire:** © PipeWire contributors, MIT-licensed:
  https://gitlab.freedesktop.org/pipewire/pipewire
- **WirePlumber:** © WirePlumber contributors, MIT-licensed:
  https://gitlab.freedesktop.org/pipewire/wireplumber
- **ALSA / Linux USB/HID and system utilities:** supplied by the user's
  distribution under each component's own terms. The application detects
  and configures them but does not redistribute them in its source tree.

For convenience a full MIT license text is included in
`licenses/MIT.txt`; it does not override the licenses of these projects.

## Original Astro EQ profiles

The five original Astro `.astroeq` defaults are vendor-authored preset
data, separate from the GPL-licensed application source. The custom
`Bass & Clarity.astroeq` preset is a new user-derived example. The Astro
brand, firmware, original Windows application binaries and driver files are
**not** licensed by the application GPL. Confirm redistribution rights for
vendor-authored presets before any public release; do not infer permission
solely because their values are human-readable.

## AppImage build records

The GitHub Actions packaging workflow records the exact dependency versions
and includes the full project GPL text, Qt LGPL and third-party legal notices
in the executable archive. The build scripts and actions workflow are public
source when this repository is made public. A source checkout uses the host's
Qt/Python installation, so its *installed* third-party versions can differ
from those in the binary AppImage.

The AppImage is free software and comes **WITHOUT ANY WARRANTY**, as described
in GPLv3 sections 15–17. Users and downstream maintainers are responsible for
their own headset configuration and audio routing.
