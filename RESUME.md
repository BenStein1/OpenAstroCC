# Current checkpoint — audio is working live; durability is open (2026-10-24)

This note supersedes older surround status below. Current live mechanism is the
PipeWire-Pulse `module-remap-sink`/`module-remap-source` set applied by
`pactl load-module`; do not describe it as restart-durable. Saved result evidence
shows an unpaused SDL2 silent stream with `device_status_running=1` and six
`pw-link` connections to the Game master, plus a paplay stream connected and
linked to `A50_Game_51` (see
`artifacts/surround-integration/easyeffects/RESULT.md`). The earlier
`artifacts/surround-integration/sdl-*-probe.log` files alone are paused probes;
use the EasyEffects result artifacts for running-stream proof.

Remaining gates: first-launch EasyEffects/stream-restore race for new app names;
PipeWire-Pulse startup can race A50 master enumeration; native WirePlumber rules
are installed but have never been activated by a fresh process; KDE tray hide
filter remains unapplied. The native node rules change maps to FL/FR/... while
`15-astro-a50-remap.conf` still expects AUX master maps, so do not run these
unchanged together. See `artifacts/surround-integration/durable-review.md` for
the smallest restart-dependent trial and its readbacks. No service restart or
new live audio change is authorized/performed by this checkpoint.

Worker model preference is NVIDIA free primary, Codex secondary; Claude is
capped (per Ben's latest instruction).

# Resume after context clear

Checkpoint: 2026-10-24 (updated by worker Astra-surround-integration, Claude/Sonnet).  Durable surround routing now active with module-remap nodes, no restart needed.
**Read this before changing anything or dispatching work.**

## Normal-game 5.1 surround — DONE, do not repeat

Ben explicitly said the prior physical Game/Voice/Dolby listening test (below)
only proved the hardware *could* work, not that games would actually get a
surround output from it — true, because `pro-audio`'s raw channel map on
pro-output-1 is `aux0..aux5`, which PulseAudio-introspecting apps (SDL2, most
games) don't recognise as 5.1 and fall back to stereo on.

Fixed **today, live, with zero restarts** via PipeWire-pulse's built-in (no
new dependency) `module-remap-sink`/`module-remap-source`: exposes
`A50 Game 5.1` (FL/FR/FC/LFE/RL/RR, 6ch), `A50 Voice` (FL/FR, 2ch), `A50 Mic`
(MONO, 1ch), each a 1:1 passthrough onto the real pro-output-0/1 / pro-input-0
nodes (no mixing, no added latency). Applied live via `pactl load-module`
(exact commands in `artifacts/surround-integration/apply-live.sh`) — this is
why games work *right now*, independent of everything below. **This is the
mechanism that is actually live and correct; see the two detours below before
touching it again.**

**Detour 1, abandoned — `pw-loopback` instead of `module-remap-sink`.** Tried
switching to `pw-loopback` (the same binary Ben's old, now-disabled
`a50-loopback-*.service` units used) specifically because `module-remap-sink`/
`-source`'s `sink_properties`/`source_properties` parser turned out too
fragile to also carry a `priority.session=0` override in the same string (see
Detour 2) — `pw-loopback`'s own `--capture-props`/`--playback-props` handle
multiple space-separated properties correctly (confirmed: description,
audio.position, *and* priority all applied correctly in one shot). **But**
`SDL_OpenAudioDevice` via `SDL_AUDIODRIVER=pulseaudio` then failed outright
("Could not connect PulseAudio stream") against every `pw-loopback`-backed
sink tested (both the 6ch Game and the 2ch Voice one) — a genuine
incompatibility between SDL2's PulseAudio backend and connecting a *new*
stream to a sink that's itself already a connected `pw-loopback` client
(a plain libpulse client, `paplay`, connected to the same sink fine, so this
is SDL2-specific, not a general Pulse-protocol problem). The failed
`SDL_OpenAudioDevice` call also left the process hung on exit (needed
`kill -9`, `timeout`'s normal SIGTERM didn't land) — a second, independent
reason not to ship this. **Reverted**: killed all three `pw-loopback`
processes, reloaded `module-remap-sink`/`-source`, re-confirmed SDL2 works
again (both drivers, see the logs below). No trace of `pw-loopback` remains
in any installed config; only the explanatory comment in
`config/15-astro-a50-remap.conf` referencing this decision does.

