import pytest
from src.utils.color import hex_to_rgb, rgb_to_hex, MAGENTA_TRANSPARENCY_RGB


class TestHexToRgb:
    def test_with_hash(self):
        assert hex_to_rgb("#FF00FF") == (255, 0, 255)

    def test_without_hash(self):
        assert hex_to_rgb("FF00FF") == (255, 0, 255)

    def test_lowercase(self):
        assert hex_to_rgb("#ff00ff") == (255, 0, 255)

    def test_black(self):
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_white(self):
        assert hex_to_rgb("#FFFFFF") == (255, 255, 255)


class TestRgbToHex:
    def test_magenta(self):
        assert rgb_to_hex((255, 0, 255)) == "#ff00ff"

    def test_black(self):
        assert rgb_to_hex((0, 0, 0)) == "#000000"

    def test_white(self):
        assert rgb_to_hex((255, 255, 255)) == "#ffffff"

    def test_roundtrip(self):
        original = (128, 64, 32)
        assert hex_to_rgb(rgb_to_hex(original)) == original


class TestConstants:
    def test_magenta_transparency(self):
        assert MAGENTA_TRANSPARENCY_RGB == (255, 0, 255)
