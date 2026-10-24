---
name: Astro A50 Linux
status: active
summary: Native Linux support for the Astro A50 Gen 3 headset, including Command Center settings and separate Game and Voice audio paths.
next: Finish the REA/Ghidra protocol map, build a native tool from verified commands, and validate the real headset controls.
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

## Progress

- [x] Create the project folder and initialize Git.
- [x] Preserve both Windows app trees and their settings in the private local artifact area.
- [x] Identify the connected headset as USB `9886:0015` and save audio/HID descriptor evidence.
- [x] Start REA/Ghidra analysis of the classic Command Center executable.
- [ ] Finish the protocol table with command framing, fields, ranges, replies, and evidence.
- [ ] Implement and test the native settings/preset tool incrementally.
- [ ] Expose and verify independent Game and Voice playback paths.
- [ ] Validate the physical Game/Voice balance control with both streams playing.
- [ ] Validate onboard sidetone, three EQ slots, microphone settings, and remaining documented controls.
- [ ] Verify reconnect behavior and document installation and recovery.

## Current findings

The connected device exposes a vendor HID interface with report ID `2` and
63-byte input/output payloads. The classic app's HID report framing has been
traced in Ghidra. Sidetone (`0x68`) and noise gate (`0x66`) command builders
have been identified statically; neither is validated by sending it to the
headset yet. EQ preset files use an INI format.

The active PipeWire profile exposes one output. The available `pro-audio`
profile advertises two outputs and two inputs. Routing and physical balance
still need real playback verification; no profile change has been applied.

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
hardware acceptance criterion is verified. The initial investigation is still
running; full Linux feature support is not yet delivered.
