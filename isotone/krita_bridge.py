from krita import ManagedColor

SRGB_PROFILE = "sRGB-elle-V2-srgbtrc.icc"
COLOR_MODEL = "RGBA"
COLOR_DEPTH = "F32"


def view_of(canvas):
    if canvas is None:
        return None
    return canvas.view()


def read_foreground_srgb(view):
    color = view.foregroundColor()
    if color is None:
        return None
    color.setColorSpace(COLOR_MODEL, COLOR_DEPTH, SRGB_PROFILE)
    red, green, blue = color.componentsOrdered()[:3]
    return tuple(min(1.0, max(0.0, channel)) for channel in (red, green, blue))


def write_foreground_srgb(view, srgb):
    color = ManagedColor(COLOR_MODEL, COLOR_DEPTH, SRGB_PROFILE)
    color.setComponents([srgb[0], srgb[1], srgb[2], 1.0])
    view.setForeGroundColor(color)
