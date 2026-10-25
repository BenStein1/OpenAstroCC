#!/usr/bin/env python3
"""Pure offline tests for local-only EQ names and Astro .astroeq Name metadata."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import a50
import a50_names


class EqNamesTests(unittest.TestCase):
    def test_names_persist_locally_and_are_not_usb_settings(self):
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root}):
            self.assertEqual(a50_names.load_names(), ["Unnamed"] * 3)
            names = ["ASTRO", "PRO", "My Gaming EQ"]
            self.assertEqual(a50_names.save_names(names), names)
            self.assertEqual(a50_names.load_names(), names)
            self.assertEqual(json.loads(a50_names.names_path().read_text())["slots"], names)
            self.assertEqual(a50_names.save_names(names), names)

    def test_validation_rejects_bad_or_corrupt_names_without_destroying_file(self):
        for value in (["one", "two"], ["ok", "ok", ""], ["ok", "ok", "x\ny"],
                      ["ok", "ok", "x" * 65], ["ok", "ok", 42]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                a50_names.validate_names(value)
        with tempfile.TemporaryDirectory() as root, patch.dict(os.environ, {"XDG_CONFIG_HOME": root}):
            path = a50_names.names_path()
            path.parent.mkdir(parents=True)
            path.write_text("{bad json")
            with self.assertRaises(ValueError):
                a50_names.load_names()
            with self.assertRaises(ValueError):
                a50_names.save_names(["A", "B", "C"])
            self.assertEqual(path.read_text(), "{bad json")

    def test_preset_name_round_trip_in_astroeq(self):
        root = Path(__file__).resolve().parents[1]
        document = json.loads((root / "evidence/a50-baseline.json").read_text())
        with tempfile.TemporaryDirectory() as dirname:
            path = Path(dirname) / "custom.astroeq"
            a50.export_preset(document, 1, path, name="Night Games")
            self.assertEqual(a50.load_astroeq(path)["name"], "Night Games")
            self.assertEqual(a50.import_preset(document, 1, path)["slots"],
                             document["slots"])

    def test_existing_backups_allow_local_name_metadata(self):
        root = Path(__file__).resolve().parents[1]
        document = json.loads((root / "evidence/a50-baseline.json").read_text())
        document["eq_names"] = ["ASTRO", "PRO", "Custom"]
        a50.validate_backup(document)
        self.assertEqual(a50_names.validate_names(document["eq_names"]),
                         ["ASTRO", "PRO", "Custom"])


if __name__ == "__main__":
    unittest.main()
