# Astro A50 Gen 3 — Reverse-Engineering Findings

Worker: Astra. Date: 2026-10-24.

Every claim below is tagged with how it was established. The three categories are
kept strictly separate, as the handoff requires:

- **[HW]** — observed on Ben's actual connected hardware (read-only inventory).
- **[STATIC]** — observed in the shipped Windows binary / shipped data files.
  Static analysis never observed execution.
- **[INFER]** — reasoned from [HW]/[STATIC] evidence. Confidence stated.
- **[UNKNOWN]** — not established. Listed, not guessed.

No bytes were ever written to the headset. No firmware path was exercised. Live
audio configuration was left untouched.

## 1. Device identity

| Fact | Value | Evidence |
|-------------------|------------------------------|-----------|
| USB VID:PID       | `9886:0015`                  | [HW] `lsusb`; `evidence/lsusb-v-9886-0015.txt` |
| iManufacturer     | `Astro Gaming`               | [HW] |
| iProduct          | `Astro A50`                  | [HW] |
| iSerial           | absent (`0`)                 | [HW] |
| bcdDevice         | `0.00`                       | [HW] |
| ALSA card         | `card 1: A50`, `USB9886:0015`| [HW] `evidence/pactl-cards.txt` |
| Variant codename  | **europa candidate** (live identity unverified)       | [STATIC] see §6 |

`bcdDevice` is `0.00` and there is no serial string, so **firmware version is not
available from USB descriptors** — the Windows app must read it over HID. That
makes a firmware *read* the natural safe round-trip to validate a client against
later; it was not performed here.

The same VID:PID appears in Ben's own Windows app logs:
`D:12:17:50 : 2907975830 : WinHardwareBus : OnDeviceArrival: [x9886:x15]`
— consistent with the same device model; VID:PID alone is not a unique unit
identifier. [STATIC]

## 2. USB topology — 7 interfaces, two independent audio functions

Interface string descriptors name the two functions outright. This removes all
guesswork about which ALSA device is which. [HW] `evidence/usb-interface-strings.txt`

| Iface | Class | `interface` string | Role |
|---|---|---|---|
| 0 | Audio Control   | **`Astro A50 Voice`** | AudioControl for ifaces 1,2 |
| 1 | Audio Streaming | —                     | mic capture |
| 2 | Audio Streaming | —                     | chat playback |
| 3 | Audio Control   | **`Astro A50 Game`**  | AudioControl for ifaces 4,5 |
| 4 | Audio Streaming | —                     | game playback |
| 5 | Audio Streaming | —                     | aux/line capture |
| 6 | HID (vendor)    | —                     | control channel |

Resolved to ALSA PCMs. [HW] `evidence/asound-stream0-voice.txt`, `-stream1-game.txt`

| ALSA | Function | Playback | Capture |
|---|---|---|---|
| `hw:1,0` | **Voice** | 2ch 48 kHz S16_LE (FL FR) | **1ch 16 kHz** mono — the headset mic |
| `hw:1,1` | **Game**  | **6ch 48 kHz** S16_LE (FL FR FC LFE RL RR) | 2ch 48 kHz (FL FR) — **aux/line in, not a mic** |

Three consequences worth stating plainly:

1. **The mic is on the Voice device at 16 kHz mono**, and its USB terminal type is
   `0x0402 Headset`. [HW]
2. **The Game device's capture stream is the Line Connector (`0x0603`) passthrough**,
   not a microphone. [HW] A naive "use the A50 capture device" config can bind this
   and record silence. Worth guarding against in any config.
3. **Game playback genuinely advertises 6 channels** with
   `wChannelConfig 0x003f` = L/R/C/LFE/LS/RS, terminal type `0x0302 Headphones`. [HW]
   That is descriptor evidence that the 6-channel profile exists and is not fabricated.
   Whether the headset renders those six positions discretely (versus downmixing
   internally) is **[UNKNOWN]** — it requires Ben's listening test. The handoff's
   "do not assume 5.1" is satisfied by keeping these two statements separate, not
   by denying the descriptor.