**Detour 2 — real escaping bug, found and fixed.** Advisor-prompted offline
validation (`pw-config -n pipewire-pulse.conf -r merge pulse.cmd` + a manual
reparse of its output) caught a real bug before it ever reached disk-persisted
config: a quoted, backslash-escaped `device.description='A50\ Game\ 5.1'`
that works fine typed at a shell (as in `apply-live.sh`, which is why the
*live* session uses exactly that spaced form successfully) does **not**
survive `config/15-astro-a50-remap.conf`'s double parse layer (PipeWire's own
config reader, then pipewire-pulse's module-argument splitter) unchanged —
came out as literal `A50`, truncated. **Also found while debugging this:**
trying to pack a *second* property (`priority.session=0`) into the same
`sink_properties=` value silently dropped it regardless of quoting style
tried (comma-separated, space-separated, nested-quoted) — `module-remap-sink`'s
property parser only reliably handles one simple `key=value`. Fixed the conf
file by using a space-free `device.description=A50_Game_5.1` (no quoting
needed, confirmed byte-identical round-trip through `pw-config -r merge`) and
abandoning the idea of setting priority through this mechanism at all (see
"priority/default-sink incident" below for where that protection actually
lives now). Also documented a known, non-fatal race in that same conf file:
it fires when pipewire-pulse itself starts, not when the A50's ALSA nodes
appear, so a bogus/missing `master=` loads as a silent disconnected stub
rather than failing (confirmed empirically) — low risk for this wired-dongle
headset, real for anything that enumerates USB late.

**Priority / default-sink incident — caught and fixed, read this before
touching defaults again.** During testing, `pactl get-default-sink`/
`-source` were briefly found to have silently switched to `A50_Game_51` /
`A50_Mic` after a sequence of module load/unload churn (not from any single
isolated action we could pin down) — i.e. the raw concern RESUME previously
flagged ("could it steal the system default") is real and was observed, not
theoretical. **Caught and reverted immediately** with `pactl set-default-sink/
-source` back to Audioengine speakers / the webcam mic, confirmed holding at
the end of this session. Root cause: ACP's own priority heuristic gives the
raw A50 ports `priority.session` values that already outrank or tie the real
defaults *before any remap layer exists* — `pro-input-0` (mic) = 2500 vs. the
webcam's 2009; `pro-output-0` (Voice) = 1500, a tie with Audioengine's 1500.
The `module-remap-sink`/`-source` virtual nodes carry no `priority.session`
of their own at all (confirmed via `pactl --format=json`, and confirmed not
fixable through their own args parser, see Detour 2) — fine on its own, but
it means **today's live fix carries no priority protection**, only the
explicit default pin above, valid only until the next node-add/remove event
re-triggers WirePlumber's default-nodes rescan. The actual fix is the
`priority.session = 0` / `priority.driver = 0` lines added to all four
`monitor.alsa.rules` node rules in `config/51-astro-a50-pro-audio.conf` (see
below) — race-free, race-free because it sets the RAW node's priority at the
moment WirePlumber's own ALSA monitor creates it — but like the rest of that
file, inactive until WirePlumber's next restart. **If anyone reboots or
restarts WirePlumber before reading this: re-check `pactl get-default-sink`/
`-source` resolve to Audioengine/webcam afterward and re-pin if not** — the
node rules should prevent a repeat, but this hasn't been restart-tested.

`config/51-astro-a50-pro-audio.conf` (installed to
`~/.config/wireplumber/wireplumber.conf.d/`) carries four new
`monitor.alsa.rules` node-level rules (added 2026-10-24, never live) that set
`audio.position`/`node.description`/`priority.session`/`priority.driver`
directly on `pro-output-0`, `pro-output-1`, `pro-input-0`, and `pro-input-1`
at the moment WirePlumber's own ALSA monitor creates them. Once live (next
WirePlumber restart), the raw nodes themselves will carry the correct channel
map and can never win default selection — at which point the
`module-remap-sink`/`-source` layer in `config/15-astro-a50-remap.conf`
becomes a harmless-but-redundant duplicate (worth unloading/removing then to
avoid doubled devices in a picker). This is the better long-term mechanism;
`module-remap-sink`/`-source` is what makes it work *today* without a restart.

Verified, not just configured:
- `pw-link -l`: `A50_Game_51`'s 6 output ports are linked straight through to
  `pro-output-1`'s 6 physical playback ports, same order (AUX0→AUX0, etc).
