"""
Utility for validating if sprites exist in skin files.
This helps handle custom skins that may omit certain sprites.
"""

from PIL import Image
import os


def validate_sprite_in_bmp(bmp_path, x, y, w, h):
    """
    Validates that a sprite exists within the bounds of a BMP file.

    Args:
        bmp_path: Path to the BMP file
        x, y: Coordinates of the sprite
        w, h: Width and height of the sprite

    Returns:
        bool: True if sprite coordinates are within the image bounds, False otherwise
    """
    if not os.path.exists(bmp_path):
        return False

    try:
        with Image.open(bmp_path) as img:
            img_width, img_height = img.size
            # Check if the sprite coordinates are within bounds
            return (x + w <= img_width) and (y + h <= img_height)
    except Exception:
        # If we can't open the image, assume the sprite doesn't exist
        return False


def get_available_sprites_from_sheet(sheet_path, spec_sprites):
    """
    Scans a sprite sheet to determine which sprites from the spec are actually available.

    Args:
        sheet_path: Path to the sprite sheet BMP file
        spec_sprites: Dictionary of sprite definitions from the spec

    Returns:
        dict: Dictionary of available sprites
    """
    if not os.path.exists(sheet_path):
        return {}

    try:
        with Image.open(sheet_path) as img:
            img_width, img_height = img.size

        available_sprites = {}
        for sprite_id, sprite_def in spec_sprites.items():
            x = sprite_def.get("x", 0)
            y = sprite_def.get("y", 0)
            w = sprite_def.get("w", 0)
            h = sprite_def.get("h", 0)

            if validate_sprite_in_bmp(sheet_path, x, y, w, h):
                available_sprites[sprite_id] = sprite_def

        return available_sprites
    except Exception:
        # If we can't process the image, return an empty dict
        return {}
