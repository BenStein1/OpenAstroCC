#!/usr/bin/env python3
"""Detect Astro A50 Gen 3 audio interfaces; safely install per-user WirePlumber rules.

Default is read-only. This tool never restarts audio services, changes system
defaults, writes HID reports, or modifies other people's configuration.
Requires PipeWire and WirePlumber 0.5.x; real reboot/hotplug verification pending.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from dataclasses import dataclass

VID, PID = 0x9886, 0x0015
OWNER = "astro-a50-linux/audio-setup/v1"
FILENAME = "52-astro-a50-auto.conf"
RELATIVE = Path("wireplumber/wireplumber.conf.d") / FILENAME
LEGACY = (
    Path("wireplumber/wireplumber.conf.d/51-astro-a50-pro-audio.conf"),
    Path("pipewire/pipewire-pulse.conf.d/15-astro-a50-remap.conf"),
    Path("pipewire/pipewire.conf.d/a50-virtual-sinks.conf"),
)
GAME_CHANNELS = ["FL", "FR", "FC", "LFE", "RL", "RR"]


class SetupError(Exception):
    pass


@dataclass(frozen=True)
class Device:
    card: str
    prefix: str
    card_index: int
    game_pcm: int
    voice_pcm: int

    def output(self, n):
        return f"alsa_output.{self.prefix}.pro-output-{n}"

    def source(self, n):
        return f"alsa_input.{self.prefix}.pro-input-{n}"


def usb_id(props, key):
    try:
        return int(str(props.get(key, "")), 0)
    except (TypeError, ValueError):
        return None


def pactl_list(kind):
    try:
        result = subprocess.run(
            ["pactl", "--format=json", "list", kind],
            check=True, capture_output=True, text=True, timeout=8)
        value = json.loads(result.stdout)
        if not isinstance(value, list):
            raise SetupError(f"Unexpected pactl output for {kind}")
        return value
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            ValueError) as exc:
        raise SetupError(f"Cannot inspect {kind}: {exc}") from exc


def inventory_live():
    cards, sinks, sources = [pactl_list(k) for k in ("cards", "sinks", "sources")]
    streams = {}
    for card in cards:
        p = card.get("properties", {})
        if (usb_id(p, "device.vendor.id"), usb_id(p, "device.product.id")) != (VID, PID):
            continue
        try:
            card_id = int(p["api.alsa.card"])
        except (KeyError, TypeError, ValueError):
            continue
        root = Path("/proc/asound") / f"card{card_id}"
        try:
            if (root / "usbid").read_text().strip().lower() != f"{VID:04x}:{PID:04x}":
                continue
            streams[card["name"]] = {
                str(int(path.name[6:])): path.read_text()
                for path in root.glob("stream[0-9]*")
                if re.fullmatch(r"stream[0-9]+", path.name)}
        except OSError:
            continue
    return {"cards": cards, "sinks": sinks, "sources": sources, "streams": streams}


def stream_info(text, direction):
    match = re.search(
        r"(?m)^" + re.escape(direction) + r":\s*\n(.*?)(?=^(?:Playback|Capture):|\Z)",
        text, re.S | re.M)
    if not match:
        return None
    section = match.group(1)
    ch = re.search(r"(?m)^\s*Channels:\s*(\d+)", section)
    rate = re.search(r"(?m)^\s*Rates:\s*(\d+)", section)
    positions = re.search(r"(?m)^\s*Channel map:\s*(.+)", section)
    if not (ch and rate and positions):
        return None
    return int(ch.group(1)), int(rate.group(1)), positions.group(1).split()


def discover(inv):
    cards = [c for c in inv.get("cards", []) if
             (usb_id(c.get("properties", {}), "device.vendor.id"),
              usb_id(c.get("properties", {}), "device.product.id")) == (VID, PID)]
    if not cards:
        raise SetupError("Astro A50 Gen 3 USB 9886:0015 not connected")
    if len(cards) != 1:
        raise SetupError("Multiple A50 sound cards found; refusing ambiguous setup")
    c = cards[0]
    name = c.get("name", "")
    if not re.fullmatch(r"alsa_card\.usb-[A-Za-z0-9_.-]+", name):
        raise SetupError(f"Unexpected ALSA card name: {name!r}")
    try:
        index = int(c["properties"]["api.alsa.card"])
    except (KeyError, TypeError, ValueError):
        raise SetupError("No usable ALSA index for this USB card") from None
    pro = c.get("profiles", {}).get("pro-audio", {})
    if pro.get("available") not in (True, "yes") or (
            pro.get("sinks"), pro.get("sources")) != (2, 2):
        raise SetupError("Pro-audio profile does not provide 2 sinks / 2 sources")
    streams = inv.get("streams", {}).get(name, {})
    game, voice = [], []
    for num, data in streams.items():
        playback = stream_info(data, "Playback")
        capture = stream_info(data, "Capture")
        if playback == (6, 48000, GAME_CHANNELS) and capture and capture[0] == 2:
            game.append(int(num))
        if playback == (2, 48000, ["FL", "FR"]) and capture == (1, 16000, ["MONO"]):
            voice.append(int(num))
    if len(game) != 1 or len(voice) != 1 or game[0] == voice[0]:
        raise SetupError("USB descriptors do not uniquely identify Game 6ch / Voice 2ch / Mic mono")
    return Device(name, name.removeprefix("alsa_card."), index, game[0], voice[0])


def render_config(device):
    # Derived from the verified connected card, not Ben's hardcoded sound-card index.
    # The trailing USB ALSA instance number may change between logins.
    base = re.sub(r"-\d+$", "", device.prefix)
    pattern = re.escape(base) + r"-[0-9]+" if base != device.prefix else re.escape(device.prefix)
    # PipeWire SPA config has quoted strings: use [.] instead of \. escapes.
    pattern = pattern.replace(r"\.", "[.]").replace(r"\-", "-")

    def node(kind, pcm, positions, description):
        regex = kind + "[.]" + pattern + "[.]pro-" + (
            "output-" if kind == "alsa_output" else "input-") + str(pcm)
        fields = [f'        node.description = "{description}"',
                  "        priority.session = 0"]
        if positions:
            fields.insert(0, "        audio.position = [ " + " ".join(positions) + " ]")
        return ("  {\n    matches = [ { node.name = \"~^" + regex + "$\" } ]\n"
                "    actions = { update-props = {\n" + "\n".join(fields) + "\n    } }\n  }")

    rules = [
        node("alsa_output", device.game_pcm, GAME_CHANNELS, "Astro A50 Game 5.1"),
        node("alsa_output", device.voice_pcm, ["FL", "FR"], "Astro A50 Voice"),
        node("alsa_input", device.voice_pcm, ["MONO"], "Astro A50 Microphone"),
        node("alsa_input", device.game_pcm, None, "Astro A50 Line Input"),
    ]
    return (
        f"# Managed by {OWNER}; do not edit this generated file.\n"
        "# Generated from a connected USB 9886:0015 and its ALSA stream descriptors.\n"
        "# Separate six-channel Game and stereo Voice; NO software Game/Voice mixing.\n"
        "# WirePlumber 0.5.x only. Never enable an AUX-based remap at the same time.\n"
        "monitor.alsa.rules = [\n"
        '  {\n    matches = [ { device.vendor.id = "0x9886" device.product.id = "0x0015" } ]\n'
        '    actions = { update-props = {\n      device.profile = "pro-audio"\n'
        "      api.acp.auto-profile = false\n    } }\n  }\n"
        + "\n".join(rules) + "\n]\n")


def config_home():
    return Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))


def config_path():
    return config_home() / RELATIVE


def legacy_conflicts():
    return [str(config_home() / path) for path in LEGACY if (config_home() / path).exists()]


def verify_native(inv, device):
    sinks = {n.get("name"): n for n in inv.get("sinks", [])}
    sources = {n.get("name"): n for n in inv.get("sources", [])}
    expected = [
        (device.output(device.game_pcm), 6,
         "front-left,front-right,front-center,lfe,rear-left,rear-right", sinks),
        (device.output(device.voice_pcm), 2, "front-left,front-right", sinks),
        (device.source(device.voice_pcm), 1, "mono", sources),
    ]
    status = {}
    for name, count, channel_map, nodes in expected:
        obj = nodes.get(name)
        props = obj.get("properties", {}) if obj else {}
        belongs = bool(obj and props.get("device.name", device.card) == device.card and
                       str(props.get("api.alsa.pcm.device", name.rsplit("-", 1)[-1])) ==
                       name.rsplit("-", 1)[-1])
        spec = obj.get("sample_spec", {}) if obj else {}
        status[name] = {"present": bool(obj), "belongs_to_card": belongs,
                        "actual_map": obj.get("channel_map") if obj else None,
                        "expected_map": channel_map,
                        "ok": bool(obj and belongs and spec.get("channels") == count and
                                   obj.get("channel_map") == channel_map)}
    active = next((c.get("active_profile") for c in inv["cards"]
                   if c.get("name") == device.card), None)
    return {"active_profile": active, "paths": status,
            "ready": active == "pro-audio" and all(x["ok"] for x in status.values())}


def check_wireplumber():
    try:
        reply = subprocess.run(["wireplumber", "--version"], check=True,
                               capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise SetupError(f"Cannot find WirePlumber 0.5.x: {exc}") from exc
    version = re.search(r"\b(\d+)\.(\d+)\.(\d+)\b", reply.stdout + reply.stderr)
    if not version or version.group(1, 2) != ("0", "5"):
        raise SetupError(f"Supported only on WirePlumber 0.5.x: {reply.stdout.strip()}")
    return version.group(0)


def install(device, yes=False):
    check_wireplumber()
    conflicts = legacy_conflicts()
    if conflicts:
        raise SetupError("Refusing to overwrite or combine existing A50 routing configs:\n  " +
                         "\n  ".join(conflicts))
    path = config_path()
    content = render_config(device)
    if path.exists() or path.is_symlink():
        if path.is_file() and not path.is_symlink() and path.read_text() == content:
            return "Already installed (identical file); no changes"
        raise SetupError(f"Managed path exists with different contents: {path}")
    if not yes:
        raise SetupError("Use preview first; installation requires --yes")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                 getattr(os, "O_NOFOLLOW", 0), 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as output:
            output.write(content)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return f"Installed {path}. Log out and back in to activate; no services restarted"


def uninstall(yes=False):
    path = config_path()
    if not path.exists() and not path.is_symlink():
        return "No owned configuration installed"
    if path.is_symlink() or not path.is_file():
        raise SetupError("Refusing to remove a symlink or non-file")
    if not path.read_text().startswith(f"# Managed by {OWNER};"):
        raise SetupError("File is not marked as ours; refusing to remove it")
    if not yes:
        raise SetupError("Uninstall requires --yes")
    path.unlink()
    return "Removed owned config only; log out and back in to apply"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", default="detect",
                        choices=("detect", "preview", "install", "verify", "uninstall"))
    parser.add_argument("--fixture", help="offline cards/sinks/sources/streams JSON, read-only")
    parser.add_argument("--yes", action="store_true", help="explicit install/uninstall approval")
    args = parser.parse_args(argv)
    try:
        if args.fixture and args.action in ("install", "uninstall"):
            raise SetupError("Cannot install or uninstall using an offline fixture")
        if args.action == "uninstall":
            print(uninstall(args.yes))
            return 0
        if args.fixture:
            try:
                inv = json.loads(Path(args.fixture).read_text())
            except (OSError, ValueError) as exc:
                raise SetupError(f"Could not load fixture: {exc}") from exc
        else:
            inv = inventory_live()
        device = discover(inv)
        details = {"usb_id": "9886:0015", "card": device.card,
                   "alsa_card": device.card_index, "game_pcm": device.game_pcm,
                   "voice_pcm": device.voice_pcm, "conflicts": legacy_conflicts(),
                   "installed_file": str(config_path()), "health": verify_native(inv, device)}
        if args.action == "detect":
            print(json.dumps(details, indent=2))
            return 0
        if args.action == "verify":
            print(json.dumps(details, indent=2))
            return 0 if details["health"]["ready"] else 2
        if args.action == "preview":
            print(json.dumps(details, indent=2))
            print("\n# Proposed config; NOT applied:\n" + render_config(device))
            return 0
        print(install(device, args.yes))
        return 0
    except SetupError as exc:
        print("A50 setup: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
