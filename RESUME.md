# Resume after context clear

Checkpoint: 2026-10-24 (updated by worker Astra-finish-sonnet, Claude/Sonnet).
**Read this before changing anything or dispatching work.**

## Mic/stream integration — VERIFIED, do not repeat

Codex `bcf7b754-4adb-4666-a2d5-9ac38fa18f3b` hit its usage limit and its
terminal failed; NVIDIA `4e1d4ca4-17ef-4201-8000-e7944c30a808` was cancelled
with no findings (its mic/stream enum evidence was already saved to
`artifacts/analysis/trace-*.json` beforehand and reused, not re-derived).
Codex left mic/stream client code, GUI tabs, backup schema v2 and a 38-point
reversible CLI test run **uncommitted**. Astra-finish-sonnet inspected
(not re-ran) that evidence: `artifacts/backups/full-controls-roundtrip/`
before.json == after.json exactly, and `capture.json` contains no `0x61`
opcode — **sync was never sent**, confirmed empirically, not assumed. Offline
`selftest` and `check_settings.py` pass. Extended `tools/check_gui.py --live`
to click a Microphone-tab slider (sidetone) and the noise-gate combo through
the real GUI and ran it live: exact before==after, evidence
`artifacts/backups/20261024-194620-a3c06269/`. Ran `a50_gui.py --smoke` live;
screenshot confirms slot1 still `[-4,-2,-3,7,7]` and the new tabs render.
All of this is now **committed** at e47c86b. See docs/FEATURES.md for the
per-feature ledger.

## Slot 1 EQ recovery — COMPLETE, do not repeat

The earlier `0x63/{page,slot}` probes were incorrectly treated as reads on A50.
The new A50 setter trace shows `0x63` is a write taking slot + five encoded
gains. Slot1 working gains `[-10,-12,-12,-12,-12]` match the final short probe
plus its zero padding. Stored gains remain `[-4,-2,-3,7,7]`; other slots and
all captured coefficients agree between working/stored banks.

**Recovery is verified and committed as `2561494`.** The worker confirmed the
working/stored roles from the A50 setter and sync paths, saved the original
state, and sent only `0x63` with six-byte payload `01 08 0a 09 13 13`.
Immediate bank readback and a full subsequent snapshot confirmed slot1 working
and stored are both `[-4,-2,-3,7,7]`, with all other captured EQ fields and
mediator settings unchanged. No persistent apply/sync was sent.

Use `artifacts/backups/slot1-recovery-host/after.json` as the baseline for
later tests. Exact before/after/readback/result/TX/RX files are in that directory;
original client/tests/baselines are in `artifacts/backups/pre-recovery/`.
**Never restore the suspect working gains from the old baseline files.**
The active Codex worker has moved on to controls, backup/restore and the native UI.

Details and causal evidence: [docs/EQ-RECOVERY.md](docs/EQ-RECOVERY.md).
The user has been informed. Do not claim no settings changed in the earlier
pass: there were no intentional writes then, but the new evidence strongly
supports an unintended working-bank modification.

## Completed workers — all inactive

All workers from this checkpoint are terminal; listed for reference only. Do not
attempt resume; all relevant work is committed.

| Worker | Brain/model | Nori ID | Terminal status | Scope |
|---|---|---|---|---|
| Astra-recover-complete | Codex/gpt-6.1-sol | `bcf7b754-4adb-4666-a2d5-9ac38fa18f3b` | **Failed** — hit usage limit before commit | Verified slot1 recovery; implemented mic/stream client code, GUI tabs, backup schema v2; uncommitted work was saved and later verified+committed by Sonnet |
| Astra-mic-map | LiteLLM/nvidia-free-fast | `4e1d4ca4-17ef-4201-8000-e7944c30a808` | **Cancelled** — no additional findings | Read-only A50 mic/stream mapping; saved evidence reused by Codex |
| Astra-finish-sonnet | Claude/Sonnet | (worker ID not recorded) | **Completed** — committed e47c86b | Verified Codex's uncommitted work against baseline evidence; extended GUI live test for Microphone tab; verified no sync sent; all checks passed and committed |

Nori process exit terminates workers. Query `get_worker` only if resuming a specific
named worker explicitly. For the current state, inspect git log and working tree.

## Current worktree state

Latest committed checkpoint is **e47c86b** (Sonnet verification pass, 2026-10-24).
This supersedes recovery/documentation milestones `2561494`/`6ed8bcc`.
Worktree is clean; no pending changes or dirty files.

The inherited A50Client, snapshot functionality, tests, recovery utility, and
verified mic/stream/GUI client code are all committed. The correct recovered
baseline for slot1 is `artifacts/backups/slot1-recovery-host/after.json`.
Do not restore suspect working gains from old baseline files. All baseline
snapshots used for reversible testing pass (`before==after`, no stray sync).

## Current feature work and evidence

- Goal: **all documented A50 Gen3 features and a usable native Linux app**,
  not just reads. Acceptance matrix: [docs/FEATURES.md](docs/FEATURES.md).
- Verified device: USB `9886:0015`; actual A50 factory/vtable binding is in
  [docs/A50-PROTOCOL.md](docs/A50-PROTOCOL.md). A20/Mimas are separate targets.
- `0x69/{slot1..3}` gains read is live-verified. `0x70/{slot,band}` coefficient
  reads and mediator settings/status were read successfully in the new baseline.
- Bank roles now have additional setter/sync evidence, pending the recovery
  worker's explicit verification and documentation. Earlier bank A/B labels
  are historical; do not infer persistence solely from a packet ACK.
