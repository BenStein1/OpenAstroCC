# Native app

Run `/usr/bin/python3 tools/a50_gui.py`. The system Python has PyQt6; the
pyenv default does not. No packages or global configuration were installed.

The app reads three EQ slots, all five frequencies and the three bell bandwidths,
dock defaults, current battery/charging, hardware balance and selected EQ slot.
It reads base/headset identity (firmware 36791/36154 on this hardware), and on
a schema-v2 device also the six sliders and microphone EQ/noise gate, shown on
the Microphone and Stream mix tabs (disabled for an offline v1 backup). Every
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
stored banks. JSON backups (schema v2) contain working/stored EQ, mediator
settings, the six A50 sliders (stream Game/Mic/Aux/Chat, microphone output,
onboard sidetone) and microphone EQ/noise gate, both banks. Older v1 backups
(EQ + mediator settings only) still import; mic/stream tabs stay disabled for
a v1-schema document until a live full-schema snapshot is loaded over it.
`.astroeq` import/export is per slot and preserves raw bandwidth precision.
Neither file import writes to the headset until the write button is pressed.
Files are created exclusively so existing backups are not silently overwritten.

Offline inspection: `/usr/bin/python3 tools/a50_gui.py --snapshot BACKUP.json`.
Hardware writing is disabled. Read-only smoke checks add `--smoke`: they read,
render, assert EQ values survive the UI unchanged, capture `/tmp/a50-ui-smoke.png`
and exit. A live desktop smoke check has succeeded. `tools/check_gui.py --live` subsequently exercised an actual write-button
gain change, independently checked hardware readback, restored through the button,
and compared all captured settings with the recovered baseline. It also exercised
a Microphone-tab slider (sidetone) and the noise-gate combo box through real
button clicks, independently checked hardware readback, and restored through the
button — exact before==after across the full device document (schema v2). It
also tested a synthetic disconnect and successful rediscovery/reload. This
proves the GUI path for both EQ and mic/stream controls; listening and physical
unplug/reinsert remain separate pending checks.

No firmware update/reset/raw-opcode control is exposed. Audio-profile switching
and sounds remain pending approval. The existing config artifact has not been
installed. Use docs/FEATURES.md for precise acceptance gaps.

`python3 tools/a50_audio.py` prepares a read-only plan from the current
PipeWire card/sink/source JSON. It validates USB identity, lists physical and
virtual routes separately, and prints exact switch/restore argv without
executing it. On this host existing virtual A50_Game/A50_Voice sinks coexist
with the physical IEC958 sink. Their presence does not prove independent USB
audio. No routes were created or modified by this work. The Device/audio tab
shows the same live plan. Profile activation remains pending approval.
