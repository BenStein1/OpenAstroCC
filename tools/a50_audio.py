#!/usr/bin/env python3
"""Read-only A50 PipeWire route plan. Never switches profiles or emits sound."""
import json
import subprocess
from pathlib import Path
import a50


def plan(cards, sinks, sources):
    def target(card):
        props = card.get('properties', {})
        try:
            return (int(props.get('device.vendor.id', '0'), 0),
                    int(props.get('device.product.id', '0'), 0)) == (a50.VID, a50.PID)
        except (TypeError, ValueError):
            return False
    matches = [card for card in cards if target(card)]
    if len(matches) != 1:
        raise ValueError('expected one PipeWire USB9886:0015 card, found %d' % len(matches))
    card = matches[0]
    profile = card.get('profiles', {}).get('pro-audio')
    if not profile or not profile.get('available') or (profile.get('sinks'), profile.get('sources')) != (2, 2):
        raise ValueError('A50 pro-audio profile does not advertise the expected two sinks/two sources')
    def routes(nodes):
        return [{'name': node['name'], 'channels': node.get('channel_map'),
                 'virtual': node.get('properties', {}).get('node.virtual') == 'true',
                 'alsa_device': node.get('properties', {}).get('alsa.device')}
                for node in nodes if target(node) and
                node.get('properties', {}).get('device.name') == card['name']]
    return {'card': card['name'], 'current_profile': card['active_profile'],
            'prepared_profile': 'pro-audio', 'advertised_sinks': 2, 'advertised_sources': 2,
            'active_sinks': routes(sinks), 'active_sources': routes(sources),
            'topology': {'Game': '6ch 48k playback; stereo line capture',
                         'Voice': 'stereo 48k playback; mono 16k microphone'},
            'approval': 'Profile switching and sounds await Ben’s explicit answer.',
            'switch_argv_after_approval': ['pactl', 'set-card-profile', card['name'], 'pro-audio'],
            'restore_argv_after_approval': ['pactl', 'set-card-profile', card['name'], card['active_profile']],
            'verification': 'Route names/channel maps after switching and physical listening remain unverified.'}


def inventory():
    values = []
    for kind in ('cards', 'sinks', 'sources'):
        reply = subprocess.run(['pactl', '--format=json', 'list', kind], check=True,
                               capture_output=True, text=True, timeout=5)
        values.append(json.loads(reply.stdout))
    return plan(*values)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-o', '--output', help='create a new JSON plan file')
    args = parser.parse_args()
    result = inventory()
    if args.output:
        a50.save_json(args.output, result)
    print(json.dumps(result, indent=2))
