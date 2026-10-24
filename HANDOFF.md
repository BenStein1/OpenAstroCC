# Astro A50 Linux — continuation handoff

Updated 2026-10-24 (Astra-read-path pass). Read PROJECT.md for the Obsidian
status; docs/FINDINGS.md contains the detailed evidence ledger, including new
§14 (transport/reply-matching trace + a live device test). The CLI is an
investigation foundation, not a finished Command Center replacement. No
settings were changed on the device; `tools/a50.py eq-read` sends one proven
read-only request and nothing else (see below). No audio profile changes
have been performed.

## This pass: wire protocol proven live; wrong device class identified (not a dead end)

`tools/a50.py eq-read --slot N --page {0,1}` sends the decompiled
KUIPER_RW_EQ_GAINS read request (opcode `0x63`, payload `{page,slot}`) and
validates the reply exactly as the decompiled app does (status byte `0x02`,
2-bit sequence match — see FINDINGS.md §14.2). Static evidence for this is
now complete: the full send→transport→wait→verify chain is traced down to
the point where the concrete blocking-read implementation leaves this EXE
(`ReadFile` has a single call site in the whole binary, inside the
already-documented write path — the read/timeout side is in a vendor DLL not
in the preserved tree).

Run live against Ben's connected A50 (`/dev/hidraw9` present this session),
all 6 slot×page combinations the CLI exposes: slot 0-2/page 0 all returned a
**well-formed, correctly-sequenced structured error**, status `0x01`, code
`13`, message `HID_ERROR_NO_EQ_WITH_THAT_VALUE`; slot 0-2/page 1 all returned
status `0x02` (success) but only a 2-byte payload (`63 01`), too short to be
5 gain bytes. This is not a transport failure — a wrong/garbled packet could
not produce a correctly-sequenced, legible English error. **The wire protocol
itself (framing, 2-bit sequence correlation, status-byte/error-packet layout)
is now confirmed live, not just inferred from the binary.**

Root cause, found statically (not by further live probing): `0x4800a0`'s only
resolved caller (`0x477770`) is the **`Devices::AstroA20`** constructor —
registers PID `0x9886:0x1c`, not the A50's `0x15`. A genuinely separate
`Devices::AstroA50` class hierarchy exists in the binary (confirmed via RTTI
strings: `AstroA50`, `AstroA50Mimas`, `AstroA50SubDevice`,
`AstroA50EuropaHeadset`, `AstroA50EuropaMediator`, …, matching the Europa vs
Mimas split in §6). **`0x4800a0` is the A20's EQ reader, not confirmed for
A50.** `AstroA50`/`AstroA50EuropaHeadset` likely has its own sibling function
reached via a vtable this pass did not resolve. See FINDINGS.md §14.3 for the
full evidence chain.

**Next step is static, not another live probe:** locate the
`AstroA50`/`AstroA50EuropaHeadset` vtable (via its RTTI typeinfo at
`0x663c4c` or the `AstroA50` constructor, by the same pattern as `0x477770`)
and walk its virtual function table for the sibling of `0x4800a0`. Do not
brute-force more slot/page/opcode combinations against the live device —
that crosses into guessed-packet territory this project explicitly avoids.
The `eq-read` CLI itself is correct and kept as-is; it is a faithful,
narrowly-scoped implementation of the proven wire mechanics, just aimed at
what turned out to be the wrong device class's opcode.

## Working tree and verification

Work in `/home/ben/Projects/astro-a50-linux`. All authored work is committed
locally; use `git log -6 --oneline` for the current review commit. Nothing pushed.

```bash
python3 tools/a50.py selftest
python3 tools/a50.py inventory
python3 tools/a50.py listen
```

The selftest checks framing/capacity, all four sequence values, malformed and
truncated input, invalid preset values, bandwidth encoding and all five preserved
factory presets. Inventory is read-only. Listen blocks until reports or Ctrl-C;
no unsolicited reports arrived during the initial 12-second idle capture.
EOF/disconnect now exits visibly. Silence is not proof that querying is impossible.
The review also exercises EOF and read-error handling with mocked I/O, and
corrects half-tenth rounding to match the app's positive roundf behavior.

Final supervisor checks: selftest passed including all five presets; read-only
inventory confirmed the USB/audio topology via sysfs/procfs; diff --check passed.
The supervisor sandbox has no `/dev/hidraw9` despite the sysfs entry, so its
listener attempt exited cleanly with ENOENT. This is an environment-access limit,
not evidence that the physical headset disappeared. The first worker's host-side
12-second passive capture is the only successful live HID capture so far.

## Preserved analysis target

Classic executable: `artifacts/classic-acc/ASTRO Command Center.exe`.
SHA-256: `991e558129af98765cba4f02b10fa5cc4d537e2b6bb4bd3032ca010832eb2dcf`.
Native PE32 x86 Qt5, classic ACC 1.0.226. Ghidra provider version 12.1.4.
The first REA session was closed. Reopen this artifact explicitly with Ghidra;
do not select the Store build by mistake. Preserved files are ignored and private.
The Windows source trees were copied and checked byte-for-byte; no more source
reads are needed for continued analysis. Do not read off-limits `*.log` files.

Key procedures from the first pass:

| Address | Role |
|---|---|
| `0x4078f0` | Report serializer: ID 2, body copied after it, padded |
| `0x404550` | Windows overlapped WriteFile transport |
| `0x4794f0` | Shared command packet builder; 2-bit sequence |
| `0x4800a0` | Startup EQ read flow, 3 slots, gains/frequencies/bandwidths |
| `0x481b80` | Property setter, app-side bounds lookup and sidetone/noise-gate dispatch |
| `0x4842d2` | Observed `0xDA` call site; unidentified, do not probe |

