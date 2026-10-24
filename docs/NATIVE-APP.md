# Native app

Run `/usr/bin/python3 tools/a50_gui.py`. The system Python has PyQt6; the
pyenv default does not. No packages or global configuration were installed.

The app reads three EQ slots, all five frequencies and the three bell bandwidths,
dock defaults, current battery/charging, hardware balance and selected EQ slot.
It reads base/headset identity (firmware 36791/36154 on this hardware). Every
transaction rediscovers the A50, validates the opened fd's USB identity, takes
an exclusive cooperative lock, and closes it on completion. Polling is five
seconds. Disconnect disables writes; subsequent polls retry discovery and load
a fresh snapshot before reenabling them. Physical unplug/reinsert still needs
Ben's test; synthetic disconnect and host GUI reads are separate evidence.

Edit controls, then **Write working settings**. Writes compare the last snapshot
with the current hardware before touching it, save a fresh baseline privately
under `artifacts/backups/`, set only changed fields, and verify readback. Failed
working transactions attempt restoration from that transaction's baseline and
retain any restoration error. No write automatically persists settings.
**Save to headset** explicitly confirms persistence of *all* current working
settings, including microphone/stream state. Do not infer persistence across
power loss from its ACK; reconnect/power-cycle verification is still pending.

Export backup saves the last hardware snapshot. Import backup validates USB
identity, schema, slot/band structure, complete banks and numeric bounds before
loading the working bank into the editor. It preserves the current device's
stored banks. JSON backups contain both working/stored EQ plus the implemented
mediator settings; microphone and stream controls are not yet covered. They are
therefore **partial device backups**, not full-device recovery images.
`.astroeq` import/export is per slot and preserves raw bandwidth precision.
Neither file import writes to the headset until the write button is pressed.
Files are created exclusively so existing backups are not silently overwritten.

Offline inspection: `/usr/bin/python3 tools/a50_gui.py --snapshot BACKUP.json`.
Hardware writing is disabled. Read-only smoke checks add `--smoke`: they read,
render, assert EQ values survive the UI unchanged, capture `/tmp/a50-ui-smoke.png`
and exit. A live desktop smoke check has succeeded. `tools/check_gui.py --live` subsequently exercised an actual write-button
gain change, independently checked hardware readback, restored through the button,
and compared all captured settings with the recovered baseline. It also tested a
synthetic disconnect and successful rediscovery/reload. This proves the GUI path;
listening and physical unplug/reinsert remain separate pending checks.

No firmware update/reset/raw-opcode control is exposed. Audio-profile switching
and sounds remain pending approval. The existing config artifact has not been
installed. Use docs/FEATURES.md for precise acceptance gaps.
