# Latest checkpoint — slot 1 recovered (2026-10-24)

The inherited uncommitted client/tests/baselines were preserved and continued.
`docs/EQ-RECOVERY.md` records static bank semantics and successful host recovery:
slot1 working and stored now both `[-4,-2,-3,7,7]`; every other captured EQ
field and mediator setting was unchanged. Only verified six-byte `0x63` SET
was sent; no persistent sync. Private before/after/TX/RX are under
`artifacts/backups/slot1-recovery-host/`. Original evidence remains historical;
never restore its corrupted working gains. `tools/check_settings.py` offline
and existing selftest pass. Full app continuation follows this checkpoint.
Older unresolved-bank and no-write descriptions below are superseded.

# Astro A50 Linux — continuation handoff

**Latest checkpoint is [RESUME.md](RESUME.md). Read it first.** The full A50
setter trace strongly indicates the earlier short `0x63` probes modified slot1
working gains. Recovery is now verified at commit `2561494`: working and
stored slot1 gains match, other captured fields/settings are unchanged, and
no persistent sync was sent. The active Codex worker continues controls/UI. Older
“current result” sections below precede this discovery.

Updated 2026-10-24. Start with PROJECT.md and docs/A50-PROTOCOL.md (the
current, A50-bound protocol note); docs/FINDINGS.md §14 is the superseded
A20 history, kept for the record, not as current guidance.
This remains an investigation utility, not working Command Center support.

**Latest scope:** Ben now wants full documented Gen 3 feature support and
explicitly permits Codex workers. Current worker IDs and action boundaries are
in docs/WORKERS.md and the project AGENTS.md. Treat older Codex-retired and
no-active-workers statements below as historical, superseded by that note.

## Current result: live A50-bound EQ read succeeded

docs/A50-PROTOCOL.md records a static Ghidra trace binding `(0x9886, 0x15)`
to `Devices::AstroA50::vftable` (model name `Astro A50 Wireless`) through
`0x483640`/`0x419b00`/`0x4821a0`, and its headset-init path's EQ read:
shared builder `0x4794f0`, opcode **`0x69`**, one-byte slot (1–3).

`tools/a50.py eq-read --slot {1,2,3}` now sends exactly that request (no
page/raw-opcode argument), validates the opened fd's USB identity via
`HIDIOCGRAWINFO` before writing, checks the full 64-byte write, and bounds
the reply wait with `O_NONBLOCK` + `select` + `time.monotonic` (2s). It was
run live, once, against Ben's connected A50 (slot 1):

- TX: `02 69 01 01` + 60 zero bytes.
- RX: status `0x02` (success), sequence matched, payload `69 01 02 00 00 00
  00 08 0a 09 13 13` (12 bytes) — echoes opcode+slot correctly.
- Decoded (unsigned byte − 12 per bank): bank A `[-10, -12, -12, -12, -12]`,
  bank B `[-4, -2, -3, 7, 7]`. Bank semantics are *not* claimed.

Full TX/RX hex and the decode are in `evidence/a50-eq-read-slot1.json`.
This is the first verified A50-class read in this project's history.

## Superseded: the earlier A20-derived correction and live results

The previous pass traced `0x4800a0` to a resolved caller at `0x477770`, whose
constructor identifies `Devices::AstroA20`, PID `0x1c`. That does not bind the
reader to Ben's A50 PID `0x15`. Virtual/shared callers remain unresolved.
The earlier EQ/sidetone/noise-gate opcode claims must be treated as unverified
for A50 until tied to its registration/vtable path.

Six requests derived from that reader were sent to Ben's A50 in worker
`fd0c34b4-9fd0-4e80-9540-af6ea7e0da49` (completed, commit `3ad761d`):
page 0 with slots 0–2 returned status 1/code13,
`HID_ERROR_NO_EQ_WITH_THAT_VALUE`; page 1 returned status2 and payload `63 01`
for each slot. These observations support the shared framing/status/sequence
interpretation; none returned five decoded A50 gains. Page1 semantics remain
unknown. No intentional settings writes were attempted, but no before/after
state readback established whether device settings were unchanged.

**At that checkpoint the A20-derived transmit helper was removed. The current
CLI uses the separately verified A50 request described above.** Retain the
captured results and offline transport tests; do not recommend rerunning this
A20-derived request. The timeout backend's concrete virtual override has not
been located. Import/call-site searches do not prove it lives in a missing DLL.
No audio profile change, firmware action, or reset has been performed.

## Active work and next concrete target

**Done:** the A50 class binding (above) and the live `0x69` read. That closes
out the "bind `9886:0015` to `Devices::AstroA50`" step this section used to
describe as open.

Read-only worker **Astra-vtables**, `0d283f16-df8a-439b-b22b-6ec6cddc844f`,
independently reproduced the constructor/vtable path and investigated the
factory registry. It was stopped after the supervisor completed the exact
PID15 binding and the native-read worker validated the read, avoiding duplicate
work. No worker remains active.

Next concrete step: docs/A50-PROTOCOL.md notes the same initializer also
issues opcode `0x70` with slot 1–3 and band 1–5 to read coefficients. Trace
that request's exact payload shape the same way `0x69` was traced, and don't
infer a write layout from either read. Map the remaining `0x60`–`0x7C`
opcodes the same bounded, static-first way.

