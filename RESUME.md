# Resume after context clear

Checkpoint: 2026-10-24. **Read this before changing anything or dispatching work.**

## Immediate priority: slot 1 EQ recovery

The earlier `0x63/{page,slot}` probes were incorrectly treated as reads on A50.
The new A50 setter trace shows `0x63` is a write taking slot + five encoded
gains. Slot1 working gains `[-10,-12,-12,-12,-12]` match the final short probe
plus its zero padding. Stored gains remain `[-4,-2,-3,7,7]`; other slots and
all captured coefficients agree between working/stored banks.

**Restoration has NOT been verified at this checkpoint.** Do not sync the
suspect working bank into storage or treat it as the desired baseline. The
recovery worker must verify bank roles, preserve before-state, restore only
slot1 working gains from the retained stored bank with the exact known write,
then read back both banks and all other settings. Keep the restored state;
do not restore the suspect working gains after subsequent test changes.

Details and causal evidence: [docs/EQ-RECOVERY.md](docs/EQ-RECOVERY.md).
The user has been informed. Do not claim no settings changed in the earlier
pass: there were no intentional writes then, but the new evidence strongly
supports an unintended working-bank modification.

## Recover existing workers first

Use **nori-client get_worker**, not the legacy bridge or a fresh duplicate.
Both were **running** when checked immediately before this checkpoint:

| Worker | Agent/model | Nori worker ID | Scope |
|---|---|---|---|
| Astra-recover-complete | codex / gpt-6.1-sol | `bcf7b754-4adb-4666-a2d5-9ac38fa18f3b` | Recovery FIRST; then full documented Gen3 app |
| Astra-mic-map | litellm / litellm/nvidia-free-fast | `4e1d4ca4-17ef-4201-8000-e7944c30a808` | Read-only A50 Europa mic/stream GET/SET/bounds mapping |

The previous primary `80fca206-08f3-4495-aa82-7c38ca632cd2` was **cancelled**
to deliver the recovery discovery before intentional write tests. It was not
stalled and its code must be preserved. Nori lacks a worker follow-up-message
tool, so the replacement received its partial work and urgent context explicitly.

A context clear can keep workers alive while Nori stays open. A Nori process
exit does not. Query status/output, inspect current files/commits, and resume
from the disk state if needed. Running metadata alone is not verification.

## Preserve the current worktree

Latest committed implementation checkpoint before this note:
`0d72ab0` — feature acceptance ledger. Prior `22b2a8b` contains the working
single-slot EQ-read foundation; `6b54cde` authorizes Codex for this project.

At checkpoint, the recovery worker owns these unfinished files:

- Modified `tools/a50.py`: new A50Client scaffold, full EQ/status/settings
  reads, exact setter methods, snapshot CLI, sequence progression and fd lock.
- Untracked `tools/check_settings.py`: new checks; inspect/run as appropriate.
- Untracked `evidence/a50-baseline.json` and
  `evidence/a50-baseline-capture.json`: read-only capture containing the suspect
  slot1 working bank and retained stored bank. Do not overwrite or clean them.

The worker was instructed to preserve full baseline/captures privately under
ignored `artifacts/backups/`, retain exact recovery TX/RX, update the recovery
note, and commit the recovery checkpoint before continuing implementation.
Do not stage unfinished worker code merely to make the tree look clean.

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

1. Collect current recovery-worker status; finish and verify slot1 restoration.
2. Collect NVIDIA mic/stream evidence and save/review it for integration.
3. Continue complete A50 GET/SET/ranges/apply semantics, PyQt6 controls,
   validated backup/import/restore, reconnect, status and firmware-version READ.
4. Update FEATURES/PROJECT/HANDOFF and commit meaningful milestones locally.
   Never push without Ben's separate instruction.
5. Complete approved live-audio and physical acceptance tests with Ben before
   claiming feature completion. Preserve precise remaining gaps otherwise.
