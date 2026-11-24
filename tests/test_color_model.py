import math
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from isotone import color_model, wheel_raster


def icc_luminance(srgb):
    return sum(
        weight * color_model.decode_srgb_channel(channel)
        for weight, channel in zip(color_model.ICC_LUMINANCE_FROM_LINEAR_RGB, srgb, strict=True)
    )


class ConstantToneTest(unittest.TestCase):
    def test_luminance_is_identical_across_hues_and_saturations(self):
        for tone in (5.0, 20.0, 50.0, 75.0, 95.0):
            expected = color_model.luminance_from_tone(tone)
            for hue_step in range(72):
                hue = math.radians(hue_step * 5)
                for saturation in (0.0, 0.3, 0.7, 1.0):
                    srgb = color_model.srgb_from_picker(hue, saturation, tone)
                    self.assertAlmostEqual(icc_luminance(srgb), expected, delta=2e-4)

    def test_tone_endpoints_are_black_and_white(self):
        for channel in color_model.srgb_from_picker(1.0, 1.0, 0.0):
            self.assertAlmostEqual(channel, 0.0, places=3)
        for channel in color_model.srgb_from_picker(1.0, 1.0, 100.0):
            self.assertAlmostEqual(channel, 1.0, places=3)

    def test_full_saturation_touches_the_gamut_boundary(self):
        for tone in (20.0, 50.0, 80.0):
            for hue_step in range(36):
                srgb = color_model.srgb_from_picker(math.radians(hue_step * 10), 1.0, tone)
                self.assertTrue(min(srgb) < 0.02 or max(srgb) > 0.98)


class RoundTripTest(unittest.TestCase):
    def test_picker_survives_srgb_round_trip(self):
        for tone in (15.0, 50.0, 85.0):
            for hue_step in range(12):
                hue = math.radians(hue_step * 30 - 170)
                for saturation in (0.25, 0.8):
                    srgb = color_model.srgb_from_picker(hue, saturation, tone)
                    restored_hue, restored_saturation, restored_tone = color_model.picker_from_srgb(
                        srgb
                    )
                    self.assertAlmostEqual(restored_tone, tone, delta=0.02)
                    self.assertAlmostEqual(restored_saturation, saturation, delta=0.01)
                    self.assertAlmostEqual(math.cos(restored_hue - hue), 1.0, delta=1e-3)

    def test_primaries_convert_to_expected_picker_values(self):
        _, white_saturation, white_tone = color_model.picker_from_srgb((1.0, 1.0, 1.0))
        self.assertAlmostEqual(white_tone, 100.0, delta=0.01)
        self.assertEqual(white_saturation, 0.0)
        _, blue_saturation, blue_tone = color_model.picker_from_srgb((0.0, 0.0, 1.0))
        _, _, yellow_tone = color_model.picker_from_srgb((1.0, 1.0, 0.0))
        self.assertLess(blue_tone, 35.0)
        self.assertGreater(yellow_tone, 95.0)
        self.assertGreater(blue_saturation, 0.99)


class WheelRasterTest(unittest.TestCase):
    def test_disc_is_filled_with_the_requested_tone(self):
        size = 64
        rows = wheel_raster.disc_rows(size)
        cell_count = sum(len(cells) for cells in rows)
        for tone in (10.0, 25.0, 60.0, 90.0):
            pixels = wheel_raster.render_disc(size, rows, tone)
            opaque = 0
            for index in range(0, len(pixels), 4):
                if pixels[index + 3] == 0:
                    continue
                opaque += 1
                srgb = tuple(pixels[index + offset] / 255.0 for offset in range(3))
                _, _, pixel_tone = color_model.picker_from_srgb(srgb)
                self.assertAlmostEqual(pixel_tone, tone, delta=0.8)
            self.assertEqual(opaque, cell_count)

    def test_render_time(self):
        for size in (128, 192):
            rows = wheel_raster.disc_rows(size)
            for tone in (15.0, 60.0):
                started = time.perf_counter()
                wheel_raster.render_disc(size, rows, tone)
                elapsed = (time.perf_counter() - started) * 1000
                print(f"render {size}px tone {tone:.0f}: {elapsed:.1f} ms")


if __name__ == "__main__":
    unittest.main()
