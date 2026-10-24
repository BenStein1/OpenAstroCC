# A50 class binding and EQ parameter read

2026-10-24. Static REA/Ghidra analysis of classic ACC 1.0.226, SHA-256
`991e558129af98765cba4f02b10fa5cc4d537e2b6bb4bd3032ca010832eb2dcf`.
Full dossiers are saved privately in ignored `artifacts/analysis/a50-*.json`.
These observations supersede the A20-derived EQ request in FINDINGS §5/14.

## Model binding

- Registry `0x41ae40` pairs runtime-ID list `0x483640` with factory `0x419b00`.
  Evidence `ev_f429b2bcb14ce35d4be4de5e72f2efd2528d5287722099f9dd68061eaf6af4f6`.
- `0x483640` constructs `(0x9886, 0x15)`. Evidence
  `ev_d0b7a682b65ff328c2102e45e60c42b4b16f9ec3713232e8f6fb89cfeca46f17`.
- Factory `0x419b00` allocates the object and calls `0x4821a0`.
  Evidence `ev_e7d2af396b68fa25b80c020f8cd522e3be95f35e251064d649ea858f95209709`.
- `0x4821a0` assigns `Devices::AstroA50::vftable`, names the model
  `Astro A50 Wireless`, constructs Europa subdevices, and calls `0x485fd0`
  on its headset initialization path. Evidence
  `ev_dd5d38ca410ff97af6968631b3c7bbf7d4683974160432327b8e18c71101e8eb`.
- The separate `(0x9886,0x14)` ID comes from `0x4835e0`; its presence in the
  constructor is not the runtime-ID registration. Its precise mode meaning
  is not needed for the read below and is not claimed here.
- A50 vtables: primary `0x4d34bc`, secondary `0x4d3518`. Type descriptor
  `0x66396c`. Europa Headset type descriptor `0x663c44`, vtable `0x4d3650`,
  constructor `0x484d30`. The latter assigns the typed vtable explicitly:
  `ev_d0b38b047abcafaf128250c2f9f62e81cbddbcb6c9fc330b309abbfd2b8d6cc0`.

## EQ gains read — static request and response

Headset initialization `0x485fd0` logs `initializing headset`, loops three
times, and calls shared builder `0x4794f0` with command **`0x69`** and a
single-byte payload **slot 1, 2 or 3**. It labels the operation
`Read EQ Parameters:`. Evidence
`ev_2f53cf60248aa930b438894ec5819b2744cac959405ab8572e7eb62b6144ea57`.

For slot 1, sequence 0, the 64-byte HID output is:

```
02 69 01 01 [60 zero bytes]
```

Successful reply: report ID2; status2; length/sequence byte; payload begins
with the echoed opcode and slot (`69 01` for slot1). The decoder must check
sequence, success status, echo prefix and enough declared payload bytes before
interpreting gains. `0x490620` wraps generic send/wait and calls `0x479f70`.
The latter explicitly compares expected bytes against **application packet
offset2**, after the status/length header, and first checks declared length.
It is not merely a header comparison. Evidence IDs:

- `ev_d5b212c16bc537f5f8e86e04347df24a58d53285b2d140c49b77d13cd91669a0`
- `ev_7a4e764439d305cc33a59f7db4510006b532723721d0636340e62764bb2ec23f`

The initializer reads ten gain bytes at application offsets4–13: first five
at4–8 and second five at9–13. With `unframe()` stripping the two-byte
application header, these are payload offsets2–6 and7–11. Each gain is
**unsigned byte minus12**, rather than the earlier A20 signed-byte encoding.
Keep the two banks named bank A/B until their actual semantics are traced.
Require at least12 payload bytes (echo2 + gains10). A short success reply
is an error, never five inferred values.

The same initializer subsequently issues `0x70` with slot1–3 and band1–5
to read coefficients. That operation is outside the initial implementation.
Do not infer writes from either read layout. No A50 EQ read has yet been
run from this newly established path at the time of this note.

## Implementation boundary

Expose only a model-bound `eq-read --slot {1,2,3}`. Validate the opened HID
fd's USB identity before output, check a complete64-byte write, bound the
read wait, and validate all response fields above. No raw opcode option,
page argument, setters, resets, firmware operations, or guessed initialization.
If the exact read returns an error, retain it; do not expand the request space.

## Live verification

The native-read worker subsequently ran the exact slot1 read once, successfully.
Full request/reply bytes and both decoded banks are retained in
`evidence/a50-eq-read-slot1.json`. Code checks the opened fd identity, full write,
timeout, sequence, status, echo and payload length. Bank roles and settings
writes remain unverified. The supervisor snapshot is
`artifacts/analysis/a50-root-snapshot.json`; raw dossiers are beside it.
