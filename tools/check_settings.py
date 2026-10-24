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
    print('settings offline checks OK')


def live(output):
    # No sync/persistence command. Only working EQ and mediator controls change.
    with a50.A50Client() as client:
        baseline = client.snapshot()
        with open(output, 'x') as fh:
            json.dump(baseline, fh, indent=2)
        slot = baseline['slots'][1]
        gains = slot['gains']['working']
        band = slot['bands'][1]['working']
        settings = baseline['settings']
        try:
            changed = gains.copy()
            changed[0] += 1 if changed[0] < 12 else -1
            client.set_gains(2, changed)
            client.set_coefficients(2, 2, band['frequency'] + (1 if band['frequency'] < 15000 else -1), band['bandwidth_raw'])
            client.set_setting('default_balance', settings['default_balance'] + (1 if settings['default_balance'] < 255 else -1))
            client.set_setting('alert_volume', settings['alert_volume'] + (1 if settings['alert_volume'] < 100 else -1))
            client.set_setting('brightness_channels', [v + (1 if v < 70 else -1) for v in settings['brightness_channels']])
        finally:
            # Attempt every restoration even when one transport operation fails.
            errors = []
            for restore in [lambda: client.set_gains(2, gains),
                            lambda: client.set_coefficients(2, 2, band['frequency'], band['bandwidth_raw']),
                            *(lambda k=k: client.set_setting(k, settings[k]) for k in settings)]:
                try:
                    restore()
                except Exception as exc:
                    errors.append(str(exc))
            with open(str(output)+'.capture.json', 'x') as fh:
                json.dump(client.capture, fh, indent=2)
            if errors:
                raise a50.EqReadError('RESTORATION FAILED; baseline at %s: %s' % (output, errors))
        after = client.snapshot()
        assert baseline['slots'] == after['slots'], 'EQ banks changed after restoration'
        assert settings == after['settings'], 'settings changed after restoration'
        Path(str(output)+'.restored.json').write_text(json.dumps(after, indent=2)+'\n')
        print('live gain, frequency, balance, alert and brightness round trips OK; original settings restored')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', metavar='NEW_BASELINE_FILE')
    args = parser.parse_args()
    offline()
    if args.live:
        live(args.live)
