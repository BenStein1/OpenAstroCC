# Astro A50 Gen 3 — native Linux support

Reverse-engineering and native tooling for the **Astro A50 Gen 3** (the wireless
headset with the large rectangular magnetic charging base), USB `9886:0015`.
Not Gen 1/2, not Gen 4.

Mission and acceptance criteria come from the project handoff
(`Projects/BlueSky/Astro-A50-Gen3-Linux-plan.md` in `BenStein1/obsidian-projects`).

**Status:** first investigation pass complete. Protocol framing and the EQ format
are established from the shipped Windows binary and cross-validated against
shipped data. The profile inventory identifies a likely Game/Voice routing issue; the supplied
configuration remains untested in playback. Nothing has been written to
the headset and no live configuration was changed.

## What's here

For a context reset, start with [HANDOFF.md](HANDOFF.md) and [PROJECT.md](PROJECT.md).

| Path | What |
|---|---|
| `docs/FINDINGS.md` | **Start here.** Full findings: device identity, USB topology, HID wire format, EQ protocol, opcode space, open unknowns, evidence IDs. |
| `docs/HARDWARE-TESTS.md` | The four tests that need Ben at the hardware, with exact commands. |
| `tools/a50.py` | Read-only inventory, passive HID listener, offline `.astroeq` decoder, one evidenced live EQ-gains read, selftest. |
| `config/51-astro-a50-pro-audio.conf` | WirePlumber rule exposing both Game and Voice. **Not installed.** |
| `evidence/` | Raw hardware evidence: `lsusb -v`, HID report descriptor, ALSA stream maps, PipeWire card dump. |
| `artifacts/` | Preserved Windows app trees and settings. **Git-ignored, never commit** — proprietary binaries and personal settings. |

## Quick start

```bash
python3 tools/a50.py selftest     # offline, no hardware needed
python3 tools/a50.py inventory    # identify the device and its audio topology
python3 tools/a50.py listen       # passively watch HID reports (read-only)
python3 tools/a50.py eq "artifacts/classic-acc/assets/Astro A50 Wireless/Astro EQ/ASTRO.astroeq"
```

Stdlib Python 3 only. The first worker observed `/dev/hidraw9` readable on the
host; rediscover the node and check access in the environment running the tool.
The supervisor sandbox exposes the sysfs entry but not that `/dev` node.

## The headline findings

- **Two real, independent audio functions**, named by the device's own USB
  interface string descriptors: `Astro A50 Voice` (`hw:1,0`, 2ch out + 1ch 16 kHz
  mic) and `Astro A50 Game` (`hw:1,1`, **6ch** 48 kHz out + 2ch aux in). No
  guesswork — the device labels them.
- **The card exposes zero UAC mixer controls.** Sidetone, EQ, balance and the rest
  are absent from that mixer. The classic app uses HID for the traced settings;
  this does not prove HID is the only possible vendor mechanism.
- **A profile is a likely Game/Voice routing blocker, pending playback tests.** Every
  PipeWire profile except `pro-audio` exposes a single sink, so both functions can
  never be live at once and the headset's hardware balance control has nothing to
  act on. `pro-audio` exposes 2 sinks + 2 sources and passes audio through
  untouched. Config supplied; applying it is Ben's call.
- **HID wire format (confirmed by two independent code paths):**
  `[0]=0x02 report ID` `[1]=opcode` `[2]=(len & 0x3F) | (seq<<6)` `[3+]=payload`,
  zero-padded to 64 bytes.
- **EQ protocol fully cross-validated:** opcodes `0x63` (gains) and `0x64`
  (frequencies), 3 slots × 5 bands, gains as signed dB bytes, frequencies as
  little-endian uint16 Hz, bandwidths as 4.12 fixed-point octaves. The decompiled
  loop counts and the shipped `.astroeq` INI schema agree exactly — five gains,
  five frequencies, three bandwidths.
- **Sidetone = opcode `0x68`** (feature 37), **noise gate = opcode `0x66`**
  (feature 35), both single-byte, range-checked by the Windows app; device enforcement is unverified.
- **Preserved app state suggests the `europa` family.** Live firmware identity
  has not been queried, so the association remains inferred.

## What is deliberately NOT here

- **No writes to the device.** `tools/a50.py` opens hidraw `O_RDONLY` and has no
  transmit path at all. ~25 of the ~29 opcodes are unidentified and the per-feature
  valid ranges were not extracted, so a setter would be invented bytes. The
  handoff forbids that, and it's the right call.
- **No firmware anything.** The `.afw` file is preserved byte-for-byte and was
  never parsed, read from the device, or written.
- **No virtual mixer, no monitor loopback, no software sidetone.** The hardware
  does the mixing; substituting a software path would defeat the point.
- **No installed config.** `config/` is an artifact with install instructions.
- **No claim of full headset support.** See the honest per-feature status table in
  `docs/FINDINGS.md` §9.

## Next steps, in order of value

1. **Run `docs/HARDWARE-TESTS.md` tests 1 and 2** (zero-risk, read-only). Whether
   any physical control emits an HID report is the biggest single unknown, and it
   tests unsolicited events. Silence cannot exclude initialization or polling.
2. **Run test 3** to confirm `pro-audio` restores simultaneous Game + Voice and
   the earcup balance control. This is acceptance criterion #1.
3. **Map the remaining opcodes** in `0x60`–`0x7C` by decompiling the other builder
   functions listed in FINDINGS.md §7. Mechanical and bounded; the call sites are
   already enumerated. Note that the shortcut heuristic was tried and *failed* —
   §7 records why, so it isn't repeated.
4. **Extract the per-feature range table** (reached via vtable from the settings
   dispatcher) before anyone writes a single byte to the device.
5. Only then consider a setter, and only for features whose opcode *and* range are
   both evidenced.

## Working rules for this repo

- `artifacts/` is git-ignored and stays that way. Proprietary binaries and Ben's
  personal settings do not get committed or published.
- Keep observations, inferences and actual hardware execution separate — findings
  are tagged `[HW]` / `[STATIC]` / `[INFER]` / `[UNKNOWN]`. Don't promote an
  inference to a fact without the evidence type it requires.
- Don't invent protocol bytes. "Unknown" is a finding.
