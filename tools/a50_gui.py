#!/usr/bin/python3
"""Native A50 settings app. Run with /usr/bin/python3 (system PyQt6)."""
import argparse
import copy
import json
import sys
from pathlib import Path
from PyQt6.QtCore import QThread, QTimer, pyqtSignal
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QGridLayout, QFormLayout, QLabel, QPushButton, QTabWidget,
    QSpinBox, QDoubleSpinBox, QComboBox, QFileDialog, QMessageBox, QPlainTextEdit)
import a50


class Job(QThread):
    result = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, action, parent):
        super().__init__(parent)
        self.action = action

    def run(self):
        try:
            self.result.emit(self.action())
        except Exception as exc:
            self.error.emit(str(exc))


class Window(QMainWindow):
    def __init__(self, offline=None, smoke=False):
        super().__init__()
        self.setWindowTitle('Astro A50 · Linux')
        self.resize(820, 610)
        self.document = None
        self.offline = offline
        self.smoke = smoke
        self.busy = False
        self.connected = False
        self.identity = None
        self.audio = None
        self.jobs = set()
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        self.status_label = QLabel('Connecting to A50 9886:0015…')
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        toolbar = QHBoxLayout()
        layout.addLayout(toolbar)
        self.buttons = {}
        for name, callback in [('Refresh / reconnect', self.refresh), ('Export backup', self.backup),
                               ('Import backup', self.load_backup), ('Write working settings', self.apply),
                               ('Save to headset', self.persist)]:
            button = QPushButton(name)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
            self.buttons[name] = button
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        self.eq = []
        for slot in range(1, 4):
            page = QWidget()
            grid = QGridLayout(page)
            grid.addWidget(QLabel('Band'), 0, 0)
            grid.addWidget(QLabel('Gain (dB)'), 0, 1)
            grid.addWidget(QLabel('Frequency (Hz)'), 0, 2)
            grid.addWidget(QLabel('Bandwidth (octaves)'), 0, 3)
            controls = []
            for band in range(1, 6):
                grid.addWidget(QLabel(str(band)), band, 0)
                gain = self.spin(-12, 12)
                freq = self.spin(80, 15000)
                width = QDoubleSpinBox()
                width.setDecimals(6)
                width.setRange(409 / 4096, 3) if band in (2, 3, 4) else width.setRange(0, 0)
                width.setSingleStep(0.1)
                width.setEnabled(band in (2, 3, 4))
                width.setToolTip('Exact headset bandwidth; six decimals preserve the stored precision')
                for column, control in enumerate((gain, freq, width), 1):
                    grid.addWidget(control, band, column)
                controls.append((gain, freq, width))
            self.eq.append(controls)
            imp = QPushButton('Import .astroeq')
            exp = QPushButton('Export .astroeq')
            imp.clicked.connect(lambda _checked=False, s=slot: self.preset(s, True))
            exp.clicked.connect(lambda _checked=False, s=slot: self.preset(s, False))
            grid.addWidget(imp, 6, 1)
            grid.addWidget(exp, 6, 2)
            grid.addWidget(QLabel('Edits remain here until “Write working settings”.'), 7, 0, 1, 4)
            self.tabs.addTab(page, 'EQ %d' % slot)
        page = QWidget()
        form = QFormLayout(page)
        self.balance = self.spin(0, 255)
        self.brightness = self.spin(20, 70)
        self.alert = self.spin(0, 100)
        form.addRow('Default Game / Voice balance (raw 0–255)', self.balance)
        form.addRow('Dock brightness (20–70)', self.brightness)
        form.addRow('Alert volume (0–100)', self.alert)
        form.addRow(QLabel('Physical listening and visual confirmation are still pending.'))
        self.tabs.addTab(page, 'Dock / defaults')
        self.sliders = {}
        page = QWidget()
        form = QFormLayout(page)
        for name, label in [('microphone_output', 'Microphone output'), ('sidetone', 'Onboard sidetone')]:
            self.sliders[name] = self.spin(0, 100)
            form.addRow(label, self.sliders[name])
        self.mic_eq = QComboBox()
        self.mic_eq.addItems(a50.MIC_EQ_NAMES)
        self.noise_gate = QComboBox()
        self.noise_gate.addItems(a50.NOISE_GATE_NAMES)
        form.addRow('Microphone EQ', self.mic_eq)
        form.addRow('Noise gate', self.noise_gate)
        form.addRow(QLabel('Onboard controls; listening and recording confirmation remain pending.'))
        self.mic_tab = self.tabs.addTab(page, 'Microphone')
        page = QWidget()
        form = QFormLayout(page)
        for name, label in [('stream_game', 'Game audio'), ('stream_chat', 'Chat / Voice audio'),
                            ('stream_microphone', 'Microphone'), ('stream_aux', 'Auxiliary input')]:
            self.sliders[name] = self.spin(0, 100)
            form.addRow(label, self.sliders[name])
        form.addRow(QLabel('USB stream mix levels; capture/listening confirmation remains pending.'))
        self.stream_tab = self.tabs.addTab(page, 'Stream mix')
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.tabs.addTab(self.details, 'Device / audio')
        self.notice = QLabel('Working writes are read back and backed up. Save to headset persists all working settings.')
        self.notice.setWordWrap(True)
        layout.addWidget(self.notice)
        self.timer = QTimer(self)
        self.timer.setInterval(5000)
        self.timer.timeout.connect(self.poll)
        self.timer.start()
        self.update_enabled()
        QTimer.singleShot(0, self.refresh)

    @staticmethod
    def spin(low, high):
        spin = QSpinBox()
        spin.setRange(low, high)
        return spin

    def update_enabled(self):
        for name, button in self.buttons.items():
            button.setEnabled(not self.busy and (name == 'Refresh / reconnect' or self.document is not None))
        self.buttons['Write working settings'].setEnabled(not self.busy and self.connected and not self.offline)
        self.buttons['Save to headset'].setEnabled(not self.busy and self.connected and not self.offline)
        self.tabs.setEnabled(not self.busy and self.document is not None)

    def run(self, action, done):
        if self.busy:
            return
        self.busy = True
        self.update_enabled()
        job = Job(action, self)
        self.jobs.add(job)
        job.result.connect(done)
        job.error.connect(self.failed)
        job.finished.connect(lambda: self.finished(job))
        job.start()

    def finished(self, job):
        self.jobs.discard(job)
        self.busy = False
        self.update_enabled()
        job.deleteLater()

    def failed(self, message):
        self.connected = False
        self.identity = None
        self.status_label.setText('A50 operation failed: ' + message)
        self.notice.setText('Reconnect / refresh to read current device state. ' + message)
        self.update_enabled()
        if self.smoke:
            QApplication.instance().exit(1)

    def refresh(self):
        def read():
            if self.offline:
                return a50.validate_backup(json.loads(Path(self.offline).read_text())), None, None
            with a50.A50Client() as client:
                document = client.snapshot()
                identity = self.identity or client.identity()
            import a50_audio
            try:
                audio = a50_audio.inventory()
            except Exception as exc:
                audio = {'inventory_error': str(exc)}
            return document, identity, audio
        self.run(read, self.refreshed)

    def refreshed(self, result):
        document, self.identity, self.audio = result
        self.connected = not self.offline
        self.populate(document)
        self.show_status(document['status'])
        self.details.setPlainText(json.dumps({'identity': self.identity, 'status': document['status'],
            'stored_EQ': [{ 'slot': s['slot'], 'gains': s['gains']['stored'],
                           'bands': [b['stored'] for b in s['bands']]} for s in document['slots']],
            'audio': self.audio,
            'microphone': document.get('microphone'), 'sliders': document.get('sliders'),
            'pending': 'Physical mic/stream listening, Dolby/mute and power-cycle persistence proof pending.'}, indent=2))
        if self.smoke:
            assert self.eq[0][0][0].value() == document['slots'][0]['gains']['working'][0]
            QTimer.singleShot(100, self.smoke_finished)

    def smoke_finished(self):
        assert not self.busy
        assert self.draft()['slots'] == self.document['slots']
        self.grab().save('/tmp/a50-ui-smoke.png')
        QApplication.instance().quit()

    def populate(self, document):
        a50.validate_backup(document)
        self.document = copy.deepcopy(document)
        for slot, controls in zip(document['slots'], self.eq):
            for index, (gain, freq, width) in enumerate(controls):
                gain.setValue(slot['gains']['working'][index])
                freq.setValue(slot['bands'][index]['working']['frequency'])
                width.setValue(slot['bands'][index]['working']['bandwidth_raw'] / 4096)
        settings = document['settings']
        self.editor_brightness = settings['brightness_channels'].copy()
        self.balance.setValue(settings['default_balance'])
        self.brightness.setValue(round(sum(settings['brightness_channels']) / 9))
        self.alert.setValue(settings['alert_volume'])
        full = document['schema'] == 'astro-a50-gen3-v2'
        self.tabs.setTabEnabled(self.mic_tab, full)
        self.tabs.setTabEnabled(self.stream_tab, full)
        if full:
            for name, spin in self.sliders.items():
                spin.setValue(document['sliders'][name]['working'])
            self.mic_eq.setCurrentIndex(document['microphone']['eq'])
            self.noise_gate.setCurrentIndex([p.hex() for p in a50.NOISE_GATE_PACKETS].index(
                document['microphone']['noise_gate']['working']))
        self.update_enabled()

    def draft(self):
        result = copy.deepcopy(self.document)
        for slot, controls in zip(result['slots'], self.eq):
            slot['gains']['working'] = [gain.value() for gain, _, _ in controls]
            for values, (_, freq, width) in zip(slot['bands'], controls):
                values['working'] = {'frequency': freq.value(), 'bandwidth_raw': round(width.value() * 4096)}
        settings = result['settings']
        settings['brightness_channels'] = self.editor_brightness.copy()
        settings['default_balance'] = self.balance.value()
        settings['alert_volume'] = self.alert.value()
        if self.brightness.value() != round(sum(settings['brightness_channels']) / 9):
            settings['brightness_channels'] = [self.brightness.value()] * 9
        if result['schema'] == 'astro-a50-gen3-v2':
            for name, spin in self.sliders.items():
                result['sliders'][name]['working'] = spin.value()
            result['microphone']['eq'] = self.mic_eq.currentIndex()
            result['microphone']['noise_gate']['working'] = a50.NOISE_GATE_PACKETS[
                self.noise_gate.currentIndex()].hex()
        return a50.validate_backup(result)

    def show_status(self, status):
        prefix = 'Offline backup' if self.offline else 'A50 connected'
        self.status_label.setText('%s · battery %d%% · %s · hardware balance %d · EQ %s' % (
            prefix, status['battery'], 'charging' if status['charging'] else 'not charging',
            status.get('current_balance', status['status_byte']), status.get('eq_slot', '?')))

    def poll(self):
        if self.busy or self.offline:
            return
        if not self.connected:
            self.refresh()
            return
        def read():
            with a50.A50Client() as client:
                return client.status()
        self.run(read, self.show_status)

    def apply(self):
        target = self.draft()
        displayed = copy.deepcopy(self.document)
        def action(client, before):
            if not a50.same_settings(before, displayed):
                raise a50.EqReadError('Settings changed since refresh; refresh before writing.')
            a50.restore_working(client, target)
        self.run(lambda: a50.change_with_backup(action), self.changed)

    def changed(self, result):
        document, directory = result
        self.populate(document)
        self.notice.setText('Readback verified. Backup and exact TX/RX: ' + directory)

    def persist(self):
        if not a50.same_settings(self.draft(), self.document):
            self.notice.setText('Write working settings first; pending editor changes have not reached the headset.')
            return
        answer = QMessageBox.question(self, 'Save all working settings?',
            'Persist all current headset settings, including microphone/stream settings. '
            'A backup will be saved first. Continue?')
        if answer != QMessageBox.StandardButton.Yes:
            return
        displayed = copy.deepcopy(self.document)
        def action(client, before):
            if not a50.same_settings(before, displayed):
                raise a50.EqReadError('Settings changed since refresh; refresh before saving.')
            client.sync()
        self.run(lambda: a50.change_with_backup(action, persistent=True), self.changed)

    def backup(self):
        path, _ = QFileDialog.getSaveFileName(self, 'Export device backup', '', 'JSON (*.json)')
        if path:
            try:
                a50.save_json(path, self.document)
                self.notice.setText('Exported last device readback: ' + path)
            except Exception as exc:
                self.notice.setText(str(exc))

    def load_backup(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Import backup to editor', '', 'JSON (*.json)')
        if path:
            try:
                wanted = a50.validate_backup(json.loads(Path(path).read_text()))
                current = copy.deepcopy(self.document)
                # Import into editor; retain current stored banks and concurrency baseline.
                for old, new in zip(current['slots'], wanted['slots']):
                    old['gains']['working'] = new['gains']['working']
                    for band, imported in zip(old['bands'], new['bands']):
                        band['working'] = imported['working']
                current['settings'] = wanted['settings']
                if wanted['schema'] == 'astro-a50-gen3-v2':
                    if current['schema'] != 'astro-a50-gen3-v2':
                        raise ValueError('Full microphone backup requires a current full device snapshot')
                    for name, banks in wanted['sliders'].items():
                        current['sliders'][name]['working'] = banks['working']
                    current['microphone']['eq'] = wanted['microphone']['eq']
                    current['microphone']['noise_gate']['working'] = wanted['microphone']['noise_gate']['working']
                baseline = self.document
                self.populate(current)
                self.document = baseline
                self.notice.setText('Backup loaded into editor; write working settings to restore it.')
            except Exception as exc:
                self.notice.setText('Import refused: ' + str(exc))

    def preset(self, slot, importing):
        chooser = QFileDialog.getOpenFileName if importing else QFileDialog.getSaveFileName
        path, _ = chooser(self, 'EQ preset', '', 'Astro EQ (*.astroeq)')
        if not path:
            return
        try:
            if importing:
                baseline = self.document
                self.populate(a50.import_preset(self.draft(), slot, path))
                self.document = baseline
                self.notice.setText('Preset loaded into editor; write working settings to use it.')
            else:
                a50.export_preset(self.draft(), slot, path)
        except Exception as exc:
            self.notice.setText(str(exc))

    def closeEvent(self, event):
        if self.jobs:
            self.notice.setText('Finishing the current device transaction before closing.')
            event.ignore()
        else:
            event.accept()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot', help='inspect a backup offline; hardware writes disabled')
    parser.add_argument('--smoke', action='store_true', help='read only, render, assert and exit')
    args = parser.parse_args()
    app = QApplication(sys.argv[:1])
    window = Window(args.snapshot, args.smoke)
    window.show()
    if args.smoke:
        QTimer.singleShot(15000, lambda: app.exit(2))
    sys.exit(app.exec())
