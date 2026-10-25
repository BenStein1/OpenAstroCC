# Astro A50 Gen 3 (Europa) — Technical Implementation and Reverse-Engineering Guide

**Status:** canonical, implementer-oriented guide as of October 25, 2026.
**Scope:** the personally tested **2016-generation A50 Wireless + Base Station**, USB **VID 9886 / PID 0015**. This is *not* a general protocol for Gen 4, A20, Mimas, Logitech-branded replacements, or all Astros.
**Audience:** developers who want to implement or review native support without reverse engineering the original Windows software again.
**Primary implementation:** tools/a50.py, tools/a50_setup.py, tools/a50_audio.py. This guide records both decoded protocol behavior and what was actually tested.

## 0. Important: where to trust the evidence

Use this document plus docs/A50-PROTOCOL.md and docs/FEATURES.md for the **current, corrected A50-specific result**. docs/FINDINGS.md is the valuable **chronological lab notebook**. Sections 5, 7–9 and 14 of FINDINGS contain early A20-derived guesses and tests that were later corrected. Those early 0x63/{page,slot} requests **are not the Gen 3 A50 gain reader**; do not copy them. The real A50 gain GET is opcode 0x69 with a **one-byte 1-based slot**, and 0x63 with slot+five values is the A50 **setter**. This difference was established by walking model registration, A50 vtables and constructor paths, and then confirmed in bounded real-device tests.

Evidence categories used below:

- **USB descriptor**: hardware truth from lsusb, /proc/asound and HID descriptors; identifies advertised capabilities, not perceived audio quality.
- **Static trace**: reverse engineering the actual compatible Windows executable, linked to a particular SHA and function address.
- **Live transaction**: actual device request/reply plus before/after GET comparison.
- **Physical listening**: user pressed an actual headset button and reported audible results.
- **Not yet verified**: future work; do not convert an assumption into protocol behavior.

Reference code and research records:
- docs/A50-PROTOCOL.md — exact corrected A50 class binding and detailed command evidence.
- docs/FINDINGS.md — 2026-10-24 research notebook, including disproven hypotheses.
- docs/FEATURES.md — feature-level acceptance ledger and unresolved physical tests.
- docs/HARDWARE-TESTS.md — controlled physical/audio test plans.
- docs/EQ-RECOVERY.md — working/stored bank semantics and restoration.
- docs/AUDIO-PIPELINE.md — 5.1 Game audio, EasyEffects, LSP EQ and routing research.
- evidence/ — reproducible nonprivate USB, kernel and selected protocol observations.
- artifacts/ (gitignored) — full preserved proprietary Windows app, device captures, Ghidra/REA dossiers and backups; not required by people using this open-source implementation.

## 1. Provenance and methodology: how the protocol was established

The owner's modern Microsoft Store Astro Command Center **did not work** for the Gen 3. An older *working* classic Astro Command Center installation was copied from Windows without modifying it. This was the correct primary target; the Store build is only secondary reference material.

### 1.1 Preserved source and identity

- Classic executable: ASTRO Command Center.exe, **version 1.0.226**, 32-bit native MSVC/Qt5 (NOT .NET).
- SHA-256: **991e558129af98765cba4f02b10fa5cc4d537e2b6bb4bd3032ca010832eb2dcf**.
- Imports: Qt5Core/Gui/Widgets/Xml/Network, quazip, HID.DLL, SETUPAPI.dll, Windows C++ runtimes.
- The old Windows installation includes five factory .astroeq files and related local user state; no firmware has been reflashed.
- Reverse engineering used Ghidra 12.1.4/REA and cross-referenced protocol structures with Windows app logs, shipped preset files, USB HID descriptors and **bounded live hardware reads/writes**.

### 1.2 Why looking for opcodes alone failed

The old study found opcode 0x63 and guessed it read EQ gains with a two-byte {page,slot} payload. That function belonged to **Devices::AstroA20** (PID 9886:001c). A deliberately bounded live test against A50 9886:0015 produced "HID_ERROR_NO_EQ_WITH_THAT_VALUE" and a 2-byte response, proving that the assumed A50 binding was wrong despite valid framing.

The fix was not brute-force USB commands. The investigation instead:

1. Found the **runtime model registry** at address 0x41ae40; registered PID **9886:0015** via factory **0x419b00**, runtime ID constructor **0x483640**.
2. Followed A50 allocation and ctor at **0x4821a0**, the Devices::AstroA50 vtable, and Europa headset/mediator/microphone/stream-mix subdevices.
3. Located A50 headset initialization **0x485fd0**; identified exact opcode **0x69** GET, slot 1–3, then opcode **0x70** coefficient reads.
4. Walked each relevant **A50-specific** setter and bounded validation routine instead of matching opcodes from unrelated device classes.
5. Reimplemented the HID transport with no raw-opcode CLI option. Queried the actual device, captured full TX/RX packets, tested bounded reversible changes, and **verified readback and restoration**.

Useful static entry points are in docs/A50-PROTOCOL.md: 0x4794f0 (packet builder), 0x4078f0 (HID serializer), 0x404550 (WriteFile transport), 0x485fd0 (A50 headset init), 0x488ab0 (gain SET), 0x489f10 (coefficient SET), 0x488d10 (settings/sync), 0x484440 (identity), 0x48a210 (current UI). The A50 RTTI/vtables are also recorded there.

The SHA and addresses are specific to the copied **1.0.226** binary. They are not stable APIs and will not transfer unchanged to another build.

## 2. Physical USB topology and audio interfaces

The connected base enumerated as USB vendor 9886, product 0015, manufacturer Astro Gaming, product Astro A50, with **seven interfaces**:

| Interface | USB function | Description |
|---|---|---|
| 0 | Audio Control | Astro A50 Voice function |
| 1 | Audio Streaming IN | Headset **microphone**, mono 16 kHz |
| 2 | Audio Streaming OUT | **Voice/chat playback**, stereo 48 kHz |
| 3 | Audio Control | Astro A50 Game function |
| 4 | Audio Streaming OUT | **Game playback, six channels at 48 kHz** |
| 5 | Audio Streaming IN | Aux/line input, stereo 48 kHz, **not the headset microphone** |
| 6 | Vendor HID | Command/control interface used by this guide |

Kernel ALSA PCMs on the original tested host were **hw:1,0 = Voice** and **hw:1,1 = Game**. The card number **1 is incidental**: never hardcode it when implementing discovery on another host.

The descriptor-provided six-channel Game positions are **FL FR FC LFE RL RR**. These are *real USB channels* and must be mapped **1:1**, not mixed together to simulate 5.1. Voice must stay an independent stereo output: the real right-earcup **Game/Voice press control** changes their relative hardware balance. The wheel remains overall volume.

**Verified live:** separate 440 Hz Game and 880 Hz Voice tones played simultaneously; pressing the physical Game side favored Game and pressing Voice favored Voice. The physical Dolby/source button changed spatial rendering audibly under a six-channel test. These are distinct from whether every PC game routes channels correctly or whether LFE position was independently validated, which still require testing.

The **pro-audio** PipeWire/ALSA card profile exposed two output sinks and two input sources on the tested host. Standard consumer profiles typically exposed only one sink and therefore obscured the independent hardware mixer. The raw Game pro-audio node exposed generic **AUX0..AUX5** positions; games might fail to negotiate 5.1 until the output is relabeled to the six real speaker positions.

The existing tested remap solution (config/15-astro-a50-remap.conf) exposes **A50 Game 5.1**, Voice and Mic, and has demonstrated 1:1 physical connections and SDL2 six-channel negotiation. The proposed native WirePlumber node-mapping approach (config/51-astro-a50-pro-audio.conf) is *an alternative*, not something to stack on top of an AUX-expecting remap. They can conflict. Startup persistence, late hotplug and post-restart device map are still not validated.

The standalone installer in **tools/a50_setup.py** detects 9886:0015 and parses ALSA stream descriptors to distinguish Game 6ch/48k, Voice 2ch/48k and Mic mono/16k. It can preview and, with explicit consent, write an owned per-user WirePlumber 0.5.x config. It refuses conflicting legacy A50 configs, never changes system-default speakers and does not restart audio services itself. Verify on actual hardware before declaring automatic setup complete. For users with different USB IDs/descriptors, **fail closed**, do not guess by brand string alone.

References: evidence/lsusb-v-9886-0015.txt; evidence/asound-stream0-voice.txt; evidence/asound-stream1-game.txt; docs/HARDWARE-TESTS.md and docs/FEATURES.md.

## 3. HID transport: bytes on the wire

