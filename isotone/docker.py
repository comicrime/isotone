from krita import DockWidget, DockWidgetFactory, DockWidgetFactoryBase, Krita
from PyQt5.QtCore import QTimer

from . import krita_bridge
from .picker_panel import PickerPanel

DOCKER_ID = "isotone"
DOCKER_TITLE = "Isotone"
FOREGROUND_POLL_MILLISECONDS = 150
SAME_COLOR_TOLERANCE = 0.004


class IsotoneDocker(DockWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(DOCKER_TITLE)
        self._panel = PickerPanel(self)
        self.setWidget(self._panel)
        self._known_srgb = None
        self._has_unsent_pick = False

        self._panel.colorPicked.connect(self._push_to_krita)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(FOREGROUND_POLL_MILLISECONDS)
        self._poll_timer.timeout.connect(self._pull_from_krita)
        self._poll_timer.start()

    def canvasChanged(self, canvas):
        self._pull_from_krita()

    def _push_to_krita(self):
        view = krita_bridge.view_of(self.canvas())
        if view is None:
            self._has_unsent_pick = True
            return
        srgb = self._panel.state.srgb()
        krita_bridge.write_foreground_srgb(view, srgb)
        self._known_srgb = srgb
        self._has_unsent_pick = False

    def _pull_from_krita(self):
        if not self.isVisible():
            return
        view = krita_bridge.view_of(self.canvas())
        if view is None:
            return
        if self._has_unsent_pick:
            self._push_to_krita()
            return
        srgb = krita_bridge.read_foreground_srgb(view)
        if srgb is None or self._is_known(srgb):
            return
        self._known_srgb = srgb
        self._panel.state.adopt_srgb(srgb)
        self._panel.refresh()

    def _is_known(self, srgb):
        if self._known_srgb is None:
            return False
        return all(
            abs(channel - known) <= SAME_COLOR_TOLERANCE
            for channel, known in zip(srgb, self._known_srgb, strict=True)
        )


def register_docker():
    Krita.instance().addDockWidgetFactory(
        DockWidgetFactory(DOCKER_ID, DockWidgetFactoryBase.DockRight, IsotoneDocker)
    )