### Zero USB-Audio mixer controls

`amixer -c 1 controls` returns only channel-map elements — **no volume, no mute, no
feature units at all**. [HW] `evidence/amixer-controls.txt`

The inspected ALSA mixer exposes none of these settings. The classic app uses
vendor HID for the traced controls; absence of ALSA controls alone does not rule
out other vendor mechanisms. PipeWire can still apply software stream volume.

## 3. HID control channel

Interface 6, two 64-byte interrupt endpoints (`0x85` IN, `0x05` OUT), bound by
`hid-generic`, exposed at **`/dev/hidraw9`**, mode `crw-rw-rw-` — readable by Ben's
user with no root and no udev rule. [HW]

Report descriptor is 39 bytes. [HW] `evidence/hid-report-descriptor.{bin,hex}`

```
06 32 ff    Usage Page (Vendor 0xFF32)
09 74       Usage (0x74)
a1 01       Collection (Application)
a1 03         Collection (Report)
85 02           Report ID (2)
75 08           Report Size (8)
15 00 26 ff 00  Logical Min 0 / Max 255
95 3f           Report Count (63)
09 75           Usage (0x75)
81 02           Input  (Data,Var,Abs)
75 08           Report Size (8)
15 00 26 ff 00  Logical Min 0 / Max 255
95 3f           Report Count (63)
09 76           Usage (0x76)
91 02           Output (Data,Var,Abs)
c0 c0       End Collection ×2
```

So: **one report ID (`0x02`), 63 data bytes in each direction, 64 bytes on the wire
including the ID.** Both directions are opaque byte arrays — the descriptor carries
no field semantics, which is why the protocol had to come from the binary.

## 4. Wire format (corroborated by a second code path)

Target: `artifacts/classic-acc/ASTRO Command Center.exe`
SHA-256 `991e558129af98765cba4f02b10fa5cc4d537e2b6bb4bd3032ca010832eb2dcf`
PE32 x86, Qt5, ACC **1.0.226**. Provider: Ghidra 12.1.4.

```
wire[0]  = 0x02                          HID report ID
wire[1]  = command opcode
wire[2]  = (payload_len & 0x3F) | (seq << 6)
wire[3+] = payload, zero-padded to 64 bytes
```

If `command & 0x80`, an extra byte `0x0A` is inserted at `wire[3]`, the payload
shifts to `wire[4]`, and the length field is incremented by one.

How each piece was established:

- **Report ID `0x02` at `wire[0]`, zero-padding** — serializer `FUN_004078f0`
  (`0x4078f0`). It allocates a `std::vector<unsigned char>` of the full report
  length, writes the report id to `buf[0]`, copies the application packet starting
  at `buf[1]` (`buf[i] = src[i-1]`), and zero-fills the remainder. [STATIC]
  Evidence `ev_f43a185a50719c861394a02d01f76cd9506f0733aa9e9928fad82fa33106e29f`
- **Transport** — `FUN_00404550` (`0x404550`), the sole caller of `WriteFile`:
  overlapped `WriteFile(handle, vec.begin(), vec.end()-vec.begin(), NULL, &ov)`
  under a mutex, handle cached at object offset `0x74`. Length is the vector size.
  [STATIC] `ev_27426c7c221ff4bec19e969b85e92d83c532e228dbae759421749a8cd6167824`
- **Header layout `cmd`,`len|seq<<6`** — packet builder `FUN_004794f0` (`0x4794f0`),
  called by all 35 command builders:
  ```c
  pkt.cmd    = command;
  pkt.lenSeq = ((end - start) & 0x3F) ^ (*seq << 6);
  (*seq)++;                                  // 2-bit sequence, per-packet
  if (command & 0x80) {                      // extended form
      pkt[6]     = 0x0A;
      pkt.lenSeq = ((lenSeq + 1) ^ lenSeq) & 0x3F ^ lenSeq;   // +1, low 6 bits only
  }
  memcpy(&pkt[6 + extended], start, end - start);
  ```
  The `((v+1) ^ v) & 0x3F ^ v` idiom increments the low 6 bits while preserving the
  two sequence bits. [STATIC]
  `ev_bea972d0c05c771d34c0ae5fef16463d2fa5e26f00e75a582eb56590471c35d7`
