#!/usr/bin/env python3
"""Bundle the XCB helper libraries Qt needs on minimally provisioned X11 hosts.

PyInstaller collects Qt's platform plugin, but many of its system XCB helper
libraries are intentionally left on the host. A clean Ubuntu/Xvfb environment
then aborts before opening the window (e.g. missing libxcb-icccm.so.4).

Copy the non-core XCB/XKB libraries resolved by the actual bundled Qt xcb
plugin into PyInstaller's _internal directory (already in its runtime library
search path). Keep libc, libX11, core libxcb, OpenGL drivers, etc. on the host.
Build distribution AppImages on the oldest supported Ubuntu runner.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HELPER = re.compile(r"^(?:libxcb-[A-Za-z0-9_-]+|libxkbcommon(?:-x11)?)\\.so\\.[0-9]+$")
LINE = re.compile(r"^\\s*(\\S+)\\s+=>\\s+(\\S+)")


def bundle(internal: Path) -> list[str]:
    internal = internal.resolve(strict=True)
    plugin = internal / "PyQt6/Qt6/plugins/platforms/libqxcb.so"
    qt_lib = internal / "PyQt6/Qt6/lib"
    if not plugin.is_file():
        raise RuntimeError(f"Missing bundled Qt XCB platform plugin: {plugin}")

    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = os.pathsep.join(
        p for p in (str(internal), str(qt_lib), env.get("LD_LIBRARY_PATH", "")) if p
    )
    result = subprocess.run(
        ["ldd", str(plugin)], capture_output=True, text=True, env=env, check=False
    )
    if result.returncode:
        raise RuntimeError(f"Cannot inspect bundled Qt XCB dependencies:\\n{result.stdout}\\n{result.stderr}")

    copied = []
    missing = []
    for line in result.stdout.splitlines():
        match = LINE.match(line)
        if not match:
            continue
        soname, source = match.groups()
        if not HELPER.fullmatch(soname):
            continue
        if source == "not":
            missing.append(soname)
            continue
        src = Path(source)
        if not src.is_file():
            missing.append(soname)
            continue
        dst = internal / soname
        if dst.exists():
            continue
        # Avoid shipping an additional copy of anything already in the bundle.
        if src.resolve().is_relative_to(internal):
            continue
        shutil.copy2(src, dst, follow_symlinks=True)
        copied.append(soname)

    if missing:
        raise RuntimeError(
            "Qt XCB helper libraries missing from build host: " + ", ".join(sorted(set(missing)))
            + ". Install the relevant libxcb-* and libxkbcommon-x11-0 packages before building."
        )
    # The exact dependency that failed the first public AppImageHub test.
    if not (internal / "libxcb-icccm.so.4").is_file():
        raise RuntimeError("libxcb-icccm.so.4 must be bundled for AppImageHub/X11 compatibility")
    return sorted(copied)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: bundle_qt_xcb.py <PyInstaller _internal directory>")
    try:
        libs = bundle(Path(sys.argv[1]))
    except (OSError, RuntimeError) as exc:
        sys.exit(str(exc))
    print("Bundled Qt XCB/XKB helper libraries: " + (", ".join(libs) or "(already bundled)"))