The vendor HID descriptor advertises report ID **0x02**, 63 opaque data bytes and 64-byte reports in both directions, interrupt OUT endpoint **0x05** and IN **0x85**. The host normally exposes a **/dev/hidrawN** path; N is dynamic.

### 3.1 Request framing

Zero-pad each report to 64 bytes. Report layout:

    Byte offset | Meaning
    0           | HID report ID: 02
    1           | opcode (e.g. 69)
    2           | low 6 bits: application payload length; high 2 bits: sequence 0..3
    3...        | payload bytes (zero-filled to byte 63)

If opcode bit 7 is set, insert **0x0A** at offset 3, put the original payload at offset 4, and count that marker in the low-six-bit length. Application payload maximums are **61 bytes normally**, **60 with extended marker**. This follows report capacity rather than the theoretical 63-byte length field.

Example **GET working/stored EQ gains for slot 1**, sequence 0:

    02 69 01 01 00 00 ... (pad to 64 bytes)

Implementation: a50.frame(command, payload, sequence), a50.unframe(raw_report).

### 3.2 Reply matching and validation

The request opcode is **not** the first reply byte: successful replies use first application byte/status **0x02**. On a response, the low-six-bit length and top-two-bit sequence are in the same positions. The response's **sequence must match** the outstanding request. Discard other reports within a bounded wait; do not resend indefinitely. Validate:

- Exact 64-byte report with report ID 02.
- Sequence match modulo four, no truncated payload, extended marker if applicable.
- **Status 02** for standard successful transactions.
- For commands that echo opcode/arguments, check the specified echo prefix and minimum payload length before decoding any value.
- Error statuses carry a little-endian 4-byte error code followed by a NUL-terminated ASCII message; display it, do not reinterpret as normal data.
- **Exception:** brightness **SET 0x75** was observed to return **status 00 and empty payload**. This specific known exception is allowed, followed by a nine-channel GET/readback. Do not generalize it to other commands.
- Require complete 64-byte write. The implementation uses a 2-second reply deadline, a cooperative exclusive lock on the hidraw descriptor and per-transaction capture of TX/RX.

The Linux client also checks opened fd identity with **HIDIOCGRAWINFO** and requires bus USB, VID 0x9886, PID 0x0015 before exchanging packets. Avoid trying to "find the headset" by guessing hidraw numbers or sending probes to unrelated devices.

### 3.3 Sequence / status facts

- Sequence is the top two bits of the second application byte: **0, 1, 2, 3 and wrap**.
- Reply success marker is **0x02**, not the echoed opcode.
- A50 gain read success *does* subsequently echo **69,slot** inside the response payload; different commands may have different echo requirements.
- A missing response is an error after the deadline, **not** an instruction to brute-force other commands.
- High-bit opcodes (including 0x83 identity GET) require the extended framing marker. An unidentified opcode such as **0xDA must never be guessed or transmitted**.

## 4. Complete supported command reference (Gen 3 PID 0015)

All hexadecimal opcodes below are currently implemented with strict payload formats/validation in tools/a50.py. The left side distinguishes read-only operations from bounded writes. Integer bytes are unsigned unless otherwise noted. Many GETs return separate **working** and **stored** banks; writes update **working** only until explicit persistent sync.

| Function | GET | SET | Request payload for GET / SET | Successful GET data decoded |
|---|---|---|---|---|
| EQ gains | **69** | **63** | GET: slot 1..3 (one byte); SET: slot, then five (gain + 12) bytes | echo 69,slot; five working raw-minus-12 gains; five stored raw-minus-12 gains |
| EQ frequency and bandwidth | **70** | **6F** | GET: slot,band (1..3; 1..5); SET: slot,band, LE16 bandwidth, LE16 frequency | echo 70,slot,band; LE16 working bandwidth, stored bandwidth, working frequency Hz, stored frequency Hz |
| Default Game/Voice balance | **77** | **73** | GET: empty; SET: byte 0..255 | First response byte is current default balance |
| Dock brightness | **79** | **75** | GET: empty; SET: nine channel bytes, 20..70 each | First nine bytes are per-channel brightness |
| Alert volume | **7A** | **76** | GET: empty; SET: byte 0..100 | First response byte is alert level |
| Current UI/status | **72** | — | GET: byte 01 | 16-byte tagged response: EQ position, hardware balance, battery/charging (see section 5) |
| Base firmware identity | **03** | — | empty | 37-byte base identity; LE32 firmware word at offset +21 |
| Headset firmware identity | **83** | — | empty + required extended framing marker 0A | 37-byte headset identity; LE32 version at offset +21 |
| USB stream mix + sidetone sliders | **68** | **62** | GET: 1-byte selector 0..5; SET: selector + level byte 0..100 | echo 68,selector; working level, stored level |
| Microphone noise gate | **6A** | **64** | GET: empty; SET: exactly one approved 12-byte preverified gate packet | echo 6A; working 12 bytes and stored 12 bytes |
| Microphone EQ selection | **7B** | **71** | GET: empty; SET: mode byte 0..2 | Current mic EQ mode byte (GET has no opcode echo) |
| Persistent apply / sync ALL settings | — | **61** | empty | echo 61; completion status byte 0 means complete; 2 means busy, not retried automatically |

