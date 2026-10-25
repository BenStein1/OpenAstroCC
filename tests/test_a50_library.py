#!/usr/bin/env python3
"""Offline preset-library tests. No USB/audio services or device writes."""
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import a50
import a50_library
import a50_names

ROOT = Path(__file__).resolve().parents[1]


def baseline():
    return json.loads((ROOT / "evidence/a50-baseline.json").read_text())


class PresetLibraryTests(unittest.TestCase):
    def test_bundled_and_custom_presets(self):
        refs = a50_library.available_presets()
        builtin = {p.name: p for p in refs if p.source == "Astro"}
        bundled_custom = {p.name: p for p in refs if p.source == "Custom"}
        self.assertGreaterEqual(len(builtin), 5)
        self.assertIn("ASTRO", builtin)
        self.assertIn("PRO", builtin)
        self.assertIn("Bass & Clarity", bundled_custom)
        self.assertTrue(all(not p.writable for p in builtin.values()))
        self.assertFalse(bundled_custom["Bass & Clarity"].writable)
        self.assertEqual(a50_library.file_signature(bundled_custom["Bass & Clarity"]),
                         ((6, -2, 0, 2, 4), (90, 406, 783, 4001, 7001),
                          (8192, 8192, 8192)))

    def test_screenshot_curve_identifies_despite_1_99_octave(self):
        doc = baseline()
        self.assertEqual(doc["slots"][2]["bands"][2]["working"]["bandwidth_raw"], 8167)
        identified = a50_library.recognize(doc, 3)
        self.assertIsNotNone(identified)
        self.assertEqual(identified.name, "Bass & Clarity")
        self.assertEqual(a50_library.recognize(doc, 2).name, "PRO")
        different = copy.deepcopy(doc)
        different["slots"][2]["gains"]["working"][0] -= 1
        self.assertIsNone(a50_library.recognize(different, 3))

    def test_save_custom_does_not_replace_bundled_astro_files(self):
        original = (ROOT / "presets/ASTRO.astroeq").read_bytes()
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"XDG_DATA_HOME": tmp}):
            doc = baseline()
            saved = a50_library.save_custom(doc, 3, "ASTRO")
            self.assertTrue(saved.writable)
            self.assertEqual(saved.path.parent, Path(tmp) / "astro-a50-linux/presets")
            self.assertEqual(a50.load_astroeq(saved.path)["name"], "ASTRO")
            self.assertEqual((ROOT / "presets/ASTRO.astroeq").read_bytes(), original)
            with self.assertRaises(FileExistsError):
                a50_library.save_custom(doc, 3, "ASTRO", overwrite=False)
            new = copy.deepcopy(doc)
            new["slots"][2]["gains"]["working"][0] = 7
            self.assertEqual(a50.load_astroeq(saved.path)["gains"][0], 6)
            a50_library.save_custom(new, 3, "ASTRO", overwrite=True)
            self.assertEqual(a50.load_astroeq(saved.path)["gains"][0], 7)
            self.assertEqual((ROOT / "presets/ASTRO.astroeq").read_bytes(), original)

    def test_custom_names_are_validated_and_safely_confined(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"XDG_DATA_HOME": tmp}):
            for value in ("/", "...", " ", "\n"):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    a50_library.custom_path(value)
            p = a50_library.save_custom(baseline(), 3, "My EQ: bass + clarity")
            self.assertTrue(p.path.is_relative_to(Path(tmp)))
            self.assertEqual(a50.load_astroeq(p.path)["name"], "My EQ: bass + clarity")
            self.assertIn("My EQ: bass + clarity", [x.name for x in a50_library.available_presets()
                                                  if x.source == "Mine"])


if __name__ == "__main__":
    unittest.main()
