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

## Authorization and remaining live-test boundary

Ben explicitly instructed (2026-10-24, superseding the prior note below): use
**Claude workers now**, choosing models to conserve tokens/session use —
Sonnet did this pass. Codex `bcf7b754-4adb-4666-a2d5-9ac38fa18f3b` hit its
usage limit and NVIDIA `4e1d4ca4-17ef-4201-8000-e7944c30a808` was cancelled;
neither is active. No paid-credit Fable/Opus without separate authorization.
Prior note for history: Ben had previously permitted **Codex or NVIDIA free
workers**; skip Gemini; LiteLLM must use `nvidia-free-reasoning` or
`nvidia-free-fast`, not the paid Merge model with exhausted credits.

Full feature work includes verified reversible headset-setting validation with
baseline/readback/restoration. No guessed/brute-force commands, firmware flash,
reset/unknown0xDA, Windows source changes, off-limits files, service restart,
or global/dotfile audio configuration changes.

**Audio permission remains unanswered.** The supervisor asked to switch only
the live A50 profile to pro-audio and play brief low-volume tests, without
restart/config edits. Do not infer approval from the full-feature goal or time.
Continue independent software/UI/protocol work. Physical Game/Voice, Dolby,
sidetone audibility, mic flip/gate and positional rendering need real tests;
do not mark100% from mocks, descriptors, or ACKs.

## Next sequence

Software implementation and reversible CLI+GUI verification are done for EQ,
dock defaults, mic and stream controls (see "Mic/stream integration — VERIFIED"
above and docs/FEATURES.md). What's left needs either Ben directly or new
static RE, not more client/GUI code:

1. Audio-profile approval is still unanswered — do not infer it from this
   pass. Once answered: switch to pro-audio, test low-volume playback, and
   verify independent Game/Voice/mic routing.
2. Physical tests only Ben can do: dock brightness/alert-volume listening,
   sidetone/mic-EQ/noise-gate audibility and recording, battery charging
   transition, physical balance/EQ-select interaction, unplug/reinsert.
3. Persistence: `sync` (`0x61`) has never been sent in this project. Test it
   only with a fresh full baseline, confirm working==stored readback, then a
   real power-cycle to prove persistence — needs Ben physically present.
4. Dolby/mic-flip/headset-link status mapping remains an open hypothesis
   (docs/A50-PROTOCOL.md): one `0x72` status field (field_id1) has no bound
   consumer and was constant in every capture so far. Needs a fresh static
   trace of its consumer, or a live toggle test with Ben.
5. Update FEATURES/PROJECT/HANDOFF and commit meaningful milestones locally.
   Never push without Ben's separate instruction.
