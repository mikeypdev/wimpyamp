from PySide6.QtGui import QPixmap, QImage, QColor, QPainter
from PySide6.QtCore import Qt
from PIL import Image


class SpriteManager:
    def __init__(self):
        self.cache = {}  # Cache for QPixmap objects

    def load_sprite(self, image_path, x, y, w, h, transparency_color=None):
        """
        Loads a sprite from an image file, applies transparency, and caches it.
        Handles .cur files directly with QPixmap.
        """
        cache_key = (image_path, x, y, w, h, transparency_color)
        if cache_key in self.cache:
            return self.cache[cache_key]

        if "TEXT.BMP" in image_path.upper():
            # TEXT.BMP is a glyph sheet, not a regular sprite. It should be handled by TextRenderer.
            # Returning an empty QPixmap to prevent errors in SpriteManager.
            return QPixmap()

        try:
            if image_path.lower().endswith(".cur"):
                # For .cur files, load directly with QPixmap
                full_pixmap = QPixmap(image_path)
                if full_pixmap.isNull():
                    raise Exception(f"QPixmap failed to load .cur file: {image_path}")

                # Crop the pixmap
                cropped_pixmap = full_pixmap.copy(x, y, w, h)

                # Apply transparency if needed (convert to QImage for pixel manipulation)
                if transparency_color:
                    q_image = cropped_pixmap.toImage()
                    for i in range(q_image.width()):
                        for j in range(q_image.height()):
                            pixel_color = q_image.pixelColor(i, j)
                            if (
                                pixel_color.red(),
                                pixel_color.green(),
                                pixel_color.blue(),
                            ) == transparency_color:
                                q_image.setPixelColor(
                                    i, j, QColor(0, 0, 0, 0)
                                )  # Set to transparent
                    pixmap = QPixmap.fromImage(q_image)
                else:
                    pixmap = cropped_pixmap
            else:
                # For other image types, use PIL
                pil_image = Image.open(image_path)
                cropped_pil_image = pil_image.crop((x, y, x + w, y + h))

                # Convert to RGBA mode for consistent transparency handling
                rgba_pil_image = cropped_pil_image.convert("RGBA")

                # Get raw RGBA data from PIL Image
                q_image = QImage(
                    rgba_pil_image.tobytes("raw", "RGBA"),
                    rgba_pil_image.width,
                    rgba_pil_image.height,
                    QImage.Format_RGBA8888,
                )

                if q_image.isNull():
                    raise Exception(
                        f"QImage failed to load from PIL Image for {image_path}"
                    )

                # Apply transparency if a color is specified
                if transparency_color:
                    for i in range(q_image.width()):
                        for j in range(q_image.height()):
                            pixel_color = q_image.pixelColor(i, j)
                            if (
                                pixel_color.red(),
                                pixel_color.green(),
                                pixel_color.blue(),
                            ) == transparency_color:
                                q_image.setPixelColor(
                                    i, j, QColor(0, 0, 0, 0)
                                )  # Set to transparent
                    # Ensure the QImage format supports alpha after pixel manipulation
                    q_image = q_image.convertToFormat(QImage.Format_ARGB32)

                # Create a QPixmap with an alpha channel and draw the QImage onto it
                pixmap = QPixmap(q_image.size())
                pixmap.fill(Qt.transparent)  # Fill with transparent color
                painter = QPainter(pixmap)
                painter.drawImage(0, 0, q_image)
                painter.end()

            self.cache[cache_key] = pixmap
            return pixmap
        except Exception as e:
            print(f"Error loading sprite from {image_path}: {e}")
            return QPixmap()  # Return an empty pixmap on error

    def clear_cache(self):
        self.cache.clear()
