#!/usr/bin/env python3
"""Read-only bundled A50 presets and a separate, writable user preset library.

The firmware knows three EQ slot numbers and numeric parameters, not file names.
Bundled presets are NEVER overwritten by library operations.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile

import a50
import a50_names


@dataclass(frozen=True)
class Preset:
    name: str
    path: Path
    source: str  # 'Astro', 'Example', or 'Mine'

    @property
    def writable(self):
        return self.source == "Mine"


def repo_root():
    return Path(__file__).resolve().parent.parent


def custom_dir():
    base = os.environ.get("XDG_DATA_HOME")
    return (Path(base) if base else Path.home() / ".local/share") / "astro-a50-linux/presets"


def preset_folders():
    root = repo_root()
    return ((root / "presets", "Astro"),
            (root / "presets/examples", "Example"),
            (custom_dir(), "Mine"))


def available_presets():
    """Scan fixed directories; validate the content rather than trusting filenames."""
    found = []
    for folder, source in preset_folders():
        if not folder.is_dir():
            continue
        for path in sorted(folder.glob("*.astroeq"), key=lambda p: p.name.lower()):
            if not path.is_file() or path.is_symlink():
                continue
            try:
                data = a50.load_astroeq(path)
                name = a50_names.normalize_name(data["name"])
                a50.encode_eq(data)
            except (OSError, ValueError, KeyError, TypeError):
                continue
            found.append(Preset(name, path, source))
    return found


def slot_signature(document, slot):
    """Exact numeric signature of the editor's working bank (no floating rounding)."""
    item = document["slots"][slot - 1]
    return (tuple(item["gains"]["working"]),
            tuple(b["working"]["frequency"] for b in item["bands"]),
            tuple(item["bands"][i - 1]["working"]["bandwidth_raw"] for i in (2, 3, 4)))


def file_signature(preset):
    values = a50.load_astroeq(preset.path)
    return (tuple(values["gains"]), tuple(values["freqs"]),
            tuple(a50.bandwidth_to_raw(values["bandwidths"][i]) for i in (2, 3, 4)))


def recognize(document, slot, presets=None):
    """Identify an EQ only when all gains/frequencies match and widths are close.

    Astro's Windows application writes octaves as rounded decimals. Allow up to
    0.01 octave difference (41 in 4.12 units); no approximate gains or Hz.
    Distinct titles with identical numbers remain ambiguous.
    """
    actual = slot_signature(document, slot)
    matches = []
    for preset in presets if presets is not None else available_presets():
        try:
            other = file_signature(preset)
        except (OSError, ValueError, KeyError, TypeError):
            continue
        if (actual[0] == other[0] and actual[1] == other[1]
                and all(abs(a - b) <= 41 for a, b in zip(actual[2], other[2]))):
            matches.append(preset)
    return matches[0] if len({p.name for p in matches}) == 1 and matches else None


def custom_path(name):
    name = a50_names.normalize_name(name)
    slug = re.sub(r"[^A-Za-z0-9._ ()-]+", "_", name).strip(" .")
    if not slug or slug.startswith("."):
        raise ValueError("Choose a name that can be used as a filename")
    return custom_dir() / (slug + ".astroeq")


def save_custom(document, slot, name, overwrite=False):
    """Explicit save to user's own folder only; never alters shipped presets.

    Never overwrite any file without an explicit overwrite=True. The temp file
    and destination share a filesystem; new saves use hardlink (O_EXCL-like)
    so concurrent filename collisions cannot clobber either user's data.
    """
    name = a50_names.normalize_name(name)
    a50.validate_backup(document)
    a50.A50Client._slot(slot)
    target = custom_path(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink() or (target.exists() and not target.is_file()):
        raise ValueError("Preset path is not a regular file")
    if target.exists() and not overwrite:
        raise FileExistsError(f"User preset already exists: {target.name}")
    fd, temp_name = tempfile.mkstemp(prefix=".a50-preset-", suffix=".tmp", dir=target.parent)
    os.close(fd)
    temp = Path(temp_name)
    try:
        temp.unlink()  # a50.export_preset uses exclusive creation.
        a50.export_preset(document, slot, temp, name=name)
        if overwrite:
            os.replace(temp, target)
        else:
            os.link(temp, target)  # Atomic no-overwrite; fails if target exists.
    finally:
        temp.unlink(missing_ok=True)
    return Preset(name, target, "Mine")
