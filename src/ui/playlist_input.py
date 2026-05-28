from PySide6.QtCore import Qt, QRect, QPoint
from ..utils.logger import get_logger
from .playlist_constants import SUB_MENU_ITEMS

logger = get_logger(__name__)


class PlaylistInputMixin:
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
                for i, (item_id, _sprite_prefix, action_name) in enumerate(items):
                    rect = QRect(main_button_x, sub_menu_start_y + i * 18, 22, 18)
                    if rect.contains(event.pos()):
                        getattr(self, action_name)()
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

