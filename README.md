# OpenAstroCC

**Open-source Command Center for the Astro A50 Gen 3 on Linux.**

OpenAstroCC is an unofficial Linux application for configuring the Astro A50
Gen 3 headset and base station, including its equalizer, microphone, dock,
and separate Game/Voice audio paths. It was built to make older hardware
useful without depending on the original Windows software.

**Supported hardware:** Astro A50 Gen 3 / Europa, USB `9886:0015`.
Other generations and USB IDs have **not** been verified.

## Features

- Three editable five-band EQ slots with a draggable response curve, frequency
  fields, and narrow/wide octave controls.
- Protected Astro factory presets and editable custom `.astroeq` profiles;
  import, export, name and save your own EQs.
- Headset battery/charging status, current EQ slot, microphone controls,
  sidetone, noise gate, dock brightness, and Game/Voice balance settings.
- Device backup and restoration with verified readback.
- Separate six-channel Game, stereo Voice and mono microphone outputs on
  supported Linux audio configurations.
- An **About → Audio setup…** tool that previews optional user-level
  PipeWire/WirePlumber configuration before requesting permission.

## Get started

**AppImage (Linux x86_64):** download an artifact from a
[successful AppImage workflow run](.github/workflows/appimage.yml), or build
one from a clone of this repository:

```bash
bash scripts/build_appimage_local.sh
```

The build produces `dist/OpenAstroCC-x86_64.AppImage`. On a compatible
AppImage runtime, launch it with:

```bash
chmod +x dist/OpenAstroCC-x86_64.AppImage
./dist/OpenAstroCC-x86_64.AppImage
```

If your AppImageLauncher cannot read its compression format, run the already
built app from `./dist/AppDir/AppRun`. Details and older-Linux compatibility:
[AppImage build and troubleshooting](docs/APPIMAGE.md).

**Run from source:** with Python 3 and PyQt6 installed on Linux:

```bash
python3 tools/a50_gui.py
```

USB device permissions and host audio routing may need one-time setup. See
[Audio setup](docs/AUTO-AUDIO-SETUP.md) before changing system configuration.

## Applying EQ and headset settings

1. Choose a preset or adjust the EQ by dragging its colored points or editing
   the frequency and bandwidth controls.
2. **Test Current Settings** applies the current editor values to the headset's
   *working* settings, with a backup and readback. It does **not** save
   those changes permanently.
3. **Save to headset** explicitly persists the current headset configuration.
   **Save preset…** is different: it writes a reusable `.astroeq` file.

AppImages are not Flatpak-style sandboxes. Your custom profiles and settings
remain writable in normal user-data directories; see
[AppImage data locations](docs/APPIMAGE.md).

## Documentation

| Topic | Guide |
|---|---|
| Install, audio discovery and setup safeguards | [Automatic audio setup](docs/AUTO-AUDIO-SETUP.md) |
| Presets, controls and persistence | [Application guide](docs/NATIVE-APP.md) |
| Developer setup, tests and known limitations | [Development and verification](docs/DEVELOPMENT.md) |
| Full USB/HID protocol and reverse-engineering methodology | [Gen 3 implementation guide](docs/GEN3-IMPLEMENTATION-GUIDE.md) |
| Six-channel Game/Voice routing | [Audio pipeline](docs/AUDIO-PIPELINE.md) |
| Verified features versus outstanding hardware tests | [Acceptance ledger](docs/FEATURES.md) |
| Distributable build and license details | [AppImage](docs/APPIMAGE.md) · [Third-party notices](docs/THIRD_PARTY_NOTICES.md) |

## Contributing and license

Bug reports, compatibility testing, documentation corrections and pull requests
are welcome. Please identify the headset generation and USB ID when reporting
protocol behavior, and avoid testing undocumented write commands on hardware.

OpenAstroCC is licensed under **[GPL-3.0-only](LICENSE)**. See
[third-party notices](docs/THIRD_PARTY_NOTICES.md) for dependency attributions.
This is an independent project, not affiliated with or endorsed by Astro Gaming
or Logitech. Firmware and proprietary Windows application binaries are not
included. The redistribution rights for original vendor-authored EQ preset
data should be verified before a public release.
