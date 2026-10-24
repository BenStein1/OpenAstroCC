# A50 Gen 3 acceptance ledger

Updated 2026-10-24. Full feature support is **not complete**. A protocol trace,
a successful transaction, a UI control, and physical behavior are separate
acceptance gates. Only `9886:0015` and its bound AstroA50/Europa classes count.
“Pending” means no claim of implementation or verification.

| Feature | Protocol / platform evidence | Native GET / SET | UI | Live verification | Missing acceptance steps |
|---|---|---|---|---|---|
| Separate Game / Voice / microphone | Measured descriptors: Game 6ch 48k playback; Voice stereo 48k playback; mic mono 16k capture | Inventory only; profile unchanged | Pending | Descriptor inventory only | Expose independent routes; approved playback/capture test |
| Physical Game / Voice balance | Physical headset control | Pending status mapping | Pending | Pending Ben interaction | Listen while moving balance on independent routes |
| Dolby / passthrough | Physical control; rendering unverified | Pending status mapping | Pending | Pending Ben interaction | Confirm mode indication and actual rendering |
| Three EQ slots: gain | A50 init 0x485fd0 → 0x69, slots 1–3 | GET/SET implemented; working/stored traced | Pending | All slots GET; slot1 recovery SET/readback recorded | Remaining slots reversible SET checks; physical listening |
| EQ frequency / bandwidth | Same init → 0x70, slot/band | Pending | Pending | Pending | Exact request/reply, bounds, writes, round trip |
| EQ persistence / apply | Pending trace | Pending | Pending | Pending | Trace apply/storage semantics; verify after reconnect |
| Adjustable onboard sidetone | Europa mic subtree assigned to complementary investigation | Pending | Pending | Pending | Bound GET/SET, range, baseline/change/restore; Ben listening |
| Microphone EQ | Europa mic subtree | Pending | Pending | Pending | Bound GET/SET and enum, readback, physical recording |
| Microphone noise gate | Europa mic subtree | Pending | Pending | Pending | Bound GET/SET and enum, readback, physical recording |
| Microphone flip mute | Physical microphone control | Pending status mapping | Pending | Pending Ben interaction | Observe flip status and capture mute |
| Default Game / Voice balance | Pending mediator trace | Pending | Pending | Pending | GET/SET, range, apply/storage, round trip |
| USB Stream mix: Game / Mic / Aux / Chat | Europa stream subtree assigned to complementary investigation | Pending | Pending | Pending | Four bound controls, bounds, readback, capture mix |
| Dock brightness | Pending mediator trace | Pending | Pending | Pending | GET/SET, range, persistence, visual confirmation |
| Alert volume | Pending mediator trace | Pending | Pending | Pending | GET/SET, range, persistence; sound test approval |
| Battery / charging / connection status | Pending status trace | Pending | Pending | Pending | Poll bound read; compare physical state |
| Disconnect / reconnect | HID discovery exists | Single transaction only | Pending | Pending | Recover on removal/reinsert without stale handles/state |
| Firmware version (READ ONLY) | Pending identity trace | Pending | Pending | Pending | Bound version request and real reply; no update/reset |
| Native Linux UI | Installed toolkit inspection in progress | Existing CLI only | Pending | Pending | Expose verified controls, precise transport errors, actual GUI check |
| Configuration backup / restore | Offline .astroeq parser exists | Device export/restore pending | Pending | Offline preset parsing tested | Versioned validated export/import; baseline/readback/restore |

Live profile changes and test tones remain blocked on the existing unanswered
approval. Physical behavior needs Ben's interaction and must never be marked
verified from a mock, descriptor, packet ACK, or static trace.
