# Native app

Run `/usr/bin/python3 tools/a50_gui.py`. The system Python has PyQt6; the
pyenv default does not. No packages or global configuration were installed.

UI (2026-10-25 redesign): dark themed window. Each EQ tab has an interactive
graphic EQ: a log-frequency response curve (estimated with RBJ biquads at 48 kHz,
not a measurement of the headset DSP) with draggable band nodes (vertical = gain,
horizontal = frequency, mouse wheel on a bell = bandwidth), plus per-band gain
sliders and exact frequency/bandwidth boxes. "Volume and balance" has sliders for
Game/Voice balance, alert volume and the four stream levels; the microphone and
dock pages use sliders too. Control semantics and the write path are unchanged.
The Game/Voice end labels follow the existing label order and are not yet
confirmed against hardware. Offscreen check: `QT_QPA_PLATFORM=offscreen python3 tools/check_gui.py`.

The Microphone page has **Test sidetone**. It is a toggle: it writes only the
sidetone level shown to the headset's working settings (backup + readback, nothing
persisted) and starts a live peak meter of the A50 mic (`parec` on the `A50_Mic`
source, falling back to another A50 source) with a "Talking" indicator. While it
runs, changing the sidetone slider, microphone EQ or noise gate writes them (working
settings only) after a short pause, so you can leave it open and hear each change. **Stop test** (or closing the app) stops the
capture. Other unwritten editor edits are kept in the editor and still
need **Write working settings**.

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
executing it. The Device/audio tab shows the same live plan.

`inventory()` attaches several live, read-only proofs rather than relying on
presence/absence alone:

- `uac_ground_truth()` reads `/proc/asound/cardN/stream0`/`stream1` directly
  from the kernel (independent of whichever PipeWire ALSA-card-profile is
  active) and reports the real channel count/rate/channel-map per USB Audio
  Class interface. On this host: hw:1,0 is 2ch 48k out + 1ch 16k mono in
  (Voice), hw:1,1 is 6ch 48k out + 2ch 48k in (Game) -- confirming the
  topology comment with hardware descriptors, not inference.
- `trace_virtual_routes()` parses live `pw-link -l` port links to find which
  physical sink each virtual A50_* sink's audio actually reaches right now,
  and flags it when two differently-named virtual sinks share one physical
  destination. **Superseded (2026-10-24):** this previously caught Ben's old,
  now-`disabled` `a50-loopback-{game,voice}.service` units both forwarding
  into the same physical `iec958-stereo` sink under the old single-sink
  profile. `pro-audio` plus the new `A50_Game_51`/`A50_Voice`/`A50_Mic` remap
  nodes (different names, no collision with the old disabled units) replace
  that setup; see README.md and `remap_status()` below.
- `remap_status()` (2026-10-24) checks the `module-remap-sink`/
  `module-remap-source` nodes installed by `config/15-astro-a50-remap.conf`
  that relabel the A50's raw `aux0..auxN` channels into app-recognisable
  positions (FL/FR/FC/LFE/RL/RR for Game, FL/FR for Voice, MONO for the mic).
  `--verify` exits 1 if any are missing or mismapped. SDL2-level enumeration
  and 6-channel negotiation proof (both pulseaudio and pipewire drivers) is in
  `artifacts/surround-integration/sdl-*-probe.log`.
