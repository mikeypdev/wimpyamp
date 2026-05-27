from collections import OrderedDict
from PySide6.QtGui import QPixmap, QImage, QColor, QPainter
from PySide6.QtCore import Qt
from PIL import Image
import numpy as np
from ..utils.logger import get_logger

logger = get_logger(__name__)

MAX_CACHE_SIZE = 500


class SpriteManager:
    def __init__(self):
        self.cache: OrderedDict = OrderedDict()
        self.invalid_sprite_cache: set[tuple] = set()

    def load_sprite(self, image_path, x, y, w, h, transparency_color=None):
        """
        Loads a sprite from an image file, applies transparency, and caches it.
        Handles .cur files directly with QPixmap.
        """
        cache_key = (image_path, x, y, w, h, transparency_color)
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]

        if "TEXT.BMP" in image_path.upper():
            return QPixmap()

        try:
            if image_path.lower().endswith(".cur"):
                full_pixmap = QPixmap(image_path)
                if full_pixmap.isNull():
                    raise OSError(f"QPixmap failed to load .cur file: {image_path}")

                cropped_pixmap = full_pixmap.copy(x, y, w, h)

                if transparency_color:
                    q_image = cropped_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
                    mask = q_image.createMaskFromColor(
                        QColor(*transparency_color).rgb(), Qt.MaskOutColor
                    )
                    q_image.setAlphaChannel(mask)
                    pixmap = QPixmap.fromImage(q_image)
                else:
                    pixmap = cropped_pixmap
            else:
                pil_image = Image.open(image_path)
                cropped_pil_image = pil_image.crop((x, y, x + w, y + h))

                rgba_pil_image = cropped_pil_image.convert("RGBA")

                q_image = QImage(
                    rgba_pil_image.tobytes("raw", "RGBA"),
                    rgba_pil_image.width,
                    rgba_pil_image.height,
                    QImage.Format_RGBA8888,
                )

                if q_image.isNull():
                    raise OSError(
                        f"QImage failed to load from PIL Image for {image_path}"
                    )

                if transparency_color:
                    arr = np.array(rgba_pil_image)
                    r, g, b = transparency_color
                    match = (arr[:, :, 0] == r) & (arr[:, :, 1] == g) & (arr[:, :, 2] == b)
                    arr[match, 3] = 0
                    rgba_pil_image = Image.fromarray(arr, "RGBA")

                    q_image = QImage(
                        rgba_pil_image.tobytes("raw", "RGBA"),
                        rgba_pil_image.width,
                        rgba_pil_image.height,
                        QImage.Format_RGBA8888,
                    )
                    q_image = q_image.convertToFormat(QImage.Format_ARGB32)

                pixmap = QPixmap(q_image.size())
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                painter.drawImage(0, 0, q_image)
                painter.end()

            self.cache[cache_key] = pixmap
            self._evict_if_needed()
            return pixmap
        except (OSError, ValueError, RuntimeError) as e:
            logger.error(f"Error loading sprite from {image_path}: {e}")
            return QPixmap()

    def _evict_if_needed(self):
        while len(self.cache) > MAX_CACHE_SIZE:
            self.cache.popitem(last=False)

    def clear_cache(self):
        self.cache.clear()
        self.invalid_sprite_cache.clear()
