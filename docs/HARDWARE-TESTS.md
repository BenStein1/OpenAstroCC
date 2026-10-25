# Hardware tests that need Ben

Everything in `docs/FINDINGS.md` marked **[UNKNOWN]** about *physical behaviour*
is here. These cannot be derived from the Windows binary or the USB descriptors —
they need a human pressing buttons and listening.

Tests 1 and 2 are **read-only and zero-risk**: nothing is written to the headset,
no setting changes, no audio interruption. Test 3 changes a live audio profile.
Test 4 is listening only.

## Test 1 — Do the physical controls emit HID reports? (read-only)

The single most valuable unknown. The handoff is explicit that the headset may
handle its controls internally. A quiet capture records no unsolicited events
during that interval; it cannot rule out a polling or initialization requirement.

```
python3 tools/a50.py listen
```

Then, pausing a beat between each so the output is easy to attribute:

1. Press the **Game** side of the right earcup, a few times.
2. Press the **Voice** side of the right earcup, a few times.
3. Press the **DOLBY ON / SOURCE AUDIO** button; watch the base indicator change.
4. Press the **EQ** button to cycle slots 1 → 2 → 3; watch the base indicator.
5. Flip the **mic boom up** (mute), then **down** (live).
6. Turn the **volume wheel** up and down.
7. Toggle the **power switch** off and on.

Ctrl-C to stop. What the output means:

- **Reports appear** → the controls are observable from Linux. Note which
  action produced which `cmd=` and payload; that maps opcodes to physical
  controls empirically, which is exactly what static analysis could not do.
- **Nothing appears** → no unsolicited reports were observed in that interval.
  Keep polling, initialization, and internal-only control behavior as open
  possibilities until the corresponding code paths are traced.

Roughly which action produced which line matters, so narrate as you go if it
helps (`listen` numbers every report).

## Test 2 — Does the device push status unprompted? (read-only)

```
python3 tools/a50.py listen
```

Leave it running a few minutes untouched, then:

1. Lift the headset **off the charging base**; wait ~30s.
2. Put it **back on the base**; wait ~30s.

Battery level, charge state and dock state are the plausible candidates. If
reports arrive here but not in test 1, the device reports *state* but not
*button events* — useful to know, and enough to build a read-only status client.

**Partial result already in hand:** the listener was run for 12 s against the
live headset with no interaction, and received **zero reports**. So the device
does not stream unsolicited status while idle on that timescale. It may still
report on a *change* (undock, mic flip, battery transition), which is what the
steps above are for. This also confirms the listener itself opens, blocks and
reports correctly against real hardware.

## Test 3 — Simultaneous Game + Voice (changes a live setting)

This is the acceptance criterion that currently fails on Linux, and the
investigation identified a likely profile-routing problem that remains unverified
(`docs/FINDINGS.md` §10). **Your call to run.**

Two things to know first:

- **This will drop whatever is currently playing.** The Voice PCM (`hw:1,0`) was
  `Status: Running` during the inventory, so the A50 is in active use. Pick a
  moment when you're not mid-something.
- **Sink names change under `pro-audio`.** Any pinned default sink or per-app
  routing will need re-pointing afterwards.

### 3a — Test the hypothesis first, with no files and no restart

Switch the profile directly. Instant, and instantly reversible:

```
pactl list sinks short                       # before: one A50 sink

pactl set-card-profile alsa_card.usb-Astro_Gaming_Astro_A50-00 pro-audio
pactl list sinks short                       # expect TWO A50 sinks now
```

Revert at any point with:

```
pactl set-card-profile alsa_card.usb-Astro_Gaming_Astro_A50-00 \
    output:iec958-stereo+input:mono-fallback
```

Doing it this way separates *"is `pro-audio` the right answer?"* from *"does my
config file make it stick?"* — so a config syntax problem can't masquerade as the
profile being wrong.

### 3b — The actual behaviour test

1. Play game/music audio to the **Game** sink.
2. Play chat/voice audio to the **Voice** sink **at the same time**.
3. Confirm you hear both mixed in the headset.
4. Press the **Game** side of the earcup control → game should get relatively
   louder. Press the **Voice** side → voice should get relatively louder.
5. Confirm the **volume wheel** still changes overall level independently.

