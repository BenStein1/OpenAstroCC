#!/usr/bin/python3
"""Native A50 settings app. Run with /usr/bin/python3 (system PyQt6)."""
import argparse
import copy
import json
import sys
from pathlib import Path
import array
import math
import subprocess
from PyQt6.QtCore import QPointF, QProcess, QRectF, Qt, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QGridLayout, QFormLayout, QLabel, QPushButton, QTabWidget,
    QSpinBox, QDoubleSpinBox, QComboBox, QFileDialog, QMessageBox, QPlainTextEdit,
    QSlider, QFrame, QSizePolicy, QStyle, QStyleOptionSlider)
import a50

ACCENT = '#ff7a1a'
STYLE = '''
* { font-family: "Inter", "Noto Sans", "Segoe UI", sans-serif; font-size: 13px; color: #e6e8ee; }
QMainWindow, QWidget#root { background: #14161b; }
QLabel#status { font-size: 14px; font-weight: 600; }
QLabel#hint, QLabel#value { color: #8b93a3; }
QLabel#value { color: #e6e8ee; font-weight: 600; min-width: 64px; }
QLabel#section { font-size: 11px; font-weight: 700; letter-spacing: 1px; color: #8b93a3; }
QFrame#card { background: #1c1f26; border: 1px solid #2a2e38; border-radius: 12px; }
QTabWidget::pane { border: none; top: 8px; }
QTabBar::tab { background: transparent; color: #8b93a3; padding: 8px 16px; margin-right: 4px;
    border-bottom: 2px solid transparent; font-weight: 600; }
QTabBar::tab:selected { color: #ffffff; border-bottom: 2px solid %(a)s; }
QTabBar::tab:hover:!selected { color: #cfd3dc; }
QTabBar::tab:disabled { color: #4a4f5c; }
QPushButton { background: #262a33; border: 1px solid #343946; border-radius: 8px; padding: 7px 14px; font-weight: 600; }
QPushButton:hover { background: #2f3440; }
QPushButton:pressed { background: #222630; }
QPushButton:disabled { color: #5b606d; background: #1d2027; border-color: #262a33; }
QPushButton#primary { background: %(a)s; border-color: %(a)s; color: #1a1006; }
QPushButton#primary:hover { background: #ff8f3d; }
QPushButton#primary:disabled { background: #3a2c1f; border-color: #3a2c1f; color: #7a6650; }
QSpinBox, QDoubleSpinBox, QComboBox { background: #14161b; border: 1px solid #343946; border-radius: 6px; padding: 4px 8px; }
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus { border-color: %(a)s; }
QSpinBox:disabled, QDoubleSpinBox:disabled { color: #4a4f5c; }
QComboBox QAbstractItemView { background: #1c1f26; selection-background-color: %(a)s; selection-color: #1a1006; }
QSlider::groove:horizontal { height: 6px; background: #2a2e38; border-radius: 3px; }
QSlider::sub-page:horizontal { background: %(a)s; border-radius: 3px; }
QSlider::handle:horizontal { background: #ffffff; width: 18px; height: 18px; margin: -6px 0; border-radius: 9px; }
QSlider::handle:horizontal:hover { background: #ffe3cc; }
QSlider::groove:vertical { width: 6px; background: #2a2e38; border-radius: 3px; }
QSlider::add-page:vertical { background: %(a)s; border-radius: 3px; }
QSlider::handle:vertical { background: #ffffff; height: 18px; width: 18px; margin: 0 -6px; border-radius: 9px; }
QSlider:disabled { }
QSlider::handle:disabled { background: #5b606d; }
QSlider::sub-page:horizontal:disabled, QSlider::add-page:vertical:disabled { background: #3a3f4b; }
QPlainTextEdit { background: #1c1f26; border: 1px solid #2a2e38; border-radius: 8px; font-family: monospace; }
''' % {'a': ACCENT}

SAMPLE_RATE = 48000
BAND_COLORS = ['#ff7a1a', '#ffc247', '#5ad19a', '#4fb3ff', '#b58cff']