## Working tree and verification

Work in `/home/ben/Projects/astro-a50-linux`. All authored work is committed
locally; use `git log -6 --oneline` for the current review commit. Nothing pushed.

```bash
python3 tools/a50.py selftest
python3 tools/a50.py inventory
python3 tools/a50.py listen
```

The selftest checks framing/capacity, all four sequence values, malformed and
truncated input, invalid preset values, bandwidth encoding, all five preserved
factory presets, and (new) the `0x69` request byte shape, signed-offset bank
decode, echo/status/short-payload rejection, wrong-VID/PID-rejects-before-write,
short-write-aborts, and timeout-closes-fd for `eq-read` — all with mocked I/O,
no hardware needed. Inventory is read-only. Listen blocks until reports or
Ctrl-C; no unsolicited reports arrived during the initial 12-second idle
capture. EOF/disconnect now exits visibly. Silence is not proof that querying
is impossible.

Final supervisor checks (prior pass): selftest passed including all five
presets; read-only inventory confirmed the USB/audio topology via
sysfs/procfs; diff --check passed. The supervisor sandbox has no
`/dev/hidraw9` despite the sysfs entry, so its listener attempt exited
cleanly with ENOENT — an environment-access limit, not evidence the physical
headset disappeared. That pass's six diagnostic request/reply exchanges (A20-
derived, see "Superseded" above) did not decode an A50 settings read; this
pass's `0x69` read, run against the real connected A50, did — see "Current
result" above.

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
| `0x4800a0` | EQ reader reached by resolved A20 constructor; **superseded, not A50** |
| `0x481b80` | Property setter, app-side bounds lookup and sidetone/noise-gate dispatch |
| `0x4842d2` | Observed `0xDA` call site; unidentified, do not probe |
| `0x41ae40`/`0x483640`/`0x419b00`/`0x4821a0` | A50 registration chain: registry pairs runtime-ID list with factory, factory constructs `(0x9886,0x15)` and calls the ctor that assigns `Devices::AstroA50::vftable` |
| `0x485fd0` | A50 headset init; logs "initializing headset", loops 3 slots, calls `0x4794f0` with opcode `0x69` — the traced EQ-gains read |
| `0x490620`/`0x479f70` | Generic send/wait wrapper and its reply-shape comparison (declared length vs. app packet offset 2) used by the `0x69` read |

Evidence IDs and analysis profile digest are in docs/FINDINGS.md §15.
The supervisor exported a provider-neutral snapshot to ignored
`artifacts/analysis/a50-root-snapshot.json` (15,118,223 bytes; 13 primitive
bindings, 17 evidence records), and saved individual A50 dossiers beside it.
Resume with REA open_binary using the preserved EXE and that snapshot_path,
subject to matching artifact/provider/profile validation. Earlier worker IDs
may still be session-bound; use the snapshot and A50-PROTOCOL.md for the verified
class path.
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
3. **Superseded.** The original `tools/a50.py eq-read` targeted `AstroA20`'s
   opcode (`0x63`), not `AstroA50`'s; it was disabled, then replaced.
4. **Done this pass.** Located `Devices::AstroA50::vftable` and its
   registration chain in Ghidra (docs/A50-PROTOCOL.md), found its headset-init
   EQ read (opcode `0x69`, slot 1–3), implemented it in `tools/a50.py eq-read`,
   and ran it live against Ben's A50 (slot 1) — success, see "Current result"
   above. **New concrete next step:** the same initializer also issues opcode
   `0x70` with slot 1–3 and band 1–5 for coefficients — trace that request's
   exact shape before implementing it; don't infer a write layout from either
   read.
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

Worker **Astra-native-read** (Claude): **completed and committed.** Used the
root-supplied docs/A50-PROTOCOL.md (static A50 model binding and the opcode
`0x69` request/response layout, already traced in Ghidra — no repeat
RE/search needed) to replace the disabled `eq-read` with the real request.
Validated the opened hidraw fd's identity via `HIDIOCGRAWINFO` before
writing, bounded the reply wait with `O_NONBLOCK`+`select`, decoded the
error-packet layout (LE uint32 code + ASCII message) from FINDINGS.md §14.2,
added offline selftest coverage for all of that (request shape, bank decode,
echo/status/short-payload rejection, wrong-identity-rejects-before-write,
short-write-abort, timeout-close), then ran exactly one live read (slot 1)
against Ben's connected A50 — success (see "Current result" above). Did not
touch the parallel read-only worker `0d283f16-df8a-439b-b22b-6ec6cddc844f`'s
scope. Remaining gap: the `0x70`/{slot,band} coefficient read is traced in
the doc but not yet implemented or exercised.

## Astra-complete milestone: acceptance ledger

`docs/FEATURES.md` now tracks every requested feature separately across evidence,
native GET/SET, UI and real verification. Full support remains incomplete.
The worktree started clean. EQ/coefficient and mediator analysis is active;
complementary mic/stream analysis is supervisor-owned. Audio approval is pending.
