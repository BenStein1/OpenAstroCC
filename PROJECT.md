# Latest checkpoint — slot 1 recovered (2026-10-24)

The inherited uncommitted client/tests/baselines were preserved and continued.
`docs/EQ-RECOVERY.md` records static bank semantics and successful host recovery:
slot1 working and stored now both `[-4,-2,-3,7,7]`; every other captured EQ
field and mediator setting was unchanged. Only verified six-byte `0x63` SET
was sent; no persistent sync. Private before/after/TX/RX are under
`artifacts/backups/slot1-recovery-host/`. Original evidence remains historical;
never restore its corrupted working gains. `tools/check_settings.py` offline
and existing selftest pass. Full app continuation follows this checkpoint.
Older unresolved-bank and no-write descriptions below are superseded.

---
name: Astro A50 Linux
status: active
summary: Native Linux support for the Astro A50 Gen 3 headset, including Command Center settings and separate Game and Voice audio paths.
next: Trace the sibling 0x70/{slot,band} coefficient read (docs/A50-PROTOCOL.md) and the remaining opcode space; then test the native client and separate Game/Voice playback on hardware.
updated: 2026-10-24
---

# Astro A50 Linux

Build native Linux support for Ben's **Astro A50 Gen 3** on KDE/PipeWire,
using a userspace HID utility and correct audio routing. Add a KDE front end
once the underlying controls work.

## Resume here

**Latest context-clear checkpoint: [[RESUME]]. Slot1 working-EQ recovery is
verified and committed as `2561494`; the worker continues controls and UI.**
Recover the existing Codex/NVIDIA worker IDs there before dispatching duplicates.

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
- [x] Bind the A50's own model/vtable in Ghidra and implement+exercise its real EQ-gains read, opcode `0x69` (docs/A50-PROTOCOL.md; live result in `evidence/a50-eq-read-slot1.json`). The earlier `0x63` request is confirmed A20-bound and stays removed.
- [ ] Map remaining opcodes and settings bounds; trace the sibling `0x70`/{slot,band} coefficient read noted in docs/A50-PROTOCOL.md.
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

**Superseded:** the earlier EQ opcodes `0x63`/`0x64`, sidetone `0x68` and noise
gate `0x66` were not bound to the A50 registration. The EQ reader's resolved
constructor was **A20**, PID `0x1c`. That diagnostic exchange returned
structured errors for page0 and two-byte success-marked replies for page1 —
real transport confirmation, but not a decoded A50 EQ read, and it stays
removed from `tools/a50.py`.

**Current:** static Ghidra analysis bound the actual A50 registration —
`(0x9886, 0x15)` constructed via `0x483640`/`0x419b00`/`0x4821a0`, which
assigns `Devices::AstroA50::vftable` and the model name `Astro A50 Wireless`
(docs/A50-PROTOCOL.md). Its headset-init path calls the shared builder with
opcode `0x69` and slot 1–3 to read EQ parameters. `tools/a50.py eq-read` now
sends exactly that request and was run live against Ben's connected A50
(slot 1): status `0x02`, matching sequence, echo `69 01`, 12-byte payload,
decoded into two 5-byte banks (unsigned byte − 12). Full TX/RX hex in
`evidence/a50-eq-read-slot1.json`. Bank A/B semantics are not yet claimed.
There were no intentional settings writes.

The active PipeWire profile exposes one sink. `pro-audio` advertises two sinks
and two sources, making it a promising routing fix. **It has not been applied
or verified with playback.** A profile-change approval question is pending;
elapsed time does not grant approval. No config files or services were changed.

A passive 12-second idle capture received no reports. This establishes only
that no unsolicited reports were observed during that interval; initialization,
subscription or polling may still be needed. The passive listener opens HID read-only; the model-bound `eq-read` sends
only its verified read request. The supervisor sandbox
exposes sysfs but not `/dev/hidraw9`; its listener exits visibly with ENOENT.
The earlier worker successfully captured from the host environment.

Ben also ran `python3 tools/a50.py listen` on Torvalds and stopped it with
Ctrl-C after **zero reports**. Duration and physical control actions were not
specified. His transcript contains the older, overly strong closing message;
the current file at commit `3f3db98` instead explains that polling or
initialization may be required. This capture confirms host access to the HID
node, but does not establish whether queried control/status reads work.

## Continuation status

**Full-feature continuation is active:** see [[docs/WORKERS]] for the current
Codex implementation worker and NVIDIA microphone/stream-mix analysis worker.
Ben explicitly authorized Codex workers and requested all documented features.
The completed checkpoint below is prior history; follow docs/FEATURES.md as
the implementation and verification matrix as it is created.

The supervisor bound the A50 model in Ghidra and exported its evidence.
Worker **Astra-native-read** (Claude) implemented the protocol note, replaced
the disabled `eq-read` with the real opcode-`0x69` request, and ran the single
authorized live read (slot 1) against Ben's connected A50 — success, see
above. Read-only worker **Astra-vtables**,
`0d283f16-df8a-439b-b22b-6ec6cddc844f`, was dispatched in parallel for the
same class-binding lookup and reproduced the constructor/vtables. It was
stopped after the exact PID15 binding and live read were verified. That earlier
worker group is inactive. The private REA snapshot and raw dossiers are recorded in
[[HANDOFF]] for continuation without this conversation.
See [[HANDOFF]] for prior worker history.

## Boundaries

Keep proprietary artifacts and personal settings in ignored `artifacts/`.
Preserve Windows sources. No firmware flashing, resets, brute-force commands,
or guessed writes. Preserve actual hardware mixing and onboard sidetone.
Keep static findings, inferences and hardware-tested behavior distinct.
Full headset feature support is **not yet delivered**.

## Astra-complete milestone: acceptance ledger

`docs/FEATURES.md` now tracks every requested feature separately across evidence,
native GET/SET, UI and real verification. Full support remains incomplete.
The worktree started clean. EQ/coefficient and mediator analysis is active;
complementary mic/stream analysis is supervisor-owned. Audio approval is pending.
