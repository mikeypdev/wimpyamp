# src/utils/color.py


def hex_to_rgb(hex_color):
    """Converts a hex color string (e.g., '#RRGGBB') to an RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb_color):
    """Converts an RGB tuple to a hex color string."""
    return "#%02x%02x%02x" % rgb_color


# Winamp specific colors or color handling utilities can be added here
MAGENTA_TRANSPARENCY_RGB = (255, 0, 255)
MAGENTA_TRANSPARENCY_HEX = "#FF00FF"
