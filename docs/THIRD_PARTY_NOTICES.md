# Third-party notices — Astro A50 Linux

This is a source-level acknowledgment list. Before publishing an AppImage,
add the full license texts and attribution notices for the **exact binaries
bundled** in that release. A source checkout and a packaged AppImage may
contain different third-party components.

Project source: https://github.com/BenStein1/astro-a50-linux
Project license: **not yet declared in a LICENSE file.**
Choose a license compatible with the PyQt6 distribution used before public
distribution; don't describe the project as licensed until this is done.

PyQt6 — Python Qt bindings
  Copyright © Riverbank Computing Limited.
  Open-source edition: GNU General Public License v3 (GPL-3.0);
  alternatively available under Riverbank commercial terms.
  https://riverbankcomputing.com/software/pyqt/

Qt 6 / Qt Widgets — application framework
  Copyright © The Qt Company Ltd. and other Qt contributors.
  The components used by the open-source PyQt6 wheels are generally
  licensed under LGPL-3.0/GPL-3.0, with module-specific terms.
  https://www.qt.io/licensing/open-source-lgpl-obligations
  https://doc.qt.io/qt-6/licensing.html

Python — language runtime and standard library
  Copyright © Python Software Foundation and contributors.
  Python Software Foundation License (PSF-2.0).
  https://docs.python.org/3/license.html

PipeWire — host Linux audio system (invoked; not bundled by source checkout)
  MIT license.
  https://gitlab.freedesktop.org/pipewire/pipewire

WirePlumber — PipeWire session manager (configured; not bundled by source checkout)
  MIT license.
  https://gitlab.freedesktop.org/pipewire/wireplumber

The Astro A50 name, original factory EQ settings and hardware/software
trademarks belong to their respective owners. This project is unofficial.

AppImage release checklist:
- Select and include the project's own license (PyQt6 GPL compatibility matters).
- Inventory **actual** versions/components bundled by the build process.
- Ship applicable complete license texts, notices, and required corresponding
  source/linking information for those bundled dependencies.
- Verify that original vendor preset redistribution is permitted.
