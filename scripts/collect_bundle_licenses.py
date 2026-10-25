#!/usr/bin/env python3
"""Include exact licensing metadata for installed packages in AppImage.

All files are copied verbatim from the wheel's installed distribution.
This complements the human-readable THIRD_PARTY_NOTICES and full SPDX texts.
"""
from importlib import metadata
from pathlib import Path
import shutil
import sys

dest = Path(sys.argv[1])
dest.mkdir(parents=True, exist_ok=True)
packages = ("PyQt6", "PyQt6-Qt6", "PyQt6-sip", "pyinstaller")
manifest = ["# Bundled component manifest", "", "Captured at build time.", ""]
for name in packages:
    try:
        dist = metadata.distribution(name)
    except metadata.PackageNotFoundError:
        if name != "pyinstaller":
            raise
        continue
    label = dist.metadata.get("Name", name)
    manifest.append(f"- {label} {dist.version} — {dist.metadata.get('License-Expression') or dist.metadata.get('License') or 'see notices'}")
    installed = 0
    for path in dist.files or []:
        lowered = str(path).lower().replace("\\", "/")
        basename = Path(str(path)).name.lower()
        legal = (
            (".dist-info/" in lowered and basename.startswith(("license", "copying", "notice")))
            or "/licenses/" in lowered
            or basename in ("copying.txt", "copyright.txt")
        )
        if not legal:
            continue
        origin = Path(dist.locate_file(path))
        if not origin.is_file() or origin.stat().st_size > 2_000_000:
            continue
        item = dest / label / str(path).replace("\\", "/")
        item.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(origin, item)
        installed += 1
    manifest.append(f"  License/notice files included: {installed}")
    if name in ("PyQt6", "PyQt6-Qt6") and installed == 0:
        # The full project GPL and Qt LGPL texts are still in /licenses.
        manifest.append("  NOTE: no wheel notice files exposed; see complete LICENSE / LGPL texts.")
(dest / "BUNDLED-COMPONENTS.md").write_text("\n".join(manifest) + "\n", encoding="utf-8")
