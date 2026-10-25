# Astro A50 Linux project instructions

Read PROJECT.md, HANDOFF.md and docs/A50-PROTOCOL.md before continuing.

Ben's latest instruction (2026-10-24) explicitly authorizes **Claude workers**
now, choosing models to conserve tokens/session use; this supersedes the
earlier note below authorizing Codex instead. No paid-credit Fable/Opus
without separate authorization. See docs/WORKERS.md for current/prior worker
status. The supervisor owns worker dispatch.

Prior note (history): explicitly authorized Codex workers, superseding the
older shared instruction that Codex workers were retired; LiteLLM models
`litellm/nvidia-free-reasoning` / `litellm/nvidia-free-fast` were permitted,
skipping Gemini and the depleted paid Merge routes.

The goal is all documented Gen 3 controls and a usable native Linux app.
Track each feature's implementation and real verification separately. Update
PROJECT.md and HANDOFF.md with every meaningful milestone and commit locally
before reporting completion. Do not push. Preserve unrelated changes.

Bind every protocol operation to the actual A50 VID:PID `9886:0015` through
the factory/vtable evidence. A20 and Mimas findings are not substitutes.
Reuse the saved REA/Ghidra snapshot and retain additional evidence privately
under ignored artifacts/analysis. Preserve non-sensitive live captures.

No firmware flashing, resets, brute-force opcodes, guessed packets, source
Windows changes, off-limits files, system service restarts or global/dotfile
configuration changes. Reversible headset settings validation may use only
statically verified controls, with a saved baseline, readback and restoration.
The existing live-audio/profile approval question remains unanswered; do not
change the active audio profile or play test tones until it is answered.

Read-only audio inventory and in-repo configuration/UI work may continue.
Prefer existing libraries and standard tools; avoid unnecessary scaffolding.
