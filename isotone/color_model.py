import math

MAX_CHROMA = 0.33
MAX_TONE = 100.0
GAMUT_TOLERANCE = 1e-4
ACHROMATIC_CHROMA = 1e-4

LMS_ROOT_FROM_AB = (
    (0.3963377774, 0.2158037573),
    (-0.1055613458, -0.0638541728),
    (-0.0894841775, -1.2914855480),
)

LINEAR_RGB_FROM_LMS = (
    (4.0767416621, -3.3077115913, 0.2309699292),
    (-1.2684380046, 2.6097574011, -0.3413193965),
    (-0.0041960863, -0.7034186147, 1.7076147010),
)

LMS_FROM_LINEAR_RGB = (
    (0.4122214708, 0.5363325363, 0.0514459929),
    (0.2119034982, 0.6806995451, 0.1073969566),
    (0.0883024619, 0.2817188376, 0.6299787005),
)

OKLAB_A_FROM_LMS_ROOT = (1.9779984951, -2.4285922050, 0.4505937099)
OKLAB_B_FROM_LMS_ROOT = (0.0259040371, 0.7827717662, -0.8086757660)

ICC_LUMINANCE_FROM_LINEAR_RGB = (0.2225045, 0.7168786, 0.0606169)

LUMINANCE_FROM_LMS = tuple(
    sum(
        weight * row[column]
        for weight, row in zip(ICC_LUMINANCE_FROM_LINEAR_RGB, LINEAR_RGB_FROM_LMS, strict=True)
    )
    for column in range(3)
)

CIE_EPSILON = 216.0 / 24389.0
CIE_KAPPA = 24389.0 / 27.0

LIGHTNESS_SOLVER_STEPS = 24
LIGHTNESS_SOLVER_PRECISION = 1e-9
CHROMA_FIT_STEPS = 20


def luminance_from_tone(tone):
    if tone > CIE_KAPPA * CIE_EPSILON:
        return ((tone + 16.0) / 116.0) ** 3
    return tone / CIE_KAPPA


def tone_from_luminance(luminance):
    if luminance > CIE_EPSILON:
        return 116.0 * luminance ** (1.0 / 3.0) - 16.0
    return luminance * CIE_KAPPA


def lms_offsets_from_ab(a, b):
    return tuple(from_a * a + from_b * b for from_a, from_b in LMS_ROOT_FROM_AB)


def lms_offsets_from_hue_chroma(hue, chroma):
    return lms_offsets_from_ab(chroma * math.cos(hue), chroma * math.sin(hue))


def lightness_for_luminance(lms_offsets, luminance):
    weight_l, weight_m, weight_s = LUMINANCE_FROM_LMS
    offset_l, offset_m, offset_s = lms_offsets
    lightness = luminance ** (1.0 / 3.0)
    for _ in range(LIGHTNESS_SOLVER_STEPS):
        root_l = lightness + offset_l
        root_m = lightness + offset_m
        root_s = lightness + offset_s
        error = weight_l * root_l**3 + weight_m * root_m**3 + weight_s * root_s**3 - luminance
        if abs(error) < LIGHTNESS_SOLVER_PRECISION:
            return lightness
        slope = 3.0 * (
            weight_l * root_l * root_l + weight_m * root_m * root_m + weight_s * root_s * root_s
        )
        if slope <= 0.0:
            return None
        lightness -= error / slope
    return None


def linear_rgb_from_lightness(lms_offsets, lightness):
    lms = tuple((lightness + offset) ** 3 for offset in lms_offsets)
    return tuple(
        sum(weight * value for weight, value in zip(row, lms, strict=True))
        for row in LINEAR_RGB_FROM_LMS
    )


def is_in_gamut(linear_rgb):
    return all(-GAMUT_TOLERANCE <= channel <= 1.0 + GAMUT_TOLERANCE for channel in linear_rgb)


def linear_rgb_at(hue, chroma, tone):
    offsets = lms_offsets_from_hue_chroma(hue, chroma)
    lightness = lightness_for_luminance(offsets, luminance_from_tone(tone))
    if lightness is None:
        return None
    linear_rgb = linear_rgb_from_lightness(offsets, lightness)
    return linear_rgb if is_in_gamut(linear_rgb) else None


def max_chroma(hue, tone, steps=CHROMA_FIT_STEPS):
    reachable = 0.0
    unreachable = MAX_CHROMA
    if linear_rgb_at(hue, unreachable, tone) is not None:
        return unreachable
    for _ in range(steps):
        candidate = (reachable + unreachable) / 2.0
        if linear_rgb_at(hue, candidate, tone) is None:
            unreachable = candidate
        else:
            reachable = candidate
    return reachable


def encode_srgb_channel(linear):
    linear = min(1.0, max(0.0, linear))
    if linear <= 0.0031308:
        return 12.92 * linear
    return 1.055 * linear ** (1.0 / 2.4) - 0.055


def decode_srgb_channel(encoded):
    encoded = min(1.0, max(0.0, encoded))
    if encoded <= 0.04045:
        return encoded / 12.92
    return ((encoded + 0.055) / 1.055) ** 2.4


def srgb_from_picker(hue, saturation, tone):
    linear_rgb = linear_rgb_at(hue, saturation * max_chroma(hue, tone), tone)
    if linear_rgb is None:
        linear_rgb = (luminance_from_tone(tone),) * 3
    return tuple(encode_srgb_channel(channel) for channel in linear_rgb)


def picker_from_srgb(srgb):
    linear_rgb = tuple(decode_srgb_channel(channel) for channel in srgb)
    lms_root = tuple(
        sum(weight * channel for weight, channel in zip(row, linear_rgb, strict=True))
        ** (1.0 / 3.0)
        for row in LMS_FROM_LINEAR_RGB
    )
    a = sum(weight * root for weight, root in zip(OKLAB_A_FROM_LMS_ROOT, lms_root, strict=True))
    b = sum(weight * root for weight, root in zip(OKLAB_B_FROM_LMS_ROOT, lms_root, strict=True))
    luminance = sum(
        weight * channel
        for weight, channel in zip(ICC_LUMINANCE_FROM_LINEAR_RGB, linear_rgb, strict=True)
    )
    hue = math.atan2(b, a)
    chroma = math.hypot(a, b)
    tone = min(MAX_TONE, tone_from_luminance(luminance))
    if chroma <= ACHROMATIC_CHROMA:
        return hue, 0.0, tone
    reachable_chroma = max_chroma(hue, tone)
    if reachable_chroma <= chroma:
        return hue, 1.0, tone
    return hue, chroma / reachable_chroma, tone
