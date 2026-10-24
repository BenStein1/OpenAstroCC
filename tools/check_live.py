#!/usr/bin/env python3
"""Reversible, statically evidenced controls only; never sync or play audio."""
import copy
import json
from pathlib import Path
import a50


def run(directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    with a50.A50Client() as client:
        before = client.snapshot()
        a50.save_json(directory / 'before.json', before)
        completed = []
        try:
            for slot in before['slots']:
                number = slot['slot']
                gains = slot['gains']['working'].copy()
                gains[0] += 1 if gains[0] < 12 else -1
                client.set_gains(number, gains)
                client.set_gains(number, slot['gains']['working'])
                completed.append('slot %d gains' % number)
                for band, banks in enumerate(slot['bands'], 1):
                    old = banks['working']
                    frequency = old['frequency'] + (1 if old['frequency'] < 15000 else -1)
                    client.set_coefficients(number, band, frequency, old['bandwidth_raw'])
                    client.set_coefficients(number, band, **old)
                    completed.append('slot %d band %d frequency' % (number, band))
                    if band in (2, 3, 4):
                        width = old['bandwidth_raw'] + (1 if old['bandwidth_raw'] < 12288 else -1)
                        client.set_coefficients(number, band, old['frequency'], width)
                        client.set_coefficients(number, band, **old)
                        completed.append('slot %d band %d bandwidth' % (number, band))
            for name, old in before['settings'].items():
                if isinstance(old, list):
                    value = [v + (1 if v < 70 else -1) for v in old]
                else:
                    maximum = 255 if name == 'default_balance' else 100
                    value = old + (1 if old < maximum else -1)
                client.set_setting(name, value)
                client.set_setting(name, old)
                completed.append(name)
        finally:
            try:
                restored = a50.restore_working(client, before)
                a50.save_json(directory / 'after.json', restored)
                assert before['slots'] == restored['slots'], 'EQ restoration differs'
                assert before['settings'] == restored['settings'], 'mediator restoration differs'
            finally:
                a50.save_json(directory / 'capture.json', client.capture)
                a50.save_json(directory / 'completed.json', completed)
        print('PASS: %d reversible controls; all banks/settings restored; no sync.' % len(completed))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('new_evidence_directory')
    run(parser.parse_args().new_evidence_directory)