Evidence IDs and analysis profile digest are in docs/FINDINGS.md §15.
Those IDs may be tied to the original REA session: raw native evidence has not
been exported into a verified portable bundle. If unavailable, reproduce focused
decompilation at the addresses above and retain/export the new evidence locally.
Do not commit proprietary code dumps or personal app state.

## Next engineering work

Additional user evidence: Ben ran the passive listener on Torvalds, opened
`/dev/hidraw9`, then stopped with Ctrl-C after zero reports. Capture duration
and which controls, if any, were used are unspecified. The pasted output uses
the pre-review closing message; current `tools/a50.py` has the qualified
wording. Do not ask Ben to repeat this passive test as a prerequisite for
tracing the initialization/query paths.

1. **Done this pass (FINDINGS.md §14).** Reply length/status/sequence matching
   is established and live-confirmed. Timeout is not traceable from this EXE
   (`ReadFile` has zero call sites outside the write path) — that remains
   genuinely unresolved, not merely unexplored.
2. Trace settings GET and identity/status calls. Locate the feature-bound table
   through the setter vtable. Most opcodes `0x60`–`0x7C` remain unidentified.
   Sidetone SET is `0x68`, feature 37; noise gate SET is `0x66`, feature 35.
   An app-side guard does not establish device enforcement or valid ranges.
3. **Done this pass.** `tools/a50.py eq-read` is the smallest verified
   read-only query transport (validated slot/page, bounded tool-side timeout,
   sequence+status reply correlation). It targets the `AstroA20` class's
   opcode, not yet `AstroA50`'s — see next item.
4. **New concrete next step (static, not live):** locate `Devices::AstroA50` /
   `AstroA50EuropaHeadset`'s own vtable (RTTI typeinfo near `0x663c4c`,
   constructor pattern like `0x477770`) and find its sibling of `0x4800a0`.
   Only then exercise a slot/page value against hardware — do not iterate
   live guesses in the meantime.
5. Complete mic EQ, default mix, stream mix, brightness and alert-volume mapping.
   Keep firmware, resets and the unidentified extended `0xDA` path disabled.
6. Finish real Game/Voice and positional playback tests with Ben. The Game USB
   descriptor advertises six channels; actual rendering and physical controls
   still require listening and interaction. Capture low-volume test audio only
   after agreeing on a live playback test.

## Audio approval and unverified configuration

The only active profile observed was
`output:iec958-stereo+input:mono-fallback`. `pro-audio` advertises two sinks and
two sources. A question asking permission to switch the live profile was sent;
**no answer/approval has arrived**. Do not assume approval after a context reset.
The proposed switch and restore commands are in docs/HARDWARE-TESTS.md §3a.
No service restart or dotfile/config installation is needed for that test.
Persistent WirePlumber config remains an unvalidated candidate artifact.
The old test PCM named `pro-audio:CARD=...` was not established as an ALSA PCM;
validate a real targeted playback route before providing/running a test command.

## Worker recovery and execution blockers

- Astra (Claude), `f84cf343-c7d2-4b47-9765-24840eb5e824`: completed; first-pass
  commits `5f8ec7a`, `7890c53`, final capacity/evidence corrections `24dba7f`.
- `93d7e2f1-9480-4dc3-b0c6-43c9e830a4bb` and
  `f895a32c-846b-44da-b91d-6b7ecbf67386`: Claude continuations cancelled after
  no substantive progress; they authored no changes.
- `0386d3b0-218f-498a-97fd-be111bf972a5`: Gemini failed session creation;
  unsupported Code Assist ACP client.
- `f041fe76-80e2-4527-b4bf-ab5ec4848a41`: LiteLLM failed with HTTP 402,
  credit balance depleted, model group `merge-deepseek-v4-flash-0731`.

Ben subsequently clarified that Claude still has session capacity; skip Gemini.
For LiteLLM use `nvidia-free-reasoning` or `nvidia-free-fast`, not the depleted
Merge route. Astra-query is dispatched with exact catalog model
`litellm/nvidia-free-reasoning`, ID `7311268f-2653-4db5-bf77-337ba8fff0fe`.
That NVIDIA attempt was cancelled before edits: it proposed a generic opcode
query without establishing the request and reply handling first.

Worker **Astra-read-path**, `claude-code`, model `sonnet`, ID
`fd0c34b4-9fd0-4e80-9540-af6ea7e0da49`: **completed and committed.** Reopened
the matching artifact, confirmed `{page, slot}` in assembly, traced the full
send/wait/verify chain (`0x412700` → `0x493fd0` → `0x494b10`, reply validation
rule in FINDINGS.md §14.2), implemented `tools/a50.py eq-read`, and ran it
live against Ben's connected A50. Result: wire protocol (framing, sequence,
status/error layout) confirmed correct live; the specific opcode traced
(`0x63` via `0x4800a0`) turned out to belong to the `Devices::AstroA20` class,
not `AstroA50` — see FINDINGS.md §14.3 for the full chain and the concrete
next static step (locate `AstroA50`'s own vtable/sibling function). Not a
dead end: the hard part (transport mechanics) is now proven; what remains is
finding the right opcode for the right class, which is bounded static work.

Recover this worker with Nori get_worker before dispatching duplicate work;
worker execution is not persistent after Nori process exit. Do not blindly
redispatch to the failed routes or modify billing/client configuration as part
of this headset task. Continue from this repository using an available worker.
Codex workers are retired per the shared user instructions; do not dispatch one.
