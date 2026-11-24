from . import color_model


class PickerState:
    def __init__(self):
        self.hue = 0.0
        self.saturation = 0.0
        self.tone = 50.0

    def srgb(self):
        return color_model.srgb_from_picker(self.hue, self.saturation, self.tone)

    def adopt_srgb(self, srgb):
        hue, saturation, tone = color_model.picker_from_srgb(srgb)
        if saturation > 0.0:
            self.hue = hue
        self.saturation = saturation
        self.tone = tone