That step 4 behaviour is the headset's own hardware mixer. If both streams are
live and the control still does nothing, that is a finding worth recording —
report what you observe rather than what the manual promises.

### 3c — Make it persist (only if 3a/3b worked)

Profile selection may be restored by WirePlumber state, but persistence has not
been tested here. The supplied rule is also unvalidated; install only after the
live-profile test succeeds and separately approve any restart. Candidate setup:

```
mkdir -p ~/.config/wireplumber/wireplumber.conf.d
cp config/51-astro-a50-pro-audio.conf ~/.config/wireplumber/wireplumber.conf.d/
systemctl --user restart wireplumber
pactl list cards | grep -A1 Astro_Gaming   # confirm Active Profile: pro-audio
```

If the profile does *not* come up as `pro-audio` after the restart, the profile
choice and persistence mechanism both need further investigation.
WirePlumber 0.5 keeps its own persisted profile selection, so the alternative is
`wpctl set-profile <card-id> <profile-index>` (card id from `wpctl status`), or
clearing the stored selection in `~/.local/state/wireplumber/`.

Revert: delete the copied file and `systemctl --user restart wireplumber`.

To pick which sink is which: `pactl list sinks short` will show
`...pro-output-0` and `...pro-output-1`. Expectation is 0 = Voice (2ch),
1 = Game (6ch) — this is now confirmed by kernel UAC descriptors (`python3
tools/a50_audio.py`'s `uac_ground_truth()`, reading `/proc/asound/card1/stream0`
/`stream1` directly, independent of the active profile), not just inferred
from PCM order. Still worth a quick `pactl list sinks short` check after
switching — profile-ordering is a strong ALSA/PipeWire convention, not a
per-device guarantee — but it is no longer a blind guess; if they are swapped
the profile is still correct, only the labels in the config comment need
swapping.

**Before running this test, know that it alone will not give you simultaneous
independent Game+Voice.** This host already runs two pre-existing, non-repo
`pw-loopback` services (`a50-loopback-game.service`, `a50-loopback-voice.service`
in `~/.config/systemd/user/`, not part of this repo) that create virtual
`A50_Game`/`A50_Voice` sinks for app routing. Live `pw-link -l` tracing
(`tools/a50_audio.py`'s `trace_virtual_routes()`) proves both of those
*currently* forward into the same single physical sink — switching to
`pro-audio` does not retarget them. For this test to actually exercise two
independent USB paths, point apps directly at the new `pro-output-0`/
`pro-output-1` sinks (or repoint those two services' `target.object`), not at
the pre-existing `A50_Game`/`A50_Voice` virtual sinks, until/unless those
services are updated — which is outside this repo.

## Test 4 — Does the 6-channel Game profile render positionally? (listening)

The descriptor advertises L/R/C/LFE/LS/RS at 48 kHz on the Game function. Whether
the headset renders those discretely or downmixes internally cannot be read from
a descriptor.

### 4a — Verified 6-channel playback method

Direct positional render with raw stdin to `pro-output-1`:

```
pw-play --raw --rate=48000 --channels=6 --format=s16 \
  --channel-map=AUX0,AUX1,AUX2,AUX3,AUX4,AUX5 \
  --target=alsa_output.usb-Astro_Gaming_Astro_A50-00.pro-output-1 \
  < six-channel.s16le
```

**Important:** Use `< six-channel.s16le` input redirection, not positional filename.
`pw-play` in raw mode requires stdin when used with explicit format parameters;
positional filename without stdin exits without playing. The WAV player path
initially negotiated only 2 channels despite the WAV header declaring 6; the raw
stdin path with explicit parameters bypasses that negotiation.

### 4b — Verification (completed 2026-10-24)

Silent probe of all six channels confirmed individual link presence. With Dolby
toggle:

Ben's report: "Very clear channel separation when Dolby was on, collapsed to L/R when off".

This confirms an audible spatial-mode change under verified six-channel Game
input. The comparison did not separately establish every channel's perceived
position or the LFE treatment; no claim of silent centre/surround channels in
the off mode is supported by this report.

## What to report back

For each test: what you did, what happened, and anything surprising. Raw
`listen` output is more useful than a summary of it — the byte patterns are the
evidence. Negative results are genuinely valuable here; several open questions in
FINDINGS.md need bounded observations. Record the capture duration and actions;
a negative passive result does not establish that polling is impossible.
