# Automatic A50 Gen 3 audio detector and setup (experimental)

The standalone helper, `tools/a50_setup.py`, turns the physical Astro A50 Gen 3's two independent USB playback interfaces into appropriately named native Linux audio endpoints. It **does not combine Game and Voice streams**: preserving that separation is what makes the headset's physical Game/Voice balance button work.

For a supported `9886:0015` Gen 3, it identifies **Game** (6-channel, 48 kHz; FL/FR/FC/LFE/RL/RR), **Voice** (2-channel, 48 kHz), and **Microphone** (mono, 16 kHz) from the kernel's ALSA stream descriptors rather than guessing the card number or channel order. Then it can create *one* persistent per-user WirePlumber 0.5.x configuration that labels Game as `Astro A50 Game 5.1`, Voice as `Astro A50 Voice`, and the mic as `Astro A50 Microphone`.

## Run (standalone; system Python, no Python dependencies)

```bash
python3 tools/a50_setup.py detect
python3 tools/a50_setup.py preview
python3 tools/a50_setup.py install --yes
python3 tools/a50_setup.py verify
python3 tools/a50_setup.py uninstall --yes
```

- **detect / preview:** read-only; headset must be connected. Preview prints the exact proposed configuration.
- **install --yes:** requires a connected supported device and WirePlumber 0.5.x. Writes `~/.config/wireplumber/wireplumber.conf.d/52-astro-a50-auto.conf` (or `$XDG_CONFIG_HOME/wireplumber/...`) *only if no conflicting legacy A50 config or existing differing file is present*. Repeat installs with identical content are no-ops.
- **verify:** read-only check of active `pro-audio` profile and the raw native Game, Voice and mic endpoint names, ownership and channel maps. This is **not** a complete real-time audio graph or listening test.
- **uninstall --yes:** removes only the owned configuration file, never the original user files.

No command automatically runs `pactl load-module`, sets default audio outputs, changes global audio settings, restarts services/Plasma, or writes headset HID/firmware. To activate an installation, log out and back in when convenient, then check `verify` and test simultaneous Game/Voice and physical earcup buttons.

**Important for Ben's current system:** It already has `51-astro-a50-pro-audio.conf` and `15-astro-a50-remap.conf`, which represent **different incompatible channel mapping strategies**. The new helper deliberately refuses to install over them. They must be reviewed and migrated *manually and reversibly* before use; your current live setup should remain untouched.

## Offline regression tests

```bash
python3 -m unittest discover -s tests -p test_a50_setup.py -v
```

These use simulated USB and PipeWire inventory data: different ALSA indices and PCM orders, wrong USB IDs, ambiguous descriptors, invalid maps, inherited card identity, conflicting config files, repeated install, uninstall, and fixture-only read paths. They do not need a headset.

## Release gates / known limitations

1. **Cold start not yet proven.** The generated native monitor rules must be validated with `pw-config`/WirePlumber on the target Linux machine and tested after a fresh session. WirePlumber may restore a previously selected profile instead of the new requested `pro-audio` initial profile; the read-only `verify` result exposes that failure. Do not claim the tool is fully automatic until this has been tested and handled.
2. **Physical hardware acceptance:** confirm 6 separate game channels, real game/Discord routing, Dolby processing, the independent Game/Voice earcup control, reconnect/hotplug and that existing default speakers/mic stay unchanged.
3. **No auto-repair service yet.** The config is intended to create native endpoints at device discovery; the helper does not stay running as a background daemon. Verify behavior when USB appears after login and when WirePlumber restarts.
4. **No other headset generations by default.** A50 Gen 4, other PIDs, different ALSA descriptors, multiple identical headsets and WirePlumber 0.4/0.6+ deliberately fail closed. Expand only with tested hardware evidence.
5. **GUI integration is a later step.** Once boot/hotplug behavior is tested, the PyQt6 app can call these functions behind a user-approved `Set up audio` / `Repair audio` interface, showing a preview and a clear rollback.

Reference: [WirePlumber 0.5 ALSA configuration](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/alsa.html) and [node priorities](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/priorities.html).