- **Corroboration that payload begins at `wire[3]`** — the EQ reader (§5) parses
  every device **response** starting at `QByteArray::data()[2]`, i.e. offset 2 of
  the application packet: a two-byte header before the payload, matching the
  `cmd` + `len|seq` pair above. [STATIC]

  Stated precisely: the serializer establishes the report ID at `wire[0]` and the
  one-byte shift *directly*. The EQ reader establishes a two-byte application
  header *on the read side*. Mapping that to `wire[3]` additionally assumes reads
  strip the report ID symmetrically to how writes add it. That is a reasonable
  assumption and the two observations reinforce each other, but the second is not
  strictly independent of it — **[INFER, high]** rather than observed.

  This does not affect the Linux decoder: `hidraw` returns the report ID as the
  first byte for numbered reports, so `unframe()` in `tools/a50.py` is correct
  either way.

### Payload capacity

The length field is 6 bits, so it can *encode* up to 63 — but that is not the
real limit. The report descriptor declares 63 data bytes, two of which are the
command header (`opcode`, `len|seq`). So the actual maximum payload is:

- **61 bytes** for a normal opcode, and
- **60 bytes** for a high-bit opcode, which spends one more byte on the `0x0A`
  extended marker.

Report capacity is the binding constraint, not the length field. `frame()` in
`tools/a50.py` enforces 61/60 and `selftest` asserts the boundary in both
directions — 61 accepted, 62 refused even though the length field could hold it.
Worth stating explicitly because the 6-bit field invites the wrong limit, and an
over-length buffer would be silently malformed rather than rejected.

## 5. EQ protocol — fully cross-validated

`FUN_004800a0` (`0x4800a0`) is the routine whose first act is logging
`"initializing headset"` — the same line present in Ben's real logs, which ties this
function to actual observed behaviour on his machine. It reads the whole EQ state at
startup. [STATIC] `ev_d3be5825b4a91d621595df0ce2ad51b4b5f6a75fd8a3f71666a0f223ee0e18f1`

```c
for (slot = 0; slot < 3; slot++) {            // exactly three slots
    send(0x63, payload = {0x00, slot});       // KUIPER_RW_EQ_GAINS (r)
    send(0x63, payload = {0x01, slot});       // second page
    for (i = 0; i < 5; i++) {                 // exactly five bands
        gainsA[i] = (int8) respA.data()[i+2];
        gainsB[i] = (int8) respB.data()[i+2];
    }
}
for (slot = 0; slot < 3; slot++) {
    send(0x64, payload = {0x00, slot});       // KUIPER_RW_EQ_FREQS (r)
    send(0x64, payload = {0x01, slot});
    freq[n]      = resp.data()[2] | (resp.data()[3] << 8);      // LE uint16, Hz
    bandwidth[n] = roundf(raw * (1.0f/4096.0f) * 10.0f);        // 3 values only
}
```

| Field | Encoding | Count |
|---|---|---|
| Band gain | signed byte, dB | 5 per slot |
| Band centre frequency | little-endian uint16, Hz | 5 per slot |
| Band bandwidth | **octaves**, 4.12 fixed point (`raw/4096`) | **3** per slot |
| Slots | `0`, `1`, `2` | 3 |
| Payload shape | `{page, slot}`, page ∈ {0,1} | — |

The bandwidth unit was pinned by the data, not assumed. The decompiled read is
`roundf(raw * (1/4096) * 10.0)` stored as an **int**, which initially looked like
an integer "Q" value — but the shipped presets contain `0.5`, `1`, `1.6`, `1.7`,
`2`. So the app's integer is **tenths of an octave** and the INI is that value
divided by ten; the device word is plain 4.12 fixed-point octaves
(`2.0 → 8192`, `0.5 → 2048`, `1.6 → 6554`). Every shipped bandwidth round-trips
exactly under that model, which `tools/a50.py selftest` asserts. The 0.5–2.0
octave span is an ordinary parametric-EQ range, which is a further consistency
check. [STATIC] + [INFER, high]