def band_response(kind, freq, gain_db, octaves, f):
    """Magnitude in dB of one RBJ biquad (shelf or peaking) at frequency f."""
    if gain_db == 0:
        return 0.0
    amp = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * min(max(freq, 1), SAMPLE_RATE / 2 - 1) / SAMPLE_RATE
    cw, sw = math.cos(w0), math.sin(w0)
    if kind == 'peak':
        alpha = sw * math.sinh(math.log(2) / 2 * max(octaves, 0.05) * w0 / sw)
        b = (1 + alpha * amp, -2 * cw, 1 - alpha * amp)
        a = (1 + alpha / amp, -2 * cw, 1 - alpha / amp)
    else:
        alpha = sw / 2 * math.sqrt(2)
        root = 2 * math.sqrt(amp) * alpha
        if kind == 'low':
            b = (amp * ((amp + 1) - (amp - 1) * cw + root), 2 * amp * ((amp - 1) - (amp + 1) * cw),
                 amp * ((amp + 1) - (amp - 1) * cw - root))
            a = ((amp + 1) + (amp - 1) * cw + root, -2 * ((amp - 1) + (amp + 1) * cw),
                 (amp + 1) + (amp - 1) * cw - root)
        else:
            b = (amp * ((amp + 1) + (amp - 1) * cw + root), -2 * amp * ((amp - 1) + (amp + 1) * cw),
                 amp * ((amp + 1) + (amp - 1) * cw - root))
            a = ((amp + 1) - (amp - 1) * cw + root, 2 * ((amp - 1) - (amp + 1) * cw),
                 (amp + 1) - (amp - 1) * cw - root)
    w = 2 * math.pi * f / SAMPLE_RATE
    z1 = complex(math.cos(w), -math.sin(w))
    z2 = z1 * z1
    num = abs(b[0] + b[1] * z1 + b[2] * z2)
    den = abs(a[0] + a[1] * z1 + a[2] * z2)
    return 20 * math.log10(num / den) if num and den else 0.0


