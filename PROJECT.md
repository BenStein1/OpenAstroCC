---
name: Astro A50 Linux
status: active
summary: Native Linux support for the Astro A50 Gen 3 headset, including Command Center settings and separate Game and Voice audio paths.
next: Trace verified settings/status reads and feature bounds in Ghidra, then test the native client and separate Game/Voice playback on hardware.
updated: 2026-10-24
---

# Astro A50 Linux

Build native Linux support for Ben's **Astro A50 Gen 3** on KDE/PipeWire,
using a userspace HID utility and correct audio routing. Add a KDE front end
once the underlying controls work.

## Resume here

Read [[HANDOFF]] first, then [[docs/FINDINGS]] for the detailed protocol ledger
and [[docs/HARDWARE-TESTS]] for physical tests. All progress is local to
`/home/ben/Projects/astro-a50-linux`; nothing has been pushed.

[Original brief and acceptance criteria](https://github.com/BenStein1/obsidian-projects/blob/main/Projects/BlueSky/Astro-A50-Gen3-Linux-plan.md).

## Progress

- [x] Initialize project Git repository and preserve both Windows apps/settings privately.
- [x] Verify the four preserved trees byte-for-byte and record artifact hashes.
- [x] Identify USB `9886:0015`, vendor HID reports, and independent audio interfaces.
- [x] Analyze classic ACC 1.0.226 with REA/Ghidra; record target hash, addresses and evidence IDs.
- [x] Trace packet framing, EQ read encoding, sidetone and noise-gate command builders.
- [x] Deliver `tools/a50.py`: inventory, passive listener, offline preset decoding and selftest.
- [x] Review malformed packet handling, sequence fields, preset validation, and disconnect handling.
- [x] Parse all five preserved factory presets successfully in runnable checks.
- [ ] Map remaining opcodes, request/reply semantics, settings bounds and initialization.
- [ ] Implement and exercise verified identity/status/settings queries on the headset.
- [ ] Implement verified settings writes and export/import of device settings.
- [ ] Test independent Game/Voice playback and the physical balance control.
- [ ] Validate onboard sidetone, EQ changes, microphone controls and remaining documented settings.
- [ ] Validate reconnect/reboot behavior and any persistent audio configuration.

## Current findings

The hardware exposes **Voice** (`hw:1,0`, stereo 48 kHz playback and mono 16 kHz
mic capture) and **Game** (`hw:1,1`, six-channel 48 kHz playback and stereo line
capture). These are descriptor observations; positional rendering remains untested.
Card and hidraw indices may change after reconnect, so use device discovery.

The HID interface uses report ID `2` and a 63-byte data area. Static framing is
`report ID, opcode, length/2-bit sequence, payload`, padded to 64 bytes. The two
header bytes leave **61 payload bytes**, or **60** with the extended marker.
The decoder rejects malformed/truncated reports and invalid extended markers.

Static analysis identified EQ opcodes `0x63`/`0x64`, three slots with five gains
and frequencies and three fractional bandwidths; sidetone `0x68` (feature 37);
and noise gate `0x66` (feature 35). Operating ranges and live replies remain
unverified. Preserved app state suggests the europa firmware family; no live
identity query has confirmed it. No firmware action has been performed.

The active PipeWire profile exposes one sink. `pro-audio` advertises two sinks
and two sources, making it a promising routing fix. **It has not been applied
or verified with playback.** A profile-change approval question is pending;
elapsed time does not grant approval. No config files or services were changed.

A passive 12-second idle capture received no reports. This establishes only
that no unsolicited reports were observed during that interval; initialization,
subscription or polling may still be needed. The utility currently opens HID
read-only and has no transmit or settings-write path. The supervisor sandbox
exposes sysfs but not `/dev/hidraw9`; its listener exits visibly with ENOENT.
The earlier worker successfully captured from the host environment.

Ben also ran `python3 tools/a50.py listen` on Torvalds and stopped it with
Ctrl-C after **zero reports**. Duration and physical control actions were not
specified. His transcript contains the older, overly strong closing message;
the current file at commit `3f3db98` instead explains that polling or
initialization may be required. This capture confirms host access to the HID
node, but does not establish whether queried control/status reads work.

## Continuation status

Ben clarified that Claude still has session capacity, Gemini should be skipped,
and LiteLLM should use `nvidia-free-reasoning` or `nvidia-free-fast`.
The NVIDIA attempt `7311268f-2653-4db5-bf77-337ba8fff0fe` was cancelled before
edits because its proposed generic query lacked the required evidence.
**Astra-read-path**, Claude Sonnet, worker ID
`fd0c34b4-9fd0-4e80-9540-af6ea7e0da49`, is the current continuation. It has
reopened the correct artifact in Ghidra and reports an exact `{page, slot}` EQ
read payload plus additional send/wait and reply-validation functions. Evidence
export, full initialization/reply semantics, implementation and live validation
are still pending. Collect its Nori `get_worker` result before claiming success.

The first Astra worker completed and committed its investigation. Subsequent
Claude workers stalled before edits and were cancelled. Gemini failed to create
an ACP session (client no longer supported). LiteLLM failed with HTTP 402
`budget_exceeded` on the paid Merge model (credit balance depleted). Those
attempts are inactive; the NVIDIA continuation above is the current attempt.
The supervisor completed the bounded validation review and this disk handoff.
See [[HANDOFF]] for worker IDs, commit history and the exact next investigation.

## Boundaries

Keep proprietary artifacts and personal settings in ignored `artifacts/`.
Preserve Windows sources. No firmware flashing, resets, brute-force commands,
or guessed writes. Preserve actual hardware mixing and onboard sidetone.
Keep static findings, inferences and hardware-tested behavior distinct.
Full headset feature support is **not yet delivered**.
