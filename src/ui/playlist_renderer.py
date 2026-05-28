from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import QRect, QPoint
from ..utils.logger import get_logger
from .playlist_constants import SUB_MENU_ITEMS, SUB_MENU_DECORATION_SPRITES

logger = get_logger(__name__)


class PlaylistRendererMixin:
    def _get_regions_map(self):
        return {
            key: self.playlist_spec["layout"]["regions"][key]
            for key in (
                "top_bar",
                "left_edge",
                "right_edge",
                "bottom_bar",
                "track_area",
            )
        }

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
        regions_map = self._get_regions_map()

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
                                logger.warning(
                                    f"Could not parse width from condition: {condition}"
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
        regions_map = self._get_regions_map()

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
        regions_map = self._get_regions_map()

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

        # Draw sub-menus if any are open
        for menu_id, items in SUB_MENU_ITEMS.items():
            if not self.menu_manager.is_menu_open(menu_id):
                continue
            button_data = next(
                (b for b in button_bar_spec["buttons"] if b["id"] == menu_id), None
            )
            if not button_data:
                continue
            if menu_id == "list":
                main_button_x = self.width() - 22 - 21
            else:
                main_button_x = button_bar_x + button_data["x"]
            main_button_y = button_bar_y + button_data["y"]
            sub_menu_start_y = (main_button_y + 18) - (len(items) * 18)

            decoration_sprite = self._get_sprite_pixmap(
                SUB_MENU_DECORATION_SPRITES[menu_id]
            )
            if decoration_sprite:
                painter.drawPixmap(
                    main_button_x - 3, sub_menu_start_y, decoration_sprite
                )

            for i, (item_id, sprite_prefix, _action_name) in enumerate(items):
                sprite_id = (
                    f"{sprite_prefix}_PRESSED"
                    if self.menu_manager.hovered_sub_menu_button_id == item_id
                    else f"{sprite_prefix}_UNPRESSED"
                )
                sprite = self._get_sprite_pixmap(sprite_id)
                if sprite:
                    painter.drawPixmap(main_button_x, sub_menu_start_y + i * 18, sprite)

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
