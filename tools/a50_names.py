#!/usr/bin/env python3
"""Local labels for the Astro A50 Gen 3's three numbered hardware EQ slots.

These names are application metadata. They are NOT sent to the headset.
"""
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
