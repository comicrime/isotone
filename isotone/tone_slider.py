from PyQt5.QtCore import QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget

from . import color_model

GRADIENT_STEPS = 128
SLIDER_HEIGHT = 26
SIDE_MARGIN = 8
HANDLE_WIDTH = 6


class ToneSlider(QWidget):
    tonePicked = pyqtSignal(float)

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state
        self._gradient = None
        self._gradient_key = None
        self.setFixedHeight(SLIDER_HEIGHT)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def _track_rect(self):
        return QRectF(SIDE_MARGIN, 3, max(1, self.width() - SIDE_MARGIN * 2), self.height() - 6)

    def _gradient_image(self):
        key = (self._state.hue, self._state.saturation)
        if self._gradient is None or self._gradient_key != key:
            pixels = bytearray()
            for step in range(GRADIENT_STEPS):
                tone = step / (GRADIENT_STEPS - 1) * color_model.MAX_TONE
                srgb = color_model.srgb_from_picker(self._state.hue, self._state.saturation, tone)
                pixels.extend(int(channel * 255.0 + 0.5) for channel in srgb)
                pixels.append(255)
            self._gradient = QImage(bytes(pixels), GRADIENT_STEPS, 1, QImage.Format_RGBA8888).copy()
            self._gradient_key = key
        return self._gradient

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        track = self._track_rect()
        painter.drawImage(track, self._gradient_image())

        handle_center = track.left() + track.width() * self._state.tone / color_model.MAX_TONE
        handle = QRectF(handle_center - HANDLE_WIDTH / 2.0, 1, HANDLE_WIDTH, self.height() - 2)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.drawRect(handle)
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawRect(handle)

    def _pick(self, position):
        track = self._track_rect()
        fraction = min(1.0, max(0.0, (position.x() - track.left()) / track.width()))
        self.tonePicked.emit(fraction * color_model.MAX_TONE)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pick(event.pos())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            self._pick(event.pos())
