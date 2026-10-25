#!/usr/bin/env python3
"""Offline tests for a50_setup.py. Never touches real USB or audio services."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import a50_setup as setup


GAME = """Astro Gaming Astro A50 : USB Audio #1
Playback:
  Status: Stop
  Interface 4
    Channels: 6
    Rates: 48000
    Channel map: FL FR FC LFE RL RR
Capture:
  Status: Stop
  Interface 5
    Channels: 2
    Rates: 48000
    Channel map: FL FR
"""
VOICE = """Astro Gaming Astro A50 : USB Audio
Playback:
  Status: Running
  Interface 2
    Channels: 2
    Rates: 48000
    Channel map: FL FR
Capture:
  Status: Stop
  Interface 1
    Channels: 1
    Rates: 16000
    Channel map: MONO
"""


def sample(name="alsa_card.usb-Astro_Gaming_Astro_A50-00", index="8", game=1, voice=0):
    return {
        "cards": [{
            "name": name, "active_profile": "pro-audio",
            "properties": {"device.vendor.id": "0x9886", "device.product.id": "0x0015",
                           "api.alsa.card": index},
            "profiles": {"pro-audio": {"available": True, "sinks": 2, "sources": 2}},
        }],
        "sinks": [], "sources": [],
        "streams": {name: {str(game): GAME, str(voice): VOICE}},
    }


class TestA50AudioSetup(unittest.TestCase):
    def test_descriptor_discovery_not_hardcoded_pcm_or_card(self):
        for game, voice in ((1, 0), (7, 2)):
            with self.subTest(game=game):
                d = setup.discover(sample(index="19", game=game, voice=voice))
                self.assertEqual((d.card_index, d.game_pcm, d.voice_pcm), (19, game, voice))
                rules = setup.render_config(d)
                self.assertIn("pro-output-" + str(game), rules)
                self.assertIn("pro-output-" + str(voice), rules)
                self.assertIn("pro-input-" + str(voice), rules)
                self.assertIn("audio.position = [ FL FR FC LFE RL RR ]", rules)
                self.assertIn('device.vendor.id = "0x9886"', rules)
                self.assertIn('device.product.id = "0x0015"', rules)
                self.assertNotIn("module-remap-sink sink_name", rules)
                self.assertNotIn("set-default-sink", rules)

    def test_wrong_usb_id_or_ambiguous_device(self):
        for key, val in [("device.vendor.id", "0x1234"), ("device.product.id", "0x0014")]:
            inv = sample()
            inv["cards"][0]["properties"][key] = val
            with self.assertRaisesRegex(setup.SetupError, "not connected"):
                setup.discover(inv)
        inv = sample()
        inv["cards"].append(inv["cards"][0].copy())
        with self.assertRaisesRegex(setup.SetupError, "Multiple"):
            setup.discover(inv)

    def test_rejects_wrong_channel_layout(self):
        inv = sample()
        inv["streams"][inv["cards"][0]["name"]]["1"] = GAME.replace(
            "Channels: 6", "Channels: 2")
        with self.assertRaisesRegex(setup.SetupError, "uniquely"):
            setup.discover(inv)

    def test_native_verify_requires_card_channels_and_map(self):
        inv = sample()
        d = setup.discover(inv)
        self.assertFalse(setup.verify_native(inv, d)["ready"])
        for name, ch, channelmap, kind, pcm in (
            (d.output(d.game_pcm), 6,
             "front-left,front-right,front-center,lfe,rear-left,rear-right", "sinks", d.game_pcm),
            (d.output(d.voice_pcm), 2, "front-left,front-right", "sinks", d.voice_pcm),
            (d.source(d.voice_pcm), 1, "mono", "sources", d.voice_pcm),
        ):
            inv[kind].append({"name": name, "sample_spec": {"channels": ch},
                              "channel_map": channelmap,
                              "properties": {"device.name": d.card,
                                             "api.alsa.pcm.device": str(pcm)}})
        self.assertTrue(setup.verify_native(inv, d)["ready"])
        inv["sinks"][0]["properties"]["device.name"] = "another_card"
        self.assertFalse(setup.verify_native(inv, d)["ready"])

    def test_install_idempotent_and_safe_uninstall(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(
                os.environ, {"XDG_CONFIG_HOME": home}), patch.object(
                    setup, "check_wireplumber", return_value="0.5.10"):
            d = setup.discover(sample())
            with self.assertRaisesRegex(setup.SetupError, "requires --yes"):
                setup.install(d)
            result = setup.install(d, yes=True)
            self.assertIn("Installed", result)
            path = setup.config_path()
            self.assertEqual(path.read_text(), setup.render_config(d))
            self.assertIn("Already installed", setup.install(d, yes=True))
            with self.assertRaisesRegex(setup.SetupError, "requires --yes"):
                setup.uninstall()
            self.assertIn("Removed", setup.uninstall(yes=True))
            self.assertFalse(path.exists())

    def test_existing_configs_never_overwritten(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(
                os.environ, {"XDG_CONFIG_HOME": home}), patch.object(
                    setup, "check_wireplumber", return_value="0.5.10"):
            d = setup.discover(sample())
            old = Path(home) / setup.LEGACY[0]
            old.parent.mkdir(parents=True)
            old.write_text("legacy\n")
            with self.assertRaisesRegex(setup.SetupError, "Refusing"):
                setup.install(d, yes=True)
            self.assertEqual(old.read_text(), "legacy\n")
            old.unlink()
            dest = setup.config_path()
            dest.write_text("custom user config\n")
            with self.assertRaisesRegex(setup.SetupError, "different contents"):
                setup.install(d, yes=True)
            with self.assertRaisesRegex(setup.SetupError, "not marked as ours"):
                setup.uninstall(yes=True)
            self.assertEqual(dest.read_text(), "custom user config\n")

    def test_fixture_cannot_modify_system(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(
                os.environ, {"XDG_CONFIG_HOME": home}):
            fixture = Path(home) / "mock.json"
            fixture.write_text(json.dumps(sample()))
            self.assertEqual(setup.main(["detect", "--fixture", str(fixture)]), 0)
            self.assertEqual(setup.main(["preview", "--fixture", str(fixture)]), 0)
            self.assertEqual(setup.main(["install", "--fixture", str(fixture), "--yes"]), 2)
            self.assertFalse(setup.config_path().exists())


if __name__ == "__main__":
    unittest.main()
