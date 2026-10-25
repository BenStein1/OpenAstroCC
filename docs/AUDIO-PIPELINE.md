# EasyEffects EQ with A50 5.1

Checkpoint: 2026-10-24, Astra-eq-channel-architecture. Preparation and offline
verification only. No installation, live graph changes, playback, service/Plasma
restart, HID operation or hardware changes. Read RESUME.md's latest checkpoint
for live routing; older direct-surround success does not establish surround
survives EasyEffects. Ben's paired listening result (similar positioning, EE
brighter) is valid subjective evidence, not proof of six independent channels.

## Root cause and channel negotiation

A normal game chooses a speaker layout, often from PulseAudio's advertised sink
map, then opens a PCM stream. Six-channel interleaved PCM has six samples per
frame; it does not need six independent game streams. PipeWire's adapter can
convert that packed buffer to six planar DSP ports. Port count and stream format
are different layers. The existing A50_Game_51 remap labels FL/FR/FC/LFE/RL/RR
and sends those six lanes to pro-output-1 AUX0..5, then USB 9886:0015 Game PCM
at 48 kHz. This review inherits that routing evidence, not a fresh hardware test.

When EE captures the game, its sink adapter can accept a six-channel stream and
mix it to the sink's FL/FR processing layout. Seeing six channels in the game's
stream format therefore does not prove six channels leave EE. The installed
7.2.5 source hardcodes both the virtual sink to `audio.position=FL,FR` and
PluginBase to two main input/two output ports. Equalizer::process passes two
buffers into LSP's `para_equalizer_x32_lr`. Probe FL/FR ports are sidechains,
not extra surround channels. Changing the destination to A50_Game_51 cannot
reverse the information lost in this mix. The downstream adapter may remix
stereo to more lanes; it cannot reconstruct the game's original six channels.

**Can EE itself preserve 6ch?** Stock 7.2.5 cannot through its effects pipeline.
There is no native multichannel setting in the inspected path. Current tagged
8.3.0 and master revision 5419e60b62681975c010d2602a76577e86761db1 still create
the same stereo main ports and use the same stereo EQ process interface.
Upgrading alone is not a demonstrated solution. Merely adding surround ports
to its sink would leave plugin processing/linking stereo. A real EE enhancement
would need changes across sink, effects graph and channel handling, beyond this
minimal fix. No software was installed or upgraded.

## Actual loaded EQ (read only)

`last-loaded-output-preset` is `A2+ Bright`. Saved JSON matches live common EQ
settings and all seven left bands; unified mode propagates left to right in EE.
The saved left/right banks are identical. Input/output gain and balance/pitch
are zero, mode IIR, split-channels false, EQ bypass false. Every filter is Bell,
APO (DR), x1, width 4, not soloed/muted:

| Hz | Gain dB | Q |
|---:|---:|---:|
| 140 | +2.5 | 0.9 |
| 280 | -2.5 | 1.0 |
| 550 | -1.5 | 1.1 |
| 2500 | +4.0 | 1.2 |
| 4500 | +5.0 | 1.25 |
| 8500 | +7.0 | 0.95 |
| 14000 | +5.5 | 0.8 |

Bass Loudness precedes EQ but **is bypassed in both saved and live settings**.
Its saved parameters are loudness -3.1 dB, output -6 dB, link -9.1 dB, external
input/output gains zero. EE uses mda Loudness for this separate effect; it is
not folded into the EQ export. Enabling it later requires separate investigation
and comparison. The exporter refuses an enabled Bass Loudness chain.

## Smallest prepared solution

`tools/a50_eq_config.py PRESET` emits a standalone PipeWire filter client config
on stdout, without reading host state or connecting to audio. It uses three
instances of the **same installed LSP LV2 URI** EE 7.2.5 uses. Front L/R,
center/LFE, rear L/R are distinct pairs. The center instance's right-channel
filters stay off: LFE passes at unity, all five full-range channels receive the
identical EQ. No downmix, software surround renderer, new dependency, multiple
EE daemons or onboard EQ write is involved. Channel positions remain
FL/FR/FC/LFE/RL/RR. Output explicitly targets A50_Game_51 with no fallback;
this is an A50 route, never a new default. The existing remap's startup durability
and channel-order limitations remain as described in RESUME.md.

