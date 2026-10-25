# Mic/stream integration verified — 2026-10-24

Worker Astra-finish-sonnet (Claude, Sonnet) verified and closed out the
mic/stream work Codex left uncommitted when it hit its usage limit. Inspected
(not re-ran) `artifacts/backups/full-controls-roundtrip/`: all 38 reversible
CLI checks (EQ + six sliders + mic EQ + noise gate) restore to an exact
before==after document, and no `0x61` SYNC was sent (confirmed from
`capture.json` opcodes) — Codex's persistent-sync step never ran. Offline
`selftest`/`check_settings.py` pass. Extended `tools/check_gui.py --live` to
click the sidetone slider and noise-gate combo through the real GUI
(previously only the EQ gain button path was covered); ran it live against
Ben's connected A50 — exact before==after, evidence
`artifacts/backups/20261024-194620-a3c06269/`. Ran `tools/a50_gui.py --smoke`
live to confirm the new Microphone/Stream mix tabs render without error;
screenshot shows slot1 still `[-4,-2,-3,7,7]`, recovered baseline intact.
Reviewed every retained `0x72` status capture across all backup directories
(no new RE): the 16-byte payload is four TLV groups: field_id1 is the only
one with no bound consumer and never varied (headset was never
disconnected/flipped/Dolby-toggled during any capture) — documented as a
hypothesis in docs/A50-PROTOCOL.md, not a claim; resolving it needs a fresh
static trace or a live toggle test with Ben. `tools/a50_audio.py` was already
complete (read-only PipeWire plan); no changes needed. Updated
docs/FEATURES.md rows for mic/noise-gate/stream sliders and JSON backup
schema v2 to reflect actual tested state. No writes beyond the two reversible
live tests above; no sync, firmware, profile switch, or sound playback.

Audio-plan follow-up: `tools/a50_audio.py` reads card/sink/source JSON only,
validates USB9886:0015, records exact current/target/restore profiles, and lists
existing physical/virtual routes. Native Device/audio tab shows the plan. Host
currently has physical IEC958 plus pre-existing virtual A50_Game/A50_Voice
sinks; they were not created/modified here. Verified plan in ignored
`artifacts/backups/audio-plan-verified.json`; active profile unchanged.

# Latest app milestone — 2026-10-24

Recovered slot1 remains intact. Thirty live reversible checks pass: gains and
all frequencies on three slots, all nine bell bandwidths, default balance,
brightness and alert volume. Full EQ banks/mediator settings restored; no sync.
Private evidence: `artifacts/backups/reversible-controls-2/`. Earlier status0
brightness handling was corrected from actual ACC transport evidence; its
restoration was separately confirmed under `reversible-controls-1/`.

Native PyQt6 app: `/usr/bin/python3 tools/a50_gui.py`. System Python is required.
Host desktop live smoke and actual GUI write-button gain change/readback/restore passed.
Synthetic disconnect disabled writes; reconnect rediscovered/reloaded correctly. Final
comparison proves recovered baseline intact. Evidence: `artifacts/backups/20261024-161552-9b5cbeb0/`.
Snapshot values rendered, screenshot
at `/tmp/a50-ui-smoke.png`. Offline smoke and backup/preset/selective-restore
checks pass. Identity GET returns base36791/headset36154, evidence under
`artifacts/backups/identity-read/`. Native writes have baseline/readback/rollback;
explicit sync is implemented but has not been exercised. See docs/NATIVE-APP.md.
Mic/stream integration awaits the independent mapping worker. Physical audio,
Dolby/mute/charging transitions, real unplug/reinsert and persistence remain open.
No profile change/sounds/global config/restart. Older investigation-only/no-write
statements below are history, superseded by this checkpoint and FEATURES.

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
next: Get Ben's audio-profile approval and run physical listening/Dolby/mic-flip/headset-link/power-cycle-persistence tests; software implementation and reversible CLI+GUI verification for EQ/dock/mic/stream are done.
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
