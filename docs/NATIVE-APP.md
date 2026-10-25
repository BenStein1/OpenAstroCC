# Native app

Run `/usr/bin/python3 tools/a50_gui.py`. The system Python has PyQt6; the
pyenv default does not. No packages or global configuration were installed.

UI (2026-10-25 redesign): dark themed window. Each EQ tab has an interactive
graphic EQ: a log-frequency response curve (estimated with RBJ biquads at 48 kHz,
not a measurement of the headset DSP) with draggable band nodes (vertical = gain,
horizontal = frequency, mouse wheel on a bell = bandwidth), plus per-band gain
sliders and editable frequency boxes (the up/down stepper arrows are hidden to
avoid inconsistent rendering in packaged Qt; keyboard input and draggable
EQ nodes still work). Bands 2–4 now use horizontal **Narrow ↔ Wide**
octave-width sliders instead of six-decimal spin boxes: 1.0 octave is at the
physical midpoint, with 0.10 octave (narrow) at the left and 3.0 (wide) at
the right. The UI shows two decimals for readability but retains the exact
4.12 raw hardware value in memory until the user actually edits the slider.
Low/high shelf bands have no adjustable octave width. "Volume and balance" has sliders for
Game/Voice balance, alert volume and the four stream levels; the microphone and
dock pages use sliders too. The settings workflow is unchanged: Test Current Settings writes to the
headset's working memory with readback, while Save to headset is a separate,
explicit persistent-sync action.
The Game/Voice end labels follow the existing label order and are not yet
confirmed against hardware. Offscreen check: `QT_QPA_PLATFORM=offscreen python3 tools/check_gui.py`.

Use **Test Current Settings** to try the displayed EQ, microphone and dock
parameters; this writes the headset's working state, **not a temporary audio
preview that automatically reverts when the app closes**. You can choose a
different preset or adjust controls and test again. Use **Save to headset**
only when you want to persist the current working configuration.

## Preset picker and custom EQ library

The EQ header has a compact **Choose preset…** dropdown plus **Save preset…**.
The list has just two visible categories:

- **Astro:** the five shipped default `.astroeq` files in `presets/`; read-only.
- **Custom:** includes the bundled `Bass & Clarity` custom EQ at
  `presets/custom/Bass & Clarity.astroeq` and your personal presets in
  `$XDG_DATA_HOME/astro-a50-linux/presets/` (default
  `~/.local/share/astro-a50-linux/presets/`). **In a writable Git checkout,
  `presets/custom/` is the default save location**; all files in Custom,
  including Bass & Clarity, can be overwritten with confirmation. The five
  factory presets under `presets/` remain protected. When running as an
  AppImage or from a read-only location, saved presets go into XDG user data.

Choosing a preset **only loads its values into the editor**. The headset is
untouched until the existing **Test Current Settings** / **Save to headset**
actions. For a preset previously read from the headset, the app matches its
numeric settings to available preset files. Because Astro's Windows files
round bandwidth, numeric identification tolerates up to 0.01 octave deviation;
it still requires exact gains and frequencies and refuses ambiguous names.

Editing any gain, frequency, or bell width labels it **(modified)**; if
the starting preset had no known name, it displays **Custom (unsaved)**.
This marker is about the preset *file*, independent of whether changes have
been written to the headset. **Save preset…** saves a separate `.astroeq`
file in your personal **Custom** library, prompting for a name. When editing a previously selected
personal custom preset, it asks whether to overwrite **that file** or save
as a new one. Overwrites require explicit approval. Factory Astro files are
never overwritten; custom files are writable when their directory is writable.
Preset-file saving never sends a USB command.

The bundled Bass & Clarity custom preset rounds the original 1.99-octave bell
to exactly **2.00**. Its file is available immediately in the dropdown;
it is not silently written into the owner's existing headset slot. Select
the custom preset, then use the existing headset-write controls if desired.

## About / third-party notices / audio setup

A small **About** button is anchored at the lower-right of the main window,
separate from the EQ controls. Its dialog displays
`docs/THIRD_PARTY_NOTICES.md` (notably PyQt6, Qt, Python, PipeWire and
WirePlumber license references and outstanding release checklist). **Audio
setup…** opens a separate dialog that uses the existing standalone
`tools/a50_setup.py` to preview A50 endpoint detection and proposed
WirePlumber configuration. **Install configuration…** stays disabled until
a successful preview and requires an explicit confirmation. The helper
refuses conflicts rather than overwriting Ben's existing audio setup; it
does not require sudo, change default speakers/microphones, restart audio
services or write to the headset. Activation may require logging out/in.
Both operations run asynchronously so the interface remains responsive.

