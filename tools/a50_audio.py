#!/usr/bin/env python3
"""Read-only A50 PipeWire route plan. Never switches profiles or emits sound."""
import json
import re
import subprocess
import sys
from pathlib import Path
import a50

# Expected channel maps (pactl's Pulse-style names) for the module-remap-sink/
# source nodes installed by config/15-astro-a50-remap.conf (or
# artifacts/surround-integration/apply-live.sh), which relabel the A50's raw
# AUXn channels into positions games/apps recognise.
REMAP_EXPECTED = {
    'A50_Game_51': 'front-left,front-right,front-center,lfe,rear-left,rear-right',
    'A50_Voice': 'front-left,front-right',
    'A50_Mic': 'mono',
}


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
            'approval': "Ben approved and physically verified pro-audio playback/balance/Dolby "
                        "(see docs/HARDWARE-TESTS.md); the raw aux0..auxN channel map is not "
                        "surround-recognisable by apps, fixed by the A50_Game_51/A50_Voice/A50_Mic "
                        "remap nodes below (config/15-astro-a50-remap.conf).",
            'switch_argv_after_approval': ['pactl', 'set-card-profile', card['name'], 'pro-audio'],
            'restore_argv_after_approval': ['pactl', 'set-card-profile', card['name'], card['active_profile']],
            'verification': 'Raw route channel maps and physical Game/Voice/Dolby listening are verified; '
                             'see remap_status for the app-facing 5.1/mono channel maps.'}


def remap_status(sinks, sources):
    """Check the module-remap-sink/source nodes that relabel the A50's raw
    AUXn channels (see REMAP_EXPECTED). Missing nodes are reported, not raised,
    since they're an optional live/persisted layer on top of the base profile."""
    by_name = {node['name']: node for node in list(sinks) + list(sources)}
    result = {}
    for name, expected_map in REMAP_EXPECTED.items():
        node = by_name.get(name)
        if node is None:
            result[name] = {'present': False}
            continue
        actual_map = node.get('channel_map')
        result[name] = {'present': True, 'channel_map': actual_map,
                         'matches_expected': actual_map == expected_map}
    result['ok'] = all(v.get('present') and v.get('matches_expected') for v in result.values()
                        if isinstance(v, dict))
    return result


def _parse_uac_direction(text, direction):
    match = re.search(direction + r':\n(.*?)(?=\n(?:Playback|Capture):|\Z)', text, re.S)
    body = match.group(1) if match else ''
    channels = re.search(r'Channels:\s*(\d+)', body)
    if not channels:
        return None
    rate = re.search(r'Rates:\s*(\d+)', body)
    channel_map = re.search(r'Channel map:\s*(.+)', body)
    return {'channels': int(channels.group(1)),
            'rate': int(rate.group(1)) if rate else None,
            'channel_map': channel_map.group(1).strip() if channel_map else None}


def uac_ground_truth():
    """Kernel-level USB Audio Class descriptors for the A50's PCM interfaces,
    independent of whichever PipeWire ALSA-card-profile is currently active.
    This is what actually proves per-interface channel counts, not a profile guess."""
    try:
        card_dirs = sorted(Path('/proc/asound').glob('card*'))
    except OSError as exc:
        return {'error': str(exc)}
    for card_dir in card_dirs:
        if a50.read_first(str(card_dir / 'usbid')).lower() != '%04x:%04x' % (a50.VID, a50.PID):
            continue
        streams = []
        for stream_path in sorted(card_dir.glob('stream*'), key=lambda p: p.name):
            text = a50.read_first(str(stream_path))
            streams.append({'device': stream_path.name,
                             'playback': _parse_uac_direction(text, 'Playback'),
                             'capture': _parse_uac_direction(text, 'Capture')})
        return {'alsa_card': card_dir.name, 'streams': streams}
    return None


def trace_virtual_routes(sinks):
    """Live pw-link port trace: shows which physical sink each virtual A50_*
    sink's output actually reaches right now. A virtual sink's name/label is not
    evidence of independent routing -- two differently-named virtual sinks can
    still collapse onto the same physical USB endpoint, which is exactly what
    this host's pre-existing A50_Game/A50_Voice loopbacks do today."""
    try:
        reply = subprocess.run(['pw-link', '-l'], check=True, capture_output=True,
                               text=True, timeout=5)
    except (OSError, subprocess.SubprocessError) as exc:
        return {'error': str(exc)}
    targets, current = {}, None
    for line in reply.stdout.splitlines():
        if line.startswith('  '):
            match = re.match(r'\s*\|->\s*([^:]+):', line)
            if match and current:
                targets.setdefault(current, set()).add(match.group(1))
        elif line.strip():
            current = line.split(':', 1)[0]
    destinations = {}
    for sink in sinks:
        group = sink.get('properties', {}).get('node.group', '')
        if not group:
            continue
        destinations[sink['name']] = sorted(targets.get('output.' + group, []))
    linked = {name: dests for name, dests in destinations.items() if dests}
    shared = {}
    for name, dests in linked.items():
        for dest in dests:
            shared.setdefault(dest, []).append(name)
    collisions = {dest: names for dest, names in shared.items() if len(names) > 1}
    # independent is only meaningful once >=2 virtual sinks are actually live and
    # linked right now; otherwise absence of a collision proves nothing (e.g. both
    # loopbacks idle/unlinked would also show no collision). Labels/counts alone
    # are not listening proof, and neither is an unlinked snapshot.
    independent = (not collisions) if len(linked) >= 2 else None
    return {'virtual_sink_destinations': destinations,
            'independent': independent,
            'collisions': collisions}


def inventory():
    values = []
    for kind in ('cards', 'sinks', 'sources'):
        reply = subprocess.run(['pactl', '--format=json', 'list', kind], check=True,
                               capture_output=True, text=True, timeout=5)
        values.append(json.loads(reply.stdout))
    result = plan(*values)
    try:
        result['uac_ground_truth'] = uac_ground_truth()
    except OSError as exc:
        result['uac_ground_truth'] = {'error': str(exc)}
    try:
        result['virtual_routing'] = trace_virtual_routes(values[1])
    except OSError as exc:
        result['virtual_routing'] = {'error': str(exc)}
    result['remap_status'] = remap_status(values[1], values[2])
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('-o', '--output', help='create a new JSON plan file')
    parser.add_argument('--verify', action='store_true',
                         help='exit 1 if the A50_Game_51/A50_Voice/A50_Mic remap nodes are '
                              'missing or have an unexpected channel map')
    args = parser.parse_args()
    result = inventory()
    if args.output:
        a50.save_json(args.output, result)
    print(json.dumps(result, indent=2))
    if args.verify and not result['remap_status']['ok']:
        sys.exit(1)
