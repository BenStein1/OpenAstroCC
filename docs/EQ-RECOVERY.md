# Slot 1 working-gain recovery

2026-10-24. The full A50 setter trace identifies opcode `0x63` as a
six-byte write: slot 1–3 plus five gain bytes encoded as gain+12.

Earlier diagnostic requests incorrectly treated the A20-shaped `0x63`
payload `{page,slot}` as a read for A50. The three page1 requests therefore
had payloads `{1,0}`, `{1,1}`, `{1,2}`. The current slot1 working gains are
`[-10,-12,-12,-12,-12]`: exactly the final `{1,2}` packet's gain byte2 and
zero-filled remaining fields after subtracting12. Slot2/3 working and stored
gains agree. The observed values strongly support unintended modification of
slot1's working gains during that earlier diagnostic pass.

The new read-only snapshot `evidence/a50-baseline.json` captured:

- Slot1 working: `[-10,-12,-12,-12,-12]`.
- Slot1 stored: `[-4,-2,-3,7,7]`.
- All slot1 frequency/bandwidth fields agree between working and stored.
- Slots2/3 working/stored agree throughout the captured EQ settings.

Worker `80fca206-08f3-4495-aa82-7c38ca632cd2` was cancelled after this
finding, before intentional write validation, to prevent treating the corrupted
working state as a baseline or syncing it over the retained stored bank.
Its uncommitted client changes, snapshot and tests are preserved in place.

## Required next action

Confirm the working/stored interpretation from the A50 constructor/setter/
sync paths, retain both banks and captures privately, and restore only slot1
working gains from the retained stored gains using the verified six-byte
write. Immediately read back both banks and verify the stored bank and all
other EQ fields remain unchanged. Do not sync the old working bank to storage.
Record exact TX/RX and before/after/restoration result before continuing.

This recovery is part of the requested headset work. No firmware or reset,
audio-profile change, test tones, or other settings mutation is authorized by
this note. Full-feature implementation follows after this checkpoint.

## Completed recovery — 2026-10-24

Confirmed from the retained classic ACC target (SHA-256 in A50-PROTOCOL):
A50 constructor `0x4821a0` constructs Europa headset `0x484d30`. Its vtable
`0x4d3650` contains setter `0x488ab0`, getter `0x47fb10`, bounds
`0x485cb0`, and post-sync copy `0x480d70` (direct PE table read).
Initializer `0x485fd0` puts first-bank gains at object+0x10, second at+0xd0.
Setter `0x488ab0` changes +0x10 and sends six bytes, slot then gain+12.
Mediator apply `0x488d10` sends `0x61`, checks completion, then invokes each
subdevice's +0xc vtable entry; `0x480d70` copies +0x10 into +0xd0. Thus
first=working, second=stored. This is static semantics, corroborated below.

Ran `tools/recover_slot1.py artifacts/backups/slot1-recovery-host` against
the host device after the sandbox could not see its hidraw node. Successful:
working slot1 is now `[-4,-2,-3,7,7]`, equal to its retained stored bank.
The only write was opcode `0x63`, six-byte payload `01 08 0a 09 13 13`
(full report and ACK in private capture). Both gain banks were read immediately;
a complete subsequent snapshot proved all other captured EQ fields and
mediator settings unchanged. No `0x61` apply/sync was sent.

Original client/tests/baselines remain in `artifacts/backups/pre-recovery/`.
Exact before/after, immediate readback, result and TX/RX are preserved in
`artifacts/backups/slot1-recovery-host/`. Original evidence files are retained
unchanged; **their corrupted working bank is historical, never a restore target**.
Use the recovered after.json as the baseline for later validation.
