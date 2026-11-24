import math

from .color_model import (
    LINEAR_RGB_FROM_LMS,
    LUMINANCE_FROM_LMS,
    encode_srgb_channel,
    lms_offsets_from_ab,
    luminance_from_tone,
    max_chroma,
)

BYTES_PER_PIXEL = 4
ENCODED_BYTE_STEPS = 4096
SOLVER_STEPS = 12
SOLVER_PRECISION = 1e-6
HUE_SAMPLES = 240
HUE_SAMPLE_FIT_STEPS = 14
RIM_OVERDRAW_PIXELS = 1.5

ENCODED_BYTE_BY_LINEAR_STEP = bytes(
    int(encode_srgb_channel(step / ENCODED_BYTE_STEPS) * 255.0 + 0.5)
    for step in range(ENCODED_BYTE_STEPS + 1)
)


def disc_rows(size):
    overdrawn_radius = 1.0 + RIM_OVERDRAW_PIXELS * 2.0 / size
    rows = []
    for row in range(size):
        y = 1.0 - (row + 0.5) / size * 2.0
        cells = []
        for column in range(size):
            x = (column + 0.5) / size * 2.0 - 1.0
            radius = math.hypot(x, y)
            if radius > overdrawn_radius:
                continue
            hue = math.atan2(y, x)
            hue_position = (hue % math.tau) / math.tau * HUE_SAMPLES
            hue_sample = min(HUE_SAMPLES - 1, int(hue_position))
            byte_index = (row * size + column) * BYTES_PER_PIXEL
            cells.append(
                (
                    byte_index,
                    min(1.0, radius),
                    hue_sample,
                    hue_position - hue_sample,
                    *lms_offsets_from_ab(math.cos(hue), math.sin(hue)),
                )
            )
        rows.append(cells)
    return rows


def max_chroma_by_hue_sample(tone):
    samples = [
        max_chroma(sample * math.tau / HUE_SAMPLES, tone, HUE_SAMPLE_FIT_STEPS)
        for sample in range(HUE_SAMPLES)
    ]
    samples.append(samples[0])
    return samples


def render_disc(size, rows, tone):
    pixels = bytearray(size * size * BYTES_PER_PIXEL)
    luminance = luminance_from_tone(tone)
    neutral_lightness = luminance ** (1.0 / 3.0)
    chroma_by_sample = max_chroma_by_hue_sample(tone)
    weight_l, weight_m, weight_s = LUMINANCE_FROM_LMS
    (red_l, red_m, red_s), (green_l, green_m, green_s), (blue_l, blue_m, blue_s) = (
        LINEAR_RGB_FROM_LMS
    )
    byte_by_step = ENCODED_BYTE_BY_LINEAR_STEP
    steps = ENCODED_BYTE_STEPS

    for cells in rows:
        lightness = neutral_lightness
        for byte_index, saturation, hue_sample, hue_blend, unit_l, unit_m, unit_s in cells:
            lower_chroma = chroma_by_sample[hue_sample]
            chroma = saturation * (
                lower_chroma + (chroma_by_sample[hue_sample + 1] - lower_chroma) * hue_blend
            )
            offset_l = chroma * unit_l
            offset_m = chroma * unit_m
            offset_s = chroma * unit_s
            solved = False
            for _ in range(SOLVER_STEPS):
                root_l = lightness + offset_l
                root_m = lightness + offset_m
                root_s = lightness + offset_s
                square_l = root_l * root_l
                square_m = root_m * root_m
                square_s = root_s * root_s
                error = (
                    weight_l * square_l * root_l
                    + weight_m * square_m * root_m
                    + weight_s * square_s * root_s
                    - luminance
                )
                if -SOLVER_PRECISION < error < SOLVER_PRECISION:
                    solved = True
                    break
                slope = 3.0 * (weight_l * square_l + weight_m * square_m + weight_s * square_s)
                if slope <= 0.0:
                    break
                lightness -= error / slope

            if solved:
                cone_l = square_l * root_l
                cone_m = square_m * root_m
                cone_s = square_s * root_s
                red = red_l * cone_l + red_m * cone_m + red_s * cone_s
                green = green_l * cone_l + green_m * cone_m + green_s * cone_s
                blue = blue_l * cone_l + blue_m * cone_m + blue_s * cone_s
            else:
                lightness = neutral_lightness
                red = green = blue = luminance

            pixels[byte_index] = byte_by_step[int(min(1.0, max(0.0, red)) * steps)]
            pixels[byte_index + 1] = byte_by_step[int(min(1.0, max(0.0, green)) * steps)]
            pixels[byte_index + 2] = byte_by_step[int(min(1.0, max(0.0, blue)) * steps)]
            pixels[byte_index + 3] = 255
    return pixels
