---
name: Astro A50 Linux
status: active
summary: Native Linux support for the Astro A50 Gen 3 headset, including Command Center settings and separate Game and Voice audio paths.
next: Run the read-only hardware tests in docs/HARDWARE-TESTS.md, then map the remaining 0x60-0x7C opcodes and the per-feature range table before any device write.
updated: 2026-10-24
---

# Astro A50 Linux

Build a native Linux replacement for the classic ASTRO Command Center for Ben's
**A50 Gen 3**. Restore the documented headset features on KDE/PipeWire using a
userspace HID tool and the correct audio profiles, with a KDE front end later
if useful.

## Starting brief

[Original investigation and acceptance criteria](https://github.com/BenStein1/obsidian-projects/blob/main/Projects/BlueSky/Astro-A50-Gen3-Linux-plan.md).

Project folder: `/home/ben/Projects/astro-a50-linux`.
Worker: **Astra**, Claude Code; Nori worker ID
`f84cf343-c7d2-4b47-9765-24840eb5e824`.

### Active continuation

Ben requested continued implementation and durable Markdown tracking after the
first pass. **Astra-protocol** (Claude Code), Nori worker ID
`93d7e2f1-9480-4dc3-b0c6-43c9e830a4bb`, is reviewing packet boundaries and preset
validation, qualifying unsupported conclusions, and extending the Ghidra command
map. Recover this worker with Nori `get_worker` while the same Nori process is
alive; after a restart, resume from the files and commits instead.

Review identified that the 63-byte HID data area includes two command-header
bytes: a normal report can carry at most **61 payload bytes**, or **60** with
the extended marker. A quiet passive capture establishes only that no unsolicited
reports were observed during that test; it cannot rule out polling or an
initialization requirement. The continuation is correcting these limits in code
and documentation. Treat earlier stronger claims below as pending review.

An approval question is pending for switching only the live A50 PipeWire profile
to `pro-audio`, without config-file edits or a service restart. **No approval or
profile change has occurred.** Continue static analysis and verified read-only
queries independently; do not infer approval from elapsed time.

## Progress

- [x] Create the project folder and initialize Git.
- [x] Preserve both Windows app trees and their settings in the private local artifact area.
- [x] Identify the connected headset as USB `9886:0015` and save audio/HID descriptor evidence.
- [x] Start REA/Ghidra analysis of the classic Command Center executable.
- [x] Establish the HID wire format (report ID, opcode, length/sequence, padding) with evidence.
- [x] Decode the EQ protocol and cross-validate it against the shipped `.astroeq` schema.
- [x] Settle the variant question: `europa`, not Mimas.
- [x] Ship a read-only tool (`tools/a50.py`) with a runnable offline selftest.
- [x] Write the hardware test plan for the controls that need Ben (`docs/HARDWARE-TESTS.md`).
- [ ] Finish the protocol table — framing, fields and evidence are done; ~25 of the ~29
      opcodes in `0x60`-`0x7C`, the per-feature valid ranges, and the reply shapes remain.
- [ ] Implement and test the native settings/preset tool incrementally.
      Deliberately blocked: no writes until opcode *and* range are both evidenced.
- [ ] Expose and verify independent Game and Voice playback paths.
      Config written (`config/51-astro-a50-pro-audio.conf`); not applied, needs test 3.
- [ ] Validate the physical Game/Voice balance control with both streams playing.
- [ ] Validate onboard sidetone, three EQ slots, microphone settings, and remaining documented controls.
- [ ] Verify reconnect behavior and document installation and recovery.

## Current findings

Full detail in [docs/FINDINGS.md](docs/FINDINGS.md), tagged `[HW]` / `[STATIC]` /
`[INFER]` / `[UNKNOWN]` with Ghidra evidence IDs. Summary:

The connected device exposes a vendor HID interface (usage page `0xFF32`) with
report ID `2` and a 63-byte data area in each direction. The wire format is
`[0]=0x02`, `[1]=opcode`, `[2]=(len & 0x3F) | (seq<<6)`, `[3+]=payload`,
zero-padded to 64 bytes; high-bit opcodes insert `0x0a` and bump the length.
Established directly from the serializer, and corroborated on the read side by
the EQ reader under read/write symmetry — see FINDINGS.md §4 for the precise
limits of that second path.

Because two of the 63 data bytes are the command header, the real payload
capacity is **61 bytes** (**60** with the extended marker), not 63. `frame()`
enforces this and `selftest` asserts the boundary.

The card exposes **zero USB-Audio mixer controls**, so HID is the only control
path — that is structural, not a configuration gap. The two audio functions are
named by the device's own interface string descriptors: `Astro A50 Voice`
(`hw:1,0`, 2ch out + 1ch 16 kHz mic) and `Astro A50 Game` (`hw:1,1`, 6ch 48 kHz
out + 2ch aux in, where the capture side is the line connector and not a mic).

EQ is decoded and cross-validated: opcodes `0x63` (gains) / `0x64` (frequencies),
3 slots × 5 bands, signed dB gains, little-endian uint16 Hz frequencies, and 3
bandwidths as 4.12 fixed-point octaves. The decompiled loop counts and the
shipped `.astroeq` INI schema agree exactly. Sidetone (`0x68`, feature 37) and
noise gate (`0x66`, feature 35) are identified as single-byte, device-range-checked
settings. None of this has been sent to the headset.

The active PipeWire profile exposes one output; `pro-audio` is the only profile
exposing two outputs and two inputs, so the single-sink fallback — not the
protocol — is what prevents simultaneous Game and Voice and leaves the hardware
balance control with nothing to act on. Routing and physical balance still need
real playback verification; no profile change has been applied.

## Scope and verification

Keep the headset's actual Game/Voice mixing and onboard sidetone. Measure the
Game channel layout instead of assuming surround support. Separate static
protocol findings from hardware-tested behavior throughout the documentation.

No firmware flashing, reset commands, speculative USB writes, or modification
of the Windows source files. Keep proprietary artifacts and personal settings
out of Git and remote publication.

## Next session

Continue from the saved REA evidence and the worker's findings. Record protocol
details and runnable checks in this repository, then update this note as each
hardware acceptance criterion is verified.

The first investigation pass is **complete** and committed. **Full Linux feature
support is not delivered** — see the honest per-feature status table in
FINDINGS.md §9 for exactly what is and isn't established.

Start next session with [docs/HARDWARE-TESTS.md](docs/HARDWARE-TESTS.md) tests 1
and 2. They are read-only and zero-risk, and they answer the biggest open
question: whether any physical control (earcup balance, Dolby, EQ button, mic
boom, volume wheel) emits an HID report at all. A silent capture is a real
answer, not a failed test, and it rules out a whole class of designs. Test 3
then confirms whether `pro-audio` restores simultaneous Game and Voice, which is
acceptance criterion #1.
