# Astro A50 Gen 3 for Linux

**For developers and future maintainers:** [Gen 3 implementation and protocol guide](docs/GEN3-IMPLEMENTATION-GUIDE.md)
documents the actual USB hardware, exact HID framing, all supported read/write
commands, EQ wire encoding, physical Game/Voice audio routing, reverse-engineering
methodology, validated evidence and remaining unknowns. It supersedes the
older A20 hypotheses in the chronological [research notebook](docs/FINDINGS.md).

**GitHub Actions failing before tests run?** See
[GitHub reliability and zero-runner troubleshooting](docs/GITHUB-RELIABILITY.md).

## Downloadable AppImage and license

This project is licensed under **GNU GPL version 3 only** (see [LICENSE](LICENSE)).
You're free to use, share, modify and redistribute it under GPLv3, including
commercially, without any warranty or support obligation. PyQt6's GPL version
is why this can't simultaneously be marked "non-commercial only."

Build the **x86_64 AppImage** locally in one command:
`bash scripts/build_appimage_local.sh`, or download a successfully tested
build artifact from the [GitHub Actions AppImage workflow](.github/workflows/appimage.yml)
when hosted runners are available.
It bundles Python, PyQt6/Qt, the app, preset files and complete license texts.
The **About** dialog displays attribution notices and has an **orange Audio
setup…** button. That action only installs WirePlumber configuration after
showing a preview and receiving explicit confirmation.

See [AppImage build and usage](docs/APPIMAGE.md) and
[third-party attribution details](docs/THIRD_PARTY_NOTICES.md).

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

**Named EQ slots:** tabs remain short (**EQ 1**, **EQ 2**, **EQ 3**), with
**Preset name:** shown under each tab and a **Rename EQ…** button. Names are
local metadata, not fields in the headset firmware. When original Astro
`.astroeq` files exist in the locally preserved `artifacts/` tree or the
user's preset folder, the app attempts to recognize a factory preset by
matching all thirteen numeric EQ parameters. It never guesses by slot number;
custom names always take precedence. Importing `.astroeq` adopts
`[General] Name`, exporting retains the displayed name, and JSON backups
include optional `eq_names`. The local saved labels live in
`~/.config/astro-a50-linux/eq-names.json` (or `$XDG_CONFIG_HOME`).
A clean clone without factory preset files will show Unnamed until a preset
is imported or renamed.

**Preset library:** Each EQ tab has **Choose preset…** and **Save preset…**.
Choose from **Astro** factory presets (protected `presets/*.astroeq`) or
**Custom** presets (`presets/custom/*.astroeq`, including Bass & Clarity).
When running from a writable Git checkout, **Save preset… defaults to
`presets/custom/`**; any custom file may be overwritten with confirmation.
An AppImage/read-only installation saves to `~/.local/share/astro-a50-linux/presets/`
(or `$XDG_DATA_HOME`), and the picker includes those too. The bundled custom preset uses +6/-2/0/+2/+4 dB at 90/406/783/4001/7001 Hz with 2.0-octave
middle bands. Loading changes only the **editor**, not the headset. Editing
shows **(modified)** and switching with unsaved edits asks whether to save,
discard or cancel. **Save preset…** creates a named personal file or, with
explicit approval, overwrites **only a Custom preset**, never the five protected Astro originals. `.astroeq` files are text, not
headset firmware. See [native app behavior](docs/NATIVE-APP.md).

**About / audio setup:** The small bottom-right **About** button opens
third-party license notices and an **Audio setup…** dialog. Audio setup
previews device detection and WirePlumber changes first, then requires a
separate approval before creating its per-user config. It does not change
system audio defaults or restart services. See
[third-party notices](docs/THIRD_PARTY_NOTICES.md). A project license and
packaged dependency notices must be finalized before an AppImage release.

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
