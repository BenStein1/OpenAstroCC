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

# Qt may load some XCB helpers indirectly, so ldd on libqxcb.so alone
# does not reliably expose every library needed on another Linux machine.
# These small XCB/XKB protocol helpers are safe to ship alongside PyQt6.
REQUIRED = (
    "libxcb-cursor.so.0",
    "libxcb-glx.so.0",
    "libxcb-icccm.so.4",
    "libxcb-image.so.0",
    "libxcb-keysyms.so.1",
    "libxcb-randr.so.0",
    "libxcb-render-util.so.0",
    "libxcb-render.so.0",
    "libxcb-shape.so.0",
    "libxcb-shm.so.0",
    "libxcb-sync.so.1",
    "libxcb-util.so.1",
    "libxcb-xfixes.so.0",
    "libxcb-xinerama.so.0",
    "libxcb-xinput.so.0",
    "libxcb-xkb.so.1",
    "libxkbcommon-x11.so.0",
    "libxkbcommon.so.0",
)
LINE = re.compile(r"^\\s*(\\S+)\\s+=>\\s+(\\S+)")
CACHE = re.compile(r"^\\s*(\\S+)\\s+\\(libc6,x86-64\\)\\s+=>\\s+(\\S+)")


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

    # ldd gives paths for linked dependencies; ldconfig also finds Qt helpers
    # that the plugin's runtime loader resolves but ldd does not enumerate.
    linked = {}
    for line in result.stdout.splitlines():
        match = LINE.match(line)
        if match and match.group(2).startswith("/"):
            linked[match.group(1)] = Path(match.group(2))
    cache = subprocess.run(
        ["ldconfig", "-p"], capture_output=True, text=True, check=True
    )
    host = {}
    for line in cache.stdout.splitlines():
        match = CACHE.match(line)
        if match:
            host.setdefault(match.group(1), Path(match.group(2)))

    copied = []
    missing = []
    for soname in REQUIRED:
        dst = internal / soname
        if dst.is_file():
            continue
        # Don't assume an existing copy inside Qt6/lib is loader-visible
        # from the packaged plugin: copy it to PyInstaller's _internal root.
        candidates = [linked.get(soname), host.get(soname)]
        candidates.extend(internal.glob("**/" + soname))
        source = next((p for p in candidates if p and p.is_file()), None)
        if source is None:
            missing.append(soname)
            continue
        shutil.copy2(source, dst, follow_symlinks=True)
        copied.append(soname)

    if missing:
        raise RuntimeError(
            "Qt XCB helper libraries missing from build host: " + ", ".join(missing)
            + ". Install the relevant libxcb-* and libxkbcommon-x11-0 packages before building."
        )
    return sorted(copied)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: bundle_qt_xcb.py <PyInstaller _internal directory>")
    try:
        libs = bundle(Path(sys.argv[1]))
    except (OSError, RuntimeError) as exc:
        sys.exit(str(exc))
    print("Bundled Qt XCB/XKB helper libraries: " + (", ".join(libs) or "(already bundled)"))