**This independently matches the shipped `.astroeq` files**, which are plain
QSettings INI (not zip — `quazip` is used elsewhere):

```ini
[General]
Name=ASTRO
[Eq_Bands]
Eq_Band_1=6  … Eq_Band_5=7            ; 5 signed gains
Eq_Freq_Band_1=90 … Eq_Freq_Band_5=7001   ; 5 frequencies in Hz
Eq_Bandwidth_2=2
Eq_Bandwidth_3=2
Eq_Bandwidth_4=2                      ; only 3 bandwidths — bands 2,3,4
```

Five gains, five frequencies, **three** bandwidths for the middle bands only — the
file schema and the decompiled loop counts agree exactly, from two independent
sources. This is the strongest single result in this pass, and it is why
`tools/a50.py eq` can be shipped as a verified decoder.

The three slots correspond to the three physical EQ-button positions documented in
the Gen 3 manual (base indicators 1/2/3, stock labels ASTRO/PRO/STUDIO). Stock
presets `ASTRO`, `PRO`, `STUDIO`, plus `MEDIA` and `A50 MOD KIT`, are preserved in
`artifacts/`.

## 6. Variant evidence: europa candidate

The handoff flagged that bundled "Mimas" assets do not prove Ben's headset is that
variant. Preserved app state suggests europa, but no live identity query has
validated this association. [INFER]

- The app created and populated `appdata-classic/Astro A50 Wireless/FW/` containing
  `merged_europa_000000000000_tm-36791_rm-36154_tr-0,0,42_rr-0,0,42.afw`.
- His logs say `copying vendor's EQ library for model 'Astro A50 Wireless'` and
  `AstroA50Sub : initializing headset`, with no Mimas model line for the attached device.
- The `Astro A50 Wireless (Mimas)/` directory holds only the vendor-shipped preset
  copies, no `FW/` directory.

The preserved app state associates **`Astro A50 Wireless`** with firmware family
**`europa`**; this is a candidate association, not proof of current live firmware, with `tm-36791` / `rm-36154` reading as transmitter
and receiver firmware revisions **[INFER, moderate]**. The internal product
codename for the software line is **`kuiper`** — from the update URL
`http://update.astrogaming.com/kuiper/win`, the command prefix `KUIPER_*`, and the
mutex `ASTRO_KUIPER_LAUNCH_MUTEX_…`. [STATIC]

**No firmware was read, written, parsed or flashed.** The `.afw` file is preserved
byte-for-byte only.

## 7. Command opcode space

All 82 call sites of the packet builder `FUN_004794f0` were located, and the opcode
immediate at each site extracted from the instruction stream. [STATIC]

Observed opcodes: **`0x60`–`0x7C` contiguous, plus `0xDA`.**

Named with direct evidence:

| Opcode | Meaning | Feature ID | Evidence |
|---|---|---|---|
| `0x63` | EQ band **gains** r/w | — | `KUIPER_RW_EQ_GAINS`, decompiled §5. **High** |
| `0x64` | EQ band **frequencies** r/w | — | `KUIPER_RW_EQ_FREQS`, decompiled §5. **High** |
| `0x66` | **Noise gate** set | `0x23` (35) | `KUIPER_SET_NOISEGATE`, decompiled §8. **High** |
| `0x68` | **Sidetone** set | `0x25` (37) | `KUIPER_SET_SIDETONE`, decompiled §8. **High** |
| `0xDA` | — | — | single site `0x4842d2` in `FUN_00484280`. **[UNKNOWN] — treat as dangerous.** |

