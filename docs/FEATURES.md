# A50 Gen 3 acceptance ledger

Updated 2026-10-24. All protocol claims bind USB9886:0015 to AstroA50/Europa.
A trace, implementation, numeric readback and physical behavior are separate gates.

| Feature | Protocol evidence | Native GET / SET | UI | Actual proof / remaining gate |
|---|---|---|---|---|
| Three EQ gain slots | 0x69/0x63, -12..12, bank semantics traced | Both, bounded + readback | Three tabs | All slots reversible changes restored; listening pending; slot1 recovery complete |
| Five EQ frequencies per slot | 0x70/0x6f, 80..15000Hz | Both | All15 frequencies | All15 reversible changes restored; listening pending |
| Three bell bandwidths per slot | Same; 4.12 fixed point,0.1..3oct | Both, raw precision retained | Nine octave controls; shelves disabled | All9 reversible changes restored |
| Persistent apply | 0x61, completion code0, full-device sync | Explicit API, bank readback | Explicit confirmation | Not sent; physical reconnect/power-cycle proof pending |
| Default Game/Voice balance | 0x77/0x73,0..255 | Both | Dock/defaults | Live reversible change restored; audible default balance pending |
| Dock brightness | 0x79/0x75,9channels20..70; empty status0 ACK | Both, GET readback | Uniform control, preserves unchanged channels | Live change restored; Ben visual confirmation pending |
| Alert volume | 0x7a/0x76,0..100 | Both | Dock/defaults | Live change restored; listening pending, no test sounds |
| Battery / charging | 0x72/01; payload14 low7/high1 | GET | Status bar | Live100%, not charging; physical charging transition pending |
| Physical balance / selected EQ | 0x72 payload10/payload6 | GET | Status bar/poll | Live balance128/EQ1; Ben physical interaction pending |
| Base/headset firmware identity | 0x03/0x83,37bytes,version at+21 | GET only | Device details | Live36791/36154; exact TX/RX retained |
| Dolby / flip mute / headset link | Remaining status semantics untraced | Raw status retained | No invented labels | Protocol mapping and physical proof pending |
| Onboard sidetone / mic gain / noise gate / mic EQ | Independent mic mapping worker owns trace | Pending integration | Pending | Bound enum/payload review + readback/listening/recording pending |
| USB stream Game/Mic/Aux/Chat | Independent mapping worker owns trace | Pending integration | Pending | Bound controls + capture mix proof pending |
| Partial JSON backup/restore | EQ + implemented mediator settings, both EQ banks | Validated, selective working-bank restore + rollback | Export/import to editor | Offline malformed-input/selective-restore tests pass; full mic/stream coverage pending |
| .astroeq import/export | Preserved presets and bounded A50 setters | Per-slot, exact bandwidth round trip | Import/export per tab | Offline exact round trip passes; live preset button write pending |
| Disconnect/reconnect | fd identity validated each operation; rediscovery | Bounded timeouts; cooperative lock | Disable writes, poll/reload on reconnect | Host GUI synthetic disconnect/reconnect passes; physical unplug/reinsert pending |
| Native PyQt6 | Installed system Python Qt6.9.2 | Threaded blocking HID I/O | Implemented | Offline render + host desktop button write/readback/restore passes; listening pending |
| Separate Game/Voice/mic audio | Measured Game6ch48k / Voice2ch48k / mic1ch16k | Read-only inventory; config artifact prepared | Route description | Profile switch/listening blocked on existing unanswered approval |

Evidence: `artifacts/backups/slot1-recovery-host/`, `reversible-controls-2/`,
`identity-read/`; GUI screenshot `/tmp/a50-ui-smoke.png`. No sync, firmware,
reset, profile switch, tones, config installation, service restart or push.
Full documented support remains incomplete until the pending rows are closed.