## EQ slot names (local metadata)

The hardware exposes three numbered EQ slots and their numeric parameters;
**no name field exists in the reverse-engineered USB EQ replies**. Tabs now
always read **EQ 1**, **EQ 2**, **EQ 3**; the separate **Preset name:** line
under each tab displays a local label. The status bar shows only the numbered
slot, never a redundant "· Unnamed" suffix.

When a device snapshot is read, the app searches **locally available** classic
Astro `.astroeq` preset files and compares *all five gains, all five
frequencies, and all three bell bandwidths* to each hardware slot. Only one
unambiguous matching name is displayed. Expected search directories include
the repo's preserved, git-ignored
`artifacts/classic-acc/assets/Astro A50 Wireless/Astro EQ/`,
`artifacts/appdata-classic/Astro A50 Wireless/Astro EQ/` and
`artifacts/appdata-store/ASTRO A50 Wireless/`, plus
`~/.local/share/astro-a50-linux/presets/`. Additional directories can be
provided in `ASTRO_A50_EQ_DIRS` (colon-separated on Linux). The five original Astro `.astroeq` text defaults are now included in
`presets/` by the repository owner; no proprietary Windows app binaries are
distributed. A custom device EQ that doesn't match any saved file remains
Unnamed until the user loads or saves a named preset.

**Rename EQ…** stores a user label locally in
`$XDG_CONFIG_HOME/astro-a50-linux/eq-names.json` (normally
`~/.config/astro-a50-linux/eq-names.json`); explicit labels override
automatic matches and survive refresh and app relaunch. **Name from file…**
lets a user select the original `.astroeq` file and adopt only its
`[General] Name` for the selected headset slot, **without changing its
current EQ gains, frequencies or widths**. This is especially useful for a
modified/custom preset that cannot be positively recognized by numeric matching.
The separate **Import .astroeq** action loads *both* its name and EQ parameters
into the editor. Export retains the chosen/displayed name. JSON backups
include optional `eq_names`; older backups remain valid. No naming operation
writes headset settings.

Renaming a preset only changes computer-local metadata. EQ gain/frequency/
bandwidth changes still require **Test Current Settings** and explicit
**Save to headset** to persist to device storage. Failed/malformed local
name files are not silently overwritten.

The Microphone page has **Test sidetone**. It is a toggle: it writes only the
sidetone level shown to the headset's working settings (backup + readback, nothing
persisted) and starts a live peak meter of the A50 mic (`parec` on the `A50_Mic`
source, falling back to another A50 source) with a "Talking" indicator. While it
runs, changing the sidetone slider, microphone EQ or noise gate writes them (working
settings only) after a short pause, so you can leave it open and hear each change. **Stop test** (or closing the app) stops the
capture. Other unwritten editor edits are kept in the editor and still
need **Test Current Settings**.

The app reads three EQ slots, all five frequencies and the three bell bandwidths,
dock defaults, current battery/charging, hardware balance and selected EQ slot.
It reads base/headset identity (firmware 36791/36154 on this hardware), and on
a schema-v2 device also the six sliders and microphone EQ/noise gate, shown on
the Microphone and Stream mix tabs (disabled for an offline v1 backup). Every
transaction rediscovers the A50, validates the opened fd's USB identity, takes
an exclusive cooperative lock, and closes it on completion. Status polling (battery/charging) runs every 60 s while connected and the
window is active, and once whenever the window is activated; while disconnected it
rescans every 3 s (a sysfs lookup, no USB traffic). **Refresh / reconnect** keeps
looking for up to 12 s, since the headset can drop off USB for a few seconds after
**Save to headset**. Polling is silent (the window is not greyed out or reloaded); only explicit Write/Save/Refresh grey the UI while they run. Disconnect disables writes; subsequent polls retry discovery and load
a fresh snapshot before re-enabling them. Physical unplug/reinsert still needs
Ben's test; synthetic disconnect and host GUI reads are separate evidence.

Edit controls, then **Test Current Settings** to apply the current values
without persisting them. The app compares the last snapshot
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