**`0xDA` is the one opcode to leave strictly alone until it is identified.** It is
the only observed opcode with the high bit set, therefore the only user of the
extended `0x0A` framing form, it sits outside the contiguous `0x60`–`0x7C` block,
and it has exactly one call site. That profile makes it the strongest candidate
for the firmware-update path the handoff explicitly ring-fences. Nothing here
proves that — it is **[UNKNOWN]** — which is precisely why it must not be probed.
`FUN_00484280` should be the first target of the next Ghidra pass, specifically to
rule in or out a firmware write before anyone builds a transmit path at all.

The remaining ~25 opcodes in `0x60`–`0x7C` are **[UNKNOWN]**. They are real opcodes
— the immediates are in the instruction stream — but nothing here establishes which
feature each one carries.

**A rejected result, recorded so nobody repeats it:** I tried to auto-map opcodes to
feature IDs by pairing each opcode push with its nearest preceding comparison
immediate. Checked against the two cases proven by decompilation, the heuristic was
**wrong** (it attributed `0x66` to feature `0x02`; the decompiler proves `0x23`). The
compiler's `cmp`/`sub` chains do not sit adjacent to the matching push. The table was
discarded rather than published. Mapping the rest requires decompiling each of the
35 builder functions individually — bounded, mechanical, not done in this pass.

## 8. Settings dispatcher and the feature-ID enum

`FUN_00481b80` (`0x481b80`) is a property setter.
[STATIC] `ev_dbe6d8421919f41df68254e02af9859a5a364ca91882eb577a036778a1773aa6`

```c
value = QVariant → uint, then & 0xFF;          // every setting is a single byte
bounds = vtable[+8](featureId);                 // per-feature {min,max}
if (value < bounds.min || value > bounds.max) {
    qWarning("attempted to set bad value (%d) for %d");
    return;                                     // range-checked, no clamping
}
if (current == new) return;                     // no redundant writes
if (featureId == 0x23) send(0x66, …);           // noise gate
if (featureId == 0x25) send(0x68, …);           // sidetone
```

Two things to carry forward: **all these settings are single-byte values**, and the
device has a **per-feature valid range** fetched at runtime. The range table itself
is reached through a vtable and was not extracted — **[UNKNOWN]**, and it matters
before any write is ever attempted.

Ben's preserved logs enumerate the live feature-ID space directly, which is better
evidence than anything static: [STATIC]

```
Device : getting feature bounds of 20 … 41, 46 … 50
Device : getting int of 10, 11, 12, 17, 18, 19, 22 … 39, …
```

So feature IDs are a dense enum in roughly **10–50 decimal** (guard immediates in
the binary reach 92). Sidetone = **37**, noise gate = **35**, both present in that
list — the binary and the real logs agree.

The logs also name the sub-device decomposition, which lines up one-to-one with the
2016 Command Center feature list the handoff cites: [STATIC]

```
AstroA50Sub : initializing headset / mediator / microphone / stream mix
Device : WidgetSubDevice ctor: Headset / A50Microphone / A50Settings / A50StreamPort
```

`A50StreamPort` is the "USB Stream Port" mix (Game/Mic/Aux/Chat), `A50Microphone`
covers mic EQ and noise gate, "stream mix" is the mix state. Their opcodes are
**[UNKNOWN]**.

## 9. Handoff feature checklist — honest status

