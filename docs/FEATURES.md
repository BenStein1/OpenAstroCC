# A50 Gen 3 acceptance ledger

Updated 2026-10-24. All protocol claims bind USB9886:0015 to AstroA50/Europa.
A trace, implementation, numeric readback and physical behavior are separate gates.

| Feature | Protocol evidence | Native GET / SET | UI | Actual proof / remaining gate |
|---|---|---|---|---|
| Three EQ gain slots | 0x69/0x63, -12..12, bank semantics traced | Both, bounded + readback | Three tabs | All slots reversible changes restored; listening pending; slot1 recovery complete |
| Five EQ frequencies per slot | 0x70/0x6f, 80..15000Hz | Both | All15 frequencies | All15 reversible changes restored; listening pending |
| Three bell bandwidths per slot | Same; 4.12 fixed point,0.1..3oct | Both, raw precision retained | Nine octave controls; shelves disabled | All9 reversible changes restored |
| Persistent apply | 0x61, completion code0, full-device sync | Explicit API, bank readback | Explicit confirmation | Not sent; physical reconnect/power-cycle proof pending |
| Default Game/Voice balance | 0x77/0x73,0..255 | Both | Dock/defaults | Live reversible setting change restored; audible startup/default-balance behavior pending. Physical earcup balance was verified separately. |
| Dock brightness | 0x79/0x75,9channels20..70; empty status0 ACK | Both, GET readback | Uniform control, preserves unchanged channels | Live change restored; Ben visual confirmation pending |
| Alert volume | 0x7a/0x76,0..100 | Both | Dock/defaults | Live change restored; listening pending, no test sounds |
| Battery / charging | 0x72/01; payload14 low7/high1 | GET | Status bar | Live100%, not charging; physical charging transition pending |
| Physical balance / selected EQ | 0x72 payload10/payload6 | GET | Status bar/poll | Physical Game/Voice mixing verified with concurrent tones; status tracking during button presses and physical EQ selection remain pending. |
| Base/headset firmware identity | 0x03/0x83,37bytes,version at+21 | GET only | Device details | Live36791/36154; exact TX/RX retained |
| Dolby ON/OFF toggle | Six-channel Game input and all six stream links verified. Ben reported clear channel separation with Dolby on and L/R collapse with it off. | Physical button; software status mapping unresolved | No invented status labels | Controlled listening comparison passed; individual channel positions and LFE treatment were not separately established. |
| Onboard sidetone / mic gain / noise gate / mic EQ | 0x68/0x62 slider GET/SET; 0x6a/0x64 noise gate GET/SET (4 fixed packets); 0x7b/0x71 mic EQ GET/SET | Both, bounded 0..100 / enum, readback-verified | Microphone tab | CLI 38-check reversible pass restores exactly (sidetone, microphone_output, mic EQ, noise gate); GUI live write/readback/restore passed for sidetone + noise gate; listening/recording confirmation pending |
| USB stream Game/Mic/Aux/Chat | 0x68/0x62 slider GET/SET, selectors 0-3 | Both, bounded 0..100, readback-verified | Stream mix tab | CLI 38-check reversible pass restores exactly (all four stream sliders); GUI slider write/readback/restore exercised via the same widget type (Microphone tab), not yet clicked per stream-tab control; capture mix proof pending |
| JSON backup/restore (schema v2) | EQ + mediator settings + 6 sliders + mic EQ/noise gate, both banks | Validated, selective working-bank restore + rollback | Export/import to editor | Offline malformed-input/selective-restore/v1-compat tests pass; live CLI+GUI reversible restore passes; this is now a full working-settings backup, not partial |
| .astroeq import/export | Preserved presets and bounded A50 setters | Per-slot, exact bandwidth round trip | Import/export per tab | Offline exact round trip passes; live preset button write pending |
| Disconnect/reconnect | fd identity validated each operation; rediscovery | Bounded timeouts; cooperative lock | Disable writes, poll/reload on reconnect | Host GUI synthetic disconnect/reconnect passes; physical unplug/reinsert pending |
| Native PyQt6 | Installed system Python Qt6.9.2 | Threaded blocking HID I/O | Implemented | Offline render + host desktop button write/readback/restore passes; listening pending |
| Separate Game/Voice audio playback | hw:1,0 is 2ch 48k Voice stereo out + 1ch 16k mic in; hw:1,1 is 6ch 48k Game out + 2ch 48k line in (confirmed kernel UAC descriptors, independent of active profile) | pro-audio profile switches card to expose both as pro-output-0 (Voice) and pro-output-1 (Game) independently | Physical routing observable | Verified 2026-10-24: separate quiet 440Hz Game / 880Hz Voice tones heard comfortably in the headset. Concurrent 20sec tones both heard; Game button press favors Game, Voice button press favors Voice. Hardware mixing confirmed functional. |

Evidence: `artifacts/backups/slot1-recovery-host/`, `reversible-controls-2/`,
`identity-read/`, `full-controls-roundtrip/` (38-point CLI reversible check,
including sliders/mic/noise-gate, exact before==after), the live GUI write
checkpoint under `artifacts/backups/20261024-194620-a3c06269/` (exact
before==after); GUI screenshots `/tmp/a50-ui-smoke.png`,
`/tmp/a50-ui-workflow.png`. No sync, firmware, reset, profile switch, tones,
config installation, service restart or push. Full documented support remains
incomplete until the pending rows are closed.
