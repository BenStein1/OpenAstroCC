# Astro A50 Linux — continuation handoff

Updated 2026-10-24. Read PROJECT.md for the Obsidian status; docs/FINDINGS.md
contains the detailed evidence ledger. The CLI is an investigation foundation,
not a finished Command Center replacement. No device writes or audio profile
changes have been performed.

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

Evidence IDs and analysis profile digest are in docs/FINDINGS.md §13.
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

1. Re-read the startup EQ path and shared packet builder to establish exact
   read requests, reply length/opcode/sequence matching, initialization and
   timeout behavior. The CLI currently builds offline examples only.
2. Trace settings GET and identity/status calls. Locate the feature-bound table
   through the setter vtable. Most opcodes `0x60`–`0x7C` remain unidentified.
   Sidetone SET is `0x68`, feature 37; noise gate SET is `0x66`, feature 35.
   An app-side guard does not establish device enforcement or valid ranges.
3. Implement the smallest verified read-only query transport with device/interface
   validation, bounded timeout and reply correlation. A query needs host output
   reports but must not change settings. Do not infer read semantics from a
   command name or reuse unknown setters as queries.
4. Exercise one evidenced harmless query, retaining non-sensitive request/reply
   bytes and exact results. Then implement only settings whose encoding, valid
   range and write/readback behavior are established. No guessed packets.
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

Current worker: **Astra-read-path**, `claude-code`, model `sonnet`, ID
`fd0c34b4-9fd0-4e80-9540-af6ea7e0da49`. It reopened the matching artifact and
reports the EQ request payload `{page, slot}` confirmed in assembly. Newly
reported chain: `0x412700` obtains transport from the device object, `0x494b10`
performs blocking send/wait, and `0x479f70` validates replies. These are worker
progress observations pending full retained evidence and review, not proof of
a working native query. It is tracing initialization/query/reply paths and may
implement/execute only statically established harmless reads. It must update
this handoff and PROJECT.md and commit before completion.

Recover this worker with Nori get_worker before dispatching duplicate work;
worker execution is not persistent after Nori process exit. Do not blindly
redispatch to the failed routes or modify billing/client configuration as part
of this headset task. Continue from this repository using an available worker.
Codex workers are retired per the shared user instructions; do not dispatch one.