- Native read capture: `evidence/a50-eq-read-slot1.json`.
- Private reusable REA/Ghidra snapshot:
  `artifacts/analysis/a50-root-snapshot.json` (17 evidence records, 13 primitive
  bindings). Individual `a50-*.json` dossiers are beside it. Use the matching
  preserved classic EXE and snapshot; avoid repeating the resolved factory search.
- Target: `artifacts/classic-acc/ASTRO Command Center.exe`, classic1.0.226,
  SHA256 `991e558129af98765cba4f02b10fa5cc4d537e2b6bb4bd3032ca010832eb2dcf`.
- Codex detected installed PyQt6; use it for the native UI without a dependency
  install if still available. Mic/stream tabs implemented and verified with live
  GUI write/readback tests; listening and other controls' audible proof pending.

## Audio profile approval and physical acceptance tests — VERIFIED (2026-10-24)

Ben explicitly approved three physical tests with A50 pro-audio profile active:
1. **Separate Game/Voice playback** — Verified: both heard comfortably when played independently, and both heard when concurrent (no restart, no config edits, profile only)
2. **Hardware balance control** — Verified: Game button favors low Game, Voice button favors high Voice; buttons functional on live concurrent streams
3. **Dolby ON/OFF toggle** — Verified: "Very clear channel separation when Dolby was on, collapsed to L/R when off" (6-channel discrete when Dolby ON, stereo passthrough when OFF)

Evidence and command line for verified 6-channel playback (including silent probe and audible test) in `docs/HARDWARE-TESTS.md` §4a-4b and `artifacts/audio-live/physical-acceptance.json`.

**Ben explicitly instructed (2026-10-24, superseding the prior note below):** use
**Claude workers now**, choosing models to conserve tokens/session use —
Sonnet did this pass. Codex `bcf7b754-4adb-4666-a2d5-9ac38fa18f3b` hit its
usage limit and NVIDIA `4e1d4ca4-17ef-4201-8000-e7944c30a808` was cancelled;
neither is active. No paid-credit Fable/Opus without separate authorization.

Full feature work includes verified reversible headset-setting validation with
baseline/readback/restoration. No guessed/brute-force commands, firmware flash,
reset/unknown0xDA, Windows source changes, off-limits files, service restart,
or global/dotfile audio configuration changes (for this approved profile test).

**New root-cause finding (worker Astra-audio-routing, 2026-10-24, read-only, no
state changed):** live kernel UAC descriptors (`/proc/asound/card1/stream0`/
`stream1`) confirm the A50 genuinely has two independent USB PCM interfaces --
hw:1,0 is Voice (2ch 48k out + 1ch 16k mono mic in), hw:1,1 is Game (6ch 48k
out + 2ch 48k line in) -- independent of any PipeWire profile choice. The
currently active profile (`output:iec958-stereo+input:mono-fallback`) only
opens hw:1,0; hw:1,1 is unopened (`Status: Stop`). Separately, live `pw-link
-l` tracing proves this host's pre-existing, non-repo A50_Game/A50_Voice
pw-loopback sinks (`~/.config/systemd/user/a50-loopback-{game,voice}.service`,
not part of this repo) both currently forward into the *same* physical
`iec958-stereo` sink -- confirmed, not just suspected: their names do not
reflect independent routing today. `tools/a50_audio.py` now carries both
proofs (`uac_ground_truth()`, `trace_virtual_routes()`) in its read-only
`inventory()` output, and `config/51-astro-a50-pro-audio.conf`'s pro-output
labeling is now stated as confirmed (by PCM order) rather than inferred. None
of this required or performed a profile switch, service restart, or config
install. Enabling `pro-audio` is necessary but not sufficient for the two
existing loopback services to become real Game/Voice paths: their
`target.object` would also need to point at the new pro-output-0/pro-output-1
sinks -- that edit is outside this repo and still Ben's call.

## Remaining work — software/persistence/per-app routing

Software implementation and reversible CLI+GUI verification are done for EQ,
dock defaults, mic and stream controls (see "Mic/stream integration — VERIFIED"
above and docs/FEATURES.md). Physical Game/Voice/Dolby playback now verified.
What's left:

1. **Pending physical tests:** dock brightness/alert-volume listening, sidetone/mic-EQ/noise-gate audibility and recording, battery charging transition, physical mic flip/mute/link interaction, unplug/reinsert, per-app stream mix audibility.

2. **Persistence:** `sync` (`0x61`) has never been sent in this project. Test it
   only with a fresh full baseline, confirm working==stored readback, then a
   real power-cycle to prove persistence — needs Ben physically present.

3. **Software-side Dolby/mic-flip/headset-link status mapping:** Physical Dolby toggle confirmed functional (Dolby ON → 6-channel discrete, OFF → stereo passthrough). Remaining open: whether `0x72` field_id1 and other payload fields map to mute/flip/link status in software; static trace shows no bound consumer in the resolved-paths analysis. Needs fresh static trace of any consumer, or live interaction test.

4. **Per-app stream routing:** Profile switch to pro-audio is now approved and tested. Pre-existing non-repo `~/.config/systemd/user/a50-loopback-{game,voice}.service` sinks still route to same physical sink (proven by live `pw-link` trace). Repointing those services' `target.object` to pro-output-0/pro-output-1 is outside this repo and user-driven.

5. **Config installation/autostart/reboot/WirePlumber persistence:** Candidate `config/51-astro-a50-pro-audio.conf` prepared; profile switch tested live without config install. Persistence (survive reboot) untested. Installation and verification is user-driven unless explicitly requested.
