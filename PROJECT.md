---
name: Astro A50 Linux
status: active
summary: Native Linux support for the Astro A50 Gen 3 headset, including Command Center settings and separate Game and Voice audio paths.
next: Locate the Devices::AstroA50 class's own EQ-read function (its vtable sibling of 0x4800a0, which traced to the AstroA20 class instead); then test the native client and separate Game/Voice playback on hardware.
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
- [x] Trace shared framing and candidate command builders; A50 class binding remains unverified.
- [x] Deliver `tools/a50.py`: inventory, passive listener, offline preset decoding and selftest.
- [x] Review malformed packet handling, sequence fields, preset validation, and disconnect handling.
- [x] Parse all five preserved factory presets successfully in runnable checks.
- [x] Trace the request/reply/sequence-correlation mechanism and confirm it live against hardware (docs/FINDINGS.md §14).
- [ ] Map remaining opcodes, settings bounds and initialization; locate `AstroA50`'s own EQ-read function (the one traced belongs to the sibling `AstroA20` class).
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

The earlier EQ opcodes `0x63`/`0x64`, sidetone `0x68` and noise gate `0x66`
were not bound to the A50 registration. The EQ reader's resolved constructor
is **A20**, PID `0x1c`; applicability to A50 is unverified. The preset INI
schema remains observed shipped data, but is not proof of a live A50 protocol.

The live diagnostic exchange returned structured errors for page0 and two-byte
success-marked replies for page1, not decoded EQ values. These support shared
transport framing/status/sequence behavior. **`eq-read` is disabled and its live transmit helper removed** pending
an A50-bound read path. There were no intentional settings writes; unchanged
device settings were not verified by a before/after readback.

The active PipeWire profile exposes one sink. `pro-audio` advertises two sinks
and two sources, making it a promising routing fix. **It has not been applied
or verified with playback.** A profile-change approval question is pending;
elapsed time does not grant approval. No config files or services were changed.

A passive 12-second idle capture received no reports. This establishes only
that no unsolicited reports were observed during that interval; initialization,
subscription or polling may still be needed. The passive listener opens HID read-only. The diagnostic transmit CLI is now
disabled; offline transport tests remain. The supervisor sandbox
exposes sysfs but not `/dev/hidraw9`; its listener exits visibly with ENOENT.
The earlier worker successfully captured from the host environment.

Ben also ran `python3 tools/a50.py listen` on Torvalds and stopped it with
Ctrl-C after **zero reports**. Duration and physical control actions were not
specified. His transcript contains the older, overly strong closing message;
the current file at commit `3f3db98` instead explains that polling or
initialization may be required. This capture confirms host access to the HID
node, but does not establish whether queried control/status reads work.

## Continuation status

Ben says Claude has session capacity; skip Gemini. Use `nvidia-free-reasoning`
or `nvidia-free-fast` for LiteLLM, not the depleted paid Merge model.
The first Sonnet read-path pass completed at `3ad761d`. The second Sonnet pass
stalled after disabling `eq-read` and correcting findings; it was cancelled.
The supervisor reviewed and preserved those changes.

Read-only worker **Astra-vtables**, `litellm/nvidia-free-fast`,
`0d283f16-df8a-439b-b22b-6ec6cddc844f`, is looking for actual A50 registration
and vtable addresses. Retrieve its result before claiming new findings.
See [[HANDOFF]] for previous worker IDs and exact next investigation.

## Boundaries

Keep proprietary artifacts and personal settings in ignored `artifacts/`.
Preserve Windows sources. No firmware flashing, resets, brute-force commands,
or guessed writes. Preserve actual hardware mixing and onboard sidetone.
Keep static findings, inferences and hardware-tested behavior distinct.
Full headset feature support is **not yet delivered**.
