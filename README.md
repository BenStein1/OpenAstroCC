# Astro A50 Gen 3 for Linux

Native HID settings client and PyQt6 app for USB **9886:0015**. Three EQ slots,
frequency/bandwidth controls, default Game/Voice balance, brightness, alert
volume, battery/charging and firmware identity are implemented. Thirty reversible
hardware checks passed and restored the recovered baseline. Mic/stream controls,
physical audio tests and persistence verification remain open; see
[FEATURES](docs/FEATURES.md) for the precise ledger.

Run the app with the installed system Python:

```bash
/usr/bin/python3 tools/a50_gui.py
```

Edits are staged until **Write working settings**. Every write saves a baseline,
checks readback and retains exact TX/RX under ignored `artifacts/backups/`.
Persistent save is a separate explicit action. JSON backup/import and per-slot
`.astroeq` import/export are available. Current JSON backups cover EQ and the
implemented dock settings, not microphone/stream settings yet.

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
firmware or reset control. Audio-profile switching and test sounds still await
Ben's answer; no global configuration or services have been changed.
