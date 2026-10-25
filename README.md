# Astro A50 Gen 3 for Linux

Native HID settings client and PyQt6 app for USB **9886:0015**. Three EQ slots,
frequency/bandwidth controls, default Game/Voice balance, brightness, alert
volume, battery/charging, firmware identity, microphone/stream controls, and
sidetone/noise-gate are implemented. Thirty-eight reversible hardware checks
passed and restored the recovered baseline. Physical Game/Voice playback,
hardware balance mixing, and Dolby ON/OFF toggle verified (2026-10-24).
Sidetone/mic audibility, sync (persist), power-cycle verification, and
per-app stream routing remain open; see [FEATURES](docs/FEATURES.md) for
the precise ledger.

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
firmware or reset control. Global audio configuration and services unchanged.
