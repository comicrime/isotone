import math

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from .picker_state import PickerState
from .tone_slider import ToneSlider
from .wheel_widget import WheelWidget


class PickerPanel(QWidget):
    colorPicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = PickerState()
        self._wheel = WheelWidget(self.state, self)
        self._slider = ToneSlider(self.state, self)
        self._readout = QLabel(self)
        self._readout.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._wheel, 1)
        layout.addWidget(self._slider)
        layout.addWidget(self._readout)

        self._wheel.huePicked.connect(self._on_hue_picked)
        self._slider.tonePicked.connect(self._on_tone_picked)
        self.refresh()

    def refresh(self):
        hue_degrees = math.degrees(self.state.hue) % 360.0
        self._readout.setText(
            f"Tone {self.state.tone:.0f}   "
            f"Saturation {self.state.saturation * 100.0:.0f}%   "
            f"Hue {hue_degrees:.0f}°"
        )
        self._wheel.update()
        self._slider.update()

    def _on_hue_picked(self, hue, saturation):
        self.state.hue = hue
        self.state.saturation = saturation
        self.refresh()
        self.colorPicked.emit()

    def _on_tone_picked(self, tone):
        self.state.tone = tone
        self.refresh()
        self.colorPicked.emit()
