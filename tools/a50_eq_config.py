#!/usr/bin/env python3
"""Export the supported EasyEffects EQ to an A50-only six-channel filter config.

Writes JSON to stdout; never connects to PipeWire or changes the host.
"""
import argparse
import json
import math
from pathlib import Path

URI = 'http://lsp-plug.in/plugins/lv2/para_equalizer_x32_lr'
CHANNELS = ['FL', 'FR', 'FC', 'LFE', 'RL', 'RR']


def controls(preset, lfe=False):
    """Deliberately support only the inspected symmetric IIR bell preset shape."""
    output = preset['output']
    eq = output['equalizer#0']
    if output['plugins_order'] != ['bass_loudness#0', 'equalizer#0'] or not output['bass_loudness#0']['bypass']:
        raise ValueError('Only bypassed Bass Loudness followed by EQ is supported')
    if (eq['bypass'] or eq['split-channels'] or eq['left'] != eq['right'] or
            eq['mode'] != 'IIR' or any(eq[k] != 0 for k in
            ['balance', 'input-gain', 'output-gain', 'pitch-left', 'pitch-right'])):
        raise ValueError('Requires active symmetric IIR EQ with unity gain and no pitch shift')
    count = eq['num-bands']
    if not isinstance(count, int) or not 1 <= count <= 32:
        raise ValueError('Invalid band count')
    result = {'mode': 0, 'g_in': 1, 'g_out': 1, 'bal': 0}
    for side in ['l', 'r']:
        for i in range(count):
            b = eq['left'][f'band{i}']
            if (b['type'], b['mode'], b['slope'], b['mute'], b['solo'], b['width']) != (
                    'Bell', 'APO (DR)', 'x1', False, False, 4.0):
                raise ValueError('Only unsoloed/unmuted APO (DR), x1 bells with width 4 are supported')
            if not all(isinstance(b[k], (int, float)) and math.isfinite(b[k]) for k in ['frequency', 'gain', 'q']):
                raise ValueError('Non-finite band parameter')
            if not (10 <= b['frequency'] <= 24000 and -36 <= b['gain'] <= 36 and 0 < b['q'] <= 100):
                raise ValueError('Band parameter outside installed plugin bounds')
            result.update({f'ft{side}_{i}': 0 if lfe and side == 'r' else 1,
                           f'fm{side}_{i}': 6, f'f{side}_{i}': b['frequency'],
                           f'g{side}_{i}': 10 ** (b['gain'] / 20), f'q{side}_{i}': b['q']})
    return result


def make_config(preset):
    nodes = [dict(type='lv2', name=name, plugin=URI, control=controls(preset, name == 'center_lfe'))
             for name in ['front', 'center_lfe', 'rear']]
    ports = lambda direction: [f'{n["name"]}:{direction}_{side}' for n in nodes for side in ['l', 'r']]
    return {'context.spa-libs': {'audio.convert.*': 'audioconvert/libspa-audioconvert',
                                 'support.*': 'support/libspa-support'},
            'context.modules': [{'name': 'libpipewire-module-' + name} for name in
                                ['protocol-native', 'client-node', 'adapter']] +
            [{'name': 'libpipewire-module-filter-chain', 'args': {
        'node.description': 'A50 5.1 Bright EQ (candidate)', 'audio.rate': 48000,
        'audio.channels': 6, 'audio.position': CHANNELS,
        'filter.graph': {'nodes': nodes, 'inputs': ports('in'), 'outputs': ports('out')},
        'capture.props': {'node.name': 'A50_EQ_51', 'media.class': 'Audio/Sink',
                          'audio.position': CHANNELS, 'priority.session': 0, 'node.autoconnect': False},
        'playback.props': {'node.name': 'A50-Loopback', 'application.name': 'A50-Loopback',
                           'application.id': 'A50-Loopback',
                           'audio.position': CHANNELS,
                           'target.object': 'A50_Game_51', 'node.passive': True,
                           'node.dont-fallback': True, 'stream.dont-remix': True}
    }}]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preset', type=Path)
    args = parser.parse_args()
    print(json.dumps(make_config(json.loads(args.preset.read_text())), indent=2, allow_nan=False))