**Critical correction:** gain SET 63 is **not** the disproved A20 two-byte page/slot request. Its A50 payload is **six bytes: slot plus all five gain values shifted by 12**.

### 4.1 Gain and frequency encoding

- Three physical EQ slots are addressed by **1,2,3**, not zero-indexed A20 slot numbers.
- Each slot has **five gain values**, integers **−12..+12 dB**; raw USB payload stores **gain+12** (so zero dB is 12).
- Each band has a **frequency**, 80..15000 Hz, LE16 in coefficient replies.
- Only **bell bands 2,3,4** have configurable bandwidth; bands 1 (low shelf) and 5 (high shelf) must have **bandwidth_raw=0**.
- Bell bandwidth is **octaves in unsigned 4.12 fixed point**: raw = round(octaves × 4096). Valid native API range raw **409..12288** (about 0.1..3.0). E.g. 1.0 = 4096; 1.6 ≈ 6554; 2.0 = 8192.
- A50 coefficient GET response: echo [70,slot,band] followed by **four little-endian uint16** in order **working bandwidth, stored bandwidth, working frequency, stored frequency**.
- A50 coefficient SET: [slot,band] then little-endian **bandwidth_raw** then **frequency**. The client confirms exact working bank readback.
- The GUI shows a simpler "Narrow ↔ Wide" slider centered at 1.0 octave but preserves the original 4.12 value until a user edits it.

### 4.2 Slider selectors and mic mode enums

0x68 GET and 0x62 SET select these verified A50StreamPort/microphone fields:

| Selector | UI key | Meaning |
|---|---|---|
| 0 | stream_microphone | USB stream-port mic level |
| 1 | stream_chat | USB stream-port chat level |
| 2 | stream_game | USB stream-port game level |
| 3 | stream_aux | USB stream-port auxiliary level |
| 4 | microphone_output | Microphone output level |
| 5 | sidetone | Locally monitored microphone level, 0..100 |

The sidetone setting controls the headset's own monitoring path where supported; do not emulate it with a delayed PipeWire microphone loopback. Its actual listening quality remains a physical test item.

Noise gate enum, the **only four supported 12-byte payloads** in current client:
- 0: **Home** — LE32 words 0x08e40132, 0x00c60f90, 0x0080002a.
- 1: **Streaming** — 0x08e40132, 0x00c60790, 0x00800067.
- 2: **Tournament** — 0x08e40132, 0x00c60f90, 0x0080000a.
- 3: **Night** — 0x09040122, 0x00c60f90, 0x008000ca.

These are **literal verified original Windows driver-setting packets**. Do not improvise arbitrary thresholds or single-byte noise-gate values. The client reads 24 bytes (working+stored gate blocks), compares with known enum packets and refuses unknown gate data for write-back. Mic EQ modes: **0 Bright, 1 Airy, 2 Warm**. Reversible numeric write/readback checks passed; acoustic behavior is still a separate test.

### 4.3 Working versus stored; persistence

Most setters only modify the *working* bank. Their GET replies expose working and stored. "Write working settings" changes the headset's volatile configuration (with baseline capture and readback) and **does not equal permanent save**.

**0x61 sync** requests persistence of **ALL working device settings**, not just one EQ band. The app exposes this only as an explicit user-confirmed "Save to headset", with readback equality check. No automatic retry of a busy status. Historical acceptance ledger records power-off/reconnect retention as an **outstanding** test; do not claim reboot persistence until measured.

