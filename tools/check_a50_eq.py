#!/usr/bin/env python3
"""Offline impulse/channel check using the installed LSP LV2 binary; no audio server.

Usage: /usr/bin/python3 tools/check_a50_eq.py 'path/to/A2+ Bright.json'
Requires the already installed numpy and LSP LV2 packages. No playback occurs.
"""
import ctypes as C
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import numpy as np
from a50_eq_config import CHANNELS, URI, make_config

BUNDLE = Path('/usr/lib/lv2/lsp-plugins.lv2')


def ports():
    # Narrow parser for the installed LSP-generated TTL port declarations.
    result = []
    for block in (BUNDLE / 'para_equalizer_x32_lr.ttl').read_text().split('\n\t] , [\n'):
        match = re.search(r'lv2:index (\d+) ;\s*lv2:symbol "([^"]+)"', block)
        if match:
            default = re.search(r'lv2:default ([-\d.]+)', block)
            result.append((int(match[1]), match[2], block, float(default[1]) if default else 0))
    assert len(result) > 600 and len({p[0] for p in result}) == len(result)
    return result


def impulse(control, active):
    """Host the same two-channel plugin EE uses, entirely in memory."""
    class Descriptor(C.Structure):
        _fields_ = [('uri', C.c_char_p)] + [(n, C.c_void_p) for n in
            ['instantiate', 'connect', 'activate', 'run', 'deactivate', 'cleanup', 'extension']]

    class Feature(C.Structure):
        _fields_ = [('uri', C.c_char_p), ('data', C.c_void_p)]

    MapFunc = C.CFUNCTYPE(C.c_uint32, C.c_void_p, C.c_char_p)
    class Map(C.Structure):
        _fields_ = [('handle', C.c_void_p), ('map', MapFunc)]

    ids = {}
    def map_uri(handle, uri):
        return ids.setdefault(uri, len(ids) + 1)
    callback = MapFunc(map_uri)
    mapper = Map(None, callback)
    feature = Feature(b'http://lv2plug.in/ns/ext/urid#map', C.cast(C.pointer(mapper), C.c_void_p))
    features = (C.POINTER(Feature) * 2)(C.pointer(feature), None)
    library = C.CDLL(str(BUNDLE / 'lsp-plugins-lv2.so'))
    library.lv2_descriptor.restype = C.POINTER(Descriptor)
    index = 0
    while True:
        ptr = library.lv2_descriptor(index)
        assert ptr, 'Installed plugin URI missing'
        if ptr.contents.uri.decode() == URI:
            break
        index += 1
    d = ptr.contents
    create = C.CFUNCTYPE(C.c_void_p, C.c_void_p, C.c_double, C.c_char_p, C.c_void_p)(d.instantiate)
    handle = create(ptr, 48000, str(BUNDLE).encode() + b'/', features)
    assert handle, 'LV2 instantiate failed'
    connect = C.CFUNCTYPE(None, C.c_void_p, C.c_uint32, C.c_void_p)(d.connect)
    run = C.CFUNCTYPE(None, C.c_void_p, C.c_uint32)(d.run)
    buffers = {}
    metadata = ports()
    for i, symbol, block, default in metadata:
        if 'lv2:AudioPort' in block:
            value = np.zeros(256, dtype=np.float32)
            address = value.ctypes.data
        elif 'lv2:ControlPort' in block:
            value = C.c_float(control.get(symbol, default))
            address = C.addressof(value)
        else:
            value = C.create_string_buffer(65536)
            address = C.addressof(value)
        buffers[symbol] = value
        connect(handle, i, address)
    assert set(control) <= set(buffers), 'Unknown LV2 control symbol'
    for i, symbol, block, default in metadata:
        if symbol in control:
            low = re.search(r'lv2:minimum ([-\d.]+)', block)
            high = re.search(r'lv2:maximum ([-\d.]+)', block)
            assert low and high and float(low[1]) <= control[symbol] <= float(high[1]), symbol
    if d.activate:
        C.CFUNCTYPE(None, C.c_void_p)(d.activate)(handle)
    outputs = []
    for step in range(16 + 256):
        for symbol in ['in_l', 'in_r']:
            buffers[symbol].fill(0)
        if step == 16:
            buffers[['in_l', 'in_r'][active]][0] = 0.1
        for i, symbol, block, default in metadata:
            if 'atom:AtomPort' in block:
                header = (C.c_uint32 * 4).from_buffer(buffers[symbol])
                header[0] = 8 if 'lv2:InputPort' in block else 65528
                header[1] = map_uri(None, b'http://lv2plug.in/ns/ext/atom#Sequence')
                header[2] = header[3] = 0
        run(handle, 256)
        if step >= 16:
            outputs.append(np.stack([buffers['out_l'].copy(), buffers['out_r'].copy()]))
    if d.deactivate:
        C.CFUNCTYPE(None, C.c_void_p)(d.deactivate)(handle)
    C.CFUNCTYPE(None, C.c_void_p)(d.cleanup)(handle)
    return np.concatenate(outputs, axis=1)


def main():
    preset = json.loads(Path(sys.argv[1]).read_text())
    for field, value in [('mode', 'FIR'), ('input-gain', -3), ('split-channels', True)]:
        unsupported = deepcopy(preset)
        unsupported['output']['equalizer#0'][field] = value
        try:
            make_config(unsupported)
        except ValueError:
            pass
        else:
            raise AssertionError('Unsupported preset accepted: ' + field)
    unsupported = deepcopy(preset)
    unsupported['output']['bass_loudness#0']['bypass'] = False
    try:
        make_config(unsupported)
    except ValueError:
        pass
    else:
        raise AssertionError('Enabled Bass Loudness silently discarded')
    args = make_config(preset)['context.modules'][-1]['args']
    graph = args['filter.graph']
    assert args['audio.position'] == CHANNELS
    assert graph['inputs'] == ['front:in_l', 'front:in_r', 'center_lfe:in_l', 'center_lfe:in_r', 'rear:in_l', 'rear:in_r']
    assert graph['outputs'] == [p.replace(':in_', ':out_') for p in graph['inputs']]
    responses = []
    for channel in range(6):
        response = impulse(graph['nodes'][channel // 2]['control'], channel % 2)
        assert np.max(np.abs(response[1 - channel % 2])) < 1e-8, 'Channel leakage'
        assert np.isfinite(response).all()
        responses.append(response[channel % 2])
    for channel in [1, 2, 4, 5]:
        assert np.max(np.abs(responses[0] - responses[channel])) < 1e-7, 'Unequal full-range EQ'
    unity = np.zeros_like(responses[3]); unity[0] = 0.1
    assert np.max(np.abs(responses[3] - unity)) < 1e-7, 'LFE changed'
    spectrum = 20 * np.log10(np.maximum(np.abs(np.fft.rfft(responses[0])) / 0.1, 1e-12))
    assert np.max(np.abs(responses[0] - unity)) > 0.01, 'EQ inactive'
    print(json.dumps({'result': 'PASS', 'rate': 48000, 'samples': len(unity),
                      'full_range_equal': ['FL', 'FR', 'FC', 'RL', 'RR'], 'LFE': 'unity',
                      'cross_channel_leakage': '<1e-8', 'peak_boost_db': float(spectrum.max()),
                      'scope': 'installed LV2 DSP + config mapping; no live PipeWire graph or hardware'}, indent=2))


if __name__ == '__main__':
    main()
