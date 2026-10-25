# Full-feature continuation

Ben requested all documented Gen 3 features on 2026-10-24, including a usable
native app. Keep implementation, protocol evidence and actual hardware/UI
verification separate in docs/FEATURES.md. Software implementation and
reversible CLI+GUI verification are done for EQ, dock, mic and stream;
physical listening/persistence/audio-profile tests with Ben remain — see
RESUME.md "Next sequence".

## Worker history (all inactive as of this checkpoint)

- **Astra-recover-complete**: Codex `gpt-6.1-sol`, Nori ID
  `bcf7b754-4adb-4666-a2d5-9ac38fa18f3b`. Slot1 recovery verified at `2561494`;
  implemented mic/stream client code, GUI tabs, backup schema v2, and ran a
  38-point reversible CLI check, but **hit its usage limit and its terminal
  failed before committing**. Its uncommitted work was preserved, verified
  (not re-run blindly), and committed by the following worker.
- **Astra-mic-map**: `litellm/nvidia-free-fast`, Nori ID
  `4e1d4ca4-17ef-4201-8000-e7944c30a808`. Read-only static mapping of A50
  Europa microphone and stream-mix GET/SET/bounds, saved to
  `artifacts/analysis/trace-*.json`. **Cancelled due to overlap with Codex's
  progress; returned no additional findings itself**, but its earlier saved
  evidence was the basis Codex's (committed) client code used.
- **Astra-finish-sonnet**: Claude/Sonnet (this worker). Verified Codex's
  uncommitted mic/stream work against actual evidence (before==after
  equality, no stray `0x61` sync), extended `check_gui.py --live` to cover
  the new Microphone-tab controls and ran it live, reviewed retained `0x72`
  status captures for the Dolby/flip/link gap without new RE, updated
  docs, and committed. See PROJECT.md's "Mic/stream integration verified"
  section for the full account.

Recover worker IDs with Nori get_worker before dispatching duplicates. Running
metadata is not implementation proof. Workers do not survive Nori process exit.

## Current authorization

Ben explicitly instructed (2026-10-24): use **Claude workers now**, choosing
models to conserve tokens/session use — this supersedes the older
Codex/NVIDIA-only note (kept below for history) and the separate
Codex-retired shared note. No paid-credit Fable/Opus without separate
authorization.

Prior note (history): Ben had permitted Codex workers, overriding the older
shared retirement note for this project; skip Gemini and the depleted Merge
route; NVIDIA choices were the two free aliases.

Verified, reversible headset-setting tests may save baseline, change the smallest
supported value, read it back, and restore baseline. No guessed commands,
firmware flashing, reset, source deletion, service restarts or global config edits.

Audio-profile switching and test sounds still await the explicit audio answer.
The supervisor asked whether it may switch the A50 alone to pro-audio and play
brief low-volume channel tests, without restart/config-file edits. An unanswered
question is not approval. Continue independent code, GUI and static work.
