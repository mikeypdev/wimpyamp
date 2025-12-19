"""
AlbumArtWindow class for WimPyAmp application.

This class implements the album art display window that can be toggled from the clutter bar.
The window follows the same docking and resizing behavior as other floating windows like
the playlist and equalizer windows.
"""

import os
from collections import OrderedDict
from PySide6.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtCore import QTimer  # For resize handle detection

from ..utils.region_utils import apply_region_mask_to_widget


class AlbumArtWindow(QWidget):
    def __init__(self, parent=None, skin_data=None, sprite_manager=None):
        super().__init__(parent)
        self.setWindowTitle("WimPyAmp Album Art")

        # Set window flags for completely borderless window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.X11BypassWindowManagerHint)

        # Set a transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.skin_data = skin_data
        self.sprite_manager = sprite_manager
        self.main_window = None  # Reference to main window for docking callbacks

        # Add docking state and related attributes
        self.is_docked = True  # Start as docked by default
        self.docking_offset = QPoint(0, 0)  # Offset from docking position when undocked
        self.dock_margin = 10  # pixels of tolerance for docking

        # Initialize window properties
        self.setMinimumSize(100, 100)  # Minimum square size

        # Current track information
        self.current_file_path = None
        self.album_art_pixmap = None

        # Set up resize handle detection
        self._resize_handle_size = (
            20  # pixels from bottom-right corner for resize detection
        )
        self._is_resizing = False
        self._resize_start_pos = None
        self._resize_start_size = None

        # Timer to handle resize detection
        self._resize_timer = QTimer()
        self._resize_timer.timeout.connect(self._check_resize_cursor)
        self._resize_timer.start(100)  # Check every 100ms

        # Set initial size to be square and match main window height (default main window height is 116)
        if parent and hasattr(parent, "height"):
            main_height = parent.height()
            self.resize(
                main_height, main_height
            )  # Square window with same height as main
        else:
            # Use the default main window height as initial size instead of 300
            # Standard Winamp main window is typically around 116 pixels high
            default_size = 116
            self.resize(
                default_size, default_size
            )  # Square window with same height as default main window

        # Add a label to display the album art
        self.album_art_label = QLabel()
        self.album_art_label.setAlignment(Qt.AlignCenter)
        self.album_art_label.setSizePolicy(self.sizePolicy())

        # Layout setup
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # No margins
        layout.addWidget(self.album_art_label)
        self.setLayout(layout)

        # Image caching system
        self._image_cache = OrderedDict()  # Use OrderedDict for LRU behavior
        self._max_cache_size = 50 * 1024 * 1024  # 50MB cache limit
        self._current_cache_size = 0

        # Track currently loading operations to limit concurrency
        self._loading_operations = set()  # Track files currently being loaded
        self._max_concurrent_loads = 2  # Maximum number of concurrent image loads

        # Apply region mask if available
        self.apply_region_mask()

        # Hide by default until toggled
        self.hide()

    def set_main_window(self, main_window):
        """Set reference to main window for docking callbacks."""
        self.main_window = main_window

    def showEvent(self, event):
        """Called when the window is shown."""
        super().showEvent(event)
        # Check if this is an initial show (before preferences are properly loaded)
        # If the window is at its default size (116x116, matching main window default height)
        # and at position (0,0), it might be an initial show that needs default positioning
        if (
            self.main_window
            and self.x() == 0
            and self.y() == 0
            and self.width() == 116
            and self.height() == 116
        ):  # Default size
            # Position the window to the right of the main window when first opened
            main_height = self.main_window.height()
            if self.width() != main_height or self.height() != main_height:
                self.resize(main_height, main_height)

            album_pos_x = self.main_window.x() + self.main_window.width()
            album_pos_y = self.main_window.y()
            self.move(album_pos_x, album_pos_y)
            # Ensure the album art window is docked when opened in default position
            self.is_docked = True

    def apply_region_mask(self):
        """Apply the region mask to the window based on the region.txt data."""
        if self.skin_data and self.skin_data.region_data:
            # For album art window, use the "AlbumArt" state from region data if it exists
            # or default to no mask if that state doesn't exist
            apply_region_mask_to_widget(
                self, self.skin_data.region_data, state="AlbumArt"
            )
        else:
            # Clear any existing mask if no region data exists
            self.clearMask()

    def _get_cache_key(self, file_path):
        """Generate a cache key for a file path."""
        if file_path:
            return os.path.normpath(file_path).lower()
        return None

    def _get_file_size(self, file_path):
        """Get the size of a file in bytes."""
        try:
            return os.path.getsize(file_path) if os.path.exists(file_path) else 0
        except OSError:
            return 0

    def _add_to_cache(self, file_path, pixmap):
        """Add a pixmap to the cache with size tracking."""
        if not file_path or pixmap is None:
            return

        cache_key = self._get_cache_key(file_path)
        if not cache_key:
            return

        # Calculate pixmap size (approximate based on dimensions)
        pixmap_size = pixmap.width() * pixmap.height() * 4  # 4 bytes per pixel (RGBA)

        # First, remove existing entry if it exists
        if cache_key in self._image_cache:
            old_pixmap, old_size = self._image_cache[cache_key]
            self._current_cache_size -= old_size

        # Add new entry
        self._image_cache[cache_key] = (pixmap, pixmap_size)
        self._current_cache_size += pixmap_size

        # Enforce cache size limit using LRU eviction
        while (
            self._current_cache_size > self._max_cache_size
            and len(self._image_cache) > 1
        ):
            # Remove oldest item (LRU)
            oldest_key, (oldest_pixmap, oldest_size) = self._image_cache.popitem(
                last=False
            )
            self._current_cache_size -= oldest_size

    def _get_from_cache(self, file_path):
        """Get a pixmap from the cache."""
        cache_key = self._get_cache_key(file_path)
        if cache_key and cache_key in self._image_cache:
            # Move to end to mark as most recently used
            pixmap, size = self._image_cache.pop(cache_key)
            self._image_cache[cache_key] = (pixmap, size)
            return pixmap
        return None

    def _preprocess_image(self, pixmap):
        """Preprocess image to optimize for performance and memory usage."""
        # Check if image is too large (>2MB equivalent in dimensions)
        if pixmap.width() * pixmap.height() * 4 > 2 * 1024 * 1024:  # 2MB equivalent
            # Scale down to a reasonable size while maintaining aspect ratio
            max_dimension = 1024  # Maximum dimension for large images
            if pixmap.width() > max_dimension or pixmap.height() > max_dimension:
                pixmap = pixmap.scaled(
                    max_dimension,
                    max_dimension,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )

        # Ensure the pixmap is valid after processing
        if pixmap.isNull():
            print("Warning: Preprocessed image is null")
            return pixmap

        return pixmap

    def set_album_art(self, pixmap):
        """Set the album art pixmap to display."""
        self.album_art_pixmap = pixmap
        if pixmap:
            # Scale the pixmap to fit the current window size while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.album_art_label.setPixmap(scaled_pixmap)
            # Ensure the label properly aligns the image
            self.album_art_label.setAlignment(Qt.AlignCenter)
        else:
            # Clear the label if no pixmap is provided
            self.album_art_label.clear()

    def refresh_album_art(self, audio_engine):
        """Refresh the album art based on the current track in the audio engine."""
        if not audio_engine or not audio_engine.has_track_loaded():
            # No track loaded, show default placeholder
            self.load_default_placeholder()
            return

        # Get the current file path
        current_file_path = audio_engine.file_path
        if not current_file_path:
            self.load_default_placeholder()
            return

        # Store current file path
        self.current_file_path = current_file_path

        # Check if embedded art is already cached
        cache_key = f"embedded_{os.path.normpath(current_file_path).lower()}"
        cached_pixmap = self._get_from_cache(cache_key)
        if cached_pixmap:
            self.set_album_art(cached_pixmap)
            return

        # 1. Try to get embedded album art from metadata first
        album_art_data = audio_engine.get_album_art()
        if album_art_data:
            try:
                # Load the embedded album art from the binary data
                pixmap = QPixmap()
                if pixmap.loadFromData(album_art_data):
                    # Check if the loaded pixmap is valid
                    if not pixmap.isNull():
                        # Preprocess the image for performance
                        pixmap = self._preprocess_image(pixmap)

                        # Make sure it's still valid after preprocessing
                        if not pixmap.isNull():
                            # Cache the embedded art
                            self._add_to_cache(cache_key, pixmap)

                            self.set_album_art(pixmap)
                            return
                        else:
                            print(
                                f"Warning: Image became null after preprocessing for {current_file_path}"
                            )
                    else:
                        print(
                            f"Warning: Failed to load image data for {current_file_path}"
                        )
                else:
                    # Embedded image data is corrupted
                    print(
                        f"Warning: Corrupted embedded album art in {current_file_path}"
                    )
            except Exception as e:
                # Error occurred while loading embedded art
                print(f"Error loading embedded album art from {current_file_path}: {e}")

        # 2. If no embedded art, search for local folder images
        folder_path = os.path.dirname(current_file_path)
        album_art_file = self._search_local_album_art(folder_path)

        if album_art_file and self.load_album_art_from_file(album_art_file):
            return

        # 3. If no art found anywhere, use default placeholder
        self.load_default_placeholder()

    def _search_local_album_art(self, folder_path):
        """Search for local album art files in the specified folder."""
        if not os.path.isdir(folder_path):
            return None

        # Define the search order according to the specification
        search_files = [
            "folder.jpg",
            "folder.png",
            "cover.jpg",
            "cover.png",
            "album.jpg",
            "album.png",
        ]

        # First, check for standard filenames in order of preference
        for filename in search_files:
            file_path = os.path.join(folder_path, filename)
            if os.path.exists(file_path):
                return file_path

        # If standard names aren't found, search for album title matches
        # Get the album name from metadata if possible
        audio_engine = getattr(self, "main_window", None)
        if audio_engine and hasattr(audio_engine, "audio_engine"):
            audio_engine_instance = audio_engine.audio_engine
            metadata = (
                audio_engine_instance.get_metadata() if audio_engine_instance else {}
            )
            album_title = metadata.get("album", "Unknown")

            # Normalize album title for matching
            normalized_title = self._normalize_filename(album_title)

            # Look for files starting with the album title
            for filename in os.listdir(folder_path):
                if os.path.isfile(os.path.join(folder_path, filename)):
                    name, ext = os.path.splitext(filename)
                    if ext.lower() in [".jpg", ".jpeg", ".png", ".bmp", ".gif"]:
                        if self._normalize_filename(name).startswith(normalized_title):
                            return os.path.join(folder_path, filename)

        return None

    def _normalize_filename(self, filename):
        """Normalize a filename for comparison by converting to lowercase and handling special characters."""
        import re

        # Convert to lowercase
        normalized = filename.lower()
        # Replace common separators with spaces
        normalized = re.sub(r"[-_\s]+", " ", normalized)
        # Remove common characters that don't affect matching
        normalized = re.sub(r"[^\w\s]", "", normalized)
        # Split and rejoin to normalize multiple spaces to single spaces
        normalized = " ".join(normalized.split())
        return normalized

    def load_default_placeholder(self):
        """Load the default album art placeholder with proper error handling."""
        # Try to load the default placeholder image
        default_art_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "resources",
            "default_art",
            "default.png",
        )

        try:
            if os.path.exists(default_art_path):
                pixmap = QPixmap(default_art_path)
                if not pixmap.isNull():
                    self.set_album_art(pixmap)
                    return
                else:
                    # Default image data is corrupted
                    print(
                        f"Warning: Default album art image is corrupted: {default_art_path}"
                    )
            else:
                # Default image file is missing
                print(f"Warning: Default album art image not found: {default_art_path}")
        except Exception as e:
            # Error occurred while loading default image
            print(f"Error loading default album art: {e}")

        # If the default image is missing or corrupted, fill with black
        black_pixmap = QPixmap(self.size())
        black_pixmap.fill(QColor(0, 0, 0))  # Black background
        self.set_album_art(black_pixmap)

    def load_album_art_from_file(self, file_path):
        """Load album art from a local image file with caching and error handling."""
        if not os.path.exists(file_path):
            return False

        # Check if image is already in cache
        cached_pixmap = self._get_from_cache(file_path)
        if cached_pixmap:
            self.set_album_art(cached_pixmap)
            return True

        # Check if we're already loading this file
        if file_path in self._loading_operations:
            # Wait for the existing load operation to complete
            # For now, return False, but in a more complex implementation we could wait
            return False

        # Check if we're at the max concurrent load limit
        if len(self._loading_operations) >= self._max_concurrent_loads:
            return False

        # Add to loading operations
        self._loading_operations.add(file_path)

        try:
            # Load pixmap from file
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Preprocess the image for performance
                pixmap = self._preprocess_image(pixmap)

                # Ensure the processed pixmap is still valid
                if not pixmap.isNull():
                    # Add to cache
                    self._add_to_cache(file_path, pixmap)

                    self.set_album_art(pixmap)
                    return True
                else:
                    print(
                        f"Warning: Image became null after preprocessing from: {file_path}"
                    )
                    return False
            else:
                # File exists but image is corrupted
                print(f"Warning: Corrupted image file: {file_path}")
                return False
        except Exception as e:
            # Error occurred while loading the image
            print(f"Error loading image file {file_path}: {e}")
            return False
        finally:
            # Remove from loading operations
            self._loading_operations.discard(file_path)

        return False

    def mousePressEvent(self, event):
        """Handle mouse press events for window dragging and resizing."""
        # Bring all related windows to foreground when clicked
        if self.main_window:
            self.main_window.bring_all_windows_to_foreground()

        if event.button() == Qt.LeftButton:
            # Check if click is in resize handle area (bottom-right)
            resize_area = QRect(
                self.width() - self._resize_handle_size,
                self.height() - self._resize_handle_size,
                self._resize_handle_size,
                self._resize_handle_size,
            )

            if resize_area.contains(event.pos()):
                # Start resize operation
                self._is_resizing = True
                self._resize_start_pos = event.globalPos()
                self._resize_start_size = self.size()
                event.accept()
                return
            else:
                # Start window dragging
                self._dragging_window = True
                self._drag_start_position = (
                    event.globalPos() - self.frameGeometry().topLeft()
                )
                event.accept()
                return

        super().mousePressEvent(event)

    def focusInEvent(self, event):
        """Called when the album art window receives focus."""
        # Bring all related windows to foreground when album art gains focus
        if self.main_window:
            self.main_window.bring_all_windows_to_foreground()
        super().focusInEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move events for window dragging and resizing."""
        if self._is_resizing and self._resize_start_pos:
            # Handle resize operation
            delta = event.globalPos() - self._resize_start_pos
            new_width = max(
                self.minimumWidth(), self._resize_start_size.width() + delta.x()
            )
            new_height = max(
                self.minimumHeight(), self._resize_start_size.height() + delta.y()
            )

            # Maintain square aspect ratio
            new_size = min(new_width, new_height)

            # Calculate resize with snapping to match docked windows
            # When docked horizontally (left/right), snap to match total height of docked group
            # When docked vertically (above/below), snap to match total width of docked group

            # Get the expected size to match based on docking with main window
            # and any other docked windows like playlist/equalizer
            target_size = new_size  # Default to the calculated size

            if self.main_window:
                # Check if horizontally aligned with main window (docked left/right)
                main_window_right = self.main_window.x() + self.main_window.width()
                main_window_bottom = self.main_window.y() + self.main_window.height()

                # Check horizontal docking (to left or right of main window)
                is_horizontally_docked = (
                    (
                        abs(self.x() - main_window_right) <= self.dock_margin
                    )  # Docked to right of main
                    or (
                        abs((self.x() + self.width()) - self.main_window.x())
                        <= self.dock_margin
                    )  # Docked to left of main
                ) and (
                    self.y() < main_window_bottom
                    and (self.y() + self.height()) > self.main_window.y()
                )

                # Check vertical docking (above or below main window)
                is_vertically_docked = (
                    (
                        abs(self.y() - main_window_bottom) <= self.dock_margin
                    )  # Docked below main
                    or (
                        abs((self.y() + self.height()) - self.main_window.y())
                        <= self.dock_margin
                    )  # Docked above main
                ) and (
                    self.x() < main_window_right
                    and (self.x() + self.width()) > self.main_window.x()
                )

                if is_horizontally_docked:
                    # When docked horizontally, snap to match the height of the main window
                    target_size = self.main_window.height()
                elif is_vertically_docked:
                    # When docked vertically, snap to match the width of the main window
                    target_size = self.main_window.width()

            # Also check for snapping to other docked windows like playlist or equalizer
            # Check against playlist window if docked
            if (
                hasattr(self.main_window, "playlist_window")
                and self.main_window.playlist_window.isVisible()
            ):
                playlist_window = self.main_window.playlist_window
                playlist_right = playlist_window.x() + playlist_window.width()
                playlist_bottom = playlist_window.y() + playlist_window.height()

                # Check if horizontally aligned with playlist
                is_horizontally_aligned_with_playlist = (
                    (abs(self.x() - playlist_right) <= self.dock_margin)
                    or (
                        abs((self.x() + self.width()) - playlist_window.x())
                        <= self.dock_margin
                    )
                ) and (
                    self.y() < playlist_bottom
                    and (self.y() + self.height()) > playlist_window.y()
                )

                # Check if vertically aligned with playlist
                is_vertically_aligned_with_playlist = (
                    (abs(self.y() - playlist_bottom) <= self.dock_margin)
                    or (
                        abs((self.y() + self.height()) - playlist_window.y())
                        <= self.dock_margin
                    )
                ) and (
                    self.x() < playlist_right
                    and (self.x() + self.width()) > playlist_window.x()
                )

                if is_horizontally_aligned_with_playlist:
                    # When docked horizontally to playlist, snap to match the playlist window height
                    target_size = playlist_window.height()
                elif is_vertically_aligned_with_playlist:
                    target_size = playlist_window.width()

            # Check against equalizer window if docked
            if (
                hasattr(self.main_window, "equalizer_window")
                and self.main_window.equalizer_window.isVisible()
            ):
                eq_window = self.main_window.equalizer_window
                eq_right = eq_window.x() + eq_window.width()
                eq_bottom = eq_window.y() + eq_window.height()

                # Check if horizontally aligned with equalizer
                is_horizontally_aligned_with_eq = (
                    (abs(self.x() - eq_right) <= self.dock_margin)
                    or (
                        abs((self.x() + self.width()) - eq_window.x())
                        <= self.dock_margin
                    )
                ) and (
                    self.y() < eq_bottom and (self.y() + self.height()) > eq_window.y()
                )

                # Check if vertically aligned with equalizer
                is_vertically_aligned_with_eq = (
                    (abs(self.y() - eq_bottom) <= self.dock_margin)
                    or (
                        abs((self.y() + self.height()) - eq_window.y())
                        <= self.dock_margin
                    )
                ) and (
                    self.x() < eq_right and (self.x() + self.width()) > eq_window.x()
                )

                if is_horizontally_aligned_with_eq:
                    # When docked horizontally to EQ, snap to match the EQ window height
                    target_size = eq_window.height()
                elif is_vertically_aligned_with_eq:
                    target_size = eq_window.width()

            # Use the target size if we're horizontally docked, otherwise maintain square aspect ratio
            if target_size is not None:
                # Ensure target size is not smaller than minimum size
                target_size = max(self.minimumWidth(), target_size)
                self.resize(target_size, target_size)
            else:
                # Maintain square aspect ratio normally
                new_size = max(self.minimumWidth(), new_size)
                self.resize(new_size, new_size)
            event.accept()
            return
        elif hasattr(self, "_dragging_window") and self._dragging_window:
            # Handle window dragging
            new_pos = event.globalPos() - self._drag_start_position
            self.move(new_pos)

            # Check docking status and apply snapping if main window is available
            if self.main_window:
                window_rect = QRect(self.x(), self.y(), self.width(), self.height())

                # Get snap alignment from main window (using the window-to-window snapping logic)
                snapped_x, snapped_y, is_snapped = (
                    self.main_window.get_window_snap_alignment(
                        window_rect, exclude_window=self
                    )
                )

                if is_snapped:
                    self.move(snapped_x, snapped_y)

                # Update docked status based on proximity to main window or other docked windows
                is_near_any = self.main_window.is_window_near_any_docked_window(
                    window_rect, exclude_window=self
                )
                self.is_docked = is_near_any

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.LeftButton:
            if self._is_resizing:
                self._is_resizing = False
                self._resize_start_pos = None
                self._resize_start_size = None
                event.accept()
                return
            elif hasattr(self, "_dragging_window") and self._dragging_window:
                self._dragging_window = False
                event.accept()
                return

        super().mouseReleaseEvent(event)

    def _check_resize_cursor(self):
        """Check if cursor is in resize handle area and update cursor accordingly."""
        if not self.underMouse():
            return

        # Get cursor position relative to this widget
        from PySide6.QtGui import QCursor

        cursor_pos = self.mapFromGlobal(QCursor.pos())

        # Check if cursor is in bottom-right resize handle area
        resize_area = QRect(
            self.width() - self._resize_handle_size,
            self.height() - self._resize_handle_size,
            self._resize_handle_size,
            self._resize_handle_size,
        )

        if resize_area.contains(cursor_pos):
            QApplication.setOverrideCursor(Qt.SizeFDiagCursor)
        else:
            QApplication.restoreOverrideCursor()

    def resizeEvent(self, event):
        """Handle resize events to maintain square aspect ratio."""
        super().resizeEvent(event)

        # Ensure the window remains square after resize
        if not self._is_resizing:
            # Only enforce square when not actively resizing (to avoid recursion)
            current_size = event.size()
            if current_size.width() != current_size.height():
                # Check if we should snap to docked window size
                target_size = None

                # Check if docked to main window (horizontally or vertically)
                if self.main_window:
                    main_window_right = self.main_window.x() + self.main_window.width()
                    main_window_bottom = self.main_window.y() + self.main_window.height()

                    # Check horizontal docking (to left or right of main window)
                    is_horizontally_docked = (
                        (
                            abs(self.x() - main_window_right) <= self.dock_margin
                        )  # Docked to right of main
                        or (
                            abs((self.x() + self.width()) - self.main_window.x())
                            <= self.dock_margin
                        )  # Docked to left of main
                    ) and (
                        self.y() < main_window_bottom
                        and (self.y() + self.height()) > self.main_window.y()
                    )

                    # Check vertical docking (above or below main window)
                    is_vertically_docked = (
                        (
                            abs(self.y() - main_window_bottom) <= self.dock_margin
                        )  # Docked below main
                        or (
                            abs((self.y() + self.height()) - self.main_window.y())
                            <= self.dock_margin
                        )  # Docked above main
                    ) and (
                        self.x() < main_window_right
                        and (self.x() + self.width()) > self.main_window.x()
                    )

                    if is_horizontally_docked:
                        # Snap to main window's height when horizontally docked
                        target_size = self.main_window.height()
                    elif is_vertically_docked:
                        # Snap to main window's width when vertically docked (to maintain square aspect ratio)
                        target_size = self.main_window.width()

                # Check against playlist window if docked
                if (
                    not target_size and
                    hasattr(self.main_window, "playlist_window")
                    and self.main_window.playlist_window.isVisible()
                ):
                    playlist_window = self.main_window.playlist_window
                    playlist_right = playlist_window.x() + playlist_window.width()
                    playlist_bottom = playlist_window.y() + playlist_window.height()

                    # Check horizontal docking with playlist
                    is_horizontally_docked_to_playlist = (
                        (abs(self.x() - playlist_right) <= self.dock_margin)
                        or (
                            abs((self.x() + self.width()) - playlist_window.x())
                            <= self.dock_margin
                        )
                    ) and (
                        self.y() < playlist_bottom
                        and (self.y() + self.height()) > playlist_window.y()
                    )

                    # Check vertical docking with playlist
                    is_vertically_docked_to_playlist = (
                        (abs(self.y() - playlist_bottom) <= self.dock_margin)
                        or (
                            abs((self.y() + self.height()) - playlist_window.y())
                            <= self.dock_margin
                        )
                    ) and (
                        self.x() < playlist_right
                        and (self.x() + self.width()) > playlist_window.x()
                    )

                    if is_horizontally_docked_to_playlist:
                        # Snap to playlist's height when horizontally docked
                        target_size = playlist_window.height()
                    elif is_vertically_docked_to_playlist:
                        # Snap to playlist's width when vertically docked (to maintain square aspect ratio)
                        target_size = playlist_window.width()

                # Check against equalizer window if docked
                if (
                    not target_size and
                    hasattr(self.main_window, "equalizer_window")
                    and self.main_window.equalizer_window.isVisible()
                ):
                    eq_window = self.main_window.equalizer_window
                    eq_right = eq_window.x() + eq_window.width()
                    eq_bottom = eq_window.y() + eq_window.height()

                    # Check horizontal docking with equalizer
                    is_horizontally_docked_to_eq = (
                        (abs(self.x() - eq_right) <= self.dock_margin)
                        or (
                            abs((self.x() + self.width()) - eq_window.x())
                            <= self.dock_margin
                        )
                    ) and (
                        self.y() < eq_bottom and (self.y() + self.height()) > eq_window.y()
                    )

                    # Check vertical docking with equalizer
                    is_vertically_docked_to_eq = (
                        (abs(self.y() - eq_bottom) <= self.dock_margin)
                        or (
                            abs((self.y() + self.height()) - eq_window.y())
                            <= self.dock_margin
                        )
                    ) and (
                        self.x() < eq_right and (self.x() + self.width()) > eq_window.x()
                    )

                    if is_horizontally_docked_to_eq:
                        # Snap to equalizer's height when horizontally docked
                        target_size = eq_window.height()
                    elif is_vertically_docked_to_eq:
                        # Snap to equalizer's width when vertically docked (to maintain square aspect ratio)
                        target_size = eq_window.width()

                # If we're horizontally docked to a window, use its height as target size
                if target_size is not None:
                    self.resize(target_size, target_size)
                else:
                    # Otherwise, enforce square aspect ratio by default
                    square_size = min(current_size.width(), current_size.height())
                    self.resize(square_size, square_size)

        # Save the album art window size to preferences
        # Only save if the window is visible (to avoid saving during initialization)
        if (
            hasattr(self, "main_window")
            and self.isVisible()
            and not getattr(self.main_window, "_is_shutting_down", False)
        ):
            self.main_window.preferences.set_album_art_window_size(
                self.width(), self.height()
            )

        # If album art is set, update the scaled display
        if self.album_art_pixmap:
            scaled_pixmap = self.album_art_pixmap.scaled(
                self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.album_art_label.setPixmap(scaled_pixmap)

    def closeEvent(self, event):
        """Override close event to delegate to main window for centralized state management."""
        # Only update main window's state if not in global shutdown
        if (
            not getattr(self.main_window, "_is_shutting_down", False)
            and hasattr(self, "main_window")
            and self.main_window
            and hasattr(self.main_window, "hide_album_art_window")
        ):

            # Call the main window's centralized method to hide the album art window
            # This ensures consistent state management from a single source of truth
            self.main_window.hide_album_art_window()

        # Accept the close event to actually close the window
        event.accept()

    def moveEvent(self, event):
        """Handle window movement to save position to preferences."""
        super().moveEvent(event)

        # Save the album art window position to preferences
        # Always save position regardless of docking state, as docked positions are also meaningful
        if hasattr(self, "main_window"):
            if hasattr(self.main_window, "preferences") and not getattr(
                self.main_window, "_is_shutting_down", False
            ):
                self.main_window.preferences.set_album_art_window_position(
                    self.x(), self.y()
                )

    def update_skin(self, skin_data, sprite_manager):
        """Update the window with new skin data."""
        self.skin_data = skin_data
        self.sprite_manager = sprite_manager

        # Apply any region mask changes
        self.apply_region_mask()
