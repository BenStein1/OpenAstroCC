# Development, local testing and project checkpoints

This file contains technical detail and test history intentionally kept out
of the public-facing [README](../README.md). For the protocol-level source of
truth, read [Gen 3 implementation guide](GEN3-IMPLEMENTATION-GUIDE.md).

## Supported hardware and observed implementation status

The tested device is an Astro A50 Gen 3 / Europa with USB ID
`9886:0015`. The native Python HID client reads and writes three EQ slots,
gain/frequency/bandwidth, dock and microphone controls, battery/charging,
Game/Voice balance and firmware identity. The app performs a baseline backup,
bounded writes and exact readback checks before reporting success.

The 2026-10-24 hardware session completed **38 reversible device-control
checks**, restoring the baseline. This proves transaction/readback behavior,
not every audible effect or all long-term storage semantics. Read
[FEATURES](FEATURES.md) for the detailed evidence and remaining gates.
The existing physical-headset checks included hearing separate Game and Voice
test tones simultaneously and changing their balance with the earcup buttons.
A separate six-channel listening comparison was performed with Dolby toggled.
Individual LFE/position fidelity and many real-game cases remain unverified.

## Local GUI and CLI

Running from source requires system Python with PyQt6 installed:

```bash
python3 tools/a50_gui.py
```

Read-only inspection and export:

```bash
python3 tools/a50.py inventory
python3 tools/a50.py snapshot -o /tmp/a50-backup.json --capture /tmp/a50-capture.json
python3 tools/a50.py selftest
python3 tools/check_settings.py
```

Offline GUI checks can be run without the actual headset:

```bash
QT_QPA_PLATFORM=offscreen python3 tools/a50_gui.py --snapshot evidence/a50-baseline.json --smoke
QT_QPA_PLATFORM=offscreen python3 tools/check_gui.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The live GUI regression mode can issue reversible HID writes and must not be
used casually:

```bash
python3 tools/check_gui.py --live
```

Review that script before using live mode. No firmware flashing, reset, or
unidentified raw-command exploration is part of this project.

## Applying versus persisting settings

**Test Current Settings** updates working device parameters from the editor.
It first snapshots the headset, compares the last on-screen read to current
hardware, writes changed fields only, and verifies readback. The changes
remain in working memory; nothing in this action sends the persistent sync.

**Save to headset** is a distinct confirmed action that asks the hardware
to sync **all current working settings**, including microphone/stream state.
Physical power-loss persistence still requires hardware acceptance testing.
**Save preset…** writes a local `.astroeq` file rather than applying anything.

JSON backup/import and per-slot `.astroeq` import/export are supported.
JSON backups include EQ, dock, microphone/stream state and noise gate; old
schema-v1 backups remain import-compatible. Headset preset *names* live
locally because no text-name field was identified in the A50 USB protocol.

## Six-channel audio integration and caveats

Kernel ALSA descriptors expose **6-channel / 48 kHz Game**, **2-channel /
48 kHz Voice** and a **mono / 16 kHz headset mic**. In the tested
`pro-audio` profile, the raw Game sink presents six AUX channels. The
tested Pulse/PipeWire remap provides named **Game 5.1** speaker positions
FL/FR/FC/LFE/RL/RR, independent stereo Voice, and mono Mic. The mapping
was verified against `pw-link` and SDL2 channel negotiation. This is not
software-fabricated surround or a Game/Voice downmix.

Two alternative configurations have been investigated:

- `config/15-astro-a50-remap.conf` — live-tested AUX-to-5.1 remap.
- `config/51-astro-a50-pro-audio.conf` — native WirePlumber mapping approach
  that changes the expected raw channel labels.

**Do not enable both strategies at once without adapting the raw master
channel names.** The separate `tools/a50_setup.py` discovers hardware using
USB identity and ALSA descriptors and offers a guarded install path,
refusing to overwrite incompatible legacy configurations. It does not
change default speakers/mic or restart audio services.

During local surround work, a default sink/source unexpectedly switched
to the A50 and was manually restored. Rules setting
`priority.session = 0` were prepared to avoid taking priority from existing
devices, but the restart-gated fix and clean login/hotplug persistence still
need verification. See [FEATURES](FEATURES.md),
[AUTO-AUDIO-SETUP](AUTO-AUDIO-SETUP.md) and
[HARDWARE-TESTS](HARDWARE-TESTS.md).

Standard EasyEffects releases inspected in
[AUDIO-PIPELINE](AUDIO-PIPELINE.md) use a stereo DSP pipeline; sending
a six-channel game stream through them can collapse surround separation.

## Packaging and local privacy

Build an AppImage through `bash scripts/build_appimage_local.sh`; the
GitHub Actions workflow tests/builds on an older Linux baseline when
hosted minutes are available. An AppImage is not sandboxed like Flatpak,
but its own image is read-only. Saved custom EQs, local labels and
transaction backups go into XDG user directories (see [APPIMAGE](APPIMAGE.md)).
When running an editable Git clone, custom EQ files default to
`presets/custom/`.

The `artifacts/` and private test captures are intentionally ignored.
Paths, screenshots and incident notes tied to an individual workstation
are not part of the public README. Do not add raw private captures,
user settings, secrets, or vendor executable backups to public commits.
The vendor-authored factory preset redistribution question is documented
in [third-party notices](THIRD_PARTY_NOTICES.md).

For contributions, keep hardware observations, static reverse-engineering
inferences and unverified hypotheses clearly separated; cite USB IDs,
packet captures, code revisions and test conditions.
