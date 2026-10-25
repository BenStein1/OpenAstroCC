# Astro A50 Linux project instructions

Read PROJECT.md, HANDOFF.md and docs/A50-PROTOCOL.md before continuing.

Ben's latest instruction (2026-10-24) sets **NVIDIA free models as primary**
and **Codex as secondary**; Claude is capped. Do not use paid-credit Fable/Opus
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
Windows changes, off-limits files, or system service restarts (no
`systemctl restart`/reboot/logout for PipeWire/WirePlumber or anything else).
Reversible headset settings validation may use only statically verified
controls, with a saved baseline, readback and restoration.

**Audio profile/config: approved and partially superseded (2026-10-24).** Ben
explicitly approved switching the live audio profile and physical
Game/Voice/Dolby listening tests (docs/HARDWARE-TESTS.md) — that blanket "no
profile change, no dotfile config changes" note above is stale for A50 scope.
Current state: `pro-audio` is active and verified; a 5.1/mono channel-map
remap (`config/15-astro-a50-remap.conf`) is installed under
`~/.config/wireplumber/wireplumber.conf.d/` and
`~/.config/pipewire/pipewire-pulse.conf.d/` and live-applied via
`pactl load-module` (no restart). The two old `a50-loopback-{game,voice}.service`
units are disabled. Any further A50-specific WirePlumber/PipeWire user config
or hide-preference edits remain authorized; do not touch non-A50 audio
defaults (Audioengine stays the system default sink) or restart any
PipeWire/WirePlumber/Plasma service yourself — prepare config and ask Ben if a
restart is genuinely required to take effect.

Read-only audio inventory and in-repo configuration/UI work may continue.
Prefer existing libraries and standard tools; avoid unnecessary scaffolding.
