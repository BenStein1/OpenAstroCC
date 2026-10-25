#!/usr/bin/env python3
"""Offline checks, or --live reversible A50 validation with a saved baseline."""
import argparse
import copy
import json
from pathlib import Path
from unittest.mock import patch
import a50


def offline():
    client = a50.A50Client('/mock')
    client.fd = 99
    sent = []
    def exchange(opcode, payload=b'', echo=b'', minimum=0):
        sent.append((opcode, payload))
        if opcode == 0x70:
            return bytes([0x70, 1, 2]) + bytes.fromhex('0010191a90019a01')
        return b''
    with patch.object(client, '_exchange', side_effect=exchange), patch.object(
            client, 'gains', return_value={'working': [-12, -1, 0, 1, 12]}):
        client.set_gains(1, [-12, -1, 0, 1, 12])
        assert sent[-1] == (0x63, bytes([1, 0, 11, 12, 13, 24]))
        assert client.coefficients(1, 2) == {
            'working': {'frequency': 400, 'bandwidth_raw': 4096},
            'stored': {'frequency': 410, 'bandwidth_raw': 6681}}
    sent.clear()
    with patch.object(client, '_exchange', side_effect=exchange):
        for action in [lambda: client.gains(0), lambda: client.coefficients(1, 6),
                       lambda: client.set_gains(1, [13]*5),
                       lambda: client.set_coefficients(1, 2, 79, 4096),
                       lambda: client.set_coefficients(1, 1, 80, 4096),
                       lambda: client.set_setting('alert_volume', 101),
                       lambda: client.set_setting('brightness_channels', [0]*9)]:
            try:
                action()
            except ValueError:
                pass
            else:
                raise AssertionError('invalid operation accepted')
        assert not sent, 'invalid values must fail before transport'
    sent.clear()
    with patch.object(client, '_exchange', side_effect=exchange), patch.object(
            client, 'slider', return_value={'working':37}), patch.object(
            client, 'microphone', return_value={'eq':2, 'noise_gate':{
                'working':a50.NOISE_GATE_PACKETS[1].hex()}}):
        for name, selector in a50.SLIDERS.items():
            client.set_slider(name, 37)
            assert sent[-1] == (0x62, bytes([selector, 37]))
        client.set_mic_eq(2)
        assert sent[-1] == (0x71, bytes([2]))
        client.set_noise_gate(1)
        assert sent[-1] == (0x64, bytes.fromhex('3201e4089007c60067008000'))
        for action in (lambda:client.set_slider('sidetone',101),
                       lambda:client.set_slider('unknown',10), lambda:client.set_mic_eq(3),
                       lambda:client.set_noise_gate(-1)):
            before = len(sent)
            try: action()
            except ValueError: pass
            else: raise AssertionError('unbounded microphone operation accepted')
            assert before == len(sent)
    print('settings offline checks OK')



