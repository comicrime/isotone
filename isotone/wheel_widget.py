import math

from PyQt5.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QSizePolicy, QWidget

from . import wheel_raster

RASTER_SIZE = 192
DISC_MARGIN = 8
MARKER_RADIUS = 6
MINIMUM_SIDE = 120


class WheelWidget(QWidget):
    huePicked = pyqtSignal(float, float)

    def __init__(self, state, parent=None):
        super().__init__(parent)
        self._state = state
        self._disc_rows = wheel_raster.disc_rows(RASTER_SIZE)
        self._image = None
        self._image_tone = None
        self._dragging = False
        self.setMinimumSize(MINIMUM_SIDE, MINIMUM_SIDE)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _disc_rect(self):
        side = max(1, min(self.width(), self.height()) - DISC_MARGIN * 2)
        return QRectF((self.width() - side) / 2.0, (self.height() - side) / 2.0, side, side)

    def _disc_image(self):
        if self._image is None or self._image_tone != self._state.tone:
            pixels = wheel_raster.render_disc(RASTER_SIZE, self._disc_rows, self._state.tone)
            self._image = QImage(
                bytes(pixels), RASTER_SIZE, RASTER_SIZE, QImage.Format_RGBA8888
            ).copy()
            self._image_tone = self._state.tone
        return self._image

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        disc = self._disc_rect()

        outline = QPainterPath()
        outline.addEllipse(disc)
        painter.setClipPath(outline)
        painter.drawImage(disc, self._disc_image())
        painter.setClipping(False)

        radius = disc.width() / 2.0 * self._state.saturation
        marker = QPointF(
            disc.center().x() + radius * math.cos(self._state.hue),
            disc.center().y() - radius * math.sin(self._state.hue),
        )
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor(0, 0, 0), 3))
        painter.drawEllipse(marker, MARKER_RADIUS, MARKER_RADIUS)
        painter.setPen(QPen(QColor(255, 255, 255), 1.5))
        painter.drawEllipse(marker, MARKER_RADIUS, MARKER_RADIUS)

    def _disc_offset(self, position):
        disc = self._disc_rect()
        return (
            position.x() - disc.center().x(),
            disc.center().y() - position.y(),
            disc.width() / 2.0,
        )

    def _is_on_disc(self, position):
        horizontal, vertical, radius = self._disc_offset(position)
        return math.hypot(horizontal, vertical) <= radius + MARKER_RADIUS

    def _pick(self, position):
        horizontal, vertical, radius = self._disc_offset(position)
        saturation = min(1.0, math.hypot(horizontal, vertical) / radius)
        hue = math.atan2(vertical, horizontal) if saturation > 0.0 else self._state.hue
        self.huePicked.emit(hue, saturation)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._is_on_disc(event.pos()):
            self._dragging = True
            self._pick(event.pos())

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.LeftButton:
            self._pick(event.pos())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._dragging = False