Per tools/a50.py restore_working(): backup is validated; writes are sent only for differences; readback is compared; **stored banks must not change** during unsynced restoration. A failed transaction should report an error and preserve recovery evidence rather than silently claiming a rollback.

## 5. Current UI / headset state message 0x72

Request: opcode **72**, payload single byte **01**.

Decoder consumes 16 bytes. Captured replies form four 4-byte tagged groups **[02, field_id, value, 00]**. Proven offsets in the *decoded application payload*:

| Offset | Interpretation | Confidence |
|---|---|---|
| payload+6 | selected physical EQ slot 1..3 | Static consumer trace + live value |
| payload+10 | current hardware Game/Voice balance 0..255 | Static consumer trace + live value |
| payload+14 low 7 bits | battery percentage 0..100 | Static consumer trace + live value |
| payload+14 bit 7 | charging indicator | Static consumer trace + live value |
| payload+2 | currently observed value 01, field_id1 | **Unknown** — no resolved consumer or verified physical state mapping |
| other fields | not decoded | Unknown; preserve raw if logging |

The battery and slot displays in the UI are derived from this response. **Dolby state, mic-flip mute state, and actual connection state have NOT been decoded as host-readable status.** The headset's physical controls may be entirely internal; do not invent "Dolby enabled" or "mic muted" labels from unidentified bits. Reported audible Dolby behavior is still real.

## 6. EQ preset file format and names

An Astro .astroeq is **plain QSettings-style INI**, not JSON, not ZIP; it can be inspected with a text editor. Typical shape:

    [General]
    Name=Bass & Clarity

    [Eq_Bands]
    Eq_Band_1=6
    Eq_Band_2=-2
    Eq_Band_3=0
    Eq_Band_4=2
    Eq_Band_5=4
    Eq_Freq_Band_1=90
    Eq_Freq_Band_2=406
    Eq_Freq_Band_3=783
    Eq_Freq_Band_4=4001
    Eq_Freq_Band_5=7001
    Eq_Bandwidth_2=2
    Eq_Bandwidth_3=2
    Eq_Bandwidth_4=2

There are **13 numeric EQ values**: 5 gains, 5 frequencies, 3 bell widths, plus a human name in [General] Name. The headset receives the **numeric values and slot ID**; no USB preset-name field has been established. Local name metadata is kept separately from firmware.

