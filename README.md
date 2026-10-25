# Astro A50 Gen 3 for Linux

Native HID settings client and PyQt6 app for USB **9886:0015**. Three EQ slots,
frequency/bandwidth controls, default Game/Voice balance, brightness, alert
volume, battery/charging, firmware identity, microphone/stream controls, and
sidetone/noise-gate are implemented. Thirty-eight reversible hardware checks
passed and restored the recovered baseline. Physical Game/Voice playback,
hardware balance mixing, and Dolby ON/OFF toggle verified (2026-10-24).
**Normal-game 5.1 surround is implemented and verified (2026-10-24):** the raw
`pro-audio` profile labels the Game output's channels `aux0..aux5`, which apps
don't recognise as surround. `config/15-astro-a50-remap.conf` (installed,
also live-applied without any service restart via
`artifacts/surround-integration/apply-live.sh`) exposes `A50 Game 5.1`
(FL/FR/FC/LFE/RL/RR), `A50 Voice` (stereo), and `A50 Mic` (mono) as named
PipeWire/Pulse devices with correct channel maps. SDL2 (both its pulseaudio
and pipewire drivers) enumerates `A50 Game 5.1` and negotiates 6 channels
against it — see `artifacts/surround-integration/sdl-*-probe.log`. The two old
stale `a50-loopback-{game,voice}.service` units are now disabled (were already
inactive). `tools/a50_audio.py --verify` checks the three remap nodes exist
with the expected channel maps.
Sidetone/mic audibility, sync (persist), power-cycle verification of these new
configs, and the optional KDE-tray hide-list update (needs Ben's sudo; see
`artifacts/surround-integration/PulseObjectFilterModel.qml.diff`) remain open;
see [FEATURES](docs/FEATURES.md) for the precise ledger.

Run the app with the installed system Python:

```bash
/usr/bin/python3 tools/a50_gui.py
```

**Settings app only:** edits are staged until **Write working settings**. Every
write saves a baseline, checks readback and retains exact TX/RX under ignored
`artifacts/backups/`. Persistent save to headset storage is a separate explicit
action. JSON backup/import and per-slot `.astroeq` import/export are available.
JSON backups cover EQ, dock settings, microphone/stream controls, and noise gate.

**Physical hardware:** with six-channel Game audio, Ben heard clear channel separation
with Dolby on and a stereo L/R collapse with it off. The Game/Voice hardware mixer is independent; both streams
can play simultaneously with Game/Voice buttons controlling relative levels (verified). The Linux
app provides settings but does not replace these physical controls. USB device paths and stream
routing are mapped for independent audio control when pro-audio profile is active.

```bash
python3 tools/a50.py inventory
python3 tools/a50.py snapshot -o /tmp/a50-backup.json --capture /tmp/a50-capture.json
python3 tools/a50.py selftest
python3 tools/check_settings.py
QT_QPA_PLATFORM=offscreen /usr/bin/python3 tools/a50_gui.py --snapshot /tmp/a50-backup.json --smoke
```

[Native app behavior](docs/NATIVE-APP.md), [protocol evidence](docs/A50-PROTOCOL.md),
[slot1 recovery](docs/EQ-RECOVERY.md), [continuation handoff](HANDOFF.md).
Proprietary app artifacts and private captures stay ignored. No raw-command,
firmware or reset control. Scope is A50-specific: the `pro-audio` profile pin
and the 5.1/mono remap config are installed under
`~/.config/wireplumber/wireplumber.conf.d/` and
`~/.config/pipewire/pipewire-pulse.conf.d/`, applied live without restarting
any PipeWire/WirePlumber service. The system default sink/source (Audioengine
speakers / webcam mic) are confirmed correct as of this README's last update,
but briefly flipped during the surround-integration work below and had to be
caught and reverted — see RESUME.md's "Priority / default-sink incident" for
why, and the installed `priority.session = 0` node rules in
`config/51-astro-a50-pro-audio.conf` for the real (restart-gated) fix.

## New: automatic audio detector / safe setup (experimental)

`python3 tools/a50_setup.py detect` discovers the connected Gen 3's six-channel Game, stereo Voice, and mono microphone endpoints from the actual USB ALSA descriptors. `preview` shows a single per-user WirePlumber config; `install --yes` creates it without restarting audio services or touching system defaults. `verify` checks the resulting native endpoints, and `uninstall --yes` removes only its owned file. **Cold reboot/hotplug are not yet hardware-verified**, and setup intentionally refuses to overwrite the existing legacy remap rules on Ben's machine. See [automatic setup guide](docs/AUTO-AUDIO-SETUP.md) and [Issue #9](https://github.com/BenStein1/astro-a50-linux/issues/9).
