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
from PyQt6.QtWidgets import QApplication, QMessageBox, QAbstractSpinBox
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
    # The spinbox stays editable but doesn't depend on platform-theme arrows.
    assert all(freq.buttonSymbols() == QAbstractSpinBox.ButtonSymbols.NoButtons
               for bank in window.eq for _, freq, _ in bank)
    if not live:
        assert not window.buttons['Test Current Settings'].isEnabled()
        # Editing an exact frequency still updates the draft without steppers.
        old_frequency = before['slots'][1]['bands'][0]['working']['frequency']
        window.eq[1][0][1].setValue(old_frequency + 1)
        assert window.draft()['slots'][1]['bands'][0]['working']['frequency'] == old_frequency + 1
        window.eq[1][0][1].setValue(old_frequency)
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
        width.slider.setValue(48)
        assert width.slider.value() == 50 and width.rawValue() == 4096, 'snap left of center'
        width.slider.setValue(52)
        assert width.slider.value() == 50 and width.rawValue() == 4096, 'snap right of center'
        width.slider.setValue(100)
        assert width.rawValue() == 12288, 'right end must be 3.0 octaves'
        width.setRawValue(original_raw)
        window.eq[1][0][0].setValue(before['slots'][1]['gains']['working'][0])
        assert window.draft()['slots'] == before['slots'], 'unchanged EQ should round-trip exactly'
        # Exercise real GUI name handlers without writing to the user's XDG config.
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {'XDG_CONFIG_HOME': home, 'XDG_DATA_HOME': home, 'APPIMAGE': '/tmp/test.AppImage'}):
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
            # Name-only file association must work even if the original
            # imported preset was customized; it must never change EQ values.
            named_file = Path(home) / 'custom-from-windows.astroeq'
            altered = copy.deepcopy(before)
            altered['slots'][2]['gains']['working'][0] += 1
            a50.export_preset(altered, 3, named_file, name='My Custom Windows EQ')
            unchanged = window.draft()['slots']
            with patch('a50_gui.QFileDialog.getOpenFileName',
                       return_value=(str(named_file), 'Astro EQ (*.astroeq)')):
                window.name_eq_from_file(3)
            assert window.eq_names[2] == 'My Custom Windows EQ'
            assert 'My Custom Windows EQ' in window.eq_name_labels[2].text()
            assert a50_names.load_names()[2] == 'My Custom Windows EQ'
            assert window.draft()['slots'] == unchanged, 'name-only import altered EQ values'
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

            # Choose the screenshot-based example from a compact dropdown.
            picker = window.eq_pickers[2]
            example_index = picker.findText('Custom · Bass & Clarity')
            assert example_index >= 0
            assert picker.findText('Example · Bass & Clarity') == -1
            assert picker.findText('Mine · Bass & Clarity Personal') == -1
            window.choose_library_preset(3, example_index)
            assert window.draft()['slots'][2]['bands'][2]['working']['bandwidth_raw'] == 8192
            assert 'Bass & Clarity' in window.eq_name_labels[2].text()
            assert window.tabs.tabText(2) == 'EQ 3'
            # Moving a gain marks the edited file as modified, but changes no hardware.
            window.eq[2][0][0].setValue(5)
            assert '(modified)' in window.eq_name_labels[2].text()
            astro_index = picker.findText('Astro · ASTRO')
            assert astro_index >= 0
            with patch('a50_gui.QMessageBox.question',
                       return_value=QMessageBox.StandardButton.Cancel):
                window.choose_library_preset(3, astro_index)
            assert window.eq[2][0][0].value() == 5, 'cancelled switch discarded edits'

            factory = root / 'presets/ASTRO.astroeq'
            unchanged_factory = factory.read_bytes()
            with patch('a50_gui.QInputDialog.getText',
                       return_value=('Bass & Clarity Personal', True)):
                window.save_library_preset(3)
            saved = Path(home) / 'astro-a50-linux/presets/Bass & Clarity Personal.astroeq'
            assert saved.exists()
            assert a50.load_astroeq(saved)['gains'][0] == 5
            assert '(modified)' not in window.eq_name_labels[2].text()
            assert factory.read_bytes() == unchanged_factory

            # Only an explicit Yes may overwrite the user's own custom preset.
            window.eq[2][0][0].setValue(7)
            assert '(modified)' in window.eq_name_labels[2].text()
            with patch('a50_gui.QMessageBox.question',
                       return_value=QMessageBox.StandardButton.No), patch(
                       'a50_gui.QInputDialog.getText', return_value=('', False)):
                window.save_library_preset(3)
            assert a50.load_astroeq(saved)['gains'][0] == 5
            with patch('a50_gui.QMessageBox.question',
                       return_value=QMessageBox.StandardButton.Yes):
                window.save_library_preset(3)
            assert a50.load_astroeq(saved)['gains'][0] == 7
            assert factory.read_bytes() == unchanged_factory
            window.populate(before)
            assert window.draft()['slots'] == before['slots']
        from a50_about import AboutDialog, AudioSetupDialog
        assert window.about_button.text() == 'About'
        about = AboutDialog(window)
        assert 'PyQt6' in about.notices.toPlainText()
        setup = AudioSetupDialog(about)
        assert not setup.install_button.isEnabled(), 'install must require preview'
        setup.close()
        about.close()
        window.close()
        print('PASS: offline EQ library, About/Notices and guarded audio setup controls')
        return
    try:
        widget = window.eq[1][0][0]
        old = widget.value()
        widget.setValue(old + (1 if old < 12 else -1))
        wanted = widget.value()
        window.buttons['Test Current Settings'].click()
        settle(window)
        assert window.connected, window.status_label.text()
        assert window.document['slots'][1]['gains']['working'][0] == wanted
        with a50.A50Client() as client:
            assert client.gains(2)['working'][0] == wanted
        widget.setValue(old)
        window.buttons['Test Current Settings'].click()
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
        window.buttons['Test Current Settings'].click()
        settle(window)
        assert window.connected, window.status_label.text()
        assert window.document['sliders']['sidetone']['working'] == wanted_level
        assert window.document['microphone']['noise_gate']['working'] == a50.NOISE_GATE_PACKETS[wanted_gate].hex()
        with a50.A50Client() as client:
            assert client.slider('sidetone')['working'] == wanted_level
            assert client.microphone()['noise_gate']['working'] == a50.NOISE_GATE_PACKETS[wanted_gate].hex()
        slider.setValue(old_level)
        window.noise_gate.setCurrentIndex(old_gate_index)
        window.buttons['Test Current Settings'].click()
        settle(window)
        assert window.document['sliders'] == before['sliders']
        assert window.document['microphone'] == before['microphone']
        print('PASS: live GUI mic/stream slider and noise-gate button write/readback/restore')
        # Exercise disconnect handling in the real GUI; physical USB stays attached.
        with patch.object(a50.A50Client, '__enter__', side_effect=OSError('synthetic disconnect')):
            window.poll()
            settle(window)
            assert not window.connected
            assert not window.buttons['Test Current Settings'].isEnabled()
        window.poll()
        settle(window)
        assert window.connected, window.status_label.text()
        assert window.buttons['Test Current Settings'].isEnabled()
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