- SDL2 (`artifacts/surround-integration/sdl_probe.c`, compiled against the
  already-installed `libsdl2-dev`), run under **both** `SDL_AUDIODRIVER=pulseaudio`
  and `SDL_AUDIODRIVER=pipewire`: enumerates `A50 Game 5.1` by name and
  negotiates `channels=6` when requesting a 5.1 spec. Logs:
  `artifacts/surround-integration/sdl-{pulse,pipewire}-probe.log` (regenerated
  clean after the `pw-loopback` revert — these are against the final,
  shipped `module-remap-sink` mechanism, not the abandoned detour). The
  device was opened paused and never unpaused — silent, no audible test tone,
  per this worker's no-audible-sound constraint.
- `tools/a50_audio.py --verify` (new `remap_status()`): asserts all three
  remap nodes exist with the exact expected channel map; exits 1 if any are
  missing/wrong (tested both ways: unloaded `A50_Voice` live, confirmed exit 1,
  reloaded it, confirmed exit 0 again).
- System default sink/source confirmed back to correct (`pactl get-default-sink`/
  `-source` → Audioengine speakers / webcam mic) at the end of this session —
  see the incident note above for why this isn't a throwaway check.

Disabled (already stopped by Ben; now also `systemctl --user disable`d so they
don't re-enable on next boot): `a50-loopback-game.service`,
`a50-loopback-voice.service`. `~/.config/pipewire/pipewire.conf.d/a50-virtual-sinks.disabled`
left alone (already inert by filename, kept as backup per prior instruction).

**One remaining manual step, not applied here (needs Ben's sudo + a plasmashell
restart, both outside this worker's scope):** Ben has a real, local, diverted
KDE Plasma volume-applet hide list at
`/usr/lib/x86_64-linux-gnu/qt6/qml/org/kde/plasma/private/volume/PulseObjectFilterModel.qml`
(installed via `dpkg-divert`, original alongside as `.qml.distrib` — this is
the "existing hide config" Ben referred to; it was real, just not under
`~/.config`, which is why earlier scoped searches of wireplumber/pipewire/pulse
dotfiles didn't find it). It currently hides the NVIDIA HDMI clutter sinks,
the EasyEffects sink, and the old single-sink A50 `iec958-stereo` output
(stale now that pro-audio is active). A reviewable diff that additionally
hides the raw `pro-output-0`/`pro-output-1` A50 nodes and the new `A50_Voice`
chat sink — leaving `A50 Game 5.1` as the one visible A50 output in the tray,
with Voice still fully usable by apps that target it by name — is at
`artifacts/surround-integration/PulseObjectFilterModel.qml.diff` (before/after
full files alongside it). Applying it needs `sudo cp` over that root-owned
file and a plasmashell restart/logout to pick up the QML change; this is
cosmetic only (per Ben's own comment in the file) and does not block surround
actually working.

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
3. **Dolby ON/OFF toggle** — Verified listening comparison: "Very clear channel separation when Dolby was on, collapsed to L/R when off" under six-channel Game input. Individual channel positions and LFE treatment were not separately established.

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

3. **Software-side Dolby/mic-flip/headset-link status mapping:** Physical Dolby toggle confirmed functional by Ben's listening comparison. Software status semantics remain unresolved; `0x72` field_id1 is not a proven Dolby/mute/link indicator. Further static analysis or correlated live interaction can investigate this.

4. **Per-app stream routing / surround — DONE**, see "Normal-game 5.1 surround" above. The old external Game/Voice loopback services are `disabled` (were already stopped). Normal system-default routing is unchanged; Audioengine remains the default sink, A50 devices are explicit-select only.

5. **Config installation/reboot persistence — installed, restart-to-take-effect untested.** `config/51-astro-a50-pro-audio.conf` and `config/15-astro-a50-remap.conf` are both now installed under `~/.config/wireplumber/wireplumber.conf.d/` and `~/.config/pipewire/pipewire-pulse.conf.d/` respectively, and are also live-applied right now (hot, via `pactl`/already-active profile). Neither WirePlumber nor pipewire-pulse was restarted to test that the installed files alone (fresh process start, no prior `pactl` commands) reproduce the same state — that needs an actual logout/reboot or an explicit restart Ben approves.

6. **KDE tray hide-list — reviewable diff prepared, not applied.** See "Normal-game 5.1 surround" above: `artifacts/surround-integration/PulseObjectFilterModel.qml.diff` against Ben's real, local, dpkg-diverted `PulseObjectFilterModel.qml`. Needs Ben's sudo + a plasmashell restart/logout; cosmetic only.
