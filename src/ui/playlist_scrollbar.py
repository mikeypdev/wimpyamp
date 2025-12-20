"""Scrollbar manager for the playlist window."""

import os
from PySide6.QtCore import QRect
from ..utils.color import MAGENTA_TRANSPARENCY_RGB


class ScrollbarManager:
    def __init__(self, window, playlist_spec, sprite_manager, skin_data):
        self.window = window
        self.playlist_spec = playlist_spec
        self.sprite_manager = sprite_manager
        self.skin_data = skin_data

        # State for scrollbar elements
        self.pressed_elements = {}  # Stores {element_id: True/False}
        self.dragging_thumb = False
        self.thumb_drag_start_y = 0
        self.thumb_start_scroll_offset = 0

    def get_element_rect(self, element_id):
        """Calculate the rectangle for a scrollbar element."""
        scrollbar_spec = self.playlist_spec["layout"]["controls"]["scrollbar"]

        x_expr = scrollbar_spec["position"]["x"]
        if isinstance(x_expr, str) and "window.width" in x_expr:
            parts = x_expr.split(" - ")
            base = self.window.width() if parts[0] == "window.width" else 0
            offset = sum(int(p) for p in parts[1:])
            scrollbar_x = base - offset
        else:
            scrollbar_x = int(x_expr)

        scrollbar_y = scrollbar_spec["position"]["y"]

        # Calculate bottom bar position
        bottom_bar_spec = self.playlist_spec["layout"]["regions"]["bottom_bar"]
        bottom_bar_y_expr = bottom_bar_spec["position"]["y"]
        if isinstance(bottom_bar_y_expr, str) and bottom_bar_y_expr.startswith(
            "window.height - "
        ):
            offset = int(bottom_bar_y_expr.split(" - ")[1])
            bottom_bar_y = self.window.height() - offset
        else:
            bottom_bar_y = bottom_bar_y_expr

        if element_id == "track":
            # Define the track area from scrollbar_y to bottom_bar_y (without buttons)
            track_y = scrollbar_y
            track_height = bottom_bar_y - scrollbar_y
            # Get width from the track sprite
            track_sprite_id = scrollbar_spec["elements"]["track"]
            track_pixmap = self._get_sprite_pixmap(track_sprite_id)
            track_width = track_pixmap.width() if track_pixmap else 8  # default width

            return QRect(scrollbar_x, track_y, track_width, track_height)
        elif element_id == "thumb":
            # Placeholder for thumb position, will be dynamic
            track_rect = self.get_element_rect("track")
            # Get thumb dimensions
            thumb_sprite_id = scrollbar_spec["elements"]["thumb"]
            thumb_pixmap = self._get_sprite_pixmap(thumb_sprite_id)
            thumb_width = thumb_pixmap.width() if thumb_pixmap else 8
            thumb_height = thumb_pixmap.height() if thumb_pixmap else 18
            return QRect(scrollbar_x, track_rect.y(), thumb_width, thumb_height)
        else:
            # For up_button and down_button, return empty rectangles since we don't use them
            return QRect()

    def _get_sprite_pixmap(self, sprite_id):
        """Helper to get a QPixmap for a given sprite ID from the spec."""
        if (
            not self.sprite_manager
            or not self.skin_data
            or not self.playlist_spec
        ):
            return None

        pledit_bmp_path = self.skin_data.get_path(self.playlist_spec["spriteSheet"]["file"])
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

    def handle_up_button_click(self):
        """Handle click on the up button - not used in this implementation."""
        # This method exists for compatibility but is not used
        pass

    def handle_down_button_click(self):
        """Handle click on the down button - not used in this implementation."""
        # This method exists for compatibility but is not used
        pass

    def handle_track_click(self, pos):
        """Handle click on the scrollbar track."""
        thumb_rect = self.get_element_rect("thumb")
        track_area_spec = self.window.playlist_spec["layout"]["regions"]["track_area"]
        row_height = track_area_spec["row_height"]
        visible_height = (
            self.window.height()
            - track_area_spec["position"]["y"]
            - (self.window.height() - self.window._get_bottom_bar_y())
        )
        num_visible_rows = visible_height // row_height
        total_rows = len(self.window.playlist_items)

        # Calculate max scroll offset based on current window size
        max_scroll_offset = max(0, total_rows - num_visible_rows)

        # Calculate the thumb's current position to determine where the click happened relative to it
        # Re-calculate thumb position based on current scroll offset
        track_rect = self.get_element_rect("track")
        if total_rows > num_visible_rows:
            thumb_proportion = self.window.scroll_offset / (
                total_rows - num_visible_rows
            )
            current_thumb_y = track_rect.y() + int(
                thumb_proportion * (track_rect.height() - thumb_rect.height())
            )
        else:
            current_thumb_y = track_rect.y()

        if pos.y() < current_thumb_y:
            # Clicked above the thumb, scroll up by one page
            self.window.scroll_offset = max(
                0, self.window.scroll_offset - num_visible_rows
            )
        else:
            # Clicked below the thumb, scroll down by one page
            self.window.scroll_offset = min(
                max_scroll_offset, self.window.scroll_offset + num_visible_rows
            )

        self.window.update()

    def start_thumb_drag(self, pos):
        """Start dragging the scrollbar thumb."""
        self.dragging_thumb = True
        self.thumb_drag_start_y = pos.y()
        self.thumb_start_scroll_offset = self.window.scroll_offset

    def update_thumb_drag(self, pos):
        """Update the scrollbar thumb drag position."""
        if not self.dragging_thumb:
            return

        delta_y = pos.y() - self.thumb_drag_start_y

        # Recalculate values based on current window state (in case of resize)
        track_rect = self.get_element_rect("track")
        thumb_pixmap = self._get_sprite_pixmap(
            self.playlist_spec["layout"]["controls"]["scrollbar"]["elements"]["thumb"]
        )
        thumb_height = (
            thumb_pixmap.height() if thumb_pixmap else 0
        )  # Use actual thumb height

        # Calculate visible rows based on current window size
        track_area_spec = self.playlist_spec["layout"]["regions"]["track_area"]
        row_height = track_area_spec["row_height"]
        visible_height = (
            self.window.height()
            - track_area_spec["position"]["y"]
            - (self.window.height() - self.window._get_bottom_bar_y())
        )
        num_visible_rows = visible_height // row_height
        total_rows = len(self.window.playlist_items)

        if total_rows <= num_visible_rows:  # No need to scroll
            return

        scroll_range_pixels = track_rect.height() - thumb_height
        scroll_range_items = total_rows - num_visible_rows

        if scroll_range_pixels > 0:
            # Calculate how many items to scroll per pixel of thumb movement
            items_per_pixel = scroll_range_items / scroll_range_pixels

            # Calculate new scroll offset based on initial offset and pixel movement
            new_scroll_offset = self.thumb_start_scroll_offset + int(
                delta_y * items_per_pixel
            )

            # Clamp scroll offset to valid range
            self.window.scroll_offset = max(
                0, min(new_scroll_offset, scroll_range_items)
            )
            self.window.update()

    def end_thumb_drag(self):
        """End dragging the scrollbar thumb."""
        self.dragging_thumb = False

    def update_sprite_manager(self, new_sprite_manager):
        """Update the sprite manager with a new instance."""
        self.sprite_manager = new_sprite_manager
