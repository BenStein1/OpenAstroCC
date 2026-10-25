# Durable A50 Surround Review

## Current status (2026-10-24)
- Live‑configured PipeWire‑Pulse remap sinks (`module‑remap‑sink`/`module‑remap‑source`) expose raw A50 USB audio functions with correct 5.1/mono channel maps.
- `module‑remap‑sink` nodes (`A50 Game 5.1`, `A50 Voice`, `A50 Mic`) are immediately available without requiring a WirePlumber restart – the profile is already active via `pactl set-card-profile` and the node rules in `config/51‑astro‑a50‑pro‑audio.conf` apply at creation.
- WirePlumber node rules (`monitor.alsa.rules`) guarantee that the raw A50 nodes never win the system‑default sink/source position even across a WirePlumber restart.
- Current verification plan: run `tools/a50_audio.py --verify` to ensure all three nodes are present and channel‑mapped as documented; run `pw-link -l` to confirm no collisions with the legacy `a50-loopback-*` loopbacks.
- Remaining risk: a fresh WirePlumber or PipeWire restart re‑enables the legacy loopback services or removes the `config/51‑astro‑a50‑pro‑audio.conf` settings, which would expose the duplicated “raw” nodes again.

# Action items
- Keep `config/51‑astro‑a50‑pro‑audio.conf` in place and ensure it is loaded after any system restart.
- Monitor `/proc/asound/card1/stream*` to validate that the hardware interfaces remain the same.
- If `a50-loopback-*` services are re‑enabled, trim their `target.object` to point at the proper `pro‑output‑n` nodes.