| Feature | Status |
|---|---|
| Separate Game + Voice playback | **Interfaces identified; playback unverified.** Independent USB audio functions exist. The profile is a likely routing blocker; test §10. |
| Real channel count | **Measured.** Voice 2ch/48k, Game 6ch/48k, mic 1ch/16k, aux 2ch/48k. Positional rendering unverified. |
| Three EQ slots | **Protocol understood** (opcodes `0x63`/`0x64`, 3 slots × 5 bands, cross-validated). Not exercised on hardware. |
| Sidetone | **Opcode identified** (`0x68`, feature 37, single byte). Valid range unknown. Not exercised. |
| Mic noise gate | **Opcode identified** (`0x66`, feature 35, single byte). Not exercised. |
| Mic EQ | Sub-device `A50Microphone` exists; opcode **[UNKNOWN]**. |
| Default Game:Voice balance | Setting exists per 2016 materials; opcode **[UNKNOWN]**. |
| USB Stream Port mix | Sub-device `A50StreamPort` exists; opcode **[UNKNOWN]**. |
| Base brightness, alert volume | In the `0x60`–`0x7C` space; opcode **[UNKNOWN]**. |
| Physical Game/Voice balance control | **[UNKNOWN] whether it emits HID at all.** A passive capture tests unsolicited events; initialization or polling may still be needed — §11. |
| Dolby / EQ buttons, flip-to-mute, battery | Same — unresolved until the passive listener runs during interaction. |
| Firmware version | Not in USB descriptors; must come over HID. Read path not located. No firmware action taken. |

## 10. Game/Voice routing — a likely Linux blocker

This is the finding with the most practical value, and it needs no protocol work.

PipeWire's ALSA-card-profile layer is treating the A50 as a single conventional
card. Active profile: [HW] `evidence/pactl-cards.txt`

```
Active Profile: output:iec958-stereo+input:mono-fallback
```

Available profiles and what they expose:

```
output:analog-stereo+input:mono-fallback     sinks: 1, sources: 1
output:iec958-stereo+input:mono-fallback     sinks: 1, sources: 1   ← active
output:iec958-ac3-surround-51                sinks: 1, sources: 0
pro-audio                                    sinks: 2, sources: 2   ← both functions
```

**Every profile except `pro-audio` exposes exactly one sink.** The Game and Voice
functions are not independently exposed as two sinks by the active profile.
That is a plausible explanation for the reported balance symptom, pending actual
playback. The generic ACP profile names alone do not establish hardware routing
or why ACP selected those mappings.

**`pro-audio` is the only profile that exposes both functions** (2 sinks, 2 sources),
and it passes channels through untouched — the headset keeps doing its own mixing,
with no substitute virtual mixer and no monitor loopback, as the handoff requires.
[HW] for the profile inventory; **[INFER, high]** that `pro-audio` is therefore the
correct profile.

Per the task's no-global-config-edits constraint, the config is delivered as an
in-repo artifact with install instructions and **has not been applied**:
`config/51-astro-a50-pro-audio.conf`. Ben's live audio was running on `hw:1,0`
during this work and was left alone.

Verification requires Ben (§11): switching the profile is a live audio change.

## 11. What needs Ben, and why it can't be inferred

These cannot be answered from shipped artifacts. Each needs a physical interaction
while `python3 tools/a50.py listen` records. Procedure: `docs/HARDWARE-TESTS.md`.

1. **Does any physical control emit an HID report?** Press the Game side, then the
   Voice side, of the right earcup; the Dolby/Source button; the EQ button; flip the
   mic boom up and down; turn the volume wheel. The handoff is explicit that button
   state may be handled internally. A silent capture means no unsolicited reports
   were observed during that test; it does not exclude initialization or polling.
2. **Does the device push unsolicited status?** Leave the listener running idle, on
   and off the charging base. Expect battery/charge/dock state if anything.
3. **Does `pro-audio` deliver simultaneous Game + Voice?** Switch profile, play game
   audio to one sink and chat to the other, then test the earcup balance control.
4. **Does the 6-channel Game profile render positionally?** Per-speaker test tones;
   confirm by listening, since no descriptor can establish this.

Items 1 and 2 are zero-risk and read-only. Item 3 changes a live setting. None
involve writing to the device.

## 12. Preservation status, and what was deliberately not analyzed

All four authorized trees were copied and verified **file-count and byte-exact**
against their sources, so the preservation is known-complete rather than
assumed-complete (`WindowsApps` in particular can silently skip ACL-restricted
files):

| Tree | Files | Bytes |
|---|---|---|
| `classic-acc` | 36 | 23,841,381 |
| `store-acc` | 98 | 15,971,353 |
| `appdata-classic` | 55 | 3,617,609 |
| `appdata-store` | 6 | 215,341 |

