#!/usr/bin/env python3
"""About and guarded host-audio setup dialogs for the Astro A50 GUI.

The setup action runs the existing a50_setup.py helper. Preview is read-only,
and installation requires a separate explicit confirmation; no sudo, session
restart, default device change or headset write happens here.
"""
import sys
from pathlib import Path

from PyQt6.QtCore import QProcess
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit,
    QTextBrowser, QVBoxLayout, QMessageBox,
)

ROOT = Path(__file__).resolve().parent.parent
NOTICES = (Path(getattr(sys, "_MEIPASS", ROOT)) / "docs/THIRD_PARTY_NOTICES.md")
SETUP = Path(__file__).resolve().with_name("a50_setup.py")


class AudioSetupDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("A50 audio setup")
        self.resize(700, 500)
        self.action = None
        self.preview_ok = False
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Checks the A50 Game 5.1, Voice and microphone endpoints. "
            "Preview first; install only with your approval."))
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setPlainText(
            "No changes have been made. Click Preview setup to inspect "
            "your hardware and the proposed WirePlumber configuration.")
        layout.addWidget(self.output, 1)
        row = QHBoxLayout()
        self.preview_button = QPushButton("Preview setup")
        self.install_button = QPushButton("Install configuration…")
        self.install_button.setEnabled(False)
        self.install_button.setObjectName('primary')
        close = QPushButton("Close")
        row.addWidget(self.preview_button)
        row.addWidget(self.install_button)
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)
        self.preview_button.clicked.connect(self.preview)
        self.install_button.clicked.connect(self.install)
        close.clicked.connect(self.close)
        self.process = QProcess(self)
        self.process.finished.connect(self.completed)
        self.process.errorOccurred.connect(self.process_failed)

    def command(self, action):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            return
        self.action = action
        self.preview_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self.output.setPlainText("Checking A50 audio configuration…" if action == "preview"
                                 else "Installing approved A50 configuration…")
        # PyInstaller's sys.executable is the frozen GUI binary, not Python.
        # The private dispatch path lets the same setup code work in AppImage.
        args = (["--a50-audio-setup", action] if getattr(sys, "frozen", False)
                else [str(SETUP), action])
        if action == "install":
            args.append("--yes")
        self.process.start(sys.executable, args)

    def preview(self):
        self.preview_ok = False
        self.command("preview")

    def install(self):
        if not self.preview_ok:
            return
        choice = QMessageBox.question(
            self, "Install A50 audio configuration?",
            "Install the per-user WirePlumber A50 configuration shown in the preview?\n\n"
            "The tool will refuse conflicting existing A50 configurations. "
            "It will not change your system defaults or restart audio services. "
            "A logout/login may be required to activate it.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if choice == QMessageBox.StandardButton.Yes:
            self.preview_ok = False
            self.command("install")

    def completed(self, code, _exit_status):
        output = self.process.readAllStandardOutput().data().decode("utf-8", "replace")
        errors = self.process.readAllStandardError().data().decode("utf-8", "replace")
        self.output.setPlainText((output + ("\n" if output and errors else "") + errors).strip()
                                 or "No details returned.")
        self.preview_ok = self.action == "preview" and code == 0
        self.preview_button.setEnabled(True)
        self.install_button.setEnabled(self.preview_ok)
        if self.action == "install" and code == 0:
            self.output.appendPlainText(
                "\nConfiguration installed. Log out and in before verifying. "
                "No audio services were restarted.")

    def process_failed(self, _error):
        self.output.setPlainText("Unable to launch the setup helper: " +
                                 self.process.errorString())
        self.preview_ok = False
        self.install_button.setEnabled(False)
        self.preview_button.setEnabled(True)

    def closeEvent(self, event):
        if self.process.state() != QProcess.ProcessState.NotRunning:
            event.ignore()  # Do not abandon a running installation.
        else:
            event.accept()


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About OpenAstroCC")
        self.resize(620, 490)
        layout = QVBoxLayout(self)
        title = QLabel("OpenAstroCC")
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        layout.addWidget(title)
        subtitle = QLabel(
            "Open-source Command Center for the Astro A50 Gen 3. "
            "Not affiliated with Astro Gaming or Logitech.")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        credit = QLabel("© 2026 Benjamin Conner and contributors · GPLv3")
        credit.setStyleSheet("color: #aeb5c3;")
        layout.addWidget(credit)
        project = QLabel(
            '<a href="https://github.com/BenStein1/OpenAstroCC" '
            'style="color:#ff9e58;">Project source, issues and contributions on GitHub</a>')
        project.setOpenExternalLinks(True)
        layout.addWidget(project)

        # Qt already understands Markdown: no external parser/web engine needed.
        # The notice file uses short sections rather than a wide table.
        self.notices = QTextBrowser()
        self.notices.setOpenExternalLinks(True)
        self.notices.setStyleSheet(
            "QTextBrowser { background: #1c1f26; color: #e6e8ee; "
            "border: 1px solid #2a2e38; border-radius: 8px; padding: 8px; }")
        self.notices.document().setDefaultStyleSheet(
            "a { color: #ff9e58; } "
            "h1, h2, h3 { color: #f4f5f8; font-weight: bold; } "
            "code { color: #f6c481; }")
        try:
            self.notices.setMarkdown(NOTICES.read_text(encoding="utf-8"))
        except OSError:
            self.notices.setPlainText(
                "Third-party notices unavailable. See docs/THIRD_PARTY_NOTICES.md "
                "in the project repository.")
        layout.addWidget(self.notices, 1)
        row = QHBoxLayout()
        audio = QPushButton("Audio setup…")
        audio.clicked.connect(self.open_audio)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        row.addWidget(audio)
        row.addStretch(1)
        row.addWidget(close)
        layout.addLayout(row)
        audio.setObjectName('primary')
        audio.setStyleSheet(
            'QPushButton { background: #ff7a1a; border: 1px solid #ff7a1a; '
            'color: #1a1006; border-radius: 8px; padding: 7px 14px; font-weight: 700; } '
            'QPushButton:hover { background: #ff8f3d; }')
        self.audio_button = audio

    def open_audio(self):
        dialog = AudioSetupDialog(self)
        dialog.exec()
