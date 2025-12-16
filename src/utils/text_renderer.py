from PySide6.QtGui import QImage, QPixmap, QColor
import os


class TextRenderer:
    def __init__(self, skin_data):
        self.skin_data = skin_data
        self.text_bmp_path = os.path.join(self.skin_data.extracted_skin_dir, "TEXT.BMP")
        self.text_bmp_image = None
        self.glyph_cache = {}  # Cache for individual glyph QPixmaps

        self.glyph_spec = self.skin_data.spec_json["sheets"]["text.bmp"]["glyph_grid"]

        # Parse transparent_color from spec (e.g., "#FF00FF" to (255, 0, 255))
        transparent_color_hex = self.glyph_spec.get("transparent_color", "#FF00FF")
        transparent_color_hex = transparent_color_hex.lstrip("#")
        self.transparent_color_rgb = tuple(
            int(transparent_color_hex[i : i + 2], 16) for i in (0, 2, 4)
        )

        # Load the image first to determine how many sections it has
        self._load_text_bmp()

        # Determine if text.bmp has 1 section (3 lines) or 4 sections (12 lines)
        if self.text_bmp_image:
            self.image_height = self.text_bmp_image.height()
            glyph_height = 6  # Fixed height per spec
            single_section_height = glyph_height * 3  # 3 lines per section

            # Check if the image height indicates 4 sections (with separators) or 1 section
            # Default skin: 4 sections with 2px separator after first section = 4*18 + 2 = 74px
            # Non-default skin: 1 section = 18px
            if (
                self.image_height >= single_section_height * 4 + 2
            ):  # At least 74px for 4 sections + separators
                self.num_bands = 4
            elif self.image_height >= single_section_height * 3:
                self.num_bands = 3
            elif self.image_height >= single_section_height * 2:
                self.num_bands = 2
            else:
                self.num_bands = 1
        else:
            # Default to 4 bands if image is not loaded
            self.num_bands = 4
            self.image_height = 74

        # Create a mapping for character coordinates for each band
        # If there's only 1 band, all bands will use the same coordinates (from first band)
        self.char_to_coords = {}
        glyph_width = 4  # User-provided insight
        self.glyph_height = 6  # Revert to hardcoded 6
        cell_spacing = 1
        band_height_for_glyphs = self.glyph_height * 3  # 3 rows per band
        band_separator_offset = 2  # Single 2-pixel separator after band 1

        logical_lines = [
            'ABCDEFGHIJKLMNOPQRSTUVWXYZ"@',
            "0123456789….:()-'!_+\\/[]^&%,=$",
            "ÅÖÄ?* ",
        ]

        # Create a character mapping for the first band
        first_band_coords = {}
        for line_idx, line_content in enumerate(logical_lines):
            current_x_offset = 0  # Reset X for each new line

            # Calculate the Y position for the current line within the first band
            line_y = line_idx * self.glyph_height

            for char_idx, char in enumerate(line_content):
                # Calculate the X position for the current character
                char_x = current_x_offset

                first_band_coords[char] = {
                    "x": char_x,
                    "y": line_y,
                    "w": glyph_width,
                    "h": self.glyph_height,
                }
                current_x_offset += glyph_width + cell_spacing

        # Now map each character to all bands, either with proper band coordinates or using the first band
        for char in first_band_coords:
            self.char_to_coords[char] = {}

            if self.num_bands == 1:
                # If there's only 1 band, all bands use the same coordinates (from first band)
                for band_idx in range(
                    4
                ):  # We still support up to 4 bands for API compatibility
                    self.char_to_coords[char][band_idx] = first_band_coords[char].copy()
            else:
                # If there are multiple bands, calculate coordinates for each
                for band_idx in range(self.num_bands):
                    # Apply the single 2-pixel separator offset for bands 2 and 3 (when they exist)
                    band_y_start = band_idx * band_height_for_glyphs
                    if band_idx >= 2:
                        band_y_start += band_separator_offset

                    # Calculate the Y position for the character in this band
                    # Get the line index from the first band coordinates (0, 1, or 2)
                    line_idx_in_first_band = (
                        first_band_coords[char]["y"] // self.glyph_height
                    )
                    line_y_in_band = band_y_start + (
                        line_idx_in_first_band * self.glyph_height
                    )

                    self.char_to_coords[char][band_idx] = {
                        "x": first_band_coords[char]["x"],
                        "y": line_y_in_band,
                        "w": first_band_coords[char]["w"],
                        "h": first_band_coords[char]["h"],
                    }

                # For bands beyond what's available in the image, fallback to first band
                for band_idx in range(self.num_bands, 4):
                    self.char_to_coords[char][band_idx] = first_band_coords[char].copy()

    def _load_text_bmp(self):
        """
        Loads TEXT.BMP and converts it to an RGBA PIL Image.
        """
        if not os.path.exists(self.text_bmp_path):
            print(f"WARNING: TEXT.BMP not found at {self.text_bmp_path}")
            return

        try:
            self.text_bmp_image = QImage(self.text_bmp_path)
            if self.text_bmp_image.isNull():
                raise Exception("QImage failed to load TEXT.BMP")
        except Exception as e:
            print(f"ERROR: Failed to load TEXT.BMP with QImage: {e}")
            self.text_bmp_image = None

    def get_glyph_pixmap(self, char_code, band=0):
        """
        Retrieves the QPixmap for a given character code from TEXT.BMP, for a specific band.
        Caches the glyph pixmaps for performance.
        """
        cache_key = (char_code, band)
        if cache_key in self.glyph_cache:
            return self.glyph_cache[cache_key]

        if self.text_bmp_image is None:
            return QPixmap()  # Return empty pixmap if TEXT.BMP failed to load

        # Get glyph coordinates for the specific character and band
        char_coords = self.char_to_coords.get(char_code)
        if char_coords is None:
            print(
                f"WARNING: Character '{char_code}' not found in char_to_coords mapping. Returning empty pixmap."
            )
            return QPixmap()

        # Get coordinates for the requested band, fallback to band 0 if band not available
        if band in char_coords:
            coords = char_coords[band]
        else:
            coords = char_coords[0]  # fallback to first band

        sheet_x = coords["x"]
        sheet_y = coords["y"]
        glyph_width = coords["w"]
        glyph_height = coords["h"]

        # Special handling for space character: return an entirely transparent pixmap
        if char_code == " ":
            transparent_image = QImage(
                glyph_width, glyph_height, QImage.Format_RGBA8888
            )
            transparent_image.fill(QColor(0, 0, 0, 0))  # Fill with transparent black
            pixmap = QPixmap.fromImage(transparent_image)
            self.glyph_cache[cache_key] = pixmap
            return pixmap

        # Ensure the glyph coordinates are within the bounds of text_bmp_image
        if (
            sheet_x + glyph_width > self.text_bmp_image.width()
            or sheet_y + glyph_height > self.text_bmp_image.height()
        ):
            print(
                f"WARNING: Glyph coordinates for char_code '{char_code}' (band {band}) out of bounds. Returning empty pixmap."
            )
            return QPixmap()

        # Crop the QImage directly
        cropped_q_image = self.text_bmp_image.copy(
            sheet_x, sheet_y, glyph_width, glyph_height
        )
        # Convert the cropped image to a 32-bit format to allow direct pixel manipulation
        cropped_q_image = cropped_q_image.convertToFormat(QImage.Format_RGBA8888)

        if cropped_q_image.isNull():
            print(
                f"ERROR: QImage failed to convert format for char_code {char_code} (band {band})"
            )
            return QPixmap()

        # Apply transparency using the top-left pixel key color
        # Get the top-left pixel color from the full TEXT.BMP image
        if self.text_bmp_image and not self.text_bmp_image.isNull():
            top_left_pixel_color = self.text_bmp_image.pixelColor(0, 0)
            transparency_rgb = (
                top_left_pixel_color.red(),
                top_left_pixel_color.green(),
                top_left_pixel_color.blue(),
            )
        else:
            # Fallback to magenta if image not loaded or top-left pixel not available
            transparency_rgb = self.transparent_color_rgb

        for i in range(cropped_q_image.width()):
            for j in range(cropped_q_image.height()):
                pixel_color = cropped_q_image.pixelColor(i, j)
                if (
                    pixel_color.red(),
                    pixel_color.green(),
                    pixel_color.blue(),
                ) == transparency_rgb:
                    cropped_q_image.setPixelColor(
                        i, j, QColor(0, 0, 0, 0)
                    )  # Set to transparent

        pixmap = QPixmap.fromImage(cropped_q_image)
        self.glyph_cache[cache_key] = pixmap
        return pixmap

    def render_text(self, painter, text, start_x, start_y):
        """
        Renders a string of text using the glyphs from TEXT.BMP.
        """
        current_x = start_x
        for char_code in text:
            # Convert character to uppercase as TEXT.BMP only contains uppercase glyphs
            upper_char_code = char_code.upper()
            glyph_pixmap = self.get_glyph_pixmap(
                upper_char_code, band=0
            )  # Pass band=0 for now
            if not glyph_pixmap.isNull():
                painter.drawPixmap(current_x, start_y, glyph_pixmap)
                # Horizontal advance per char is fixed at 5 px (glyph_width + cell_spacing)
                current_x += 5

    def draw_number(self, painter, number_str, start_x, start_y):
        """
        Renders a number string using the glyphs from TEXT.BMP.
        This method handles digits and special characters for number display.
        """
        current_x = start_x
        for char in number_str:
            # For numbers, we'll use the digit characters directly
            glyph_pixmap = self.get_glyph_pixmap(char, band=0)
            if not glyph_pixmap.isNull():
                painter.drawPixmap(current_x, start_y, glyph_pixmap)
                # Horizontal advance per char is fixed at 5 px (glyph_width + cell_spacing)
                current_x += 5
