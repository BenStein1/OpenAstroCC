# Resume after context clear

Checkpoint: 2026-10-24. **Read this before changing anything or dispatching work.**

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

## Recover existing workers first

Use **nori-client get_worker**, not the legacy bridge or a fresh duplicate.
Both were **running** when checked immediately before this checkpoint:

| Worker | Agent/model | Nori worker ID | Scope |
|---|---|---|---|
| Astra-recover-complete | codex / gpt-6.1-sol | `bcf7b754-4adb-4666-a2d5-9ac38fa18f3b` | Recovery committed; continuing full Gen3 app |
| Astra-mic-map | litellm / litellm/nvidia-free-fast | `4e1d4ca4-17ef-4201-8000-e7944c30a808` | Read-only A50 Europa mic/stream GET/SET/bounds mapping |

The previous primary `80fca206-08f3-4495-aa82-7c38ca632cd2` was **cancelled**
to deliver the recovery discovery before intentional write tests. It was not
stalled and its code must be preserved. Nori lacks a worker follow-up-message
tool, so the replacement received its partial work and urgent context explicitly.

A context clear can keep workers alive while Nori stays open. A Nori process
exit does not. Query status/output, inspect current files/commits, and resume
from the disk state if needed. Running metadata alone is not verification.

## Preserve the current worktree

The recovery/client checkpoint is **`2561494`**; context-clear documentation
followed at `6ed8bcc`. Check `git log` and `git status` for newer milestones
from the active worker rather than assuming the checkpoint is still latest.
The worktree was clean immediately after the recovery and documentation commits.

The inherited A50Client, snapshot functionality, tests and recovery utility are
preserved/committed. Earlier baseline JSON files under evidence/ describe the
pre-recovery state and are historical. The correct recovered baseline is the
private after.json identified above. Preserve any new dirty files from the
continuing worker; do not revert/clean them or commit incomplete code blindly.

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
  install if still available. UI is not implemented or verified at this checkpoint.

## Authorization and remaining live-test boundary

Ben explicitly permits **Codex or NVIDIA free workers** now; this overrides the
older Codex-retired shared note. Claude has about6% session left and may cap;
avoid spending it. Skip Gemini. LiteLLM must use `nvidia-free-reasoning` or
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

1. Collect current Codex-worker status; recovery is already verified at2561494.
   Continue controls/UI using the recovered baseline; do not repeat recovery.
2. Collect NVIDIA mic/stream evidence and save/review it for integration.
3. Continue complete A50 GET/SET/ranges/apply semantics, PyQt6 controls,
   validated backup/import/restore, reconnect, status and firmware-version READ.
4. Update FEATURES/PROJECT/HANDOFF and commit meaningful milestones locally.
   Never push without Ben's separate instruction.
5. Complete approved live-audio and physical acceptance tests with Ben before
   claiming feature completion. Preserve precise remaining gaps otherwise.