SHA-256 for every file: `evidence/ARTIFACT-MANIFEST.txt`. Source mtimes are
unchanged (the classic EXE still reads 2021-05-05), confirming read-only access.

**The Microsoft Store build 1.1.55.0 was preserved but deliberately not
analyzed.** That is a scoping decision, not an oversight. It is 64-bit managed
code (`AstroCommandCenter.dll`, `AstroGaming.Xbox.Devices.dll`, `.winmd`) and the
handoff states it is the version that does *not* work with Ben's Gen 3 — so the
classic native build was the authoritative target. It remains available for a
comparison pass, which could be worthwhile: a managed assembly usually retains
real method and enum names, so it is a plausible shortcut to naming the feature-ID
enum and the unidentified opcodes in §7. Route it via
`inspect_managed_artifact`, not Ghidra.

## 13. Prior art

Checked narrowly, as authorized. Public Linux Astro work I am aware of targets later
generations under Logitech's `046d` VID; this Gen 3 base enumerates under Astro's own
`9886:0015` with the `KUIPER` protocol described here, and I found no existing
open-source support for it to cite or build on. Recorded as a bounded negative
result from a brief search, not an exhaustive survey — worth a second look before
anyone writes a setter from scratch.

## 13. Evidence IDs

Ghidra 12.1.4, target SHA-256 `991e5581…2eb2dcf`, analysis profile digest
`4f6212bfe31448a7b96743a449e91c35890105cedd34e1d9951e9467d284e0a5`.

| Evidence ID | Operation |
|---|---|
| `ev_96fe7f31b3d87290bd4120b5c81bfcf37d33e4e77796f7bf2a77a144d7c6577a` | strings `sidetone` |
| `ev_c5004a870be495eb24b8153f6ac19f5fbcbf463b2fa322df172fc952a3553987` | strings `KUIPER_` |
| `ev_267ff994784ca74d648ffa0f4de1997db4338938637c374b45d1c4705a906301` | strings ` (w):` |
| `ev_5c4bcdafe9ec1561415ab494757ef930f85e60e80ca67635cd97bfce71b98e80` | xrefs `0x4d3480` |
| `ev_0bc52d6e5a988548f4ddc75ca2dd74c30f7ab20590ea707072989c3a988294af` | xrefs `0x4d3350` |
| `ev_dbe6d8421919f41df68254e02af9859a5a364ca91882eb577a036778a1773aa6` | pseudocode `0x481b80` settings dispatcher |
| `ev_bea972d0c05c771d34c0ae5fef16463d2fa5e26f00e75a582eb56590471c35d7` | pseudocode `0x4794f0` packet builder |
| `ev_27426c7c221ff4bec19e969b85e92d83c532e228dbae759421749a8cd6167824` | pseudocode `0x404550` WriteFile transport |
| `ev_f43a185a50719c861394a02d01f76cd9506f0733aa9e9928fad82fa33106e29f` | pseudocode `0x4078f0` report serializer |
| `ev_d3be5825b4a91d621595df0ce2ad51b4b5f6a75fd8a3f71666a0f223ee0e18f1` | pseudocode `0x4800a0` EQ reader |
| `ev_8e94388d7bacc364575d7e01cc40ca2c83d036cf164afa571657b8021c389b61` | callers of `0x4794f0` (35 builders) |
| `ev_e66b83a4044c1f3058c7a4e6c58e6cb9beb53a0d0d2b5eed359c524242d34619` | callers of `WriteFile` |
| `ev_6fc669734c53314e0b0d361e82a9abe145a5e06d6f2cdafa45888bf3f5025ba9` | containing procedure `0x480129` |
| `ev_579de45820396d1b0dbff1e595d72aaf1e82df9a43f02e7b3dfeab133634d9f1` | containing procedure `0x481c8f` |

Ghidra's own stated limits apply: only decompiler output, only Ghidra-defined
strings, and an empty search does not prove text is absent. Pseudocode is not
original source.
