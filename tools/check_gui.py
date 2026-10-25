#!/usr/bin/python3
"""GUI workflow check; --live changes one gain via buttons and restores it."""
import argparse
import copy
import json
import time
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
import a50
from a50_gui import Window


def settle(window):
    deadline = time.monotonic() + 12
    # Process initial singleShot and queued cross-thread signals.
    QTest.qWait(20)
    while window.busy and time.monotonic() < deadline:
        QTest.qWait(10)
    assert not window.busy, 'GUI worker did not finish within bound'
    QTest.qWait(20)


def run(live):
    app = QApplication([])
    root = Path(__file__).resolve().parent.parent
    baseline_path = root / 'evidence/a50-baseline.json'
    window = Window(None if live else str(baseline_path))
    window.show()
    settle(window)
    assert window.document, window.status_label.text()
    window.timer.stop()
    before = copy.deepcopy(window.document)
    assert window.draft()['slots'] == before['slots']
    if not live:
        assert not window.buttons['Write working settings'].isEnabled()
        window.eq[1][0][0].setValue(before['slots'][1]['gains']['working'][0] + 1)
        assert window.draft()['slots'] != before['slots']
        window.close()
        print('PASS: offline GUI exact values, editing, hardware writes disabled')
        return
    try:
        widget = window.eq[1][0][0]
        old = widget.value()
        widget.setValue(old + (1 if old < 12 else -1))
        wanted = widget.value()
        window.buttons['Write working settings'].click()
        settle(window)
        assert window.connected, window.status_label.text()
        assert window.document['slots'][1]['gains']['working'][0] == wanted
        with a50.A50Client() as client:
            assert client.gains(2)['working'][0] == wanted
        widget.setValue(old)
        window.buttons['Write working settings'].click()
        settle(window)
        assert window.document['slots'] == before['slots']
        assert window.document['settings'] == before['settings']

        assert window.document['schema'] == 'astro-a50-gen3-v2', 'live device must expose mic/stream controls'
        slider = window.sliders['sidetone']
        old_level = slider.value()
        slider.setValue(old_level + (1 if old_level < 100 else -1))
        wanted_level = slider.value()
        old_gate_index = window.noise_gate.currentIndex()
        window.noise_gate.setCurrentIndex((old_gate_index + 1) % window.noise_gate.count())
        wanted_gate = window.noise_gate.currentIndex()
        window.buttons['Write working settings'].click()
        settle(window)
        assert window.connected, window.status_label.text()
        assert window.document['sliders']['sidetone']['working'] == wanted_level
        assert window.document['microphone']['noise_gate']['working'] == a50.NOISE_GATE_PACKETS[wanted_gate].hex()
        with a50.A50Client() as client:
            assert client.slider('sidetone')['working'] == wanted_level
            assert client.microphone()['noise_gate']['working'] == a50.NOISE_GATE_PACKETS[wanted_gate].hex()
        slider.setValue(old_level)
        window.noise_gate.setCurrentIndex(old_gate_index)
        window.buttons['Write working settings'].click()
        settle(window)
        assert window.document['sliders'] == before['sliders']
        assert window.document['microphone'] == before['microphone']
        print('PASS: live GUI mic/stream slider and noise-gate button write/readback/restore')
        # Exercise disconnect handling in the real GUI; physical USB stays attached.
        with patch.object(a50.A50Client, '__enter__', side_effect=OSError('synthetic disconnect')):
            window.poll()
            settle(window)
            assert not window.connected
            assert not window.buttons['Write working settings'].isEnabled()
        window.poll()
        settle(window)
        assert window.connected, window.status_label.text()
        assert window.buttons['Write working settings'].isEnabled()
        assert window.document['slots'] == before['slots']
        window.grab().save('/tmp/a50-ui-workflow.png')
        print('PASS: live GUI button write/readback/restore; synthetic disconnect/reconnect; no sync/audio')
    finally:
        settle(window)
        # Preserve evidence even if the GUI path fails; never revert recovered slot1.
        def restore(client, current):
            a50.restore_working(client, before)
        after, directory = a50.change_with_backup(restore)
        assert after['slots'] == before['slots'] and after['settings'] == before['settings']
        print('Final baseline comparison passed; evidence:', directory)
        window.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live', action='store_true')
    run(parser.parse_args().live)