The exporter deliberately accepts only the inspected symmetric IIR/APO bell
shape with unity external gains, and rejects unsupported settings rather than
silently approximating them. EE enum values Bell=1, APO(DR)=6, x1=0 map to the
same LSP controls; band gains use 10**(dB/20), frequency/Q unchanged. Remaining
filters are off by the installed plugin's defaults. PipeWire's LV2 host uses
port **symbols**, verified in 1.4.7 source, so `ftl_0`, `gl_0`, etc. are valid.
A generic PipeWire biquad would require a separate response comparison; the
A50 onboard five-band EQ cannot express seven independently placed bells and
is not claimed equivalent.

Keep EE as the desktop stereo processor and preset editor. Save the liked EE
preset, export it, and route the surround game directly to A50_EQ_51. The game
must be excluded from EE processing through EE's application blocklist; otherwise
EE's process-all-outputs policy can capture it again. The new filter's playback
sets node.name and application.id to `A50-Loopback`, retaining
application.name. EE 7.2.5 checks its blocklist against either `application_id`
or node name in [stream_output_effects.cpp](https://github.com/wwmm/easyeffects/blob/v7.2.5/src/stream_output_effects.cpp);
[pipe_manager.cpp](https://github.com/wwmm/easyeffects/blob/v7.2.5/src/pipe_manager.cpp)
sets node name from `PW_KEY_NODE_NAME`.
There is no live synchronization: subsequent EE edits require saving/exporting
again and loading the new standalone filter client. This manual boundary keeps
the initial solution small. Desktop EE use remains available; this is not an EE
multichannel implementation or a finished one-click integration.

Private generated candidate:
`artifacts/surround-integration/eq-research/a50-eq-51.conf`.
Regenerate (repo output only):

```sh
python3 tools/a50_eq_config.py "$HOME/.config/easyeffects/output/A2+ Bright.json" > artifacts/surround-integration/eq-research/a50-eq-51.conf
/usr/bin/python3 tools/check_a50_eq.py "$HOME/.config/easyeffects/output/A2+ Bright.json"
pw-config -n "$PWD/artifacts/surround-integration/eq-research/a50-eq-51.conf" -r merge context.modules
```

## Verification and next approval gate

Offline check uses the installed LSP shared object directly through LV2's C ABI
and in-memory samples; no PipeWire connection or audio device. Six isolated
0.1-amplitude impulses, 65536 samples each at 48 kHz: five full-range impulse
responses agree within 1e-7, paired-channel leakage <1e-8, LFE matches the unity
impulse within 1e-7, EQ is active and finite, all exported controls exist and are
within installed TTL bounds. Generated config parses with installed pw-config.
The measured maximum frequency-response boost is about **10.36 dB**; full-scale
content needs headroom (e.g. 11 dB attenuation before EQ in an approved trial).
No attenuation was silently added to the preset export.

This proves mapping and native DSP behavior, **not an EE-versus-PipeWire captured
output null test**, game routing, headset sound, or Dolby transfer equivalence. Identical plugin/control
mapping strongly supports matching EQ transfer, but do not claim measured
end-to-end equivalence. Baseline/preset/loaded-settings/source snapshots and
results remain ignored under artifacts/surround-integration/eq-research/.

Silent runtime validation after `6281d1d` found that application.name alone
failed EE exclusion: capture appeared as `A50_EQ_51`; adding application.id
alone also failed. Setting playback node.name exactly to `A50-Loopback` and
application.id to the same value passed: six correct links reached
`A50_Game_51`. The stream was paused (not running) and silent; no audio played,
no EE settings or defaults changed. Candidate config:
`artifacts/surround-integration/eq-research/a50-eq-51-node-check.conf`. Current
A50_Game_51 default remains the user's setting. Next is ordinary real-game
acceptance when Ben chooses. Any service/Plasma restart is user-owned; agents
must not perform one.

## EQ after binaural rendering while keeping hardware Dolby

Hardware Dolby renders downstream of the USB Game endpoint, inside the A50.
There is no verified host-accessible post-render insertion point. EE on the PC
cannot EQ **after that hardware render**. The six-channel candidate EQs before
it and leaves hardware Dolby available. Applying identical linear EQ to every
source channel would commute mathematically with an ideal linear binaural
renderer; the real hardware's processing is unmeasured, LFE treatment differs,
and dynamic/nonlinear stages invalidate that shortcut as a proof.

A software binaural renderer could produce stereo first and feed EE afterwards,
but feeding that stereo into enabled hardware Dolby is a different, potentially
second spatial-processing stage; it does not retain the original six-channel
hardware rendering path. Onboard EQ might act after rendering, but its placement
is unverified and its five bands do not reproduce this preset. Neither is a
verified exact substitute for the pre-hardware six-channel EQ solution.

## Hardware and DSP boundary

The [official Gen 3 manual](https://cx-assets.logi.com/ASTRO/A50_ASTRO_PS4-Gen3.pdf)
documents USB PC Game and the Dolby button. Astro's [2016 release](https://www.impulsegamer.com/astro-gaming-releases-significantly-updated-a50-wireless-gaming-headset-featuring-new-base-station/)
describes Dolby Headphone 7.1. Observed `/proc/asound/card1/stream1` format is
S16_LE, six channels, 48 kHz (FL/FR/FC/LFE/RL/RR). Generic Dolby Headphone is a
multichannel-to-two-ear renderer, unlike Pro Logic II's two-channel matrix
decoder. Public sources do not establish exact Gen 3 DSP order, Pro Logic II in
stereo mode, or wireless codec. The [FCC filing](https://fccid.io/YQ6-TXDP01/Internal-Photos/Internal-photos-3083765)
marks the block diagram/operation description confidential; it does not establish
that processing must be inside the headset rather than the base.

## Primary software sources

- [EE 7.2.5 PipeManager: stereo virtual sink](https://github.com/wwmm/easyeffects/blob/v7.2.5/src/pipe_manager.cpp#L1615).
- [EE 7.2.5 PluginBase: main FL/FR ports](https://github.com/wwmm/easyeffects/blob/v7.2.5/src/plugin_base.cpp#L254).
- [EE 7.2.5 EQ constructor and processing](https://github.com/wwmm/easyeffects/blob/v7.2.5/src/equalizer.cpp), [band bindings](https://github.com/wwmm/easyeffects/blob/v7.2.5/include/equalizer.hpp#L70).
- [EE 7.2.5 Bass Loudness](https://github.com/wwmm/easyeffects/blob/v7.2.5/src/bass_loudness.cpp).
- [EE 8.3.0 stereo ports](https://github.com/wwmm/easyeffects/blob/v8.3.0/src/plugin_base.cpp#L365), [EQ](https://github.com/wwmm/easyeffects/blob/v8.3.0/src/equalizer.cpp).
- [Inspected upstream revision](https://github.com/wwmm/easyeffects/tree/5419e60b62681975c010d2602a76577e86761db1).
- [PipeWire 1.4.7 filter-chain graph and LV2 configuration](https://github.com/PipeWire/pipewire/blob/1.4.7/src/modules/module-filter-chain.c), [LV2 symbol naming](https://github.com/PipeWire/pipewire/blob/1.4.7/spa/plugins/filter-graph/lv2_plugin.c#L433), [standalone client base](https://github.com/PipeWire/pipewire/blob/1.4.7/src/daemon/filter-chain.conf.in).
- Installed metadata: `/usr/lib/lv2/lsp-plugins.lv2/para_equalizer_x32_lr.ttl`
and `/usr/share/glib-2.0/schemas/com.github.wwmm.easyeffects.equalizer*.gschema.xml`.
