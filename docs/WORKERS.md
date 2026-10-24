# Full-feature continuation

Ben requested all documented Gen 3 features on 2026-10-24, including a usable
native app. Keep implementation, protocol evidence and actual hardware/UI
verification separate in docs/FEATURES.md. This is not complete yet.

## Active workers

- **Astra-recover-complete**: Codex `gpt-6.1-sol`, Nori ID
  `bcf7b754-4adb-4666-a2d5-9ac38fa18f3b`. Slot1 recovery verified at `2561494`;
  continuing primary implementation, EQ/status/mediator, UI and integration. Read
  ../RESUME.md and EQ-RECOVERY.md. Must commit milestones locally; no push.
- **Astra-mic-map**: `litellm/nvidia-free-fast`, Nori ID
  `4e1d4ca4-17ef-4201-8000-e7944c30a808`. Read-only static mapping of A50
  Europa microphone and stream-mix GET/SET/bounds. No code or hardware writes.
  Supervisor will persist and review its evidence for integration.

Recover these IDs with Nori get_worker before dispatching duplicates. Running
metadata is not implementation proof. Workers do not survive Nori process exit.

Prior primary `80fca206-08f3-4495-aa82-7c38ca632cd2` was cancelled to deliver
the critical recovery finding; its unfinished client/snapshot/test files are
preserved and belong to the replacement worker. Do not revert or clean them.

## Current authorization

Ben explicitly permits Codex workers now, overriding the older shared retirement
note for this project. Claude has about 6% session left; avoid spending it.
Skip Gemini and the depleted Merge route. NVIDIA choices are the two free aliases.

Verified, reversible headset-setting tests may save baseline, change the smallest
supported value, read it back, and restore baseline. No guessed commands,
firmware flashing, reset, source deletion, service restarts or global config edits.

Audio-profile switching and test sounds still await the explicit audio answer.
The supervisor asked whether it may switch the A50 alone to pro-audio and play
brief low-volume channel tests, without restart/config-file edits. An unanswered
question is not approval. Continue independent code, GUI and static work.
