#!/usr/bin/python3
"""GUI workflow check; --live changes one gain via buttons and restores it."""
import argparse
import copy
import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
import a50
import a50_names
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
        # The 1-octave reference is in the slider's center; programmatically
        # loading an arbitrary raw hardware value must never round it.
        width = window.eq[1][2][2]  # Bell 3 in slot 2
        assert window.eq[1][0][2] is None, 'shelves have no bandwidth control'
        original_raw = before['slots'][1]['bands'][2]['working']['bandwidth_raw']
        width.setRawValue(4567)
        assert width.rawValue() == 4567
        assert window.draft()['slots'][1]['bands'][2]['working']['bandwidth_raw'] == 4567
        width.slider.setValue(0)
        assert width.rawValue() == 409
        width.slider.setValue(50)
        assert width.rawValue() == 4096, 'center must be exactly 1.0 octave'
        width.slider.setValue(100)
        assert width.rawValue() == 12288, 'right end must be 3.0 octaves'
        width.setRawValue(original_raw)
        window.eq[1][0][0].setValue(before['slots'][1]['gains']['working'][0])
        assert window.draft()['slots'] == before['slots'], 'unchanged EQ should round-trip exactly'
        # Exercise real GUI name handlers without writing to the user's XDG config.
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {'XDG_CONFIG_HOME': home}):
            with patch('a50_gui.QInputDialog.getText', return_value=('Night Gaming', True)):
                window.rename_eq(2)
            assert window.eq_names[1] == 'Night Gaming'
            assert window.tabs.tabText(1) == 'EQ 2'
            assert 'Night Gaming' in window.eq_name_labels[1].text()
            assert a50_names.load_names()[1] == 'Night Gaming'
            preset_path = Path(home) / 'preset.astroeq'
            with patch('a50_gui.QFileDialog.getSaveFileName',
                       return_value=(str(preset_path), 'Astro EQ (*.astroeq)')):
                window.preset(2, False)
            assert a50.load_astroeq(preset_path)['name'] == 'Night Gaming'
            imported = Path(home) / 'imported.astroeq'
            a50.export_preset(before, 2, imported, name='Imported from Windows')
            with patch('a50_gui.QFileDialog.getOpenFileName',
                       return_value=(str(imported), 'Astro EQ (*.astroeq)')):
                window.preset(2, True)
            assert window.eq_names[1] == 'Imported from Windows'
            assert window.tabs.tabText(1) == 'EQ 2'
            assert 'Imported from Windows' in window.eq_name_labels[1].text()
            assert a50_names.load_names()[1] == 'Imported from Windows'
            backup_path = Path(home) / 'backup.json'
            with patch('a50_gui.QFileDialog.getSaveFileName',
                       return_value=(str(backup_path), 'JSON (*.json)')):
                window.backup()
            assert json.loads(backup_path.read_text())['eq_names'][1] == 'Imported from Windows'
            with patch('a50_gui.QInputDialog.getText', return_value=('Temporary', True)):
                window.rename_eq(2)
            with patch('a50_gui.QFileDialog.getOpenFileName',
                       return_value=(str(backup_path), 'JSON (*.json)')):
                window.load_backup()
            assert window.eq_names[1] == 'Imported from Windows'
            assert window.draft()['slots'] == before['slots']
            # A hardware numeric match may suggest a label, but never overrides
            # the explicit name the user chose (including an imported label).
            matches = Path(home) / 'matches'
            matches.mkdir()
            a50.export_preset(before, 2, matches / 'PRO.astroeq', name='PRO')
            auto = a50_names.match_preset_names(before, [matches])
            assert auto[1] == 'PRO'
            window.eq_auto_names = auto
            window.refresh_eq_names()
            assert window.eq_display_names()[1] == 'Imported from Windows'
            assert window.tabs.tabText(1) == 'EQ 2'
        window.close()
        print('PASS: offline EQ bandwidth Narrow/1.0/Wide slider, raw precision, writes disabled')
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
