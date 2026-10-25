#!/usr/bin/env python3
"""Local labels for the Astro A50 Gen 3's three numbered hardware EQ slots.

These names are application metadata. They are NOT sent to the headset.
"""
import configparser
import json
import os
from pathlib import Path
import tempfile

SCHEMA = "astro-a50-eq-names-v1"
DEFAULT_NAMES = ("Unnamed", "Unnamed", "Unnamed")
MAX_LENGTH = 64


def normalize_name(name):
    if not isinstance(name, str):
        raise ValueError("EQ preset name must be text")
    name = name.strip()
    if not name or len(name) > MAX_LENGTH or any(ord(ch) < 32 or ord(ch) == 127 for ch in name):
        raise ValueError("EQ preset name must be 1–64 characters without control characters")
    return name


def validate_names(names):
    if not isinstance(names, list) or len(names) != 3:
        raise ValueError("EQ preset names require exactly three slots")
    return [normalize_name(value) for value in names]


def names_path():
    config = os.environ.get("XDG_CONFIG_HOME")
    root = Path(config) if config else Path.home() / ".config"
    return root / "astro-a50-linux" / "eq-names.json"


def load_names():
    path = names_path()
    if not path.exists() and not path.is_symlink():
        return list(DEFAULT_NAMES)
    if path.is_symlink() or not path.is_file():
        raise ValueError("EQ names path must be a regular file")
    doc = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError("Unrecognized EQ names file schema; refusing to overwrite")
    return validate_names(doc.get("slots"))


def save_names(names):
    validated = validate_names(names)
    path = names_path()
    if path.exists() or path.is_symlink():
        load_names()  # Refuse to silently replace invalid files or symlinks.
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps({"schema": SCHEMA, "slots": validated}, indent=2) + "\n"
    temp = None
    try:
        fd, temp = tempfile.mkstemp(prefix=".eq-names-", suffix=".tmp", dir=path.parent)
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temp, path)
    finally:
        if temp is not None:
            Path(temp).unlink(missing_ok=True)
    return validated


# Never ship the proprietary Astro preset collection in GitHub. The original
# .astroeq files are available only when the user already has a local copy.
# Archived Windows app assets may exist in the ignored artifacts/ working tree.
def preset_directories():
    root = Path(__file__).resolve().parent.parent
    dirs = [
        root / "presets",  # Factory defaults.
        root / "presets/custom",  # Bundled read-only custom curves.
        root / "artifacts/classic-acc/assets/Astro A50 Wireless/Astro EQ",
        root / "artifacts/appdata-classic/Astro A50 Wireless/Astro EQ",
        root / "artifacts/appdata-store/ASTRO A50 Wireless",
        Path.home() / ".local/share/astro-a50-linux/presets",
    ]
    additional = os.environ.get("ASTRO_A50_EQ_DIRS", "")
    dirs.extend(Path(value).expanduser() for value in additional.split(os.pathsep) if value)
    return dirs


def match_preset_names(document, directories=None):
    """Read existing .astroeq files and identify unambiguous hardware slot matches.

    A USB EQ bank contains gains, frequencies and bell widths, not text names.
    For a match all 13 numeric EQ parameters must agree: gains/frequencies exactly,
    widths within 0.01 octave to account for rounded Windows .astroeq text.
    Identical numeric curves with different names are ambiguous and NOT named.
    This performs local file reads only and never modifies device/settings.
    """
    import a50

    if not isinstance(document, dict) or not isinstance(document.get("slots"), list):
        return [None, None, None]
    preset_paths = []
    for folder in (directories if directories is not None else preset_directories()):
        folder = Path(folder)
        if folder.is_dir():
            preset_paths.extend(sorted(folder.glob("*.astroeq")))
    references = []
    seen_paths = set()
    for path in preset_paths:
        resolved = str(path.resolve())
        if resolved in seen_paths:
            continue
        seen_paths.add(resolved)
        try:
            preset = a50.load_astroeq(path)
            name = normalize_name(preset["name"])
            gains = tuple(preset["gains"])
            freqs = tuple(preset["freqs"])
            widths = tuple(round(preset["bandwidths"][n] * 4096)
                           for n in (2, 3, 4))
            if len(gains) != 5 or len(freqs) != 5:
                continue
            references.append((name, gains, freqs, widths))
        except (OSError, ValueError, KeyError, TypeError, IndexError, configparser.Error):
            continue

    identified = []
    for slot in document["slots"][:3]:
        try:
            gains = tuple(slot["gains"]["working"])
            freqs = tuple(band["working"]["frequency"] for band in slot["bands"])
            widths = tuple(slot["bands"][n - 1]["working"]["bandwidth_raw"]
                           for n in (2, 3, 4))
            if len(gains) != 5 or len(freqs) != 5:
                raise ValueError("unexpected slot shape")
        except (TypeError, ValueError, KeyError, IndexError):
            identified.append(None)
            continue
        matches = {
            name for name, g, f, w in references
            if gains == g
            and freqs == f
            and all(abs(a - b) <= 41 for a, b in zip(widths, w))
        }
        identified.append(next(iter(matches)) if len(matches) == 1 else None)
    return (identified + [None] * 3)[:3]
