from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtCore import QRect, QPoint
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PlaylistRendererMixin:
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
                                logger.warning(f"Could not parse width from condition: {condition}")
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