The repo layout is intentionally simple:
- **presets/*.astroeq**: original factory Astro defaults (protected/read-only through the app; third-party redistribution rights should be reviewed before public publication).
- **presets/custom/*.astroeq**: custom profiles such as Bass & Clarity, editable in writable source checkouts.
- In a **read-only AppImage**, user edits save to XDG_DATA_HOME/astro-a50-linux/presets (normally ~/.local/share/astro-a50-linux/presets).
- Local EQ slot labels: XDG_CONFIG_HOME/astro-a50-linux/eq-names.json. JSON settings exports/backups may include the optional eq_names array.
- Preset picker compares actual 13 numeric values against available .astroeq files, with at most **0.01 octave tolerance** for text rounding; exact gains/frequencies are required and ambiguous same-curve names are rejected. Explicitly chosen names win.
- Editing marks the named preset "(modified)"; a new Custom save asks for name/overwrite confirmation. The original factory files must never be silently replaced.

The screenshot-derived **Bass & Clarity** bundled custom profile is +6/−2/0/+2/+4 at 90/406/783/4001/7001 Hz, with all three bell widths precisely 2.0 octaves. Loading a file into the editor does not automatically write or persist to the headset.

## 7. Safe implementation recipe for another developer

**Step A — read-only discovery**
1. Find USB device 9886:0015 via sysfs/udev/ALSA. Do not rely on a particular ALSA card index or /dev/hidraw number.
2. Read USB interface strings, HID report descriptor, ALSA PCM streams; distinguish Game six-channel playback, Voice stereo playback, headset mic mono capture, and AUX line capture.
3. Verify opened hidraw fd identity (bus USB, matching VID/PID). Avoid chmodding every hidraw node or using sudo indiscriminately.

**Step B — implement and prove the transport**
1. Implement frame/unframe exactly in section 3; test 64-byte report length, sequence 0..3 wrap, extended marker, payload bounds and malformed replies offline.
2. Implement read-only 0x69 slot1 gain GET with exact minimum lengths and echo verification; capture anonymized TX/RX, compare with original device display.
3. Add read-only 0x70 coefficient GET, 0x72 status, 0x03/0x83 identity, then settings and mic reads. Do not enable raw-opcode scanning.

**Step C — bounded setters and reversible verification**
1. Save full baseline JSON (both banks), validate firmware/device family.
2. Add only the **exact matching class-bound** setters in section 4; enforce ranges, verify each readback and restore baseline without sync.
3. Preserve the evidence if a write, rollback or readback fails. Do not claim success merely because the device ACKed.
4. Save permanently using 0x61 **only after a separate explicit user action**. Firmware-write/reset endpoints stay outside this project.

**Step D — proper Linux audio**
1. Select a profile exposing both independent USB functions (pro-audio on this hardware).
2. Publish Game as 5.1 with verified FL/FR/FC/LFE/RL/RR mapping (one-to-one channel routing), Voice as separate stereo, and headset mic as mono source. Do not route the Game aux line-in as microphone.
3. Validate graph links, app channel negotiation, simultaneous Game+Voice audio, physical right-earcup balance and Dolby. Avoid EasyEffects' ordinary stereo chain if it would downmix the Game stream.
4. Make configuration idempotent, hotplug-safe and removable; preserve preexisting system default outputs. Do not enable mutually incompatible native map and AUX remap methods together.

**Step E — release quality**
1. Add offline protocol/backup/preset/config tests; record the first real-device regression per hardware generation.
2. Check cold boot, late insertion, USB reconnect, charging transitions, physical mute, EQ slot switch, user defaults and all real game channels.
3. Show only states that the tested protocol actually returns. Mark unknowns as unknown in code and docs.

## 8. Files future contributors should open first

| Goal | Source / document |
|---|---|
| Wire framing, command client, raw limits, backup and rollback | tools/a50.py |
| Correct class registration, original binary addresses, command traces | docs/A50-PROTOCOL.md |
| Historical RE methodology and failed A20 hypothesis | docs/FINDINGS.md |
| Working vs stored bank restore semantics | docs/EQ-RECOVERY.md |
| Device USB/ALSA profile evidence | evidence/ + docs/HARDWARE-TESTS.md |
| Automated A50 audio detection and safe config provisioning | tools/a50_setup.py |
| Existing channel mapping verification | tools/a50_audio.py |
| Alternative WirePlumber and remap approaches | config/51-astro-a50-pro-audio.conf and config/15-astro-a50-remap.conf |
| Preset library, names, values | tools/a50_library.py, tools/a50_names.py, presets/ |
| User controls and native UI | tools/a50_gui.py, tools/a50_about.py |
| Acceptance tests already done versus pending | docs/FEATURES.md, docs/HARDWARE-TESTS.md |
| Releases, packaging and third-party notices | docs/APPIMAGE.md, docs/THIRD_PARTY_NOTICES.md |

## 9. Remaining unknowns and explicit safety exclusions

- Physical power-cycle and unplug/replug **persistence of synced settings** not yet proven.
- Mapping of USB status field_id1 (+2), **Dolby status, mute state, headset link** remain unresolved.
- Actual game compatibility, individual perceived surround positions/LFE, EasyEffects bypass/headroom and cold-start/hotplug native audio provisioning need real-machine testing.
- Alternative device variants (Europa/Mimas/Gen 4/A20) are **not automatically compatible** merely because an opcode or EQ file format looks similar.
- Firmware flashing, reset and unidentified opcodes (particularly unusual high-bit commands) are **not part of the application**, and must not be experimentally transmitted to users' hardware.
- The existence of a live settings write/readback does **not** prove acoustic effect, permanent save or all hardware switch states.

## 10. Respect for original vendors and release/legal boundaries

This project is an independent, unofficial open-source compatibility implementation. It targets the owner's hardware and contains protocol knowledge **not** proprietary Windows executable bytes or vendor firmware. App source is GPL-3.0-only; factory vendor presets have **independent rights** which must be confirmed before a public release. Attribution in docs/THIRD_PARTY_NOTICES.md.

Contributions correcting this guide should cite **which hardware revision, exact VID/PID, Windows executable hash or Linux code revision, raw capture/test, and the resulting observation**. Please do not "simplify" historical failed experiments away: they are exactly how we avoid having the next contributor repeat the original reverse engineering.