def backup_checks():
    import tempfile
    root = Path(__file__).resolve().parent.parent
    # Historical corruption is test input only, never a hardware restore target.
    document = json.loads((root / 'evidence/a50-baseline.json').read_text())
    document['slots'][0]['gains']['working'] = document['slots'][0]['gains']['stored'].copy()
    a50.validate_backup(document)
    for mutate in [lambda d: d.update(pid=0x1c), lambda d: d.update(schema='wrong'),
                   lambda d: d['slots'].pop(),
                   lambda d: d['slots'][0]['gains'].update(working=[False]*5),
                   lambda d: d['slots'][0]['bands'][1]['stored'].update(frequency=15001),
                   lambda d: d['settings'].update(brightness_channels=[70]*8),
                   lambda d: d['settings'].update(alert_volume=101)]:
        bad = copy.deepcopy(document)
        mutate(bad)
        try:
            a50.validate_backup(bad)
        except (ValueError, TypeError, KeyError):
            pass
        else:
            raise AssertionError('malformed backup accepted')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'slot.astroeq'
        a50.export_preset(document, 1, path)
        imported = a50.import_preset(document, 1, path)
        assert imported == document, 'preset import must preserve exact raw bandwidth'
        class Fake:
            def __init__(self):
                self.document = copy.deepcopy(document)
                self.writes = []
            def snapshot(self): return copy.deepcopy(self.document)
            def set_gains(self, slot, gains):
                self.writes.append(('gains',slot))
                self.document['slots'][slot-1]['gains']['working'] = gains.copy()
            def set_coefficients(self, slot, band, **values):
                self.writes.append(('coefficients',slot,band))
                self.document['slots'][slot-1]['bands'][band-1]['working'] = values
            def set_setting(self, name, value):
                self.writes.append(('settings',name))
                self.document['settings'][name] = copy.deepcopy(value)
        fake = Fake()
        assert a50.restore_working(fake, document) == document
        assert not fake.writes, 'identical restore must send no setters'
        target = copy.deepcopy(document)
        target['slots'][1]['gains']['working'][0] += 1
        target['slots'][2]['bands'][2]['working']['frequency'] += 1
        target['settings']['alert_volume'] -= 1
        assert a50.restore_working(fake, target) == target
        assert len(fake.writes) == 3
        assert a50.restore_working(fake, document) == document
        # Reject stale/wrong identity before any snapshot or write.
        with patch.object(fake, 'snapshot', side_effect=AssertionError('invalid import touched device')):
            try: a50.restore_working(fake, {'schema':'wrong'})
            except ValueError: pass
            else: raise AssertionError('invalid import accepted')
    # Brightness-only status0 is allowed; all other operations still require2.
    zero = a50.frame(0, b'', 0)
    client = a50.A50Client('/mock'); client.fd = 99
    with patch.object(a50.os, 'write', return_value=64), patch.object(a50, '_read_reply', return_value=zero):
        assert client._exchange(0x75, bytes([70]*9)) == b''
        try: client._exchange(0x77)
        except a50.EqReadError: pass
        else: raise AssertionError('status0 accepted for GET')
    print('backup validation, exact preset round trip, selective restore and ACK checks OK')
    import a50_audio
    props = {'device.vendor.id':'0x9886', 'device.product.id':'0x0015', 'device.name':'a50-card'}
    card = {'name':'a50-card', 'index':7, 'properties': props, 'active_profile':'original',
            'profiles':{'pro-audio':{'available':True, 'sinks':2, 'sources':2}}}
    node = {'name':'existing-route', 'properties':props, 'channel_map':'front-left,front-right'}
    prepared = a50_audio.plan([card], [node], [])
    assert prepared['active_sinks'][0]['name'] == 'existing-route'
    assert prepared['restore_argv_after_approval'][-1] == 'original'
    with patch.object(a50_audio.subprocess, 'run') as run:
        run.return_value.stdout = '[]'
        try: a50_audio.inventory()
        except ValueError: pass
        assert all(call.args[0][2] == 'list' for call in run.call_args_list)
    # UAC descriptor parser against real /proc/asound/cardN/streamM text shape.
    sample = ('Interface 2\n  Altset 1\n  Format: S16_LE\nPlayback:\n  Status: Running\n'
              '    Channels: 2\n    Rates: 48000\n    Channel map: FL FR\n'
              'Capture:\n  Status: Stop\n    Channels: 1\n    Rates: 16000\n'
              '    Channel map: MONO\n')
    parsed_pb = a50_audio._parse_uac_direction(sample, 'Playback')
    parsed_cap = a50_audio._parse_uac_direction(sample, 'Capture')
    assert parsed_pb == {'channels': 2, 'rate': 48000, 'channel_map': 'FL FR'}
    assert parsed_cap == {'channels': 1, 'rate': 16000, 'channel_map': 'MONO'}
    assert a50_audio._parse_uac_direction('Capture:\n  Status: Stop\n', 'Playback') is None
    # Live-link independence trace: two virtual sinks sharing node.group must be
    # flagged as colliding on the same physical destination, not "independent".
    fake_links = (
        'alsa_output.x:playback_FL\n'
        '  |<- output./usr/bin/pw-loopback-1:output_FL\n'
        '  |<- output./usr/bin/pw-loopback-2:output_FL\n'
        'output./usr/bin/pw-loopback-1:output_FL\n'
        '  |-> alsa_output.x:playback_FL\n'
        'output./usr/bin/pw-loopback-2:output_FL\n'
        '  |-> alsa_output.x:playback_FL\n')
    with patch.object(a50_audio.subprocess, 'run') as run:
        run.return_value.stdout = fake_links
        trace = a50_audio.trace_virtual_routes([
            {'name': 'A50_Game', 'properties': {'node.group': '/usr/bin/pw-loopback-1'}},
            {'name': 'A50_Voice', 'properties': {'node.group': '/usr/bin/pw-loopback-2'}}])
        assert trace['independent'] is False
        assert sorted(trace['collisions']['alsa_output.x']) == ['A50_Game', 'A50_Voice']
        # No sink currently linked anywhere: absence of a collision proves nothing,
        # so independence must read as unknown, not True.
        run.return_value.stdout = ''
        idle = a50_audio.trace_virtual_routes([
            {'name': 'A50_Game', 'properties': {'node.group': '/usr/bin/pw-loopback-1'}},
            {'name': 'A50_Voice', 'properties': {'node.group': '/usr/bin/pw-loopback-2'}}])
        assert idle['independent'] is None
        run.side_effect = OSError('no pw-link')
        assert 'error' in a50_audio.trace_virtual_routes([])
    print('audio plan identity/route matching and read-only subprocess checks OK')
    print('UAC descriptor parse and virtual-route independence trace checks OK')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', metavar='NEW_BASELINE_FILE')
    args = parser.parse_args()
    offline()
    backup_checks()
    if args.live:
        from check_live import run
        run(args.live)
