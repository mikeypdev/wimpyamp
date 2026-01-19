from PySide6.QtWidgets import QWidget, QMessageBox, QFileDialog
from PySide6.QtGui import QPainter, QColor, QFont  # Added QFont and QFontMetrics
from PySide6.QtCore import Qt, QRect, QPoint
import os

from ..utils.color import MAGENTA_TRANSPARENCY_RGB
from ..utils.region_utils import apply_region_mask_to_widget
from ..core.user_preferences import get_preferences
from .playlist_constants import (
    DEFAULT_FONT_NAME,
    DEFAULT_NORMAL_TEXT_COLOR,
    DEFAULT_CURRENT_TEXT_COLOR,
    DEFAULT_NORMAL_BG_COLOR,
    DEFAULT_SELECTED_BG_COLOR,
    SCROLLBAR_GROOVE_HEIGHT,
    BOTTOM_FILLER_WIDTH,
)
from .playlist_config import PlaylistConfig
from .playlist_scrollbar import ScrollbarManager
from .playlist_menu import MenuManager
from .playlist_buttonbar import ButtonBarManager


class PlaylistWindow(QWidget):
    def __init__(
        self, parent=None, skin_data=None, sprite_manager=None, text_renderer=None
    ):
        super().__init__(parent)
        self.setWindowTitle("WimPyAmp Playlist Editor")
        # Set window flags for completely borderless window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.X11BypassWindowManagerHint)

        # Set a transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.skin_data = skin_data
        self.sprite_manager = sprite_manager
        self.text_renderer = text_renderer  # Store TextRenderer instance
        self.main_window = None  # Reference to main window for callbacks
        self.extracted_skin_dir = (
            self.skin_data.extracted_skin_dir if self.skin_data else None
        )

        # Add docking state and related attributes
        # When window is opened in default position (typically below main window), consider it docked
        self.is_docked = True  # Start as docked by default
        self.docking_offset = QPoint(0, 0)  # Offset from docking position when undocked
        self.dock_margin = 10  # pixels of tolerance for docking

        # Load playlist configuration
        self.config_manager = PlaylistConfig(self.skin_data.playlist_spec_json)
        self.playlist_spec = self.config_manager.get_spec()
        if not self.playlist_spec:
            QMessageBox.critical(
                self, "Error", "Failed to load playlist window specification."
            )
            return

        # Get user preferences
        self.preferences = get_preferences()

        # Load playlist display options from preferences
        playlist_settings = self.preferences.get_playlist_settings()
        self.display_options = playlist_settings.get(
            "display_options",
            {
                "track_filename": True,  # On by default
                "track_number": False,
                "song_name": False,
                "artist": False,
                "album_artist": False,
                "album_name": False,
            },
        )

        # Initialize UI component managers
        self.scrollbar_manager = ScrollbarManager(
            self, self.playlist_spec, self.sprite_manager, self.skin_data
        )
        self.menu_manager = MenuManager(self, self.playlist_spec)
        self.buttonbar_manager = ButtonBarManager(self, self.playlist_spec)

        self.playlist_font_name = DEFAULT_FONT_NAME  # Default font
        self.playlist_font_size = self.playlist_spec["layout"]["regions"]["track_area"][
            "font"
        ][
            "char_height"
        ]  # Use char_height from spec as base size
        self.playlist_normal_text_color = QColor(
            DEFAULT_NORMAL_TEXT_COLOR
        )  # Default to green
        self.playlist_current_text_color = QColor(
            DEFAULT_CURRENT_TEXT_COLOR
        )  # Default to white

        self._load_playlist_font_settings()  # Load font settings from pledit.txt
        self.playlist_font = QFont(self.playlist_font_name, self.playlist_font_size)

        default_width = self.playlist_spec["layout"]["window"]["default_size"]["width"]
        default_height = self.playlist_spec["layout"]["window"]["default_size"][
            "height"
        ]
        min_height = self.playlist_spec["layout"]["window"]["min_height"]

        self.setGeometry(0, 0, default_width, default_height)
        self.setMinimumHeight(min_height)
        if self.playlist_spec["layout"]["window"]["resizeable"]:
            self.setWindowFlags(self.windowFlags() | Qt.WindowMinMaxButtonsHint)

        # Initialize empty playlist
        self.playlist_items = []
        self.playlist_filepaths = []  # Store actual file paths
        self.current_track_index = -1  # Index of currently playing track
        self.selected_items = set()  # Stores indices of selected items
        self.last_selected_item_index = -1  # For Shift+click functionality
        self.scroll_offset = 0  # Index of the first visible item

        # State for custom buttons
        # State for scrollbar elements is now managed by scrollbar_manager
        # State for menus is now managed by menu_manager
        # State for button presses is now managed by buttonbar_manager

        # Transport control button states
        self._is_previous_pressed = False
        self._is_play_pressed = False
        self._is_pause_pressed = False
        self._is_stop_pressed = False
        self._is_next_pressed = False
        self._is_eject_pressed = False

        # Close button state (for the close button in the top right corner)
        self._is_close_pressed = False

        self._resizing = False
        self._resize_start_pos = None
        self._resize_start_size = None

        # Window dragging state
        self._dragging_window = False
        self._drag_start_position = QPoint()

        # State for scrollbar thumb dragging is now managed by scrollbar_manager

        # Flag to prevent recursive resize calls when applying constraints
        self._applying_resize_constraints = False

        self.setMouseTracking(True)  # Enable mouse tracking

        # Initialize timer for updating time display
        from PySide6.QtCore import QTimer

        self.time_display_timer = QTimer()
        self.time_display_timer.timeout.connect(self.update)
        self.time_display_timer.start(1000)  # Update every second

        # Apply stepped resize constraints to ensure initial size follows proper dimensions
        self._apply_stepped_resize_constraints()

        self.normal_bg_color = QColor(DEFAULT_NORMAL_BG_COLOR)  # Default to black
        self.selected_bg_color = QColor(
            DEFAULT_SELECTED_BG_COLOR
        )  # Default to dark blue (0000C6)
        self.current_playing_bg_color = QColor(
            0, 100, 0
        )  # Darker green for currently playing track
        self._load_pledit_colors()

        # Cache for track durations to avoid repeated file loads
        self._track_durations_cache = {}

        # Apply region mask if available
        self.apply_region_mask()

        self.show()

    def apply_region_mask(self):
        """Apply the region mask to the window based on the region.txt data."""
        if self.skin_data and self.skin_data.region_data:
            # For playlist, use the "Playlist" state from region data if it exists, otherwise don't apply mask
            # Since our test region.txt doesn't have a playlist section, it will default to normal mask behavior
            apply_region_mask_to_widget(
                self, self.skin_data.region_data, state="Playlist"
            )
        else:
            # Clear any existing mask if no region data exists
            self.clearMask()

    def set_main_window(self, main_window):
        """Set reference to main window for callbacks."""
        self.main_window = main_window

    def set_playlist_items(self, display_items):
        """Set the playlist items to display."""
        self.playlist_items = display_items
        # Reset selection and scroll when loading new playlist
        self.selected_items.clear()
        self.current_track_index = -1
        self.scroll_offset = 0
        self.last_selected_item_index = -1
        # Clear the track durations cache since playlist has changed
        self._track_durations_cache.clear()
        self.update()

    def set_current_track_index(self, index):
        """Set the index of the currently playing track."""
        self.current_track_index = index
        self.update()

    def _regenerate_playlist_display_items(self):
        """Regenerate playlist display items based on current display options."""
        if not self.playlist_filepaths:
            return

        self.playlist_items = []
        for i, filepath in enumerate(self.playlist_filepaths):
            # Load metadata for the track to get all possible display data
            track_metadata = self._get_track_metadata(filepath)

            # Build display string based on selected options
            display_parts = []

            # Add track number from metadata if option is selected and available
            if (
                self.display_options["track_number"]
                and track_metadata.get("tracknumber")
                and track_metadata["tracknumber"] != "Unknown"
            ):
                display_parts.append(track_metadata["tracknumber"])

            # Add song name if option is selected and available
            if (
                self.display_options["song_name"]
                and track_metadata.get("title")
                and track_metadata["title"] != "Unknown"
            ):
                display_parts.append(track_metadata["title"])

            # Add artist if option is selected and available
            if (
                self.display_options["artist"]
                and track_metadata.get("artist")
                and track_metadata["artist"] != "Unknown"
            ):
                display_parts.append(track_metadata["artist"])

            # Add album artist if option is selected and available
            if (
                self.display_options["album_artist"]
                and track_metadata.get("album_artist")
                and track_metadata["album_artist"] != "Unknown"
            ):
                display_parts.append(track_metadata["album_artist"])

            # Add album name if option is selected and available
            if (
                self.display_options["album_name"]
                and track_metadata.get("album")
                and track_metadata["album"] != "Unknown"
            ):
                display_parts.append(track_metadata["album"])

            # Add filename if option is selected or if no other metadata is available/selected
            if self.display_options["track_filename"] or not display_parts:
                filename = os.path.basename(filepath)
                # Avoid adding filename if it's the same as the title
                if not (
                    self.display_options["song_name"]
                    and track_metadata.get("title", "Unknown").lower()
                    == filename.lower()
                ):
                    display_parts.append(filename)

            # Join the selected parts with " - " separator
            display_text = " - ".join(part for part in display_parts if part)

            # Always add the playlist number as a prefix
            display_text = f"{i+1}. {display_text}"

            self.playlist_items.append(display_text)

        self.update()

    def _get_track_metadata(self, filepath):
        """Get metadata for a track using the main window's audio engine or mutagen."""
        # Try to get metadata from main window's audio engine if it's the currently loaded track
        if (
            self.main_window
            and hasattr(self.main_window, "audio_engine")
            and self.main_window.audio_engine
            and self.main_window.audio_engine.file_path == filepath
        ):
            try:
                return self.main_window.audio_engine.get_metadata()
            except Exception:
                # If getting metadata from audio engine fails, fall through to mutagen approach
                pass

        # Otherwise, try to load metadata directly using mutagen
        try:
            from mutagen import File as MutagenFile

            audio_file = MutagenFile(filepath)
            if audio_file is not None:
                metadata = {}

                # Helper function to safely extract metadata
                def safe_extract_metadata(audio_file, keys):
                    result = "Unknown"
                    for key in keys:
                        try:
                            if key in audio_file:
                                tag_value = audio_file[key]
                                if isinstance(tag_value, list) and len(tag_value) > 0:
                                    try:
                                        raw_value = tag_value[0]
                                        # Only convert to string if it's not None
                                        if raw_value is not None:
                                            result = str(raw_value).strip()
                                        else:
                                            result = "Unknown"
                                    except (
                                        UnicodeDecodeError,
                                        TypeError,
                                        AttributeError,
                                    ):
                                        # Handle cases where value can't be converted to string
                                        result = "Unknown"
                                elif (
                                    isinstance(tag_value, list) and len(tag_value) == 0
                                ):
                                    continue
                                else:
                                    try:
                                        # Handle single values
                                        if tag_value is not None:
                                            result = str(tag_value).strip()
                                        else:
                                            result = "Unknown"
                                    except (
                                        UnicodeDecodeError,
                                        TypeError,
                                        AttributeError,
                                    ):
                                        # Handle cases where value can't be converted to string
                                        result = "Unknown"
                                break
                        except Exception:
                            # If any key access fails, continue to next key
                            continue
                    return result if result else "Unknown"

                # Title
                title_keys = ["TIT2", "title", "\xa9nam", "TITLE", "©nam"]
                metadata["title"] = safe_extract_metadata(audio_file, title_keys)

                # Artist
                artist_keys = ["TPE1", "artist", "\xa9ART", "ARTIST", "©ART"]
                metadata["artist"] = safe_extract_metadata(audio_file, artist_keys)

                # Album
                album_keys = ["TALB", "album", "\xa9alb", "ALBUM", "©alb"]
                metadata["album"] = safe_extract_metadata(audio_file, album_keys)

                # Album artist (if available)
                album_artist_keys = ["TPE2", "albumartist", "aART", "©aAR"]
                metadata["album_artist"] = safe_extract_metadata(
                    audio_file, album_artist_keys
                )

                # Track number - handle different formats
                track_number_str = "Unknown"
                try:
                    if "trkn" in audio_file:  # MP4/M4A style
                        # Value is a list of tuples, e.g., [(2, 12)]
                        track_info = audio_file["trkn"]
                        if (
                            track_info
                            and len(track_info) > 0
                            and len(track_info[0]) > 0
                        ):
                            track_number_str = str(track_info[0][0])
                    elif "TRCK" in audio_file:  # MP3 style
                        # Value is a TRCK object, str(obj) is '2/12' or '2'
                        track_number_str = str(audio_file["TRCK"])
                    elif "tracknumber" in audio_file:  # FLAC/Vorbis style
                        # Value is a list of strings, e.g., ['2']
                        track_number_str = str(audio_file["tracknumber"][0])
                except Exception:
                    track_number_str = "Unknown"

                if track_number_str and track_number_str != "Unknown":
                    # The value can be '3/12' or just '3'. We only want the '3'.
                    parsed_track = track_number_str.split("/")[0].strip()
                    metadata["tracknumber"] = parsed_track
                else:
                    metadata["tracknumber"] = "Unknown"

                # Duration from audio data
                try:
                    audio_file_for_duration = MutagenFile(filepath)
                    if hasattr(audio_file_for_duration, "info") and hasattr(
                        audio_file_for_duration.info, "length"
                    ):
                        duration = audio_file_for_duration.info.length
                    else:
                        # Fallback: load with librosa
                        import librosa

                        try:
                            audio_data, sample_rate = librosa.load(
                                filepath, sr=None, mono=False
                            )
                            duration = librosa.get_duration(
                                y=audio_data, sr=sample_rate
                            )
                        except Exception:
                            duration = 0.0
                except Exception:
                    duration = 0.0
                metadata["duration"] = duration

                return metadata
            else:
                return {
                    "title": "Unknown",
                    "artist": "Unknown",
                    "album": "Unknown",
                    "album_artist": "Unknown",
                    "tracknumber": "Unknown",
                    "duration": 0.0,
                }
        except Exception:
            # If metadata loading fails completely, return defaults
            return {
                "title": "Unknown",
                "artist": "Unknown",
                "album": "Unknown",
                "album_artist": "Unknown",
                "tracknumber": "Unknown",
                "duration": 0.0,
            }

    def get_playlist_filepaths(self):
        """Get the list of file paths for the playlist."""
        return self.playlist_filepaths

    def get_selected_track_index(self):
        """Get the index of the first selected track, or -1 if none selected."""
        if self.selected_items:
            return min(self.selected_items)  # Return first selected item index
        return -1  # No selected item

    def set_playlist_filepaths(self, filepaths):
        """Set the list of file paths for the playlist."""
        self.playlist_filepaths = filepaths
        # Generate display items based on current display options
        self._regenerate_playlist_display_items()
        # Reset selection and scroll when loading new playlist
        self.selected_items.clear()
        self.current_track_index = -1
        self.scroll_offset = 0
        self.last_selected_item_index = -1
        # Clear the track durations cache since playlist has changed
        self._track_durations_cache.clear()

    def _get_scrollbar_element_rect(self, element_id):
        """Get the rectangle for a scrollbar element."""
        return self.scrollbar_manager.get_element_rect(element_id)

    def _load_pledit_colors(self):
        pledit_txt_path = self.skin_data.get_path("pledit.txt")
        if not pledit_txt_path or not os.path.exists(pledit_txt_path):
            print("WARNING: pledit.txt not found. Using default colors.")
            return

        try:
            with open(pledit_txt_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("NormalBG="):
                        hex_color = line.split("=")[1]
                        self.normal_bg_color = QColor(hex_color)
                    elif line.startswith("SelectedBG="):
                        hex_color = line.split("=")[1]
                        self.selected_bg_color = QColor(hex_color)
                    elif line.startswith("Normal="):
                        hex_color = line.split("=")[1]
                        self.playlist_normal_text_color = QColor(hex_color)
                    elif line.startswith("Current="):
                        hex_color = line.split("=")[1]
                        self.playlist_current_text_color = QColor(hex_color)
        except Exception as e:
            print(f"Error loading pledit.txt colors: {e}. Using default colors.")

    def _load_playlist_font_settings(self):
        pledit_txt_path = self.skin_data.get_path("pledit.txt")

        # Check if pledit.txt exists
        if not pledit_txt_path or not os.path.exists(pledit_txt_path):
            print("WARNING: pledit.txt not found. Using default font settings.")
            return

        try:
            with open(pledit_txt_path, "r") as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line.startswith("Font="):
                        self.playlist_font_name = line.split("=")[1]
                    elif line.startswith("Normal="):
                        self.playlist_normal_text_color = QColor(line.split("=")[1])
                    elif line.startswith("Current="):
                        self.playlist_current_text_color = QColor(line.split("=")[1])
        except Exception as e:
            print(
                f"Error parsing pledit.txt content for font settings: {e}. Using default font settings."
            )

    def _get_bottom_bar_y(self):
        bottom_bar_spec = self.playlist_spec["layout"]["regions"]["bottom_bar"]
        bottom_bar_y_expr = bottom_bar_spec["position"]["y"]
        if isinstance(bottom_bar_y_expr, str) and bottom_bar_y_expr.startswith(
            "window.height - "
        ):
            offset = int(bottom_bar_y_expr.split(" - ")[1])
            return self.height() - offset
        return bottom_bar_y_expr

    def _get_close_button_rect(self):
        """Get the rectangle for the close button based on spec."""
        if not self.playlist_spec:
            return QRect(0, 0, 0, 0)  # Return empty rectangle if no spec

        close_button_spec = self.playlist_spec["layout"]["controls"]["close_button"]
        x_expr = close_button_spec["position"]["x"]
        y_expr = close_button_spec["position"]["y"]

        # Evaluate expressions like "window.width - 11"
        if isinstance(x_expr, str) and "window.width" in x_expr:
            parts = x_expr.split(" - ")
            base = self.width()
            offset = sum(int(p) for p in parts[1:])
            x = base - offset
        else:
            x = int(x_expr)

        y = int(y_expr) if isinstance(y_expr, int) else int(y_expr.split(" - ")[1])

        width = close_button_spec["width"]
        height = close_button_spec["height"]

        return QRect(x, y, width, height)

    def _load_playlist_spec(self):
        """Load the playlist specification - now handled by config manager."""
        return self.playlist_spec

    def _get_sprite_pixmap(self, sprite_id):
        """Helper to get a QPixmap for a given sprite ID from the spec."""
        if (
            not self.sprite_manager
            or not self.extracted_skin_dir
            or not self.playlist_spec
        ):
            return None

        pledit_bmp_path = self.skin_data.get_path(
            self.playlist_spec["spriteSheet"]["file"]
        )
        if not pledit_bmp_path or not os.path.exists(pledit_bmp_path):
            print(f"WARNING: {self.playlist_spec['spriteSheet']['file']} not found.")
            return None

        for sprite_data in self.playlist_spec["spriteSheet"]["sprites"]:
            if sprite_data["id"] == sprite_id:
                return self.sprite_manager.load_sprite(
                    pledit_bmp_path,
                    sprite_data["x"],
                    sprite_data["y"],
                    sprite_data["width"],
                    sprite_data["height"],
                    transparency_color=MAGENTA_TRANSPARENCY_RGB,
                )
        print(f"WARNING: Sprite ID '{sprite_id}' not found in spec.")
        return None

    def _close_all_sub_menus(self):
        """Close all open sub-menus."""
        self.menu_manager.close_all_menus()

    def _draw_tiled_region(self, painter, region_spec, target_rect):
        """Draws a region with tiling rules."""
        tiling = region_spec.get("tiling")

        if not tiling:
            if region_spec.get("tile_rule") == "solid_color_or_pattern":
                if region_spec.get("id") == "track_area":
                    painter.fillRect(target_rect, QColor(0, 0, 0))
            return

        left_sprite_pixmap = (
            self._get_sprite_pixmap(tiling["left"]) if "left" in tiling else None
        )
        right_sprite_pixmap = (
            self._get_sprite_pixmap(tiling["right"]) if "right" in tiling else None
        )

        # Draw fill_x (horizontal tiling) first
        if "fill_x" in tiling:
            fill_sprite_pixmap = self._get_sprite_pixmap(tiling["fill_x"])
            if fill_sprite_pixmap:
                start_x = target_rect.x() + (
                    left_sprite_pixmap.width() if left_sprite_pixmap else 0
                )
                end_x = (
                    target_rect.x()
                    + target_rect.width()
                    - (right_sprite_pixmap.width() if right_sprite_pixmap else 0)
                )

                if (
                    region_spec.get("id") == "bottom_bar"
                    and "components" in region_spec
                ):
                    for component in region_spec["components"]:
                        if (
                            component.get("id") == "visualization_miniscreen"
                            and component.get("type") == "conditional"
                        ):
                            condition = component.get("condition", "False")
                            if "window.width" in condition:
                                parts = condition.split(">=")
                                if len(parts) == 2:
                                    try:
                                        min_width = int(parts[1].strip())
                                        if self.width() >= min_width:
                                            miniscreen_sprite = self._get_sprite_pixmap(
                                                component["sprite"]
                                            )
                                            if miniscreen_sprite:
                                                end_x -= miniscreen_sprite.width()
                                    except ValueError:
                                        pass

                current_x = start_x
                while current_x < end_x:
                    painter.drawPixmap(current_x, target_rect.y(), fill_sprite_pixmap)
                    current_x += fill_sprite_pixmap.width()

        # Draw left corner on top
        if left_sprite_pixmap:
            painter.drawPixmap(target_rect.topLeft(), left_sprite_pixmap)

        # Draw right corner on top
        if right_sprite_pixmap:
            adjusted_width = right_sprite_pixmap.width()
            painter.drawPixmap(
                target_rect.topRight() - QPoint(adjusted_width, 0), right_sprite_pixmap
            )

        # Draw fill_y (vertical tiling) - for left/right edges
        if "fill_y" in tiling:
            fill_sprite_pixmap = self._get_sprite_pixmap(tiling["fill_y"])
            if fill_sprite_pixmap:
                current_y = target_rect.y()
                while current_y < target_rect.y() + target_rect.height():
                    painter.drawPixmap(target_rect.x(), current_y, fill_sprite_pixmap)
                    current_y += fill_sprite_pixmap.height()

    def paintEvent(self, event):
        painter = QPainter(self)
        if (
            not self.playlist_spec
            or not self.extracted_skin_dir
            or not self.sprite_manager
            or not self.text_renderer
        ):
            painter.end()
            return

        # Clear background with black
        painter.fillRect(self.rect(), QColor(0, 0, 0))

        # Draw regions in specified Z-order
        z_order = self.playlist_spec["renderingRules"]["z_order"]

        for layer in z_order:
            if layer == "background fill/tiling":
                self._draw_background_regions(painter)
            elif layer == "track text lines":
                self._draw_track_text_lines(painter)
            elif layer == "borders and edges":
                self._draw_borders_and_edges(painter)
            elif layer == "buttons and scrollbar":
                self._draw_buttons_and_scrollbar(painter)
            elif layer == "selection highlight overlays":
                # This layer is handled within "track text lines" for now, but could be separated
                pass
        painter.end()

    def _draw_background_regions(self, painter):
        """Draw background regions including top bar, bottom bar, and track area."""
        regions_map = {
            "top_bar": self.playlist_spec["layout"]["regions"]["top_bar"],
            "left_edge": self.playlist_spec["layout"]["regions"]["left_edge"],
            "right_edge": self.playlist_spec["layout"]["regions"]["right_edge"],
            "bottom_bar": self.playlist_spec["layout"]["regions"]["bottom_bar"],
            "track_area": self.playlist_spec["layout"]["regions"]["track_area"],
        }

        # Draw top bar components
        top_bar_spec = regions_map["top_bar"]

        # Special handling for the top bar to properly center the title area
        # The center fill should be truly centered in the window, with tiling fill on both sides
        left_corner_width = 25  # Width of PLEDIT_TOP_LEFT_ACTIVE
        center_fill_width = 100  # Width of PLEDIT_TOP_CENTER_FILL_ACTIVE
        right_corner_width = 25  # Width of PLEDIT_TOP_RIGHT_ACTIVE

        # Calculate the centered position for the center fill
        total_width = self.width()
        if total_width > (left_corner_width + center_fill_width + right_corner_width):
            # Calculate centered position for center fill
            remaining_space = total_width - (
                left_corner_width + center_fill_width + right_corner_width
            )
            left_filler_space = remaining_space // 2  # Space for left tiling
            right_filler_space = (
                remaining_space - left_filler_space
            )  # Space for right tiling

            for component in top_bar_spec["components"]:
                sprite_pixmap = self._get_sprite_pixmap(component["sprite"])
                if not sprite_pixmap:
                    continue

                if component["id"] == "top_left_corner":
                    painter.drawPixmap(0, component["y"], sprite_pixmap)
                elif component["id"] == "top_title":
                    # Position the center fill in the calculated centered position
                    center_x = left_corner_width + left_filler_space
                    painter.drawPixmap(center_x, component["y"], sprite_pixmap)
                elif component["id"] == "top_right_corner":
                    # Position the right corner at the right edge
                    painter.drawPixmap(
                        total_width - right_corner_width, component["y"], sprite_pixmap
                    )
                elif component["id"] == "top_tiling_fill":
                    # Tile on the left side between left corner and center fill
                    tiling_sprite = sprite_pixmap
                    left_start_x = left_corner_width
                    left_end_x = left_corner_width + left_filler_space

                    # Draw as many full tiles as possible, but at least one if space exists
                    current_x = left_start_x
                    if left_filler_space > 0:
                        # If we have space but it's less than one full tile width, we can scale or clip the tile
                        if left_filler_space < tiling_sprite.width():
                            # Draw a scaled version of the tile to fill the space exactly
                            painter.drawPixmap(
                                current_x,
                                component["y"],
                                tiling_sprite.scaled(
                                    left_filler_space, tiling_sprite.height()
                                ),
                            )
                        else:
                            # Draw full tiles as before
                            while current_x < left_end_x:
                                remaining_space = left_end_x - current_x
                                if remaining_space >= tiling_sprite.width():
                                    # Draw full tile
                                    painter.drawPixmap(
                                        current_x, component["y"], tiling_sprite
                                    )
                                    current_x += tiling_sprite.width()
                                else:
                                    # Draw a scaled tile to fill remaining space
                                    scaled_tile = tiling_sprite.scaled(
                                        remaining_space, tiling_sprite.height()
                                    )
                                    painter.drawPixmap(
                                        current_x, component["y"], scaled_tile
                                    )
                                    break

                    # Also tile on the right side between center fill and right corner
                    right_start_x = (
                        left_corner_width + left_filler_space + center_fill_width
                    )
                    right_end_x = total_width - right_corner_width

                    current_x = right_start_x
                    right_filler_space = right_end_x - right_start_x
                    if right_filler_space > 0:
                        # If we have space but it's less than one full tile width, we can scale or clip the tile
                        if right_filler_space < tiling_sprite.width():
                            # Draw a scaled version of the tile to fill the space exactly
                            painter.drawPixmap(
                                current_x,
                                component["y"],
                                tiling_sprite.scaled(
                                    right_filler_space, tiling_sprite.height()
                                ),
                            )
                        else:
                            # Draw full tiles as before
                            while current_x < right_end_x:
                                remaining_space = right_end_x - current_x
                                if remaining_space >= tiling_sprite.width():
                                    # Draw full tile
                                    painter.drawPixmap(
                                        current_x, component["y"], tiling_sprite
                                    )
                                    current_x += tiling_sprite.width()
                                else:
                                    # Draw a scaled tile to fill remaining space
                                    scaled_tile = tiling_sprite.scaled(
                                        remaining_space, tiling_sprite.height()
                                    )
                                    painter.drawPixmap(
                                        current_x, component["y"], scaled_tile
                                    )
                                    break
        else:
            # If the window is too narrow, draw components in sequence
            # Draw left corner
            for component in top_bar_spec["components"]:
                sprite_pixmap = self._get_sprite_pixmap(component["sprite"])
                if not sprite_pixmap:
                    continue

                if component["id"] == "top_left_corner":
                    painter.drawPixmap(0, component["y"], sprite_pixmap)
                elif component["id"] == "top_title":
                    # Calculate center position in narrow windows too
                    center_pos = (total_width - center_fill_width) // 2
                    center_pos = max(
                        left_corner_width,
                        min(
                            center_pos,
                            total_width - right_corner_width - center_fill_width,
                        ),
                    )
                    painter.drawPixmap(center_pos, component["y"], sprite_pixmap)
                elif component["type"] == "tiled_x":
                    # Tile in the available remaining space
                    start_x = left_corner_width
                    end_x = total_width - right_corner_width
                    current_x = start_x
                    while current_x < end_x:
                        painter.drawPixmap(current_x, component["y"], sprite_pixmap)
                        current_x += sprite_pixmap.width()
                elif component["id"] == "top_right_corner":
                    painter.drawPixmap(
                        total_width - right_corner_width, component["y"], sprite_pixmap
                    )

        # Draw bottom bar
        bottom_bar_spec = regions_map["bottom_bar"]
        bottom_bar_y = self._get_bottom_bar_y()
        bottom_bar_rect = QRect(
            bottom_bar_spec["position"]["x"],
            bottom_bar_y,
            self.width(),
            bottom_bar_spec["height"],
        )
        self._draw_tiled_region(painter, bottom_bar_spec, bottom_bar_rect)

        # Draw bottom bar components if they exist
        if "components" in bottom_bar_spec:
            for component in bottom_bar_spec["components"]:
                if component.get("type") == "conditional":
                    condition = component.get("condition", "False")
                    # Basic evaluation for "window.width >= X"
                    if "window.width" in condition:
                        parts = condition.split(">=")
                        if len(parts) == 2:
                            try:
                                min_width = int(parts[1].strip())
                                if self.width() < min_width:
                                    continue  # Skip this component if condition is not met
                            except ValueError:
                                print(
                                    f"WARNING: Could not parse width from condition: {condition}"
                                )
                                continue

                sprite_pixmap = self._get_sprite_pixmap(component["sprite"])
                if not sprite_pixmap:
                    continue

                comp_x_expr = component["x"]
                if isinstance(comp_x_expr, str):
                    if "window.width" in comp_x_expr:
                        parts = comp_x_expr.split(" - ")
                        base = self.width()
                        offset = sum(int(p.strip()) for p in parts[1:])
                        comp_x = base - offset
                    else:
                        comp_x = int(comp_x_expr)
                else:
                    comp_x = comp_x_expr

                # The y position in the component is relative to the bottom bar's y
                comp_y = self._get_bottom_bar_y() + component["y"]

                painter.drawPixmap(comp_x, comp_y, sprite_pixmap)

        # Draw track area background (solid fill for now)
        track_area_spec = regions_map["track_area"]
        track_area_x = track_area_spec["position"]["x"]
        track_area_y = track_area_spec["position"]["y"]

        track_area_width_expr = track_area_spec["size"]["width"]
        track_area_height_expr = track_area_spec["size"]["height"]

        if isinstance(track_area_width_expr, str) and track_area_width_expr.startswith(
            "window.width - "
        ):
            offset = int(track_area_width_expr.split(" - ")[1])
            track_area_width = self.width() - offset
        else:
            track_area_width = track_area_width_expr

        if isinstance(
            track_area_height_expr, str
        ) and track_area_height_expr.startswith("window.height - "):
            offset = int(track_area_height_expr.split(" - ")[1])
            track_area_height = self.height() - offset
        else:
            track_area_height = track_area_height_expr

        track_area_rect = QRect(
            track_area_x, track_area_y, track_area_width, track_area_height
        )
        painter.fillRect(track_area_rect, self.normal_bg_color)

    def _draw_track_text_lines(self, painter):
        """Draw the playlist item text lines in the track area."""
        regions_map = {
            "top_bar": self.playlist_spec["layout"]["regions"]["top_bar"],
            "left_edge": self.playlist_spec["layout"]["regions"]["left_edge"],
            "right_edge": self.playlist_spec["layout"]["regions"]["right_edge"],
            "bottom_bar": self.playlist_spec["layout"]["regions"]["bottom_bar"],
            "track_area": self.playlist_spec["layout"]["regions"]["track_area"],
        }

        track_area_spec = regions_map["track_area"]
        track_area_x = track_area_spec["position"]["x"]
        track_area_y = track_area_spec["position"]["y"]
        row_height = track_area_spec["row_height"]

        # Calculate visible items
        bottom_bar_y = self._get_bottom_bar_y()
        visible_height = self.height() - track_area_y - (self.height() - bottom_bar_y)
        num_visible_rows = visible_height // row_height

        # Calculate track area dimensions for selection highlighting
        track_area_width_expr = track_area_spec["size"]["width"]
        track_area_height_expr = track_area_spec["size"]["height"]

        if isinstance(track_area_width_expr, str) and track_area_width_expr.startswith(
            "window.width - "
        ):
            offset = int(track_area_width_expr.split(" - ")[1])
            track_area_width = self.width() - offset
        else:
            track_area_width = track_area_width_expr

        if isinstance(
            track_area_height_expr, str
        ) and track_area_height_expr.startswith("window.height - "):
            offset = int(track_area_height_expr.split(" - ")[1])
            track_area_height = self.height() - offset
        else:
            track_area_height = track_area_height_expr

        track_area_rect = QRect(
            track_area_x, track_area_y, track_area_width, track_area_height
        )

        for i in range(num_visible_rows):
            item_index = self.scroll_offset + i
            if item_index < len(self.playlist_items):
                text_to_draw = self.playlist_items[item_index]

                # Set font and color for native text rendering
                painter.setFont(self.playlist_font)

                # Set color based on selection and current track status
                if item_index == self.current_track_index:
                    # Currently playing track - use special color
                    painter.setPen(self.playlist_current_text_color)
                elif item_index in self.selected_items:
                    # Selected track - use current color
                    painter.setPen(self.playlist_current_text_color)
                else:
                    # Normal track - use normal color
                    painter.setPen(self.playlist_normal_text_color)

                # Calculate vertical centering offset using QFontMetrics
                font_metrics = painter.fontMetrics()
                text_height = font_metrics.height()
                vertical_offset = (row_height - text_height) // 2
                text_y = (
                    track_area_y
                    + (i * row_height)
                    + vertical_offset
                    + font_metrics.ascent()
                )  # Adjust for baseline

                # Draw background highlight for this row
                row_rect = QRect(
                    track_area_x,
                    track_area_y + (i * row_height),
                    track_area_rect.width(),
                    row_height,
                )

                # Highlight current playing track differently from selected items
                if item_index == self.current_track_index:
                    # Draw currently playing track background
                    painter.fillRect(row_rect, self.current_playing_bg_color)
                    # If also selected, draw a selection border
                    if item_index in self.selected_items:
                        painter.setPen(
                            QColor(255, 255, 0)
                        )  # Yellow border for selected + current track
                        painter.drawRect(row_rect.adjusted(0, 0, -1, -1))
                elif item_index in self.selected_items:
                    # Draw selection highlight
                    painter.fillRect(row_rect, self.selected_bg_color)
                else:
                    # Draw normal background if not selected or current
                    painter.fillRect(row_rect, self.normal_bg_color)

                painter.drawText(track_area_x, text_y, text_to_draw)

    def _draw_borders_and_edges(self, painter):
        """Draw borders and edges including left and right edges."""
        regions_map = {
            "top_bar": self.playlist_spec["layout"]["regions"]["top_bar"],
            "left_edge": self.playlist_spec["layout"]["regions"]["left_edge"],
            "right_edge": self.playlist_spec["layout"]["regions"]["right_edge"],
            "bottom_bar": self.playlist_spec["layout"]["regions"]["bottom_bar"],
            "track_area": self.playlist_spec["layout"]["regions"]["track_area"],
        }

        # Ensure bottom_bar_y is defined
        bottom_bar_y = self._get_bottom_bar_y()

        # Calculate scrollbar dimensions
        scrollbar_spec = self.playlist_spec["layout"]["controls"]["scrollbar"]
        scrollbar_y = scrollbar_spec["position"]["y"]  # 20

        # Draw left edge
        left_edge_spec = regions_map["left_edge"]
        left_edge_rect = QRect(
            left_edge_spec["position"]["x"],
            left_edge_spec["position"]["y"],
            left_edge_spec["width"],
            self.height()
            - regions_map["top_bar"]["height"]
            - regions_map["bottom_bar"]["height"],
        )
        self._draw_tiled_region(painter, left_edge_spec, left_edge_rect)

        # Draw right edge (scrollbar area)
        right_edge_spec = regions_map["right_edge"]
        right_edge_x = self.width() - right_edge_spec["width"]

        # Adjust right_edge_y and right_edge_height to fit the full height of the scrollbar area
        right_edge_y = scrollbar_y
        right_edge_height = bottom_bar_y - scrollbar_y

        for component in right_edge_spec["components"]:
            sprite_pixmap = self._get_sprite_pixmap(component["sprite"])
            if not sprite_pixmap:
                continue

            comp_x = right_edge_x + component["x"]
            # comp_y is now relative to the new right_edge_y
            comp_y_start = right_edge_y + component["y"]

            if component["type"] == "tiled_y":
                current_y = comp_y_start
                while current_y < right_edge_y + right_edge_height:
                    painter.drawPixmap(comp_x, current_y, sprite_pixmap)
                    current_y += sprite_pixmap.height()
            elif component["type"] == "fixed":
                painter.drawPixmap(comp_x, comp_y_start, sprite_pixmap)

    def _draw_buttons_and_scrollbar(self, painter):
        """Draw buttons and scrollbar including all sub-menu elements."""
        # Draw buttons
        button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]
        button_bar_x = button_bar_spec["position"]["x"]
        # Evaluate "window.height - 30" to center buttons vertically within the 38px bottom bar (corrected 2-pixel offset)
        button_bar_y = self.height() - 30

        for button_data in button_bar_spec["buttons"]:
            button_id = button_data["id"]
            if self.buttonbar_manager.is_button_pressed(
                button_id
            ):  # Check if button is pressed
                sprite_id = (
                    button_data["sprite_pressed"]
                    if "sprite_pressed" in button_data
                    else button_data["sprite"]
                )
                button_pixmap = self._get_sprite_pixmap(sprite_id)
                if button_pixmap:
                    # Calculate dynamic position for LIST button to maintain position relative to right edge
                    if button_id == "list":
                        # Maintain the same distance from right edge as in original skin
                        # Original button position was button_bar_x (14) + list button x (218) = 232
                        # Original window width was approximately 275, button width is 22
                        # Right edge of button was at 232 + 22 = 254
                        # So right margin was 275 - 254 = 21
                        right_margin = 21  # Approximate right margin in original skin

                        # Position button maintaining same margin to right edge
                        button_draw_x = (
                            self.width() - button_pixmap.width() - right_margin
                        )
                    else:
                        # Use fixed positioning for other buttons
                        button_draw_x = button_bar_x + button_data["x"]

                    painter.drawPixmap(
                        button_draw_x, button_bar_y + button_data["y"], button_pixmap
                    )

        # Draw current time display
        self._draw_time_display(painter)

        # Draw playlist time status display
        self._draw_playlist_time_status_display(painter)

        # Draw add button sub-menu if open
        if self.menu_manager.is_menu_open("add"):
            # Get the position of the main "add" button
            add_button_data = next(
                (b for b in button_bar_spec["buttons"] if b["id"] == "add"), None
            )
            if add_button_data:
                main_add_button_x = button_bar_x + add_button_data["x"]
                main_add_button_y = button_bar_y + add_button_data["y"]
                main_add_button_height = 18  # Assuming button height is 18

                # Calculate the starting Y for the sub-menu to align its bottom with the main add button's bottom
                # The sub-menu has 3 buttons, each 18px high, so total height is 3 * 18 = 54px
                # The bottom of the sub-menu should be at main_add_button_y + main_add_button_height
                # So, sub_menu_start_y = (main_add_button_y + main_add_button_height) - (3 * 18)
                sub_menu_start_y = (main_add_button_y + main_add_button_height) - (
                    3 * 18
                )

                # Draw decoration bar (add)
                decoration_bar_sprite = self._get_sprite_pixmap(
                    "PLEDIT_DECORATION_BAR_ADD"
                )
                if decoration_bar_sprite:
                    # Position to the left of the sub-menu buttons, aligned with sub_menu_start_y
                    painter.drawPixmap(
                        main_add_button_x - 3, sub_menu_start_y, decoration_bar_sprite
                    )

                # Draw sub-menu buttons
                # Add URL button
                add_url_sprite_id = (
                    "PLEDIT_ADD_URL_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "add_url"
                    else "PLEDIT_ADD_URL_BUTTON_UNPRESSED"
                )
                add_url_sprite = self._get_sprite_pixmap(add_url_sprite_id)
                if add_url_sprite:
                    painter.drawPixmap(
                        main_add_button_x, sub_menu_start_y + 0, add_url_sprite
                    )

                # Add DIR button
                add_dir_sprite_id = (
                    "PLEDIT_ADD_DIR_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "add_dir"
                    else "PLEDIT_ADD_DIR_BUTTON_UNPRESSED"
                )
                add_dir_sprite = self._get_sprite_pixmap(add_dir_sprite_id)
                if add_dir_sprite:
                    painter.drawPixmap(
                        main_add_button_x, sub_menu_start_y + 18, add_dir_sprite
                    )

                # Add FILE button
                add_file_sprite_id = (
                    "PLEDIT_ADD_FILE_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "add_file"
                    else "PLEDIT_ADD_FILE_BUTTON_UNPRESSED"
                )
                add_file_sprite = self._get_sprite_pixmap(add_file_sprite_id)
                if add_file_sprite:
                    painter.drawPixmap(
                        main_add_button_x, sub_menu_start_y + 36, add_file_sprite
                    )
        elif self.menu_manager.is_menu_open("remove"):
            remove_button_data = next(
                (b for b in button_bar_spec["buttons"] if b["id"] == "remove"), None
            )
            if remove_button_data:
                main_remove_button_x = button_bar_x + remove_button_data["x"]
                main_remove_button_y = button_bar_y + remove_button_data["y"]
                main_remove_button_height = 18

                sub_menu_start_y = (
                    main_remove_button_y + main_remove_button_height
                ) - (
                    4 * 18
                )  # 4 buttons in remove menu

                decoration_bar_sprite = self._get_sprite_pixmap(
                    "PLEDIT_DECORATION_BAR_REMOVE"
                )
                if decoration_bar_sprite:
                    painter.drawPixmap(
                        main_remove_button_x - 3,
                        sub_menu_start_y,
                        decoration_bar_sprite,
                    )

                remove_duplicates_sprite_id = (
                    "PLEDIT_MISC_REMOVE_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id
                    == "remove_duplicates"
                    else "PLEDIT_MISC_REMOVE_BUTTON_UNPRESSED"
                )
                remove_duplicates_sprite = self._get_sprite_pixmap(
                    remove_duplicates_sprite_id
                )
                if remove_duplicates_sprite:
                    painter.drawPixmap(
                        main_remove_button_x,
                        sub_menu_start_y + 0,
                        remove_duplicates_sprite,
                    )

                remove_all_sprite_id = (
                    "PLEDIT_REMOVE_ALL_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "remove_all"
                    else "PLEDIT_REMOVE_ALL_BUTTON_UNPRESSED"
                )
                remove_all_sprite = self._get_sprite_pixmap(remove_all_sprite_id)
                if remove_all_sprite:
                    painter.drawPixmap(
                        main_remove_button_x, sub_menu_start_y + 18, remove_all_sprite
                    )

                crop_sprite_id = (
                    "PLEDIT_CROP_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "crop"
                    else "PLEDIT_CROP_BUTTON_UNPRESSED"
                )
                crop_sprite = self._get_sprite_pixmap(crop_sprite_id)
                if crop_sprite:
                    painter.drawPixmap(
                        main_remove_button_x, sub_menu_start_y + 36, crop_sprite
                    )

                remove_selected_sprite_id = (
                    "PLEDIT_REMOVE_FILE_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "remove_selected"
                    else "PLEDIT_REMOVE_FILE_BUTTON_UNPRESSED"
                )
                remove_selected_sprite = self._get_sprite_pixmap(
                    remove_selected_sprite_id
                )
                if remove_selected_sprite:
                    painter.drawPixmap(
                        main_remove_button_x,
                        sub_menu_start_y + 54,
                        remove_selected_sprite,
                    )

        elif self.menu_manager.is_menu_open("select"):
            select_button_data = next(
                (b for b in button_bar_spec["buttons"] if b["id"] == "select"), None
            )
            if select_button_data:
                main_select_button_x = button_bar_x + select_button_data["x"]
                main_select_button_y = button_bar_y + select_button_data["y"]
                main_select_button_height = 18

                sub_menu_start_y = (
                    main_select_button_y + main_select_button_height
                ) - (
                    3 * 18
                )  # 3 buttons

                decoration_bar_sprite = self._get_sprite_pixmap(
                    "PLEDIT_DECORATION_BAR_SELECT"
                )
                if decoration_bar_sprite:
                    painter.drawPixmap(
                        main_select_button_x - 3,
                        sub_menu_start_y,
                        decoration_bar_sprite,
                    )

                invert_selection_sprite_id = (
                    "PLEDIT_INVERT_SELECTION_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id
                    == "invert_selection"
                    else "PLEDIT_INVERT_SELECTION_BUTTON_UNPRESSED"
                )
                invert_selection_sprite = self._get_sprite_pixmap(
                    invert_selection_sprite_id
                )
                if invert_selection_sprite:
                    painter.drawPixmap(
                        main_select_button_x,
                        sub_menu_start_y + 0,
                        invert_selection_sprite,
                    )

                select_none_sprite_id = (
                    "PLEDIT_SELECT_NONE_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "select_none"
                    else "PLEDIT_SELECT_NONE_BUTTON_UNPRESSED"
                )
                select_none_sprite = self._get_sprite_pixmap(select_none_sprite_id)
                if select_none_sprite:
                    painter.drawPixmap(
                        main_select_button_x, sub_menu_start_y + 18, select_none_sprite
                    )

                select_all_sprite_id = (
                    "PLEDIT_SELECT_ALL_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "select_all"
                    else "PLEDIT_SELECT_ALL_BUTTON_UNPRESSED"
                )
                select_all_sprite = self._get_sprite_pixmap(select_all_sprite_id)
                if select_all_sprite:
                    painter.drawPixmap(
                        main_select_button_x, sub_menu_start_y + 36, select_all_sprite
                    )

        elif self.menu_manager.is_menu_open("misc"):
            misc_button_data = next(
                (b for b in button_bar_spec["buttons"] if b["id"] == "misc"), None
            )
            if misc_button_data:
                main_misc_button_x = button_bar_x + misc_button_data["x"]
                main_misc_button_y = button_bar_y + misc_button_data["y"]
                main_misc_button_height = 18

                sub_menu_start_y = (main_misc_button_y + main_misc_button_height) - (
                    3 * 18
                )  # 3 buttons

                decoration_bar_sprite = self._get_sprite_pixmap(
                    "PLEDIT_DECORATION_BAR_MISC"
                )
                if decoration_bar_sprite:
                    painter.drawPixmap(
                        main_misc_button_x - 3, sub_menu_start_y, decoration_bar_sprite
                    )

                sort_list_sprite_id = (
                    "PLEDIT_SORT_LIST_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "sort_list"
                    else "PLEDIT_SORT_LIST_BUTTON_UNPRESSED"
                )
                sort_list_sprite = self._get_sprite_pixmap(sort_list_sprite_id)
                if sort_list_sprite:
                    painter.drawPixmap(
                        main_misc_button_x, sub_menu_start_y + 0, sort_list_sprite
                    )

                file_info_sprite_id = (
                    "PLEDIT_FILE_INFO_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "file_info"
                    else "PLEDIT_FILE_INFO_BUTTON_UNPRESSED"
                )
                file_info_sprite = self._get_sprite_pixmap(file_info_sprite_id)
                if file_info_sprite:
                    painter.drawPixmap(
                        main_misc_button_x, sub_menu_start_y + 18, file_info_sprite
                    )

                misc_options_sprite_id = (
                    "PLEDIT_MISC_OPTIONS_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "misc_options"
                    else "PLEDIT_MISC_OPTIONS_BUTTON_UNPRESSED"
                )
                misc_options_sprite = self._get_sprite_pixmap(misc_options_sprite_id)
                if misc_options_sprite:
                    painter.drawPixmap(
                        main_misc_button_x, sub_menu_start_y + 36, misc_options_sprite
                    )

        elif self.menu_manager.is_menu_open("list"):
            list_button_data = next(
                (b for b in button_bar_spec["buttons"] if b["id"] == "list"), None
            )
            if list_button_data:
                # Use the same dynamic positioning for the LIST button as in the button manager
                # Maintain the same distance from right edge as in original skin
                # Original button position was button_bar_x (14) + list button x (218) = 232
                # Original window width was approximately 275, button width is 22
                # Right edge of button was at 232 + 22 = 254
                # So right margin was 275 - 254 = 21
                right_margin = 21  # Approximate right margin in original skin

                # Position button maintaining same margin to right edge
                main_list_button_x = (
                    self.width() - 22 - right_margin
                )  # 22 is typical button width
                # Calculate Y position using the same logic as in the other event handlers
                button_bar_y_calc = self.height() - 28  # Consistent with other handlers
                main_list_button_y = button_bar_y_calc + list_button_data["y"]
                main_list_button_height = 18

                sub_menu_start_y = (main_list_button_y + main_list_button_height) - (
                    3 * 18
                )  # 3 buttons

                decoration_bar_sprite = self._get_sprite_pixmap(
                    "PLEDIT_DECORATION_BAR_LIST"
                )
                if decoration_bar_sprite:
                    painter.drawPixmap(
                        main_list_button_x - 3, sub_menu_start_y, decoration_bar_sprite
                    )

                new_list_sprite_id = (
                    "PLEDIT_NEW_LIST_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "new_list"
                    else "PLEDIT_NEW_LIST_BUTTON_UNPRESSED"
                )
                new_list_sprite = self._get_sprite_pixmap(new_list_sprite_id)
                if new_list_sprite:
                    painter.drawPixmap(
                        main_list_button_x, sub_menu_start_y + 0, new_list_sprite
                    )

                save_list_sprite_id = (
                    "PLEDIT_SAVE_LIST_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "save_list"
                    else "PLEDIT_SAVE_LIST_BUTTON_UNPRESSED"
                )
                save_list_sprite = self._get_sprite_pixmap(save_list_sprite_id)
                if save_list_sprite:
                    painter.drawPixmap(
                        main_list_button_x, sub_menu_start_y + 18, save_list_sprite
                    )

                load_list_sprite_id = (
                    "PLEDIT_LOAD_LIST_BUTTON_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == "load_list"
                    else "PLEDIT_LOAD_LIST_BUTTON_UNPRESSED"
                )
                load_list_sprite = self._get_sprite_pixmap(load_list_sprite_id)
                if load_list_sprite:
                    painter.drawPixmap(
                        main_list_button_x, sub_menu_start_y + 36, load_list_sprite
                    )

        # Draw scrollbar
        scrollbar_spec = self.playlist_spec["layout"]["controls"]["scrollbar"]

        # Get track area spec for scrollbar calculations
        track_area_spec = self.playlist_spec["layout"]["regions"]["track_area"]

        # Draw scrollbar track (tiled vertically)
        track_sprite_id = scrollbar_spec["elements"]["track"]
        track_pixmap = self._get_sprite_pixmap(track_sprite_id)
        if track_pixmap:
            track_rect = self._get_scrollbar_element_rect("track")
            current_y = track_rect.y()
            while current_y < track_rect.y() + track_rect.height():
                painter.drawPixmap(track_rect.x(), current_y, track_pixmap)
                current_y += track_pixmap.height()

        # Draw scrollbar thumb
        thumb_pixmap = self._get_sprite_pixmap(scrollbar_spec["elements"]["thumb"])
        if thumb_pixmap and len(self.playlist_items) > 0:
            track_rect = self._get_scrollbar_element_rect("track")

            # Calculate thumb height
            num_visible_rows = track_rect.height() // track_area_spec["row_height"]
            total_rows = len(self.playlist_items)

            if total_rows > num_visible_rows:
                # Proportional height
                thumb_height = thumb_pixmap.height()
            else:
                # If all items are visible, thumb fills the track or is min_thumb_height
                thumb_height = (
                    thumb_pixmap.height()
                )  # If all items visible, thumb fills the track

            # Calculate thumb position
            # The scrollable range for the thumb is track_rect.height() - thumb_height
            # The scrollable range for items is total_rows - num_visible_rows
            if total_rows > num_visible_rows:
                scroll_range_pixels = track_rect.height() - thumb_height
                scroll_range_items = total_rows - num_visible_rows
                thumb_y_offset = int(
                    scroll_range_pixels * (self.scroll_offset / scroll_range_items)
                )
            else:
                thumb_y_offset = 0  # No scrolling needed, thumb at top

            thumb_rect = QRect(
                track_rect.x(),
                track_rect.y() + thumb_y_offset,
                thumb_pixmap.width(),
                thumb_height,
            )
            painter.drawPixmap(thumb_rect.topLeft(), thumb_pixmap)

        # Draw close button pressed state overlay when button is clicked
        # The normal state is part of the top-right corner sprite, only draw the pressed overlay
        if self._is_close_pressed:
            # Get the pressed state sprite specifically
            close_button_spec = self.playlist_spec["layout"]["controls"]["close_button"]
            # Use the pressed sprite if available
            if "sprite_pressed" in close_button_spec:
                sprite_id = close_button_spec["sprite_pressed"]
                close_button_pixmap = self._get_sprite_pixmap(sprite_id)
                if close_button_pixmap:
                    # Draw the pressed state overlay at the calculated button position
                    close_button_rect = self._get_close_button_rect()
                    painter.drawPixmap(
                        close_button_rect.x(),
                        close_button_rect.y(),
                        close_button_pixmap,
                    )

        # Note: Up and down arrow buttons are not drawn in this implementation

    def mousePressEvent(self, event):
        # Bring all related windows to foreground when clicked
        if self.main_window:
            self.main_window.bring_all_windows_to_foreground()

        if event.button() == Qt.LeftButton:
            # Check for close button first (before titlebar dragging, since it's in the titlebar area)
            close_button_rect = self._get_close_button_rect()
            if close_button_rect.contains(event.pos()):
                self._is_close_pressed = True
                self.update()
                return

            # Check if click is on titlebar for window dragging
            # Titlebar is at the top of the window, typically 14 pixels high
            titlebar_rect = QRect(0, 0, self.width(), 14)
            if titlebar_rect.contains(event.pos()):
                self._dragging_window = True
                self._drag_start_position = (
                    event.globalPos() - self.frameGeometry().topLeft()
                )
                return

            # Check for clicks outside open sub-menus
            menu_closed = self.menu_manager.handle_outside_click(event.pos())
            if menu_closed:
                self.update()
                return  # Event handled, stop further processing

            # Check for resize handle
            if self._handle_resize_press(event):
                return  # Event handled, stop further processing

            # Check for button presses
            if self._handle_button_press(event):
                return  # Event handled, stop further processing

            # Check for scrollbar element presses
            if self._handle_scrollbar_press(event):
                return  # Event handled, stop further processing

            # Check for track area clicks for selection
            if self._handle_track_area_click(event):
                return  # Event handled, stop further processing

        super().mousePressEvent(event)

    def focusInEvent(self, event):
        """Called when the playlist window receives focus."""
        # Bring all related windows to foreground when playlist gains focus
        if self.main_window:
            self.main_window.bring_all_windows_to_foreground()
        super().focusInEvent(event)

    def mouseDoubleClickEvent(self, event):
        """Handle double-click events on tracks to start playback from that track."""
        if event.button() == Qt.LeftButton:
            # Check if double-click is in the track area
            track_area_spec = self.playlist_spec["layout"]["regions"]["track_area"]
            track_area_x = track_area_spec["position"]["x"]
            track_area_y = track_area_spec["position"]["y"]
            row_height = track_area_spec["row_height"]

            # Calculate dynamic width and height for the track area
            track_area_width_expr = track_area_spec["size"]["width"]
            track_area_height_expr = track_area_spec["size"]["height"]

            window_width = self.width()
            window_height = self.height()

            if isinstance(
                track_area_width_expr, str
            ) and track_area_width_expr.startswith("window.width - "):
                offset = int(track_area_width_expr.split(" - ")[1])
                track_area_width = window_width - offset
            else:
                track_area_width = track_area_width_expr

            if isinstance(
                track_area_height_expr, str
            ) and track_area_height_expr.startswith("window.height - "):
                offset = int(track_area_height_expr.split(" - ")[1])
                track_area_height = window_height - offset
            else:
                track_area_height = track_area_height_expr

            track_area_rect = QRect(
                track_area_x, track_area_y, track_area_width, track_area_height
            )

            if track_area_rect.contains(event.pos()):
                relative_y = event.pos().y() - track_area_y
                clicked_row_in_view = relative_y // row_height
                clicked_item_index = self.scroll_offset + clicked_row_in_view

                if 0 <= clicked_item_index < len(self.playlist_items):
                    # Handle double-click: play the selected track
                    self._play_track_at_index(clicked_item_index)

                    # Also select the track for visual feedback
                    self.selected_items.clear()
                    self.selected_items.add(clicked_item_index)
                    self.last_selected_item_index = clicked_item_index
                    self.update()
                    return  # Event handled

        # If not in track area or not a left double-click, let the parent handle it
        super().mouseDoubleClickEvent(event)

    def _play_track_at_index(self, index):
        """Play the track at the given index through the main window."""
        if self.main_window and 0 <= index < len(self.playlist_items):
            # Call the main window's play_selected_track method
            self.main_window.play_selected_track(index)

    def mouseMoveEvent(self, event):
        if self._dragging_window:
            # Calculate the new position
            new_pos = event.globalPos() - self._drag_start_position

            # Check for snapping with main window and other windows if main window exists
            if self.main_window:
                # Get the potential new rectangle for this window
                new_rect = QRect(new_pos, self.size())

                # Use the main window's window-to-window snapping algorithm
                snap_x, snap_y, should_snap = (
                    self.main_window.get_window_snap_alignment(
                        new_rect, exclude_window=self
                    )
                )

                if should_snap:
                    # Snap to the calculated position
                    self.is_docked = True
                    self.move(snap_x, snap_y)
                    # Store the offset from the snapped position in case the window is un-snapped later
                    self.docking_offset = new_pos - QPoint(snap_x, snap_y)
                else:
                    # Check if we're significantly far from any snapped position to un-snap
                    # If we were previously snapped and now we're moving away from snapped position
                    if self.is_docked:
                        # Determine if we've moved far enough to un-snap (more than 25 pixels)
                        current_pos = QPoint(self.x(), self.y())
                        distance_moved = (
                            (new_pos.x() - current_pos.x()) ** 2
                            + (new_pos.y() - current_pos.y()) ** 2
                        ) ** 0.5
                        # If moved more than 25 pixels from snapped position, un-snap
                        if distance_moved > 25:
                            self.is_docked = False

                    # If not snapping, move to the calculated position
                    self.move(new_pos)
            else:
                # No main window reference, move normally
                self.move(event.globalPos() - self._drag_start_position)
            return
        if self._resizing:
            self._handle_resize_move(event)
            return  # Consume event for resizing
        elif self.scrollbar_manager.dragging_thumb:
            self._handle_scrollbar_drag_move(event)
            return

        # Change cursor based on hover position
        self._update_cursor_for_hover(event)

        # Handle sub-menu button hover
        self._handle_submenu_hover(event)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._dragging_window:
                self._dragging_window = False
                return
            if self._resizing:
                self._resizing = False
                self.unsetCursor()  # Restore default cursor
                return  # Consume event for resizing
            elif self.scrollbar_manager.dragging_thumb:
                self.scrollbar_manager.end_thumb_drag()
                self.unsetCursor()  # Restore default cursor
                return  # Consume event for dragging

            # Reset all pressed states
            self.buttonbar_manager.clear_pressed_buttons()
            self.scrollbar_manager.pressed_elements.clear()
            self.update()  # Request repaint to show normal state

            # Handle sub-menu button clicks BEFORE main button clicks to ensure proper event handling
            # when submenu buttons overlap with main control buttons
            button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]
            button_bar_x = button_bar_spec["position"]["x"]
            # Use the same button_bar_y calculation as in paintEvent
            button_bar_y = self.height() - 30

            # Handle sub-menu button clicks if any menu is open
            if self.menu_manager.is_menu_open("add"):
                add_button_data = next(
                    (b for b in button_bar_spec["buttons"] if b["id"] == "add"), None
                )
                if add_button_data:
                    main_add_button_x = button_bar_x + add_button_data["x"]
                    main_add_button_y = button_bar_y + add_button_data["y"]
                    main_add_button_height = 18
                    sub_menu_start_y = (main_add_button_y + main_add_button_height) - (
                        3 * 18
                    )

                    add_url_rect = QRect(
                        main_add_button_x, sub_menu_start_y + 0, 22, 18
                    )
                    add_dir_rect = QRect(
                        main_add_button_x, sub_menu_start_y + 18, 22, 18
                    )
                    add_file_rect = QRect(
                        main_add_button_x, sub_menu_start_y + 36, 22, 18
                    )

                    if add_url_rect.contains(event.pos()):
                        self._load_url_to_playlist()
                        self._close_all_sub_menus()
                        return
                    elif add_dir_rect.contains(event.pos()):
                        self._load_directory_to_playlist()
                        self._close_all_sub_menus()
                        return
                    elif add_file_rect.contains(event.pos()):
                        self._load_file_to_playlist()  # Re-using existing function for now
                        self._close_all_sub_menus()
                        return
            elif self.menu_manager.is_menu_open("remove"):
                remove_button_data = next(
                    (b for b in button_bar_spec["buttons"] if b["id"] == "remove"), None
                )
                if remove_button_data:
                    main_remove_button_x = button_bar_x + remove_button_data["x"]
                    main_remove_button_y = button_bar_y + remove_button_data["y"]
                    main_remove_button_height = 18
                    sub_menu_start_y = (
                        main_remove_button_y + main_remove_button_height
                    ) - (4 * 18)

                    remove_duplicates_rect = QRect(
                        main_remove_button_x, sub_menu_start_y + 0, 22, 18
                    )
                    remove_all_rect = QRect(
                        main_remove_button_x, sub_menu_start_y + 18, 22, 18
                    )
                    crop_rect = QRect(
                        main_remove_button_x, sub_menu_start_y + 36, 22, 18
                    )
                    remove_selected_rect = QRect(
                        main_remove_button_x, sub_menu_start_y + 54, 22, 18
                    )

                    if remove_duplicates_rect.contains(event.pos()):
                        self._remove_duplicate_tracks()
                        self._close_all_sub_menus()
                        return
                    elif remove_all_rect.contains(event.pos()):
                        self._remove_all_tracks()
                        self._close_all_sub_menus()
                        return
                    elif crop_rect.contains(event.pos()):
                        self._crop_playlist()
                        self._close_all_sub_menus()
                        return
                    elif remove_selected_rect.contains(event.pos()):
                        self.remove_playlist_item()  # Reuse existing functionality
                        self._close_all_sub_menus()
                        return
            elif self.menu_manager.is_menu_open("select"):
                select_button_data = next(
                    (b for b in button_bar_spec["buttons"] if b["id"] == "select"), None
                )
                if select_button_data:
                    main_select_button_x = button_bar_x + select_button_data["x"]
                    main_select_button_y = button_bar_y + select_button_data["y"]
                    main_select_button_height = 18
                    sub_menu_start_y = (
                        main_select_button_y + main_select_button_height
                    ) - (3 * 18)

                    invert_selection_rect = QRect(
                        main_select_button_x, sub_menu_start_y + 0, 22, 18
                    )
                    select_none_rect = QRect(
                        main_select_button_x, sub_menu_start_y + 18, 22, 18
                    )
                    select_all_rect = QRect(
                        main_select_button_x, sub_menu_start_y + 36, 22, 18
                    )

                    if invert_selection_rect.contains(event.pos()):
                        self._invert_selection()
                        self._close_all_sub_menus()
                        return
                    elif select_none_rect.contains(event.pos()):
                        self._select_none()
                        self._close_all_sub_menus()
                        return
                    elif select_all_rect.contains(event.pos()):
                        self._select_all()
                        self._close_all_sub_menus()
                        return
            elif self.menu_manager.is_menu_open("misc"):
                misc_button_data = next(
                    (b for b in button_bar_spec["buttons"] if b["id"] == "misc"), None
                )
                if misc_button_data:
                    main_misc_button_x = button_bar_x + misc_button_data["x"]
                    main_misc_button_y = button_bar_y + misc_button_data["y"]
                    main_misc_button_height = 18
                    sub_menu_start_y = (
                        main_misc_button_y + main_misc_button_height
                    ) - (3 * 18)

                    sort_list_rect = QRect(
                        main_misc_button_x, sub_menu_start_y + 0, 22, 18
                    )
                    file_info_rect = QRect(
                        main_misc_button_x, sub_menu_start_y + 18, 22, 18
                    )
                    misc_options_rect = QRect(
                        main_misc_button_x, sub_menu_start_y + 36, 22, 18
                    )

                    if sort_list_rect.contains(event.pos()):
                        self._show_sort_dialog()
                        self._close_all_sub_menus()
                        return
                    elif file_info_rect.contains(event.pos()):
                        self._show_file_info()
                        self._close_all_sub_menus()
                        return
                    elif misc_options_rect.contains(event.pos()):
                        self._show_misc_options()
                        self._close_all_sub_menus()
                        return
            elif self.menu_manager.is_menu_open("list"):
                list_button_data = next(
                    (b for b in button_bar_spec["buttons"] if b["id"] == "list"), None
                )
                if list_button_data:
                    # Use the same dynamic positioning for the LIST button as in the button manager
                    # Maintain the same distance from right edge as in original skin
                    # Original button position was button_bar_x (14) + list button x (218) = 232
                    # Original window width was approximately 275, button width is 22
                    # Right edge of button was at 232 + 22 = 254
                    # So right margin was 275 - 254 = 21
                    right_margin = 21  # Approximate right margin in original skin

                    # Position button maintaining same margin to right edge
                    main_list_button_x = (
                        self.width() - 22 - right_margin
                    )  # 22 is typical button width
                    # Use the same Y position calculation as other buttons in this event handler
                    main_list_button_y = button_bar_y + list_button_data["y"]
                    main_list_button_height = 18
                    sub_menu_start_y = (
                        main_list_button_y + main_list_button_height
                    ) - (3 * 18)

                    new_list_rect = QRect(
                        main_list_button_x, sub_menu_start_y + 0, 22, 18
                    )
                    save_list_rect = QRect(
                        main_list_button_x, sub_menu_start_y + 18, 22, 18
                    )
                    load_list_rect = QRect(
                        main_list_button_x, sub_menu_start_y + 36, 22, 18
                    )

                    if new_list_rect.contains(event.pos()):
                        self._new_playlist()
                        self._close_all_sub_menus()
                        return
                    elif save_list_rect.contains(event.pos()):
                        self._save_playlist()  # Re-using existing function
                        self._close_all_sub_menus()
                        return
                    elif load_list_rect.contains(event.pos()):
                        self._load_playlist_from_file()  # Re-using existing function
                        self._close_all_sub_menus()
                        return

            # Handle main button clicks (only toggle menus, no direct actions)
            # Only check main buttons if NO submenu is currently open
            if not (
                self.menu_manager.is_menu_open("add")
                or self.menu_manager.is_menu_open("remove")
                or self.menu_manager.is_menu_open("select")
                or self.menu_manager.is_menu_open("misc")
                or self.menu_manager.is_menu_open("list")
            ):
                for button_data in button_bar_spec["buttons"]:
                    button_id = button_data["id"]
                    button_pixmap = self._get_sprite_pixmap(button_data["sprite"])
                    if button_pixmap:
                        button_rect = self.buttonbar_manager.get_button_rect(
                            button_data
                        )
                        if button_rect.contains(event.pos()):
                            # All main buttons only toggle their respective menus (per SPEC_PLAYLIST.md)
                            # Actual actions are performed by submenu buttons
                            self.menu_manager.toggle_menu(button_id)
                            self.update()
                            return

            # Check if the release happened on any transport buttons, and if so, reset their pressed state
            # Need to check the same rectangles defined in _handle_button_press
            bottom_bar_y = self._get_bottom_bar_y()

            # Get the right control bar sprite and its actual position in the window
            right_control_bar_sprite = self._get_sprite_pixmap(
                "PLEDIT_BOTTOM_RIGHT_CONTROL_BAR"
            )
            if right_control_bar_sprite:
                # The right control bar is positioned at the right side of the bottom bar
                right_control_bar_x = self.width() - right_control_bar_sprite.width()

                transport_button_rects = {
                    "previous": QRect(
                        right_control_bar_x + 6, bottom_bar_y + 22, 7, 8
                    ),  # x=6, y=22 within sprite
                    "play": QRect(
                        right_control_bar_x + 14, bottom_bar_y + 22, 8, 8
                    ),  # x=14, y=22 within sprite
                    "pause": QRect(
                        right_control_bar_x + 23, bottom_bar_y + 22, 9, 8
                    ),  # x=23, y=22 within sprite
                    "stop": QRect(
                        right_control_bar_x + 33, bottom_bar_y + 22, 9, 8
                    ),  # x=33, y=22 within sprite
                    "next": QRect(
                        right_control_bar_x + 43, bottom_bar_y + 22, 7, 8
                    ),  # x=43, y=22 within sprite
                    "open": QRect(
                        right_control_bar_x + 51, bottom_bar_y + 22, 9, 8
                    ),  # x=51, y=22 within sprite
                }
            else:
                # Fallback to empty dict if sprite not available
                transport_button_rects = {}

            for control_name, rect in transport_button_rects.items():
                if rect.contains(event.pos()):
                    # For play/pause/stop, don't reset immediately since their state should reflect playback status
                    # Only reset previous, next, and eject buttons on release
                    if control_name in ["previous", "next", "open"]:
                        if control_name == "previous" and self._is_previous_pressed:
                            self._is_previous_pressed = False
                        elif control_name == "next" and self._is_next_pressed:
                            self._is_next_pressed = False
                        elif control_name == "open" and self._is_eject_pressed:
                            self._is_eject_pressed = False
                        self.update()
                        return
                    # For play/pause/stop, update their states based on the actual audio engine state
                    elif control_name in ["play", "pause", "stop"] and self.main_window:
                        # Update the UI to reflect actual audio engine state
                        state = self.main_window.audio_engine.get_playback_state()
                        self._is_play_pressed = (
                            state["is_playing"] and not state["is_paused"]
                        )
                        self._is_pause_pressed = state["is_paused"]
                        self._is_stop_pressed = not (
                            state["is_playing"] or state["is_paused"]
                        )
                        self.update()
                        return

            # Check if close button was pressed and released over the button to close the window
            close_button_rect = self._get_close_button_rect()
            if close_button_rect.contains(event.pos()) and self._is_close_pressed:
                # Close the window when the close button is clicked
                self.close()
                return
            else:
                # If mouse was released outside the close button, reset its state
                self._is_close_pressed = False
                self.update()

        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        """Called when the mouse enters the widget."""
        # Handle potential hover effects for buttons if needed in the future
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Called when the mouse leaves the widget."""
        # Reset button states when mouse leaves the window
        if self._is_close_pressed:
            self._is_close_pressed = False
            self.update()
        super().leaveEvent(event)

    def closeEvent(self, event):
        """Override close event to delegate to main window for centralized state management."""
        # Only update main window's state if not in global shutdown
        if (
            not getattr(self.main_window, "_is_shutting_down", False)
            and self.main_window
            and hasattr(self.main_window, "hide_playlist_window")
        ):

            # Call the main window's centralized method to hide the playlist window
            # This ensures consistent state management from a single source of truth
            self.main_window.hide_playlist_window()

        # Accept the close event to actually close the window
        event.accept()

    def _format_time(self, total_seconds):
        """Format time in seconds to MM:SS or H:MM:SS format."""
        total_seconds = int(total_seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def _get_playlist_total_time(self):
        """Calculate the total time of all tracks in the playlist."""
        # First try to use the internal playlist_filepaths if available
        playlist_filepaths = getattr(self, "playlist_filepaths", [])

        # If internal playlist_filepaths is empty, try to get from main window
        if not playlist_filepaths and self.main_window:
            playlist_filepaths = getattr(self.main_window, "playlist", [])

        if not playlist_filepaths:
            return 0.0

        total_time = 0.0
        for filepath in playlist_filepaths:
            # First check if we have the duration cached
            if filepath in self._track_durations_cache:
                total_time += self._track_durations_cache[filepath]
            # Try to get duration from metadata if the file is already loaded in the main engine
            elif (
                self.main_window
                and self.main_window.audio_engine.file_path == filepath
                and self.main_window.audio_engine.duration > 0
            ):
                duration = self.main_window.audio_engine.duration
                self._track_durations_cache[filepath] = duration
                total_time += duration
            else:
                # For files not currently loaded, use mutagen to get the duration efficiently
                try:
                    from mutagen import File as MutagenFile

                    audio_file = MutagenFile(filepath)
                    if audio_file is not None and hasattr(audio_file, "info"):
                        duration = getattr(audio_file.info, "length", 0.0)
                        # Cache the duration for future use
                        self._track_durations_cache[filepath] = duration
                        total_time += duration
                    else:
                        # Could not get duration with mutagen
                        self._track_durations_cache[filepath] = 0.0
                except Exception:
                    # If we can't get the duration, skip this track and cache as 0
                    self._track_durations_cache[filepath] = 0.0
                    continue

        return total_time

    def _draw_time_display(self, painter):
        """Draw the current time display (minutes and seconds) using text renderer."""
        if not self.main_window or not self.text_renderer:
            return

        # Get current playback state from main window
        state = self.main_window.audio_engine.get_playback_state()
        current_position = state.get("position", 0.0)

        # Calculate minutes and seconds
        total_seconds = int(current_position)
        minutes = total_seconds // 60
        seconds = total_seconds % 60

        # Format as two-digit strings
        minutes_str = f"{minutes:02d}"  # Two-digit minutes string (e.g., "05", "12")
        seconds_str = f"{seconds:02d}"  # Two-digit seconds string (e.g., "05", "43")

        # Get the right control bar sprite position to place the time display
        right_control_bar_sprite = self._get_sprite_pixmap(
            "PLEDIT_BOTTOM_RIGHT_CONTROL_BAR"
        )
        if right_control_bar_sprite:
            right_control_bar_x = self.width() - right_control_bar_sprite.width()
            bottom_bar_y = self._get_bottom_bar_y()

            # The time display areas are located in the control bar at specific coordinates
            # According to the spec: PLEDIT_CURRENT_TIME_MINUTES at x=190, y=95 and PLEDIT_CURRENT_TIME_SECONDS at x=212, y=95
            # These are relative to the control bar sprite: minutes at (190-126=64, 95-72=23) and seconds at (212-126=86, 23)

            # Calculate base positions for minutes and seconds displays
            minutes_display_x = right_control_bar_x + 64  # 190 - 126
            seconds_display_x = right_control_bar_x + 86  # 212 - 126
            time_display_y = bottom_bar_y + 23  # 95 - 72

            # Draw minutes digits - right-aligned within the minutes display area
            # Minutes display area is 19px wide, 2 digits take 10px (2 * 5px), so right-align by moving right
            minutes_text_width = len(minutes_str) * 5  # 5px per character
            minutes_right_aligned_x = (
                minutes_display_x + 19 - minutes_text_width - 1
            )  # Right-align within 19px area with 1px padding
            self.text_renderer.render_text(
                painter, minutes_str, minutes_right_aligned_x, time_display_y
            )

            # Draw seconds digits - left-aligned within the seconds display area
            # Seconds display area is 10px wide, 2 digits take 10px (2 * 5px), so use base position
            self.text_renderer.render_text(
                painter, seconds_str, seconds_display_x, time_display_y
            )

    def _draw_playlist_time_status_display(self, painter):
        """Draw the playlist time status display showing current / total time."""
        if not self.main_window or not self.text_renderer:
            return

        # Get the PLEDIT_TIME_STATUS_DISPLAY sprite position
        time_status_sprite = self._get_sprite_pixmap("PLEDIT_TIME_STATUS_DISPLAY")
        if time_status_sprite:
            # Position is relative to bottom right control bar
            right_control_bar_sprite = self._get_sprite_pixmap(
                "PLEDIT_BOTTOM_RIGHT_CONTROL_BAR"
            )
            if right_control_bar_sprite:
                right_control_bar_x = self.width() - right_control_bar_sprite.width()
                bottom_bar_y = self._get_bottom_bar_y()

                # According to the spec: PLEDIT_TIME_STATUS_DISPLAY at (133, 82) in the sprite
                # So relative to the control bar: x = 133 - 126 = 7, y = 82 - 72 = 10
                time_status_x = right_control_bar_x + 7  # 133 - 126
                time_status_y = bottom_bar_y + 10  # 82 - 72

                # Format the time as "0:00 / total_time"
                current_time_str = "0:00"
                total_time = self._get_playlist_total_time()
                total_time_str = self._format_time(total_time)

                display_text = f"{current_time_str} / {total_time_str}"

                # Draw the formatted time string - right-aligned within the display area
                text_width = len(display_text) * 5  # 5px per character
                display_area_width = time_status_sprite.width()

                # Right-align the text within the display area
                text_x = (
                    time_status_x + display_area_width - text_width - 2
                )  # 2px padding from right edge
                # Adjust vertical position - the time status area is 6px high
                # Position the text at the top of the area
                text_y = time_status_y  # Align to top of the 6px area

                # Use a smaller font or scale for better fit if needed
                self.text_renderer.render_text(painter, display_text, text_x, text_y)

    def resizeEvent(self, event):
        # Call the parent's resize event first to update the size
        super().resizeEvent(event)

        # Apply stepped resize constraints to ensure the window maintains proper proportions
        self._apply_stepped_resize_constraints()

        # Cancel any active thumb dragging when window is resized
        if self.scrollbar_manager.dragging_thumb:
            self.scrollbar_manager.end_thumb_drag()
            self.unsetCursor()  # Restore default cursor

        # Recalculate visible rows and clamp scroll_offset
        track_area_spec = self.playlist_spec["layout"]["regions"]["track_area"]
        row_height = track_area_spec["row_height"]
        track_area_y = track_area_spec["position"]["y"]
        bottom_bar_y = self._get_bottom_bar_y()

        visible_height = self.height() - track_area_y - (self.height() - bottom_bar_y)
        num_visible_rows = visible_height // row_height
        total_rows = len(self.playlist_items)

        # Calculate the maximum scroll offset for the new window size
        max_scroll_offset = max(0, total_rows - num_visible_rows)

        # Always clamp the scroll offset to the new maximum to prevent invalid positions
        self.scroll_offset = min(self.scroll_offset, max_scroll_offset)
        self.scroll_offset = max(0, self.scroll_offset)  # Ensure it's not negative

        # Save the playlist window size to preferences
        # Only save if the window is not docked and is visible (to avoid saving docked sizes)
        if (
            hasattr(self, "main_window")
            and self.isVisible()
            and not getattr(self.main_window, "_is_shutting_down", False)
        ):
            self.main_window.preferences.set_playlist_window_size(
                self.width(), self.height()
            )

        self.update()  # Request a repaint

    def _apply_stepped_resize_constraints(self):
        """Apply stepped resize constraints to ensure window size follows proper dimensions."""
        # Prevent recursive calls when applying constraints
        if self._applying_resize_constraints:
            return

        # Get default size for minimum constraints
        default_width = self.playlist_spec["layout"]["window"]["default_size"]["width"]
        default_height = self.playlist_spec["layout"]["window"]["default_size"][
            "height"
        ]

        # Calculate what the constrained size should be based on current size
        base_height = 58  # 20 (top bar) + 38 (bottom bar)
        current_height = self.height()
        if current_height > default_height:
            resizable_height = current_height - base_height
            num_steps = round(resizable_height / SCROLLBAR_GROOVE_HEIGHT)
            constrained_height = base_height + (num_steps * SCROLLBAR_GROOVE_HEIGHT)
        else:
            constrained_height = default_height  # Maintain at least default size

        # For width, snap to multiples of the bottom filler width (25px)
        current_width = self.width()
        filler_width = BOTTOM_FILLER_WIDTH  # PLEDIT_BOTTOM_BAR_FILLER width
        if current_width > default_width:
            resizable_amount = current_width - default_width
            num_steps = round(resizable_amount / filler_width)
            constrained_width = default_width + num_steps * filler_width
        else:
            constrained_width = default_width  # Ensure it doesn't go below default

        # Only resize if the current size doesn't match the constraints
        if self.width() != constrained_width or self.height() != constrained_height:
            # Set flag to prevent recursive calls
            self._applying_resize_constraints = True
            self.resize(constrained_width, constrained_height)
            # Reset flag after resize
            self._applying_resize_constraints = False

    def scroll_up(self):
        if self.scroll_offset > 0:
            self.scroll_offset -= 1
            self.update()

    def scroll_down(self):
        track_area_spec = self.playlist_spec["layout"]["regions"]["track_area"]
        row_height = track_area_spec["row_height"]
        track_area_y = track_area_spec["position"]["y"]

        # Calculate bottom_bar_y within this method
        bottom_bar_y = self._get_bottom_bar_y()

        visible_height = self.height() - track_area_y - (self.height() - bottom_bar_y)
        num_visible_rows = visible_height // row_height

        if self.scroll_offset + num_visible_rows < len(self.playlist_items):
            self.scroll_offset += 1
            self.update()

    def add_playlist_item(self):
        # Add a corresponding entry to playlist_filepaths (for demo purposes)
        self.playlist_filepaths.append("")  # Empty path for demo item
        # Regenerate playlist display items based on current display options
        self._regenerate_playlist_display_items()
        self.selected_items.clear()
        self.last_selected_item_index = -1
        self.update()

    def remove_playlist_item(self):
        if not self.selected_items:
            QMessageBox.information(
                self, "Playlist Editor", "Please select items to remove."
            )
            return

        # Sort in descending order to avoid index issues when deleting
        sorted_selected_indices = sorted(list(self.selected_items), reverse=True)

        # Remove from filepaths in reverse order to avoid index issues
        for index in sorted_selected_indices:
            if 0 <= index < len(self.playlist_filepaths):
                del self.playlist_filepaths[index]

        # Regenerate playlist display items based on current display options
        self._regenerate_playlist_display_items()

        self.selected_items.clear()
        self.last_selected_item_index = -1

        # Adjust scroll offset if necessary
        if (
            self.scroll_offset >= len(self.playlist_items)
            and len(self.playlist_items) > 0
        ):
            self.scroll_offset = len(self.playlist_items) - 1
        elif len(self.playlist_items) == 0:
            self.scroll_offset = 0

        # Update main window's playlist to sync both lists
        if self.main_window:
            self.main_window.set_playlist(self.playlist_filepaths)

        self.update()

    def _load_file_to_playlist(self):
        options = QFileDialog.Options()
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        test_music_dir = os.path.join(project_root, "resources", "test_music")

        # Use default music path from preferences if available, otherwise use test music directory
        initial_path = test_music_dir  # Default fallback
        if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'preferences'):
            default_music_path = self.main_window.preferences.get_default_music_path()
            if default_music_path:
                initial_path = default_music_path
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Music File",
            initial_path,
            "Music Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.opus *.aiff *.au);;All Files (*)",
            options=options,
        )
        if file_path:
            # Add to internal file path list
            self.playlist_filepaths.append(file_path)

            # Regenerate playlist display items based on current display options
            self._regenerate_playlist_display_items()

            self.selected_items.clear()
            self.last_selected_item_index = -1

            # Update main window's playlist
            if self.main_window:
                self.main_window.set_playlist(self.playlist_filepaths)

            self.update()

    def _remove_all_tracks(self):
        """Remove all tracks from the playlist."""
        self.playlist_items.clear()
        self.playlist_filepaths.clear()  # Clear the file paths as well
        self.selected_items.clear()
        self.last_selected_item_index = -1
        self.scroll_offset = 0
        # Clear the track durations cache since playlist has changed
        self._track_durations_cache.clear()
        self.update()

    def _crop_playlist(self):
        """Remove all tracks except for the currently selected ones."""
        if not self.selected_items:
            # If no items are selected, show a message and return
            QMessageBox.information(
                self, "Playlist Editor", "Please select items to keep."
            )
            return

        # Get the currently selected items in descending order to avoid index issues
        # Create new playlist with only selected items
        new_playlist_items = []
        new_playlist_filepaths = []
        for i, item in enumerate(self.playlist_items):
            if i in self.selected_items:
                new_playlist_items.append(item)
                # Also add the corresponding filepath if the index is valid
                if i < len(self.playlist_filepaths):
                    new_playlist_filepaths.append(self.playlist_filepaths[i])

        # Update the file paths only
        self.playlist_filepaths = new_playlist_filepaths

        # Regenerate playlist display items based on current display options
        self._regenerate_playlist_display_items()

        # Clear and reselect the first items in the new list (or all if they were all kept)
        self.selected_items.clear()
        self.last_selected_item_index = -1

        # Adjust scroll offset if necessary
        if (
            self.scroll_offset >= len(self.playlist_items)
            and len(self.playlist_items) > 0
        ):
            self.scroll_offset = max(0, len(self.playlist_items) - 1)
        elif len(self.playlist_items) == 0:
            self.scroll_offset = 0

        # Clear the track durations cache since playlist has changed
        self._track_durations_cache.clear()

        # Update main window's playlist to sync both lists
        if self.main_window:
            self.main_window.set_playlist(self.playlist_filepaths)

        self.update()

    def _remove_duplicate_tracks(self):
        """Scan the playlist and remove duplicate entries."""
        seen_items = set()
        unique_items = []
        unique_indices = []

        for i, item in enumerate(self.playlist_items):
            # Extract the actual track name after the number prefix (e.g., "1. Song Name" -> "Song Name")
            # Look for pattern like "X. " where X is any number
            import re

            # This regex will match the pattern "number. " at the beginning
            match = re.match(r"^\d+\.\s*(.*)", item)
            track_content = match.group(1) if match else item

            if track_content not in seen_items:
                seen_items.add(track_content)
                unique_items.append(item)
                unique_indices.append(i)

        # Create new filepaths list corresponding to unique items
        new_playlist_filepaths = []
        for i in unique_indices:
            if i < len(self.playlist_filepaths):
                new_playlist_filepaths.append(self.playlist_filepaths[i])

        # Update the file paths only
        self.playlist_filepaths = new_playlist_filepaths

        # Regenerate playlist display items based on current display options
        self._regenerate_playlist_display_items()

        self.selected_items.clear()
        self.last_selected_item_index = -1

        # Adjust scroll offset if necessary
        if (
            self.scroll_offset >= len(self.playlist_items)
            and len(self.playlist_items) > 0
        ):
            self.scroll_offset = max(0, len(self.playlist_items) - 1)
        elif len(self.playlist_items) == 0:
            self.scroll_offset = 0

        # Clear the track durations cache since playlist has changed
        self._track_durations_cache.clear()

        # Update main window's playlist to sync both lists
        if self.main_window:
            self.main_window.set_playlist(self.playlist_filepaths)

        self.update()

    def _invert_selection(self):
        """Invert the current selection - deselect selected items and select unselected items."""
        current_selected = (
            self.selected_items.copy()
        )  # Make a copy to avoid modification during iteration
        new_selected_items = set()

        for i in range(len(self.playlist_items)):
            # Invert: if it was selected, don't select it; if it wasn't selected, select it
            if i in current_selected:
                # Item was selected, so don't select it (invert)
                continue
            else:
                # Item wasn't selected, so select it (invert)
                new_selected_items.add(i)

        self.selected_items = new_selected_items
        if self.selected_items:
            # Set the last selected item to the first one in the new selection
            self.last_selected_item_index = min(self.selected_items)
        else:
            self.last_selected_item_index = -1
        self.update()

    def _select_none(self):
        """Deselect all tracks."""
        self.selected_items.clear()
        self.last_selected_item_index = -1
        self.update()

    def _select_all(self):
        """Select all tracks in the playlist."""
        self.selected_items.clear()
        for i in range(len(self.playlist_items)):
            self.selected_items.add(i)
        self.last_selected_item_index = (
            len(self.playlist_items) - 1 if self.playlist_items else -1
        )
        self.update()

    def _show_sort_dialog(self):
        """Show dialog with options to sort the playlist."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("Sort Playlist")
        dialog.setModal(True)

        layout = QVBoxLayout()

        label = QLabel("Select sorting method:")
        layout.addWidget(label)

        # Sort by title (extract from playlist item text)
        sort_by_title_btn = QPushButton("Sort by Title")
        sort_by_title_btn.clicked.connect(lambda: self._sort_playlist_by_title())
        layout.addWidget(sort_by_title_btn)

        # Sort by filename (extract from playlist item text)
        sort_by_filename_btn = QPushButton("Sort by Filename")
        sort_by_filename_btn.clicked.connect(lambda: self._sort_playlist_by_filename())
        layout.addWidget(sort_by_filename_btn)

        # Sort randomly
        sort_randomly_btn = QPushButton("Sort Randomly")
        sort_randomly_btn.clicked.connect(lambda: self._sort_playlist_randomly())
        layout.addWidget(sort_randomly_btn)

        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.close)
        layout.addWidget(cancel_btn)

        dialog.setLayout(layout)
        dialog.exec_()

    def _sort_playlist_by_title(self):
        """Sort playlist by track title."""
        if not self.playlist_items:
            return

        # Extract titles from playlist items for sorting
        def extract_title(item):
            # Format is "X. Title" - extract the title part after the number and ". "
            parts = item.split(". ", 1)
            return parts[1] if len(parts) > 1 else item

        # Create tuples of (original_index, extracted_title, original_item, original_filepath)
        indexed_items = [
            (
                i,
                extract_title(item),
                item,
                self.playlist_filepaths[i] if i < len(self.playlist_filepaths) else "",
            )
            for i, item in enumerate(self.playlist_items)
        ]

        # Sort by extracted title
        sorted_items = sorted(indexed_items, key=lambda x: x[1])

        # Extract the sorted original filepaths
        self.playlist_filepaths = [item[3] for item in sorted_items]

        # Regenerate playlist display items based on current display options
        self._regenerate_playlist_display_items()

        # Update main window's playlist to sync both lists
        if self.main_window:
            self.main_window.set_playlist(self.playlist_filepaths)

        self.update()

    def _sort_playlist_by_filename(self):
        """Sort playlist by filename."""
        if not self.playlist_items:
            return

        def extract_filename(item):
            # Extract filename from the item text (after the number prefix)
            parts = item.split(". ", 1)
            title = parts[1] if len(parts) > 1 else item
            # Get just the filename part (remove path if present)
            import os

            return os.path.basename(title).lower()

        indexed_items = [
            (
                i,
                extract_filename(item),
                item,
                self.playlist_filepaths[i] if i < len(self.playlist_filepaths) else "",
            )
            for i, item in enumerate(self.playlist_items)
        ]
        sorted_items = sorted(indexed_items, key=lambda x: x[1])
        self.playlist_filepaths = [item[3] for item in sorted_items]

        # Regenerate playlist display items based on current display options
        self._regenerate_playlist_display_items()

        # Update main window's playlist to sync both lists
        if self.main_window:
            self.main_window.set_playlist(self.playlist_filepaths)

        self.update()

    def _sort_playlist_randomly(self):
        """Sort playlist in random order."""
        import random

        if not self.playlist_items:
            return

        # Create copies and shuffle them in the same order
        indices = list(range(len(self.playlist_items)))
        random.shuffle(indices)  # Shuffle the indices

        # Create shuffled versions based on shuffled indices
        shuffled_filepaths = [
            self.playlist_filepaths[i] if i < len(self.playlist_filepaths) else ""
            for i in indices
        ]

        # Update filepaths list
        self.playlist_filepaths = shuffled_filepaths

        # Regenerate playlist display items based on current display options
        self._regenerate_playlist_display_items()

        # Update main window's playlist to sync both lists
        if self.main_window:
            self.main_window.set_playlist(self.playlist_filepaths)

        self.update()

    def _renumber_playlist(self):
        """Update the numbering of playlist items."""
        for i, item in enumerate(self.playlist_items):
            # Extract original title
            parts = item.split(". ", 1)
            title = parts[1] if len(parts) > 1 else item
            # Update with new number
            self.playlist_items[i] = f"{i + 1}. {title}"

    def _show_file_info(self):
        """Show file info for selected track."""
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QLabel,
            QPushButton,
            QScrollArea,
            QWidget,
        )

        if not self.selected_items:
            QMessageBox.information(
                self, "File Info", "Please select a track to view its information."
            )
            return

        # Get the first selected item (or if multiple, just show the first one)
        selected_index = min(self.selected_items)

        # Get the actual file path from playlist_filepaths
        if selected_index >= len(self.playlist_filepaths):
            QMessageBox.warning(
                self, "File Info", "No file path available for selected track."
            )
            return

        filepath = self.playlist_filepaths[selected_index]

        # Get metadata for the file
        metadata = self._get_track_metadata(filepath)

        # Try to get technical info from mutagen
        try:
            from mutagen import File as MutagenFile

            audio_file = MutagenFile(filepath)
            if audio_file and hasattr(audio_file, "info"):
                info = audio_file.info
                technical_info = {
                    "format": audio_file.__class__.__name__,
                    "bitrate": getattr(info, "bitrate", 0),
                    "sample_rate": getattr(info, "sample_rate", 0),
                    "channels": getattr(info, "channels", 2),
                    "length": getattr(info, "length", 0.0),
                }
            else:
                technical_info = {
                    "format": "Unknown",
                    "bitrate": 0,
                    "sample_rate": 0,
                    "channels": 0,
                    "length": 0.0,
                }
        except Exception as e:
            print(f"Error getting technical info: {e}")
            technical_info = {
                "format": "Unknown",
                "bitrate": 0,
                "sample_rate": 0,
                "channels": 0,
                "length": 0.0,
            }

        # Get file size
        import os

        try:
            file_size = os.path.getsize(filepath)
            file_size_mb = file_size / (1024 * 1024)  # Convert to MB
        except OSError:
            file_size_mb = 0

        dialog = QDialog(self)
        dialog.setWindowTitle("File Information")
        dialog.setModal(True)
        dialog.resize(500, 600)  # Set a reasonable size

        # Create scroll area for the content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        # Basic Information
        layout.addWidget(QLabel("<b>Basic Information:</b>"))
        layout.addWidget(QLabel(f"Filename: {os.path.basename(filepath)}"))
        layout.addWidget(QLabel(f"File Path: {filepath}"))
        layout.addWidget(QLabel(""))

        # Metadata information
        layout.addWidget(QLabel("<b>Metadata:</b>"))
        layout.addWidget(QLabel(f"Title: {metadata.get('title', 'Unknown')}"))
        layout.addWidget(QLabel(f"Artist: {metadata.get('artist', 'Unknown')}"))
        layout.addWidget(QLabel(f"Album: {metadata.get('album', 'Unknown')}"))
        layout.addWidget(
            QLabel(f"Album Artist: {metadata.get('album_artist', 'Unknown')}")
        )

        # Try to get additional metadata fields
        try:
            from mutagen import File as MutagenFile

            audio_file = MutagenFile(filepath)
            if audio_file:
                # Get genre if available
                genre = "Unknown"
                for key in ["TCON", "genre", "\xa9gen", "GNRE", "©gen"]:
                    if key in audio_file:
                        genre_value = audio_file[key]
                        if isinstance(genre_value, list) and len(genre_value) > 0:
                            genre = str(genre_value[0])
                        elif isinstance(genre_value, list) and len(genre_value) == 0:
                            continue
                        else:
                            genre = str(genre_value)
                        break
                layout.addWidget(QLabel(f"Genre: {genre}"))

                # Get year/date if available
                year = "Unknown"
                for key in ["TYER", "TDRC", "date", "\xa9day", "©day", "year"]:
                    if key in audio_file:
                        year_value = audio_file[key]
                        if isinstance(year_value, list) and len(year_value) > 0:
                            year = str(year_value[0])
                        elif isinstance(year_value, list) and len(year_value) == 0:
                            continue
                        else:
                            year = str(year_value)
                        break
                layout.addWidget(QLabel(f"Year: {year}"))

                # Get track number if available
                track_number = "Unknown"
                for key in ["TRCK", "tracknumber", "\xa9trk", "©trk"]:
                    if key in audio_file:
                        track_value = audio_file[key]
                        if isinstance(track_value, list) and len(track_value) > 0:
                            track_number = str(track_value[0])
                        elif isinstance(track_value, list) and len(track_value) == 0:
                            continue
                        else:
                            track_number = str(track_value)
                        break
                layout.addWidget(QLabel(f"Track Number: {track_number}"))

                # Get disc number if available
                disc_number = "Unknown"
                for key in ["TPOS", "discnumber", "\xa9dis", "©dis"]:
                    if key in audio_file:
                        disc_value = audio_file[key]
                        if isinstance(disc_value, list) and len(disc_value) > 0:
                            disc_number = str(disc_value[0])
                        elif isinstance(disc_value, list) and len(disc_value) == 0:
                            continue
                        else:
                            disc_number = str(disc_value)
                        break
                layout.addWidget(QLabel(f"Disc Number: {disc_number}"))

                # Get composer if available
                composer = "Unknown"
                for key in ["TCOM", "composer", "\xa9wrt", "©wrt"]:
                    if key in audio_file:
                        composer_value = audio_file[key]
                        if isinstance(composer_value, list) and len(composer_value) > 0:
                            composer = str(composer_value[0])
                        elif (
                            isinstance(composer_value, list)
                            and len(composer_value) == 0
                        ):
                            continue
                        else:
                            composer = str(composer_value)
                        break
                layout.addWidget(QLabel(f"Composer: {composer}"))

                # Get comments if available
                comments = "None"
                for key in ["COMM", "comment", "\xa9cmt", "©cmt", "desc"]:
                    if key in audio_file:
                        comment_value = audio_file[key]
                        if isinstance(comment_value, list) and len(comment_value) > 0:
                            comments = str(comment_value[0])
                        elif (
                            isinstance(comment_value, list) and len(comment_value) == 0
                        ):
                            continue
                        else:
                            comments = str(comment_value)
                        break
                if comments != "None":
                    comments_label = QLabel(f"Comments: {comments}")
                    comments_label.setWordWrap(True)
                    layout.addWidget(comments_label)

        except Exception as e:
            print(f"Error getting additional metadata: {e}")

        layout.addWidget(QLabel(""))

        # Technical information
        layout.addWidget(QLabel("<b>Technical Information:</b>"))
        layout.addWidget(QLabel(f"Format: {technical_info['format']}"))
        if technical_info["bitrate"] > 0:
            layout.addWidget(
                QLabel(f"Bitrate: {technical_info['bitrate'] // 1000} kbps")
            )
        layout.addWidget(QLabel(f"Sample Rate: {technical_info['sample_rate']} Hz"))

        channels_str = (
            "Stereo"
            if technical_info["channels"] == 2
            else (
                "Mono"
                if technical_info["channels"] == 1
                else f"{technical_info['channels']} channels"
            )
        )
        layout.addWidget(QLabel(f"Channels: {channels_str}"))

        layout.addWidget(
            QLabel(f"Duration: {self._format_time(technical_info['length'])}")
        )
        layout.addWidget(QLabel(f"File Size: {file_size_mb:.2f} MB"))

        # Add some space before the close button
        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        # Set the content widget to the scroll area
        scroll.setWidget(content_widget)

        # Create the main layout for the dialog
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        dialog.setLayout(main_layout)

        dialog.exec_()

    def _show_misc_options(self):
        """Show miscellaneous options/preferences dialog."""
        from PySide6.QtWidgets import (
            QDialog,
            QVBoxLayout,
            QHBoxLayout,
            QPushButton,
            QLabel,
            QCheckBox,
        )

        dialog = QDialog(self)
        dialog.setWindowTitle("Playlist Options")
        dialog.setModal(True)

        layout = QVBoxLayout()

        label = QLabel("Playlist Display Options:")
        layout.addWidget(label)

        # Create checkboxes for each metadata option
        checkboxes = {}

        track_filename_cb = QCheckBox(
            "Track Filename (always shown if no options selected)"
        )
        track_filename_cb.setChecked(self.display_options["track_filename"])
        checkboxes["track_filename"] = track_filename_cb
        layout.addWidget(track_filename_cb)

        track_number_cb = QCheckBox("Track Number")
        track_number_cb.setChecked(self.display_options["track_number"])
        checkboxes["track_number"] = track_number_cb
        layout.addWidget(track_number_cb)

        song_name_cb = QCheckBox("Song Name")
        song_name_cb.setChecked(self.display_options["song_name"])
        checkboxes["song_name"] = song_name_cb
        layout.addWidget(song_name_cb)

        artist_cb = QCheckBox("Artist")
        artist_cb.setChecked(self.display_options["artist"])
        checkboxes["artist"] = artist_cb
        layout.addWidget(artist_cb)

        album_artist_cb = QCheckBox("Album Artist")
        album_artist_cb.setChecked(self.display_options["album_artist"])
        checkboxes["album_artist"] = album_artist_cb
        layout.addWidget(album_artist_cb)

        album_name_cb = QCheckBox("Album Name")
        album_name_cb.setChecked(self.display_options["album_name"])
        checkboxes["album_name"] = album_name_cb
        layout.addWidget(album_name_cb)

        # Buttons layout
        button_layout = QHBoxLayout()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        dialog.setLayout(layout)

        # Handle OK button click to update display options
        if dialog.exec_() == QDialog.Accepted:
            # Update the display options based on checkbox states
            for option_name, checkbox in checkboxes.items():
                self.display_options[option_name] = checkbox.isChecked()

            # Save the updated display options to preferences
            playlist_settings = {"display_options": self.display_options}
            self.preferences.set_playlist_settings(playlist_settings)

            # Regenerate playlist display items based on new options
            self._regenerate_playlist_display_items()

    def _new_playlist(self):
        """Clear the current playlist and start a new, empty one."""
        # Clear all playlist items
        self.playlist_items.clear()
        self.playlist_filepaths.clear()

        # Clear all selections
        self.selected_items.clear()
        self.last_selected_item_index = -1
        self.current_track_index = -1

        # Reset scroll position
        self.scroll_offset = 0

        # Clear the track durations cache since playlist has changed
        self._track_durations_cache.clear()

        # Update main window's playlist
        if self.main_window:
            self.main_window.set_playlist([])
            # Reset main window's current track info
            self.main_window.current_track_title = "Not Playing"
            self.main_window.current_track_index = -1

        # Update the display
        self.update()

    def _load_directory_to_playlist(self):
        """Load all media files from a selected directory and its subdirectories."""
        options = QFileDialog.Options()
        project_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        test_music_dir = os.path.join(project_root, "resources", "test_music")

        # Use default music path from preferences if available, otherwise use test music directory
        initial_path = test_music_dir  # Default fallback
        if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'preferences'):
            default_music_path = self.main_window.preferences.get_default_music_path()
            if default_music_path:
                initial_path = default_music_path
        
        directory_path = QFileDialog.getExistingDirectory(
            self, "Select Directory to Add", initial_path, options=options
        )
        if directory_path:
            # Define supported media file extensions
            media_extensions = {
                ".mp3",
                ".wav",
                ".ogg",
                ".flac",
                ".m4a",
                ".aac",
                ".wma",
                ".mp4",
                ".m3u",
                ".pls",
            }

            # Collect new files first
            new_files_collected = []
            for root, dirs, files in os.walk(directory_path):
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in media_extensions:
                        full_path = os.path.join(root, file)
                        new_files_collected.append(full_path)

            # Sort the new files by filename
            new_files_collected.sort(key=lambda path: os.path.basename(path).lower())

            # Add sorted new files to the playlist filepaths
            new_files_added = []
            for full_path in new_files_collected:
                self.playlist_filepaths.append(full_path)
                new_files_added.append(full_path)

            # Regenerate playlist display items based on current display options
            self._regenerate_playlist_display_items()

            self.selected_items.clear()
            self.last_selected_item_index = -1

            # Update main window's playlist
            if self.main_window and new_files_added:
                self.main_window.set_playlist(self.playlist_filepaths)

            self.update()

    def _load_url_to_playlist(self):
        """Prompt user for a URL to add to the playlist."""
        from PySide6.QtWidgets import QInputDialog

        url, ok = QInputDialog.getText(self, "Add URL", "Enter streaming URL:", text="")
        if ok and url:
            # Validate that the URL is not empty and follows a proper format
            if url.strip():
                # Add to internal file path list (URLs are also "paths" in this context)
                self.playlist_filepaths.append(url)

                # Regenerate playlist display items based on current display options
                self._regenerate_playlist_display_items()

                self.selected_items.clear()
                self.last_selected_item_index = -1

                # Update main window's playlist
                if self.main_window:
                    self.main_window.set_playlist(self.playlist_filepaths)

                self.update()
            else:
                QMessageBox.warning(self, "Invalid URL", "Please enter a valid URL.")

    def _save_playlist(self):
        options = QFileDialog.Options()
        # Use default music path for saving if available, otherwise use empty string
        initial_path = ""  # Default fallback
        if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'preferences'):
            default_music_path = self.main_window.preferences.get_default_music_path()
            if default_music_path:
                initial_path = default_music_path
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Save Playlist",
            initial_path,
            "Playlist Files (*.m3u *.m3u8 *.pls *.txt);;All Files (*)",
            options=options,
        )
        if file_path:
            # Determine if it's an M3U file or text file
            if file_path.lower().endswith((".m3u", ".m3u8")):
                with open(file_path, "w") as f:
                    f.write("#EXTM3U\n")  # M3U header
                    for filepath in self.playlist_filepaths:
                        # Try to get metadata if available
                        f.write(
                            f"#EXTINF:0,{os.path.basename(filepath)}\n"
                        )  # Placeholder duration
                        f.write(f"{filepath}\n")
            else:
                # Save as text file with just file paths
                with open(file_path, "w") as f:
                    for filepath in self.playlist_filepaths:
                        f.write(filepath + "\n")
            QMessageBox.information(
                self, "Playlist Editor", "Playlist saved successfully!"
            )

    def _load_playlist_from_file(self):
        options = QFileDialog.Options()
        # Use default music path for loading if available, otherwise use empty string
        initial_path = ""  # Default fallback
        if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'preferences'):
            default_music_path = self.main_window.preferences.get_default_music_path()
            if default_music_path:
                initial_path = default_music_path
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Playlist",
            initial_path,
            "Playlist Files (*.m3u *.m3u8 *.pls *.txt);;All Files (*)",
            options=options,
        )
        if file_path:
            new_filepaths = []
            new_display_items = []

            if file_path.lower().endswith((".m3u", ".m3u8")):
                # Parse M3U file format
                with open(file_path, "r") as f:
                    lines = f.readlines()

                i = 0
                item_number = 1
                while i < len(lines):
                    line = lines[i].strip()
                    if (
                        line
                        and not line.startswith("#EXTM3U")
                        and not line.startswith("#EXTINF")
                    ):
                        # This is a file path
                        new_filepaths.append(line)
                        new_display_items.append(
                            f"{item_number}. {os.path.basename(line)}"
                        )
                        item_number += 1
                    elif line.startswith("#EXTINF"):
                        # This is metadata, skip to the next line which should be the file path
                        i += 1
                        if i < len(lines):
                            path_line = lines[i].strip()
                            if path_line:
                                new_filepaths.append(path_line)
                                # Extract title from EXTINF line if available
                                title = os.path.basename(path_line)
                                parts = line.split(",", 1)
                                if len(parts) > 1:
                                    title = parts[1]
                                new_display_items.append(f"{item_number}. {title}")
                                item_number += 1
                    i += 1
            elif file_path.lower().endswith(".pls"):
                # Parse PLS (Playlist) file format
                # PLS format: [playlist], File1=/path/to/file, Title1=song title, Length1=duration, NumberOfEntries=total count
                with open(file_path, "r") as f:
                    lines = f.readlines()

                pls_entries = {}
                for line in lines:
                    line = line.strip()
                    if line.lower().startswith("file") and "=" in line:
                        # Parse FileN=filepath
                        key, value = line.split("=", 1)
                        # Extract the number from keys like File1, File2, etc.
                        key_lower = key.lower()
                        if key_lower.startswith("file") and len(key_lower) > 4:
                            file_num = key_lower[4:]  # Get the number after "file"
                            if file_num.isdigit():
                                pls_entries[file_num] = pls_entries.get(file_num, {})
                                pls_entries[file_num]['file'] = value
                    elif line.lower().startswith("title") and "=" in line:
                        # Parse TitleN=title
                        key, value = line.split("=", 1)
                        # Extract the number from keys like Title1, Title2, etc.
                        key_lower = key.lower()
                        if key_lower.startswith("title") and len(key_lower) > 5:
                            title_num = key_lower[5:]  # Get the number after "title"
                            if title_num.isdigit():
                                pls_entries[title_num] = pls_entries.get(title_num, {})
                                pls_entries[title_num]['title'] = value

                # Add entries in numerical order
                item_number = 1
                for file_num in sorted(pls_entries.keys(), key=int):
                    entry = pls_entries[file_num]
                    if 'file' in entry:
                        new_filepaths.append(entry['file'])
                        # Use title if available, otherwise use filename
                        display_title = entry.get('title', os.path.basename(entry['file']))
                        new_display_items.append(f"{item_number}. {display_title}")
                        item_number += 1
            else:
                # Plain text file with one file path per line
                with open(file_path, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            new_filepaths.append(line)
                            new_display_items.append(
                                f"{len(new_display_items) + 1}. {os.path.basename(line)}"
                            )

            # Update internal lists
            self.playlist_filepaths = new_filepaths

            # Regenerate playlist display items based on current display options
            self._regenerate_playlist_display_items()

            self.selected_items.clear()
            self.last_selected_item_index = -1
            self.scroll_offset = 0

            # Update main window's playlist
            if self.main_window:
                self.main_window.set_playlist(self.playlist_filepaths)

            self.update()

    def _handle_resize_press(self, event):
        """Handle resize handle press events."""
        resize_handle_size = 16
        resize_rect = QRect(
            self.width() - resize_handle_size,
            self.height() - resize_handle_size,
            resize_handle_size,
            resize_handle_size,
        )
        if resize_rect.contains(event.pos()):
            self._resizing = True
            self._resize_start_pos = event.globalPos()
            self._resize_start_size = self.size()
            self.setCursor(Qt.SizeFDiagCursor)
            return True
        return False

    def _handle_button_press(self, event):
        """Handle button press events."""
        button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]

        for button_data in button_bar_spec["buttons"]:
            button_id = button_data["id"]

            button_rect = self.buttonbar_manager.get_button_rect(button_data)

            button_pixmap = self._get_sprite_pixmap(button_data["sprite"])
            if button_pixmap:
                if button_rect.contains(event.pos()):
                    self.buttonbar_manager.set_button_pressed(button_id, True)
                    self.update()  # Request repaint to show pressed state
                    return True

        # Check for transport control button presses
        # Transport controls are located inside the right control bar sprite at specific relative positions
        bottom_bar_y = self._get_bottom_bar_y()

        # Get the right control bar sprite and its actual position in the window
        right_control_bar_sprite = self._get_sprite_pixmap(
            "PLEDIT_BOTTOM_RIGHT_CONTROL_BAR"
        )
        if right_control_bar_sprite:
            # The right control bar is positioned at the right side of the bottom bar
            # Calculate its x position based on window width and sprite width
            right_control_bar_x = self.width() - right_control_bar_sprite.width()

            # Define rectangles for transport control buttons based on their positions within the right control bar sprite
            # These are relative coordinates within the PLEDIT_BOTTOM_RIGHT_CONTROL_BAR sprite (x=126, y=72 in the sprite)
            # but the transport controls are located at specific positions: previous(132,94), play(140,94), etc.
            # relative to their position in the sprite: prev(132-126=6, 94-72=22), play(140-126=14, 22), etc.
            transport_button_rects = {
                "previous": QRect(
                    right_control_bar_x + 6, bottom_bar_y + 22, 7, 8
                ),  # x=6, y=22 within sprite
                "play": QRect(
                    right_control_bar_x + 14, bottom_bar_y + 22, 8, 8
                ),  # x=14, y=22 within sprite
                "pause": QRect(
                    right_control_bar_x + 23, bottom_bar_y + 22, 9, 8
                ),  # x=23, y=22 within sprite
                "stop": QRect(
                    right_control_bar_x + 33, bottom_bar_y + 22, 9, 8
                ),  # x=33, y=22 within sprite
                "next": QRect(
                    right_control_bar_x + 43, bottom_bar_y + 22, 7, 8
                ),  # x=43, y=22 within sprite
                "open": QRect(
                    right_control_bar_x + 51, bottom_bar_y + 22, 9, 8
                ),  # x=51, y=22 within sprite
            }
        else:
            # Fallback to old approach if sprite not available
            transport_button_rects = {}

        for control_name, rect in transport_button_rects.items():
            if rect.contains(event.pos()):
                # Set the appropriate button pressed state
                if control_name == "previous":
                    self._is_previous_pressed = True
                elif control_name == "play":
                    self._is_play_pressed = True
                elif control_name == "pause":
                    self._is_pause_pressed = True
                elif control_name == "stop":
                    self._is_stop_pressed = True
                elif control_name == "next":
                    self._is_next_pressed = True
                elif control_name == "open":
                    self._is_eject_pressed = True

                # Handle the action associated with the button
                self._handle_transport_control_action(control_name)

                self.update()  # Request repaint to show pressed state
                return True

        return False

    def _handle_transport_control_action(self, control_name):
        """Handle the action for a transport control button."""
        if not self.main_window:
            print("ERROR: No main window reference available for transport controls")
            return

        if control_name == "previous":
            # Trigger previous track in playlist
            self.main_window.play_previous_track()
            # Update the visual state after action
            if self.main_window:
                state = self.main_window.audio_engine.get_playback_state()
                self._is_play_pressed = state["is_playing"] and not state["is_paused"]
                self._is_pause_pressed = state["is_paused"]
                self._is_stop_pressed = not (state["is_playing"] or state["is_paused"])
                self.update()
        elif control_name == "play":
            # Make sure play button is pressed and pause is not
            self._is_play_pressed = True
            self._is_pause_pressed = False  # Reset pause state

            # If playlist is empty, just start playback if track is loaded
            if not self.main_window.playlist:
                if (
                    not self.main_window.audio_engine.is_playing
                    or self.main_window.audio_engine.is_paused
                ):
                    self.main_window.audio_engine.play()
                # Update the visual state after action
                state = self.main_window.audio_engine.get_playback_state()
                self._is_play_pressed = state["is_playing"] and not state["is_paused"]
                self._is_pause_pressed = state["is_paused"]
                self._is_stop_pressed = not (state["is_playing"] or state["is_paused"])
                self.update()
                return

            # Get the selected track from the playlist window
            selected_track_index = self.get_selected_track_index()

            # If no track is selected in the playlist window, use the current track
            if selected_track_index == -1:
                selected_track_index = self.current_track_index

            # If still no track selected, use the first track in the main playlist
            if selected_track_index == -1 and self.main_window.playlist:
                selected_track_index = 0

            # Play the selected track (or current/first track if none selected)
            self.main_window.play_track_at_index(selected_track_index)
            # Update the visual state after action
            state = self.main_window.audio_engine.get_playback_state()
            self._is_play_pressed = state["is_playing"] and not state["is_paused"]
            self._is_pause_pressed = state["is_paused"]
            self._is_stop_pressed = not (state["is_playing"] or state["is_paused"])
            self.update()
        elif control_name == "pause":
            # Toggle pause via audio engine
            if self.main_window.audio_engine.is_playing:
                self.main_window.audio_engine.pause()
            elif self.main_window.audio_engine.is_paused:
                self.main_window.audio_engine.play()
            # Update the visual state after action
            state = self.main_window.audio_engine.get_playback_state()
            self._is_play_pressed = state["is_playing"] and not state["is_paused"]
            self._is_pause_pressed = state["is_paused"]
            self._is_stop_pressed = not (state["is_playing"] or state["is_paused"])
            self.update()
        elif control_name == "stop":
            # Stop playback via audio engine
            self.main_window.audio_engine.stop()
            # Update the visual state after action
            state = self.main_window.audio_engine.get_playback_state()
            self._is_play_pressed = state["is_playing"] and not state["is_paused"]
            self._is_pause_pressed = state["is_paused"]
            self._is_stop_pressed = not (state["is_playing"] or state["is_paused"])
            # Make sure the playlist window remembers which track was playing so it can be restarted
            self.set_current_track_index(self.main_window.current_track_index)
            self.update()
        elif control_name == "next":
            # Trigger next track in playlist
            self.main_window.play_next_track()
            # Update the visual state after action
            if self.main_window:
                state = self.main_window.audio_engine.get_playback_state()
                self._is_play_pressed = state["is_playing"] and not state["is_paused"]
                self._is_pause_pressed = state["is_paused"]
                self._is_stop_pressed = not (state["is_playing"] or state["is_paused"])
                self.update()
        elif control_name == "open":
            # Open file dialog to load a track
            from PySide6.QtWidgets import QFileDialog

            # Use default music path from preferences if available, otherwise use empty string
            initial_path = ""  # Default fallback
            if hasattr(self, 'main_window') and self.main_window and hasattr(self.main_window, 'preferences'):
                default_music_path = self.main_window.preferences.get_default_music_path()
                if default_music_path:
                    initial_path = default_music_path
            
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Open Audio File",
                initial_path,
                "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.opus *.aiff *.au);;All Files (*)",
            )

            if file_path:
                # Add to main window's playlist and play immediately
                if self.main_window.audio_engine.load_track(file_path):
                    # For single file loading via open, create a new playlist with just this file
                    self.main_window.playlist = [file_path]
                    self.main_window.current_track_index = 0

                    # Update the playlist window display
                    self.main_window.update_playlist_display()

                    # Update the current track title
                    metadata = self.main_window.audio_engine.get_metadata()
                    if metadata:
                        # Format as "artist - song title" for display
                        self.main_window.current_track_title = f"{metadata.get('artist', 'Unknown')} - {metadata.get('title', 'Unknown')}"
                    else:
                        self.main_window.current_track_title = os.path.basename(
                            file_path
                        )

                    # Start playback
                    self.main_window.audio_engine.play()

                    # Update playlist window to show currently playing track
                    self.set_current_track_index(0)
                else:
                    self.main_window.current_track_title = "Error loading track"
            # Update the visual state after action
            if self.main_window:
                state = self.main_window.audio_engine.get_playback_state()
                self._is_play_pressed = state["is_playing"] and not state["is_paused"]
                self._is_pause_pressed = state["is_paused"]
                self._is_stop_pressed = not (state["is_playing"] or state["is_paused"])
                self.update()

    def _handle_scrollbar_press(self, event):
        """Handle scrollbar element press events."""
        # Check for scrollbar element presses
        # Note: Up and down arrow buttons are not handled in this implementation
        # Their functionality is replaced by clicking the track area to page up/down

        thumb_rect = self._get_scrollbar_element_rect("thumb")
        if thumb_rect.contains(event.pos()):
            self.scrollbar_manager.start_thumb_drag(event.pos())
            self.setCursor(Qt.OpenHandCursor)
            return True

        thumb_rect = self._get_scrollbar_element_rect("thumb")
        track_rect = self._get_scrollbar_element_rect("track")

        if track_rect.contains(event.pos()) and not thumb_rect.contains(event.pos()):
            self.scrollbar_manager.handle_track_click(event.pos())
            self.update()
            return True

        return False

    def _handle_track_area_click(self, event):
        """Handle track area click events for selection."""

        # Check if any submenu is open and if click is within a submenu button area
        # If so, don't process as a track area click
        if self._is_submenu_button_click(event.pos()):
            return False  # Don't handle as track area click

        track_area_spec = self.playlist_spec["layout"]["regions"]["track_area"]
        track_area_x = track_area_spec["position"]["x"]
        track_area_y = track_area_spec["position"]["y"]
        row_height = track_area_spec["row_height"]

        # Calculate dynamic width and height for the track area
        track_area_width_expr = track_area_spec["size"]["width"]
        track_area_height_expr = track_area_spec["size"]["height"]

        window_width = self.width()
        window_height = self.height()

        if isinstance(track_area_width_expr, str) and track_area_width_expr.startswith(
            "window.width - "
        ):
            offset = int(track_area_width_expr.split(" - ")[1])
            track_area_width = window_width - offset
        else:
            track_area_width = track_area_width_expr

        if isinstance(
            track_area_height_expr, str
        ) and track_area_height_expr.startswith("window.height - "):
            offset = int(track_area_height_expr.split(" - ")[1])
            track_area_height = window_height - offset
        else:
            track_area_height = track_area_height_expr

        track_area_rect = QRect(
            track_area_x, track_area_y, track_area_width, track_area_height
        )

        if track_area_rect.contains(event.pos()):
            relative_y = event.pos().y() - track_area_y
            clicked_row_in_view = relative_y // row_height
            clicked_item_index = self.scroll_offset + clicked_row_in_view

            if 0 <= clicked_item_index < len(self.playlist_items):
                # If clicked on the currently playing track, just select it without changing playback
                if clicked_item_index == self.current_track_index:
                    if event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier):
                        # Ctrl/Command+click: Toggle selection
                        if clicked_item_index in self.selected_items:
                            self.selected_items.remove(clicked_item_index)
                        else:
                            self.selected_items.add(clicked_item_index)
                    else:
                        # Single click: Clear previous selection and select current
                        self.selected_items.clear()
                        self.selected_items.add(clicked_item_index)
                    self.last_selected_item_index = clicked_item_index
                else:
                    # Different track was clicked - handle selection and playback
                    if event.modifiers() & (Qt.ControlModifier | Qt.MetaModifier):
                        # Ctrl/Command+click: Toggle selection
                        if clicked_item_index in self.selected_items:
                            self.selected_items.remove(clicked_item_index)
                        else:
                            self.selected_items.add(clicked_item_index)
                        self.last_selected_item_index = clicked_item_index
                    elif event.modifiers() & Qt.ShiftModifier:
                        # Shift+click: Select range
                        if self.last_selected_item_index != -1:
                            start = min(
                                self.last_selected_item_index, clicked_item_index
                            )
                            end = max(self.last_selected_item_index, clicked_item_index)
                            for i in range(start, end + 1):
                                self.selected_items.add(i)
                        else:
                            # If no previous selection, select from beginning to current
                            for i in range(clicked_item_index + 1):
                                self.selected_items.add(i)
                        self.last_selected_item_index = clicked_item_index
                    else:
                        # Single click: Clear previous selection and select current
                        self.selected_items.clear()
                        self.selected_items.add(clicked_item_index)
                        self.last_selected_item_index = clicked_item_index

                self.update()
            return True
        return False

    def _is_submenu_button_click(self, pos):
        """Check if a click position is within any open submenu button area."""
        button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]
        button_bar_x = button_bar_spec["position"]["x"]
        button_bar_y = self.height() - 30  # Consistent with paintEvent

        # Check each open menu for submenu button clicks
        for menu_id in ["add", "remove", "select", "misc", "list"]:
            if self.menu_manager.is_menu_open(menu_id):
                menu_button_data = next(
                    (b for b in button_bar_spec["buttons"] if b["id"] == menu_id), None
                )
                if not menu_button_data:
                    continue

                main_button_x = button_bar_x + menu_button_data["x"]
                main_button_y = button_bar_y + menu_button_data["y"]
                main_button_height = 18

                # Calculate submenu position based on menu type
                if menu_id == "add":
                    sub_menu_start_y = (main_button_y + main_button_height) - (
                        3 * 18
                    )  # 3 buttons
                    # Check Add URL button area
                    add_url_rect = QRect(main_button_x, sub_menu_start_y + 0, 22, 18)
                    # Check Add DIR button area
                    add_dir_rect = QRect(main_button_x, sub_menu_start_y + 18, 22, 18)
                    # Check Add FILE button area
                    add_file_rect = QRect(main_button_x, sub_menu_start_y + 36, 22, 18)

                    if (
                        add_url_rect.contains(pos)
                        or add_dir_rect.contains(pos)
                        or add_file_rect.contains(pos)
                    ):
                        return True

                elif menu_id == "remove":
                    sub_menu_start_y = (main_button_y + main_button_height) - (
                        4 * 18
                    )  # 4 buttons
                    # Check submenu button areas
                    remove_all_rect = QRect(main_button_x, sub_menu_start_y + 0, 22, 18)
                    crop_rect = QRect(main_button_x, sub_menu_start_y + 18, 22, 18)
                    remove_selected_rect = QRect(
                        main_button_x, sub_menu_start_y + 36, 22, 18
                    )
                    remove_duplicates_rect = QRect(
                        main_button_x, sub_menu_start_y + 54, 22, 18
                    )

                    if (
                        remove_all_rect.contains(pos)
                        or crop_rect.contains(pos)
                        or remove_selected_rect.contains(pos)
                        or remove_duplicates_rect.contains(pos)
                    ):
                        return True

                elif menu_id == "select":
                    sub_menu_start_y = (main_button_y + main_button_height) - (
                        3 * 18
                    )  # 3 buttons
                    # Check Invert Selection button area
                    invert_selection_rect = QRect(
                        main_button_x, sub_menu_start_y + 0, 22, 18
                    )
                    # Check Select None button area
                    select_none_rect = QRect(
                        main_button_x, sub_menu_start_y + 18, 22, 18
                    )
                    # Check Select All button area
                    select_all_rect = QRect(
                        main_button_x, sub_menu_start_y + 36, 22, 18
                    )

                    if (
                        invert_selection_rect.contains(pos)
                        or select_none_rect.contains(pos)
                        or select_all_rect.contains(pos)
                    ):
                        return True

                elif menu_id == "misc":
                    sub_menu_start_y = (main_button_y + main_button_height) - (
                        3 * 18
                    )  # 3 buttons
                    # Check Sort List button area
                    sort_list_rect = QRect(main_button_x, sub_menu_start_y + 0, 22, 18)
                    # Check File Info button area
                    file_info_rect = QRect(main_button_x, sub_menu_start_y + 18, 22, 18)
                    # Check Misc Options button area
                    misc_options_rect = QRect(
                        main_button_x, sub_menu_start_y + 36, 22, 18
                    )

                    if (
                        sort_list_rect.contains(pos)
                        or file_info_rect.contains(pos)
                        or misc_options_rect.contains(pos)
                    ):
                        return True

                elif menu_id == "list":
                    sub_menu_start_y = (main_button_y + main_button_height) - (
                        3 * 18
                    )  # 3 buttons
                    # Check New List button area
                    new_list_rect = QRect(main_button_x, sub_menu_start_y + 0, 22, 18)
                    # Check Save List button area
                    save_list_rect = QRect(main_button_x, sub_menu_start_y + 18, 22, 18)
                    # Check Load List button area
                    load_list_rect = QRect(main_button_x, sub_menu_start_y + 36, 22, 18)

                    if (
                        new_list_rect.contains(pos)
                        or save_list_rect.contains(pos)
                        or load_list_rect.contains(pos)
                    ):
                        return True

        return False

    def _handle_resize_move(self, event):
        """Handle window resizing during mouse move."""
        delta = event.globalPos() - self._resize_start_pos

        # Get default size for minimum constraints
        default_width = self.playlist_spec["layout"]["window"]["default_size"]["width"]
        default_height = self.playlist_spec["layout"]["window"]["default_size"][
            "height"
        ]
        # Use the provided content directly

        # Calculate new dimensions
        new_width = self._resize_start_size.width() + delta.x()
        new_height = self._resize_start_size.height() + delta.y()

        # Apply minimum size constraints - window should never be smaller than default size
        new_width = max(new_width, default_width)
        new_height = max(new_height, default_height)  # Never smaller than default size

        # Apply stepped resizing
        # For height, snap to multiples that accommodate complete scrollbar elements
        # The scrollbar groove sprite is SCROLLBAR_GROOVE_HEIGHT (29px), so we should step by this amount
        # The track area starts at y=20 and ends at bottom_bar_y (window.height - 38)
        # So the resizable height portion is new_height - 20 - 38 = new_height - 58
        # This portion should be a multiple of SCROLLBAR_GROOVE_HEIGHT (29) to properly fit scrollbar elements
        base_height = 58  # 20 (top bar) + 38 (bottom bar)
        if new_height > default_height:
            resizable_height = new_height - base_height
            num_steps = round(resizable_height / SCROLLBAR_GROOVE_HEIGHT)
            new_height = base_height + (num_steps * SCROLLBAR_GROOVE_HEIGHT)
        else:
            new_height = default_height  # Maintain at least default size

        # For width, snap to multiples of the bottom filler width (25px)
        filler_width = BOTTOM_FILLER_WIDTH  # PLEDIT_BOTTOM_BAR_FILLER width
        if new_width > default_width:
            resizable_amount = new_width - default_width
            num_steps = round(resizable_amount / filler_width)
            new_width = default_width + num_steps * filler_width
        else:
            new_width = default_width  # Ensure it doesn't go below default

        self.resize(new_width, new_height)

    def _handle_scrollbar_drag_move(self, event):
        """Handle scrollbar thumb dragging during mouse move."""
        self.scrollbar_manager.update_thumb_drag(event.pos())

    def _update_cursor_for_hover(self, event):
        """Update cursor based on hover position."""
        # Change cursor if hovering over resize handle
        resize_handle_size = 16
        resize_rect = QRect(
            self.width() - resize_handle_size,
            self.height() - resize_handle_size,
            resize_handle_size,
            resize_handle_size,
        )

        thumb_rect = self._get_scrollbar_element_rect("thumb")

        if resize_rect.contains(event.pos()):
            self.setCursor(Qt.SizeFDiagCursor)
        elif thumb_rect.contains(event.pos()):
            self.setCursor(Qt.OpenHandCursor)
        elif (
            not self._resizing and not self.scrollbar_manager.dragging_thumb
        ):  # Only reset cursor if not currently resizing or dragging
            self.unsetCursor()  # Restore default cursor

    def _handle_submenu_hover(self, event):
        """Handle hover detection for sub-menu buttons."""
        hovered_id = None
        if self.menu_manager.is_menu_open("add"):
            add_button_data = next(
                (
                    b
                    for b in self.playlist_spec["layout"]["controls"]["button_bar"][
                        "buttons"
                    ]
                    if b["id"] == "add"
                ),
                None,
            )
            if add_button_data:
                button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]
                button_bar_x = button_bar_spec["position"]["x"]
                button_bar_y = self.height() - 30  # Consistent with paintEvent

                main_add_button_x = button_bar_x + add_button_data["x"]
                main_add_button_y = button_bar_y + add_button_data["y"]
                main_add_button_height = 18

                sub_menu_start_y = (main_add_button_y + main_add_button_height) - (
                    3 * 18
                )

                add_url_rect = QRect(main_add_button_x, sub_menu_start_y + 0, 22, 18)
                add_dir_rect = QRect(main_add_button_x, sub_menu_start_y + 18, 22, 18)
                add_file_rect = QRect(main_add_button_x, sub_menu_start_y + 36, 22, 18)

                if add_url_rect.contains(event.pos()):
                    hovered_id = "add_url"
                elif add_dir_rect.contains(event.pos()):
                    hovered_id = "add_dir"
                elif add_file_rect.contains(event.pos()):
                    hovered_id = "add_file"
        elif self.menu_manager.is_menu_open("remove"):
            remove_button_data = next(
                (
                    b
                    for b in self.playlist_spec["layout"]["controls"]["button_bar"][
                        "buttons"
                    ]
                    if b["id"] == "remove"
                ),
                None,
            )
            if remove_button_data:
                button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]
                button_bar_x = button_bar_spec["position"]["x"]
                button_bar_y = self.height() - 30

                main_remove_button_x = button_bar_x + remove_button_data["x"]
                main_remove_button_y = button_bar_y + remove_button_data["y"]
                main_remove_button_height = 18

                sub_menu_start_y = (
                    main_remove_button_y + main_remove_button_height
                ) - (
                    4 * 18
                )  # 4 buttons in remove menu

                remove_duplicates_rect = QRect(
                    main_remove_button_x, sub_menu_start_y + 0, 22, 18
                )
                remove_all_rect = QRect(
                    main_remove_button_x, sub_menu_start_y + 18, 22, 18
                )
                crop_rect = QRect(main_remove_button_x, sub_menu_start_y + 36, 22, 18)
                remove_selected_rect = QRect(
                    main_remove_button_x, sub_menu_start_y + 54, 22, 18
                )

                if remove_duplicates_rect.contains(event.pos()):
                    hovered_id = "remove_duplicates"
                elif remove_all_rect.contains(event.pos()):
                    hovered_id = "remove_all"
                elif crop_rect.contains(event.pos()):
                    hovered_id = "crop"
                elif remove_selected_rect.contains(event.pos()):
                    hovered_id = "remove_selected"
        elif self.menu_manager.is_menu_open("select"):
            select_button_data = next(
                (
                    b
                    for b in self.playlist_spec["layout"]["controls"]["button_bar"][
                        "buttons"
                    ]
                    if b["id"] == "select"
                ),
                None,
            )
            if select_button_data:
                button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]
                button_bar_x = button_bar_spec["position"]["x"]
                button_bar_y = self.height() - 30

                main_select_button_x = button_bar_x + select_button_data["x"]
                main_select_button_y = button_bar_y + select_button_data["y"]
                main_select_button_height = 18

                sub_menu_start_y = (
                    main_select_button_y + main_select_button_height
                ) - (
                    3 * 18
                )  # 3 buttons in select menu

                invert_selection_rect = QRect(
                    main_select_button_x, sub_menu_start_y + 0, 22, 18
                )
                select_none_rect = QRect(
                    main_select_button_x, sub_menu_start_y + 18, 22, 18
                )
                select_all_rect = QRect(
                    main_select_button_x, sub_menu_start_y + 36, 22, 18
                )

                if invert_selection_rect.contains(event.pos()):
                    hovered_id = "invert_selection"
                elif select_none_rect.contains(event.pos()):
                    hovered_id = "select_none"
                elif select_all_rect.contains(event.pos()):
                    hovered_id = "select_all"
        elif self.menu_manager.is_menu_open("misc"):
            misc_button_data = next(
                (
                    b
                    for b in self.playlist_spec["layout"]["controls"]["button_bar"][
                        "buttons"
                    ]
                    if b["id"] == "misc"
                ),
                None,
            )
            if misc_button_data:
                button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]
                button_bar_x = button_bar_spec["position"]["x"]
                button_bar_y = self.height() - 30

                main_misc_button_x = button_bar_x + misc_button_data["x"]
                main_misc_button_y = button_bar_y + misc_button_data["y"]
                main_misc_button_height = 18

                sub_menu_start_y = (main_misc_button_y + main_misc_button_height) - (
                    3 * 18
                )  # 3 buttons in misc menu

                sort_list_rect = QRect(main_misc_button_x, sub_menu_start_y + 0, 22, 18)
                file_info_rect = QRect(
                    main_misc_button_x, sub_menu_start_y + 18, 22, 18
                )
                misc_options_rect = QRect(
                    main_misc_button_x, sub_menu_start_y + 36, 22, 18
                )

                if sort_list_rect.contains(event.pos()):
                    hovered_id = "sort_list"
                elif file_info_rect.contains(event.pos()):
                    hovered_id = "file_info"
                elif misc_options_rect.contains(event.pos()):
                    hovered_id = "misc_options"
        elif self.menu_manager.is_menu_open("list"):
            list_button_data = next(
                (
                    b
                    for b in self.playlist_spec["layout"]["controls"]["button_bar"][
                        "buttons"
                    ]
                    if b["id"] == "list"
                ),
                None,
            )
            if list_button_data:
                # Use the same dynamic positioning for the LIST button as in the button manager
                # Maintain the same distance from right edge as in original skin
                # Original button position was button_bar_x (14) + list button x (218) = 232
                # Original window width was approximately 275, button width is 22
                # Right edge of button was at 232 + 22 = 254
                # So right margin was 275 - 254 = 21
                right_margin = 21  # Approximate right margin in original skin

                # Position button maintaining same margin to right edge
                main_list_button_x = (
                    self.width() - 22 - right_margin
                )  # 22 is typical button width
                # Use the same Y position calculation as in the paintEvent and mouseReleaseEvent
                button_bar_y_calc = self.height() - 28  # Consistent with other handlers
                main_list_button_y = button_bar_y_calc + list_button_data["y"]
                main_list_button_height = 18

                sub_menu_start_y = (main_list_button_y + main_list_button_height) - (
                    3 * 18
                )  # 3 buttons in list menu

                new_list_rect = QRect(main_list_button_x, sub_menu_start_y + 0, 22, 18)
                save_list_rect = QRect(
                    main_list_button_x, sub_menu_start_y + 18, 22, 18
                )
                load_list_rect = QRect(
                    main_list_button_x, sub_menu_start_y + 36, 22, 18
                )

                if new_list_rect.contains(event.pos()):
                    hovered_id = "new_list"
                elif save_list_rect.contains(event.pos()):
                    hovered_id = "save_list"
                elif load_list_rect.contains(event.pos()):
                    hovered_id = "load_list"

        if hovered_id != self.menu_manager.hovered_sub_menu_button_id:
            self.menu_manager.hovered_sub_menu_button_id = hovered_id
            self.update()  # Repaint to show/hide pressed state

    def update_skin(self, skin_data, sprite_manager, text_renderer):
        """Update the playlist window with new skin data."""
        self.skin_data = skin_data
        self.sprite_manager = sprite_manager
        self.text_renderer = text_renderer
        self.extracted_skin_dir = (
            self.skin_data.extracted_skin_dir if self.skin_data else None
        )

        # Reload the playlist specification
        self.config_manager = PlaylistConfig(
            self.skin_data.playlist_spec_json
        )  # Reload config with new skin data
        self.playlist_spec = self.config_manager.get_spec()
        if not self.playlist_spec:
            QMessageBox.critical(
                self,
                "Error",
                "Failed to load playlist window specification after skin change.",
            )
            return

        # Update the scrollbar manager with the new sprite manager
        self.scrollbar_manager.update_sprite_manager(sprite_manager)
        self.scrollbar_manager.extracted_skin_dir = self.extracted_skin_dir

        # Update the menu manager and buttonbar manager if needed
        # Update any other necessary components

        # Reload font settings and colors from pledit.txt
        self._load_playlist_font_settings()  # Load font settings from pledit.txt
        self._load_pledit_colors()  # Reload the color settings

        # Recalculate the font with new settings
        self.playlist_font = QFont(self.playlist_font_name, self.playlist_font_size)

        # Apply region mask if available
        self.apply_region_mask()

        self.update()  # Repaint with new skin

    def moveEvent(self, event):
        """Handle window movement to save position to preferences."""
        super().moveEvent(event)

        # Save the playlist window position to preferences
        # Always save position regardless of docking state, as docked positions are also meaningful
        if hasattr(self, "main_window"):
            if hasattr(self.main_window, "preferences") and not getattr(
                self.main_window, "_is_shutting_down", False
            ):
                self.main_window.preferences.set_playlist_window_position(
                    self.x(), self.y()
                )