class DragSlider(QSlider):
    """QSlider that only moves when its handle is dragged.

    The handle drags normally; a click on the groove steps by one page toward the click
    instead of jumping; the pointer never moves it without a pressed button; the wheel
    only works once the slider has keyboard focus (so scrolling past it does nothing).
    """

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(False)
        self.dragging = False

    def handle_rect(self):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        return self.style().subControlRect(QStyle.ComplexControl.CC_Slider, opt,
                                           QStyle.SubControl.SC_SliderHandle, self)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return
        pos = event.position().toPoint()
        handle = self.handle_rect()
        if handle.adjusted(-4, -4, 4, 4).contains(pos):
            self.dragging = True
            super().mousePressEvent(event)
            return
        self.setFocus()
        horizontal = self.orientation() == Qt.Orientation.Horizontal
        toward_max = (pos.x() > handle.center().x()) if horizontal else (pos.y() < handle.center().y())
        self.setValue(self.value() + (self.pageStep() if toward_max else -self.pageStep()))

    def mouseMoveEvent(self, event):
        if self.dragging and event.buttons() & Qt.MouseButton.LeftButton:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            super().mouseReleaseEvent(event)
        self.setSliderDown(False)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class SliderRow(QWidget):
    """Horizontal slider with a live value readout; value()/setValue() like a spin box."""
    valueChanged = pyqtSignal(int)

    def __init__(self, low, high, fmt='%d', ends=None, detent=None, parent=None):
        super().__init__(parent)
        self.fmt = fmt
        self.slider = DragSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(low, high)
        self.slider.setPageStep(max(1, (high - low) // 20))
        self.slider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if detent is not None:
            self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            self.slider.setTickInterval(max(1, detent))
        self.readout = QLabel()
        self.readout.setObjectName('value')
        self.readout.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        if ends:
            left = QLabel(ends[0])
            left.setObjectName('hint')
            layout.addWidget(left)
        layout.addWidget(self.slider, 1)
        if ends:
            right = QLabel(ends[1])
            right.setObjectName('hint')
            layout.addWidget(right)
        layout.addWidget(self.readout)
        self.slider.valueChanged.connect(self._changed)
        self._changed(self.slider.value())

    def _changed(self, value):
        self.readout.setText(self.fmt % value if '%' in self.fmt else self.fmt)
        self.valueChanged.emit(value)

    def value(self):
        return self.slider.value()

    def setValue(self, value):
        self.slider.setValue(value)

    def setEnabled(self, enabled):
        super().setEnabled(enabled)


class LevelMeter(QWidget):
    """Horizontal peak meter, -60..0 dBFS, with a decaying peak-hold tick."""
    FLOOR = -60.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.level = self.hold = self.FLOOR
        self.setMinimumHeight(26)
        self.decay = QTimer(self)
        self.decay.setInterval(40)
        self.decay.timeout.connect(self._decay)
        self.decay.start()

    def push(self, peak):
        """peak is 0..1 linear full scale."""
        db = 20 * math.log10(peak) if peak > 0 else self.FLOOR
        self.level = max(db, self.FLOOR)
        if self.level >= self.hold:
            self.hold = self.level
        self.update()

    def reset(self):
        self.level = self.hold = self.FLOOR
        self.update()

    def _decay(self):
        self.level = max(self.FLOOR, self.level - 2.0)
        self.hold = max(self.FLOOR, self.hold - 0.4, self.level)
        self.update()

    def x_of(self, db):
        return 2 + (self.width() - 4) * (db - self.FLOOR) / -self.FLOOR

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        bar = QRectF(0, 3, self.width(), self.height() - 6)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#14161b'))
        p.drawRoundedRect(bar, 6, 6)
        if self.level > self.FLOOR:
            gradient = QLinearGradient(bar.left(), 0, bar.right(), 0)
            gradient.setColorAt(0, QColor('#3ecf8e'))
            gradient.setColorAt(0.7, QColor('#3ecf8e'))
            gradient.setColorAt(0.85, QColor('#ffc247'))
            gradient.setColorAt(1, QColor('#ff5a4f'))
            p.setBrush(gradient)
            p.setClipRect(QRectF(0, 0, self.x_of(self.level), self.height()))
            p.drawRoundedRect(bar, 6, 6)
            p.setClipping(False)
        if self.hold > self.FLOOR:
            p.setPen(QPen(QColor('#ffffff'), 2))
            x = self.x_of(self.hold)
            p.drawLine(QPointF(x, bar.top() + 2), QPointF(x, bar.bottom() - 2))
        p.end()


def pcm_peak(data):
    """Peak (0..1) of little-endian signed 16-bit mono PCM bytes."""
    samples = array.array('h')
    samples.frombytes(data[:len(data) // 2 * 2])
    if sys.byteorder == 'big':
        samples.byteswap()
    return max((abs(v) for v in samples), default=0) / 32768


def card(title=None):
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(18, 14, 18, 16)
    layout.setSpacing(12)
    if title:
        label = QLabel(title.upper())
        label.setObjectName('section')
        layout.addWidget(label)
    return frame, layout


def hint(text):
    label = QLabel(text)
    label.setObjectName('hint')
    label.setWordWrap(True)
    return label


class EqCurve(QWidget):
    """Interactive graphic EQ: log-frequency response of the five bands, draggable nodes.

    Drag a node to change gain (vertical) and frequency (horizontal); mouse wheel over
    a bell node changes its bandwidth. The response is an estimate (RBJ biquads at 48 kHz),
    not a measurement of the headset DSP.
    """
    FMIN, FMAX, DB = 40.0, 20000.0, 12
    KINDS = ('low', 'peak', 'peak', 'peak', 'high')

    def __init__(self, controls, parent=None):
        super().__init__(parent)
        self.controls = controls
        self.active = None
        self.hover = None
        self.setMinimumHeight(260)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        for gain, freq, width in controls:
            for control in (gain, freq, width):
                control.valueChanged.connect(lambda *_: self.update())

    def plot(self):
        return QRectF(44, 14, max(self.width() - 60, 10), max(self.height() - 44, 10))

    def x_of(self, f):
        r = self.plot()
        return r.left() + r.width() * math.log(f / self.FMIN) / math.log(self.FMAX / self.FMIN)

    def f_of(self, x):
        r = self.plot()
        return self.FMIN * (self.FMAX / self.FMIN) ** ((x - r.left()) / r.width())

    def y_of(self, db):
        r = self.plot()
        return r.center().y() - db / self.DB * r.height() / 2

    def db_of(self, y):
        r = self.plot()
        return (r.center().y() - y) / (r.height() / 2) * self.DB

    def band(self, i):
        gain, freq, width = self.controls[i]
        return self.KINDS[i], freq.value(), gain.value(), width.value()

    def total(self, f):
        return sum(band_response(*self.band_args(i), f) for i in range(5))

    def band_args(self, i):
        kind, freq, gain, width = self.band(i)
        return kind, freq, gain, width

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.plot()
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#1c1f26'))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 12, 12)
        small = QFont(self.font())
        small.setPixelSize(10)
        p.setFont(small)
        for db in range(-self.DB, self.DB + 1, 6):
            y = self.y_of(db)
            p.setPen(QPen(QColor('#3a3f4b' if db == 0 else '#272b34'), 1))
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            p.setPen(QColor('#8b93a3'))
            p.drawText(QRectF(0, y - 8, r.left() - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       '%+d' % db if db else '0')
        for f in (50, 100, 200, 500, 1000, 2000, 5000, 10000):
            x = self.x_of(f)
            p.setPen(QPen(QColor('#272b34'), 1))
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            p.setPen(QColor('#8b93a3'))
            p.drawText(QRectF(x - 24, r.bottom() + 6, 48, 14), Qt.AlignmentFlag.AlignCenter,
                       '%gk' % (f / 1000) if f >= 1000 else str(f))
        steps = 160
        pts = [QPointF(r.left() + r.width() * i / steps,
                       min(max(self.y_of(self.total(self.f_of(r.left() + r.width() * i / steps))), r.top()), r.bottom()))
               for i in range(steps + 1)]
        line = QPainterPath(pts[0])
        for pt in pts[1:]:
            line.lineTo(pt)
        fill = QPainterPath(line)
        zero = self.y_of(0)
        fill.lineTo(QPointF(r.right(), zero))
        fill.lineTo(QPointF(r.left(), zero))
        fill.closeSubpath()
        gradient = QLinearGradient(0, r.top(), 0, r.bottom())
        top, bottom = QColor(ACCENT), QColor(ACCENT)
        top.setAlpha(110)
        bottom.setAlpha(110)
        mid = QColor(ACCENT)
        mid.setAlpha(8)
        gradient.setColorAt(0, top)
        gradient.setColorAt(0.5, mid)
        gradient.setColorAt(1, bottom)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(gradient)
        p.drawPath(fill)
        p.setPen(QPen(QColor(ACCENT), 2.4))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(line)
        for i in range(5):
            _kind, freq, gain, _w = self.band(i)
            c = QPointF(self.x_of(freq), self.y_of(gain))
            color = QColor(BAND_COLORS[i])
            hot = i in (self.active, self.hover)
            p.setPen(QPen(QColor('#14161b'), 2))
            p.setBrush(color)
            p.drawEllipse(c, 9 if hot else 7, 9 if hot else 7)
            p.setPen(QColor('#14161b'))
            bold = QFont(small)
            bold.setBold(True)
            p.setFont(bold)
            p.drawText(QRectF(c.x() - 8, c.y() - 8, 16, 16), Qt.AlignmentFlag.AlignCenter, str(i + 1))
            p.setFont(small)
        if self.active is not None or self.hover is not None:
            i = self.active if self.active is not None else self.hover
            _kind, freq, gain, width = self.band(i)
            text = 'Band %d  ·  %d Hz  ·  %+d dB' % (i + 1, freq, gain)
            if 1 <= i <= 3:
                text += '  ·  %.2f oct' % width
            p.setPen(QColor('#e6e8ee'))
            p.drawText(QRectF(r.left() + 8, r.top() + 4, r.width() - 16, 16),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        p.end()

    def node_at(self, pos):
        best, dist = None, 14.0
        for i in range(5):
            _k, freq, gain, _w = self.band(i)
            d = math.hypot(pos.x() - self.x_of(freq), pos.y() - self.y_of(gain))
            if d < dist:
                best, dist = i, d
        return best

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.active = self.node_at(event.position())
            self.update()

    def mouseMoveEvent(self, event):
        if self.active is None:
            hover = self.node_at(event.position())
            if hover != self.hover:
                self.hover = hover
                self.setCursor(Qt.CursorShape.OpenHandCursor if hover is not None else Qt.CursorShape.ArrowCursor)
                self.update()
            return
        gain, freq, _width = self.controls[self.active]
        gain.setValue(round(min(max(self.db_of(event.position().y()), -self.DB), self.DB)))
        freq.setValue(round(min(max(self.f_of(event.position().x()), freq.minimum()), freq.maximum())))

    def mouseReleaseEvent(self, _event):
        self.active = None
        self.update()

    def leaveEvent(self, _event):
        self.hover = None
        self.update()

    def wheelEvent(self, event):
        i = self.node_at(event.position())
        if i is None or not 1 <= i <= 3:
            return
        width = self.controls[i][2]
        width.setValue(width.value() + (0.1 if event.angleDelta().y() > 0 else -0.1))
        event.accept()


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
        self.resize(940, 760)
        self.document = None
        self.offline = offline
        self.smoke = smoke
        self.busy = False
        self.done_message = None
        self.testing = False
        self.pending = None
        self.capture = None
        self.sidetone_timer = QTimer(self)
        self.sidetone_timer.setSingleShot(True)
        self.sidetone_timer.setInterval(350)
        self.sidetone_timer.timeout.connect(self.apply_sidetone)
        self.connected = False
        self.identity = None
        self.audio = None
        self.jobs = set()
        self.setStyleSheet(STYLE)
        central = QWidget()
        central.setObjectName('root')
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(10)
        self.status_label = QLabel('Connecting to A50 9886:0015…')
        self.status_label.setObjectName('status')
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        layout.addLayout(toolbar)
        self.buttons = {}
        for name, callback in [('Refresh / reconnect', self.refresh), ('Export backup', self.backup),
                               ('Import backup', self.load_backup)]:
            button = QPushButton(name)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
            self.buttons[name] = button
        toolbar.addStretch(1)
        for name, callback in [('Write working settings', self.apply), ('Save to headset', self.persist)]:
            button = QPushButton(name)
            button.clicked.connect(callback)
            toolbar.addWidget(button)
            self.buttons[name] = button
        self.buttons['Write working settings'].setObjectName('primary')
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.eq = []
        self.curves = []
        for slot in range(1, 4):
            page = QWidget()
            box = QVBoxLayout(page)
            box.setContentsMargins(0, 0, 0, 0)
            box.setSpacing(12)
            controls = []
            for band in range(1, 6):
                gain = DragSlider(Qt.Orientation.Vertical)
                gain.setRange(-12, 12)
                gain.setTickPosition(QSlider.TickPosition.TicksRight)
                gain.setTickInterval(6)
                gain.setPageStep(1)
                freq = self.spin(80, 15000)
                freq.setSuffix(' Hz')
                width = QDoubleSpinBox()
                width.setDecimals(6)
                width.setRange(409 / 4096, 3) if band in (2, 3, 4) else width.setRange(0, 0)
                width.setSingleStep(0.1)
                width.setEnabled(band in (2, 3, 4))
                width.setSuffix(' oct')
                width.setToolTip('Exact headset bandwidth; six decimals preserve the stored precision')
                controls.append((gain, freq, width))
            self.eq.append(controls)
            curve = EqCurve(controls)
            self.curves.append(curve)
            box.addWidget(curve, 1)
            frame, inner = card()
            strip = QGridLayout()
            strip.setHorizontalSpacing(14)
            strip.setVerticalSpacing(6)
            names = ['Low shelf', 'Bell', 'Bell', 'Bell', 'High shelf']
            for column, ((gain, freq, width), name) in enumerate(zip(controls, names)):
                title = QLabel('%d · %s' % (column + 1, name))
                title.setStyleSheet('font-weight: 700; color: %s;' % BAND_COLORS[column])
                title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                readout = QLabel()
                readout.setObjectName('value')
                readout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                gain.valueChanged.connect(lambda v, r=readout: r.setText('%+d dB' % v))
                readout.setText('%+d dB' % gain.value())
                gain.setMinimumHeight(110)
                strip.addWidget(title, 0, column)
                strip.addWidget(gain, 1, column, Qt.AlignmentFlag.AlignHCenter)
                strip.addWidget(readout, 2, column)
                strip.addWidget(freq, 3, column)
                strip.addWidget(width, 4, column)
                strip.setColumnStretch(column, 1)
            inner.addLayout(strip)
            footer = QHBoxLayout()
            footer.addWidget(hint('Drag a node on the curve, or use the sliders. Wheel over a bell node to widen it. '
                                  'Curve is an estimate. Edits stay here until “Write working settings”.'), 1)
            flat = QPushButton('Flatten gains')
            flat.clicked.connect(lambda _c=False, c=controls: [g.setValue(0) for g, _, _ in c])
            imp = QPushButton('Import .astroeq')
            exp = QPushButton('Export .astroeq')
            imp.clicked.connect(lambda _checked=False, s=slot: self.preset(s, True))
            exp.clicked.connect(lambda _checked=False, s=slot: self.preset(s, False))
            for button in (flat, imp, exp):
                footer.addWidget(button)
            inner.addLayout(footer)
            box.addWidget(frame)
            self.tabs.addTab(page, 'EQ %d' % slot)
        self.sliders = {}
        # Volume and balance
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(12)
        frame, inner = card('Game / Voice balance')
        self.balance = SliderRow(0, 255, '%d', ends=('Game', 'Voice'), detent=128)
        inner.addWidget(self.balance)
        inner.addWidget(hint('Default balance applied by the dock (raw 0–255, center 128). '
                             'Physical listening and visual confirmation are still pending.'))
        box.addWidget(frame)
        frame, inner = card('Volume')
        self.alert = SliderRow(0, 100, '%d%%')
        form = QFormLayout()
        form.setVerticalSpacing(14)
        form.addRow('Alert volume', self.alert)
        self.stream_rows = []
        for name, label in [('stream_game', 'Game audio'), ('stream_chat', 'Chat / Voice audio'),
                            ('stream_microphone', 'Microphone'), ('stream_aux', 'Auxiliary input')]:
            self.sliders[name] = SliderRow(0, 100, '%d%%')
            form.addRow(label, self.sliders[name])
        inner.addLayout(form)
        inner.addWidget(hint('Stream levels are USB mix levels; capture/listening confirmation remains pending.'))
        box.addWidget(frame)
        box.addStretch(1)
        self.stream_tab = self.tabs.addTab(page, 'Volume and balance')
        # Microphone
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        frame, inner = card('Microphone')
        form = QFormLayout()
        form.setVerticalSpacing(14)
        for name, label in [('microphone_output', 'Microphone output'), ('sidetone', 'Onboard sidetone')]:
            self.sliders[name] = SliderRow(0, 100, '%d%%')
            form.addRow(label, self.sliders[name])
        self.sidetone = self.sliders['sidetone']
        self.mic_eq = QComboBox()
        self.mic_eq.addItems(a50.MIC_EQ_NAMES)
        self.noise_gate = QComboBox()
        self.noise_gate.addItems(a50.NOISE_GATE_NAMES)
        form.addRow('Microphone EQ', self.mic_eq)
        form.addRow('Noise gate', self.noise_gate)
        inner.addLayout(form)
        test_row = QHBoxLayout()
        self.sidetone_test = QPushButton('Test sidetone')
        self.sidetone_test.setObjectName('primary')
        self.sidetone_test.setToolTip('Sets the sidetone level on the headset and shows your mic level')
        self.sidetone_test.clicked.connect(self.toggle_sidetone_test)
        test_row.addWidget(self.sidetone_test)
        self.meter = LevelMeter()
        test_row.addWidget(self.meter, 1)
        self.talking = QLabel('')
        self.talking.setObjectName('value')
        self.talking.setMinimumWidth(110)
        test_row.addWidget(self.talking)
        inner.addLayout(test_row)
        inner.addWidget(hint('Test sidetone writes the level above to the headset (working setting only, nothing '
                             'is saved) and shows a live meter of the A50 mic. Leave it running and move the '
                             'slider to hear the change as you talk.'))
        inner.addWidget(hint('Changes here stay in the editor until you press “Write working settings”. Only the sidetone '
                             'test writes on its own. Listening and recording confirmation remain pending.'))
        box.addWidget(frame)
        box.addStretch(1)
        self.mic_tab = self.tabs.addTab(page, 'Microphone')
        # Dock
        page = QWidget()
        box = QVBoxLayout(page)
        box.setContentsMargins(0, 0, 0, 0)
        frame, inner = card('Dock')
        form = QFormLayout()
        self.brightness = SliderRow(20, 70, '%d')
        form.addRow('Dock brightness', self.brightness)
        inner.addLayout(form)
        box.addWidget(frame)
        box.addStretch(1)
        self.tabs.addTab(page, 'Dock')
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        self.tabs.addTab(self.details, 'Device / audio')
        self.notice = QLabel('Working writes are read back and backed up. Save to headset persists all working settings.')
        self.notice.setObjectName('hint')
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
        self.sidetone_test.setEnabled(self.testing or not self.busy and self.connected and not self.offline
                                      and self.document is not None and self.document['schema'] == 'astro-a50-gen3-v2')
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
        self.pending = None
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
        for name, row in self.sliders.items():
            if name.startswith('stream_'):
                row.setEnabled(full)
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

    def toggle_sidetone_test(self):
        if self.testing:
            self.stop_sidetone_test()
            return
        source = self.mic_source()
        if not source:
            self.notice.setText('Test sidetone: no A50 microphone source found in PipeWire/PulseAudio; '
                                'sidetone is still written but no meter is available.')
        else:
            self.capture = QProcess(self)
            self.capture.readyReadStandardOutput.connect(self.capture_ready)
            self.capture.errorOccurred.connect(lambda _e: self.stop_sidetone_test(
                'Test sidetone: could not start parec (is pulseaudio-utils/pipewire-pulse installed?).'))
            self.capture.start('parec', ['--device=' + source, '--format=s16le', '--rate=16000',
                                         '--channels=1', '--latency-msec=40'])
        self.testing = True
        self.sidetone_test.setText('Stop test')
        self.sidetone.valueChanged.connect(self.sidetone_edited)
        self.mic_eq.currentIndexChanged.connect(self.sidetone_edited)
        self.noise_gate.currentIndexChanged.connect(self.sidetone_edited)
        self.apply_sidetone()

    @staticmethod
    def mic_source():
        try:
            sources = json.loads(subprocess.run(['pactl', '--format=json', 'list', 'sources'], check=True,
                                                capture_output=True, text=True, timeout=5).stdout)
        except (OSError, subprocess.SubprocessError, ValueError):
            return None
        names = [x['name'] for x in sources if not x['name'].endswith('.monitor')]
        for name in names:
            if name == 'A50_Mic':
                return name
        return next((n for n in names if 'Astro' in n or 'A50' in n), None)

    def capture_ready(self):
        peak = pcm_peak(bytes(self.capture.readAllStandardOutput()))
        self.meter.push(peak)
        self.talking.setText('● Talking' if peak > 0.02 else '')
        self.talking.setStyleSheet('color: #3ecf8e;' if peak > 0.02 else '')

    def stop_sidetone_test(self, message=None):
        if self.capture is not None:
            capture, self.capture = self.capture, None
            capture.blockSignals(True)
            capture.kill()
            capture.waitForFinished(500)
            capture.deleteLater()
        if self.testing:
            self.sidetone.valueChanged.disconnect(self.sidetone_edited)
            self.mic_eq.currentIndexChanged.disconnect(self.sidetone_edited)
            self.noise_gate.currentIndexChanged.disconnect(self.sidetone_edited)
        self.testing = False
        self.sidetone_timer.stop()
        self.sidetone_test.setText('Test sidetone')
        self.meter.reset()
        self.talking.setText('')
        if message:
            self.notice.setText(message)
        self.update_enabled()

    def sidetone_edited(self, _value):
        self.sidetone_timer.start()

    def apply_sidetone(self):
        if not self.testing:
            return
        if self.busy or not self.connected:
            self.sidetone_timer.start()
            return
        level = self.sidetone.value()
        self.pending = self.draft()
        target = copy.deepcopy(self.document)
        target['sliders']['sidetone']['working'] = level
        target['microphone']['eq'] = self.mic_eq.currentIndex()
        target['microphone']['noise_gate']['working'] = a50.NOISE_GATE_PACKETS[self.noise_gate.currentIndex()].hex()
        self.apply(target, 'Test running: sidetone %d%%, mic EQ %s, noise gate %s written (nothing saved). Talk to hear it.'
                   % (level, self.mic_eq.currentText(), self.noise_gate.currentText()))

    def apply(self, target=None, message=None):
        self.done_message = message
        target = target or self.draft()
        displayed = copy.deepcopy(self.document)
        def action(client, before):
            if not a50.same_settings(before, displayed):
                raise a50.EqReadError('Settings changed since refresh; refresh before writing.')
            a50.restore_working(client, target)
        self.run(lambda: a50.change_with_backup(action), self.changed)

    def changed(self, result):
        document, directory = result
        pending, self.pending = self.pending, None
        self.populate(document)
        if pending is not None:
            # Keep the other unwritten editor edits; they still need "Write working settings".
            baseline = self.document
            self.populate(pending)
            self.document = baseline
        self.notice.setText(getattr(self, 'done_message', None) or 'Readback verified. Backup and exact TX/RX: ' + directory)
        self.done_message = None

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
        self.stop_sidetone_test()
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
