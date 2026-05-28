from PySide6.QtCore import QRect
from ..utils.region_utils import apply_region_mask_to_widget


class DockingMixin:
    """Mixin providing window docking and snapping logic for MainWindow."""

    def _get_visible_floating_windows(self, exclude_window=None, require_visible=True):
        windows = []
        for attr in ("playlist_window", "equalizer_window", "album_art_window"):
            win = getattr(self, attr, None)
            if win is None:
                continue
            if exclude_window is not None and win == exclude_window:
                continue
            if require_visible and not win.isVisible():
                continue
            windows.append(win)
        return windows

    def _recalculate_docking_states(self):
        """Recalculate docking states for all floating windows after loading positions.

        This method recalculates the docking state of all floating windows (playlist,
        equalizer, album art) based on their proximity to main window and each other,
        ensuring proper docked state when positions are loaded from preferences.
        """
        floating_windows = self._get_visible_floating_windows(require_visible=False)

        # For each floating window, check if it should be considered docked
        for window in floating_windows:
            if window and window.isVisible():
                # Create QRect for the window's current position
                window_rect = QRect(
                    window.x(), window.y(), window.width(), window.height()
                )

                # Check if the window is near the main window or any other docked windows
                is_near_any = self.is_window_near_any_docked_window(
                    window_rect, exclude_window=window
                )

                # Update the window's docked state
                if hasattr(window, "is_docked"):
                    window.is_docked = is_near_any

    def get_docking_zones(self):
        """Get the docking zones around the main window based on the window snapping specification."""
        # Define docking zones around the main window following SPEC_WINDOWS.md
        edge_threshold = 10  # pixels of tolerance for edge snapping
        center_threshold = 15  # pixels of tolerance for center alignment

        # Define all edges for snapping detection
        zones = {}

        # Horizontal edge zones - detect when other window's horizontal edges approach main window's edges
        zones["main_top"] = QRect(
            self.x() - edge_threshold,
            self.y(),
            self.width() + 2 * edge_threshold,
            edge_threshold,
        )
        zones["main_bottom"] = QRect(
            self.x() - edge_threshold,
            self.y() + self.height(),
            self.width() + 2 * edge_threshold,
            edge_threshold,
        )

        # Vertical edge zones - detect when other window's vertical edges approach main window's edges
        zones["main_left"] = QRect(
            self.x(),
            self.y() - edge_threshold,
            edge_threshold,
            self.height() + 2 * edge_threshold,
        )
        zones["main_right"] = QRect(
            self.x() + self.width(),
            self.y() - edge_threshold,
            edge_threshold,
            self.height() + 2 * edge_threshold,
        )

        # Center alignment zones - detect when other window's center approaches main window's center
        main_center_x = self.x() + self.width() // 2
        main_center_y = self.y() + self.height() // 2

        zones["main_center_x"] = QRect(
            main_center_x - center_threshold,
            self.y(),
            2 * center_threshold,
            self.height(),
        )
        zones["main_center_y"] = QRect(
            self.x(),
            main_center_y - center_threshold,
            self.width(),
            2 * center_threshold,
        )

        return zones

    def apply_region_mask(self):
        """Apply the region mask to the window based on the region.txt data."""
        if self.skin_data.region_data:
            # Apply the region mask for the "Normal" state by default
            apply_region_mask_to_widget(
                self, self.skin_data.region_data, state="Normal"
            )
        else:
            # Clear any existing mask if no region data exists
            self.clearMask()

    def get_snap_alignment(self, dragging_window_rect):
        """
        Calculate proper alignment based on the window snapping specification.
        This method determines the best alignment for a dragging window relative to this main window.

        Args:
            dragging_window_rect: QRect representing the current position of the window being dragged

        Returns:
            tuple: (snapped_x, snapped_y, is_snapped) where is_snapped indicates if any snapping occurred
        """
        # Use helper to check snapping to main window and other windows
        return self._get_snap_alignment_to_target(dragging_window_rect, self)

    def _get_snap_alignment_to_target(self, dragging_window_rect, target_window):
        """
        Calculate alignment to a specific target window.

        Args:
            dragging_window_rect: QRect representing the current position of the window being dragged
            target_window: The window to check alignment against

        Returns:
            tuple: (snapped_x, snapped_y, is_snapped) where is_snapped indicates if any snapping occurred
        """
        # Define the thresholds
        edge_threshold = 10  # pixels for edge alignment
        center_threshold = 15  # pixels for center alignment

        # Define important points of the dragging window
        drag_left = dragging_window_rect.left()
        drag_right = dragging_window_rect.right()
        drag_top = dragging_window_rect.top()
        drag_bottom = dragging_window_rect.bottom()
        drag_center_x = dragging_window_rect.center().x()
        drag_center_y = dragging_window_rect.center().y()
        drag_width = dragging_window_rect.width()
        drag_height = dragging_window_rect.height()

        # Define important points of the target window
        target_left = target_window.x()
        target_right = target_window.x() + target_window.width()
        target_top = target_window.y()
        target_bottom = target_window.y() + target_window.height()
        target_center_x = target_window.x() + target_window.width() // 2
        target_center_y = target_window.y() + target_window.height() // 2

        # Variables to store the snap results
        snap_x = dragging_window_rect.x()
        snap_y = dragging_window_rect.y()
        is_snapped = False

        # 1. Horizontal edge alignment (top/bottom alignment)
        # Check for alignment of dragging window's top with target window's edges
        if abs(drag_top - target_bottom) <= edge_threshold:
            snap_y = target_bottom  # Align drag top with target bottom
            is_snapped = True
        elif abs(drag_bottom - target_top) <= edge_threshold:
            snap_y = target_top - drag_height  # Align drag bottom with target top
            is_snapped = True
        elif abs(drag_top - target_top) <= edge_threshold:
            snap_y = target_top  # Align drag top with target top
            is_snapped = True
        elif abs(drag_bottom - target_bottom) <= edge_threshold:
            snap_y = target_bottom - drag_height  # Align drag bottom with target bottom
            is_snapped = True
        elif abs(drag_center_y - target_center_y) <= center_threshold:
            snap_y = target_center_y - drag_height // 2  # Align centers vertically
            is_snapped = True

        # 2. Vertical edge alignment (left/right alignment)
        # Check for alignment of dragging window's left with target window's edges
        if abs(drag_left - target_right) <= edge_threshold:
            snap_x = target_right  # Align drag left with target right
            is_snapped = True
        elif abs(drag_right - target_left) <= edge_threshold:
            snap_x = target_left - drag_width  # Align drag right with target left
            is_snapped = True
        elif abs(drag_left - target_left) <= edge_threshold:
            snap_x = target_left  # Align drag left with target left
            is_snapped = True
        elif abs(drag_right - target_right) <= edge_threshold:
            snap_x = target_right - drag_width  # Align drag right with target right
            is_snapped = True
        elif abs(drag_center_x - target_center_x) <= center_threshold:
            snap_x = target_center_x - drag_width // 2  # Align centers horizontally
            is_snapped = True

        return snap_x, snap_y, is_snapped

    def get_window_snap_alignment(self, dragging_window_rect, exclude_window=None):
        """
        Calculate proper alignment based on the window snapping specification.
        This method determines the best alignment for a dragging window relative to other windows.

        Args:
            dragging_window_rect: QRect representing the current position of the window being dragged
            exclude_window: Optional window to exclude from checking (e.g., if checking for self)

        Returns:
            tuple: (snapped_x, snapped_y, is_snapped) where is_snapped indicates if any snapping occurred
        """
        # Define the thresholds
        edge_threshold = 10  # pixels for edge alignment
        center_threshold = 15  # pixels for center alignment

        # Define important points of the dragging window
        drag_left = dragging_window_rect.left()
        drag_right = dragging_window_rect.right()
        drag_top = dragging_window_rect.top()
        drag_bottom = dragging_window_rect.bottom()
        drag_center_x = dragging_window_rect.center().x()
        drag_center_y = dragging_window_rect.center().y()
        drag_width = dragging_window_rect.width()
        drag_height = dragging_window_rect.height()

        # Variables to store the final snap results
        snap_x = dragging_window_rect.x()
        snap_y = dragging_window_rect.y()
        is_snapped = False

        # Store all potential snaps with their distances for prioritization
        potential_snaps = []

        # Check for snapping to other windows (main window and floating windows)
        target_windows = [self] + self._get_visible_floating_windows(
            exclude_window=exclude_window
        )

        # Check each target window for potential snapping
        for target_window in target_windows:
            target_left = target_window.x()
            target_right = target_window.x() + target_window.width()
            target_top = target_window.y()
            target_bottom = target_window.y() + target_window.height()
            target_center_x = target_window.x() + target_window.width() // 2
            target_center_y = target_window.y() + target_window.height() // 2

            # 1. Horizontal edge alignment (top/bottom alignment)
            # Calculate distances for each potential snap
            top_to_bottom_dist = abs(drag_top - target_bottom)
            bottom_to_top_dist = abs(drag_bottom - target_top)
            top_to_top_dist = abs(drag_top - target_top)
            bottom_to_bottom_dist = abs(drag_bottom - target_bottom)
            center_y_dist = abs(drag_center_y - target_center_y)

            # Check for alignment of dragging window's top with target window's edges
            if top_to_bottom_dist <= edge_threshold:
                potential_snaps.append(("y", target_bottom, top_to_bottom_dist))
            if bottom_to_top_dist <= edge_threshold:
                potential_snaps.append(
                    ("y", target_top - drag_height, bottom_to_top_dist)
                )
            if top_to_top_dist <= edge_threshold:
                potential_snaps.append(("y", target_top, top_to_top_dist))
            if bottom_to_bottom_dist <= edge_threshold:
                potential_snaps.append(
                    ("y", target_bottom - drag_height, bottom_to_bottom_dist)
                )
            if center_y_dist <= center_threshold:
                potential_snaps.append(
                    ("y", target_center_y - drag_height // 2, center_y_dist)
                )

            # 2. Vertical edge alignment (left/right alignment)
            left_to_right_dist = abs(drag_left - target_right)
            right_to_left_dist = abs(drag_right - target_left)
            left_to_left_dist = abs(drag_left - target_left)
            right_to_right_dist = abs(drag_right - target_right)
            center_x_dist = abs(drag_center_x - target_center_x)

            # Check for alignment of dragging window's left with target window's edges
            if left_to_right_dist <= edge_threshold:
                potential_snaps.append(("x", target_right, left_to_right_dist))
            if right_to_left_dist <= edge_threshold:
                potential_snaps.append(
                    ("x", target_left - drag_width, right_to_left_dist)
                )
            if left_to_left_dist <= edge_threshold:
                potential_snaps.append(("x", target_left, left_to_left_dist))
            if right_to_right_dist <= edge_threshold:
                potential_snaps.append(
                    ("x", target_right - drag_width, right_to_right_dist)
                )
            if center_x_dist <= center_threshold:
                potential_snaps.append(
                    ("x", target_center_x - drag_width // 2, center_x_dist)
                )

        # If we found potential snaps, choose the one with the smallest distance
        if potential_snaps:
            # Sort by distance (closest first)
            sorted_snaps = sorted(potential_snaps, key=lambda x: x[2])

            # Apply the closest snaps for x and y directions (if different directions)
            applied_x = False
            applied_y = False

            for snap_type, snap_pos, dist in sorted_snaps:
                if snap_type == "x" and not applied_x:
                    snap_x = snap_pos
                    applied_x = True
                    is_snapped = True
                elif snap_type == "y" and not applied_y:
                    snap_y = snap_pos
                    applied_y = True
                    is_snapped = True

                # If both x and y are applied, we can stop
                if applied_x and applied_y:
                    break

        return snap_x, snap_y, is_snapped

    def is_window_near_main(self, window_rect):
        """
        Check if a window is still close enough to the main window to be considered docked.

        Args:
            window_rect: QRect representing the position of the window to check

        Returns:
            bool: True if the window is close enough to be considered docked
        """
        # Define the unsnap threshold - if any part of the window is within this distance
        # of any part of the main window, consider it still docked
        unsnap_threshold = 25  # pixels

        # Get main window rect
        main_rect = QRect(self.x(), self.y(), self.width(), self.height())

        # Check if any edges are within the unsnap threshold
        # We calculate the minimum distance between any points of the two rectangles
        # If the rectangles overlap or are within the threshold, consider docked

        # Horizontal distance: distance between rectangles horizontally
        horiz_dist = 0
        if window_rect.right() < main_rect.left():
            horiz_dist = main_rect.left() - window_rect.right()
        elif main_rect.right() < window_rect.left():
            horiz_dist = window_rect.left() - main_rect.right()

        # Vertical distance: distance between rectangles vertically
        vert_dist = 0
        if window_rect.bottom() < main_rect.top():
            vert_dist = main_rect.top() - window_rect.bottom()
        elif main_rect.bottom() < window_rect.top():
            vert_dist = window_rect.top() - main_rect.bottom()

        # Calculate direct distance between closest points of the rectangles
        max_distance = max(horiz_dist, vert_dist)

        # Consider docked if distance is within threshold
        return max_distance <= unsnap_threshold

    def is_window_near_any_docked_window(self, window_rect, exclude_window=None):
        """
        Check if a window is close enough to the main window or any other docked floating window
        to be considered docked.

        Args:
            window_rect: QRect representing the position of the window to check
            exclude_window: Optional window to exclude from checking

        Returns:
            bool: True if the window is close enough to any docked window
        """
        # Define the unsnap threshold - if any part of the window is within this distance
        # of any part of another window, consider it still docked
        unsnap_threshold = 25  # pixels

        target_windows = [self] + self._get_visible_floating_windows(
            exclude_window=exclude_window
        )

        # Check each target window to see if the specified window rect is near it
        for target_window in target_windows:
            target_rect = QRect(
                target_window.x(),
                target_window.y(),
                target_window.width(),
                target_window.height(),
            )

            # Calculate distance between rectangles
            horiz_dist = 0
            if window_rect.right() < target_rect.left():
                horiz_dist = target_rect.left() - window_rect.right()
            elif target_rect.right() < window_rect.left():
                horiz_dist = window_rect.left() - target_rect.right()

            vert_dist = 0
            if window_rect.bottom() < target_rect.top():
                vert_dist = target_rect.top() - window_rect.bottom()
            elif target_rect.bottom() < window_rect.top():
                vert_dist = window_rect.top() - target_rect.bottom()

            # The minimum distance between the rectangles
            max_distance = max(horiz_dist, vert_dist)

            # If this window is within the threshold of any target window, return True
            if max_distance <= unsnap_threshold:
                return True

        # If not near any target window, return False
        return False

    def bring_all_windows_to_foreground(self):
        """Bring all related windows (main, playlist, equalizer, album art) to the foreground."""
        # Activate the main window first
        self.raise_()
        self.activateWindow()

        for win in self._get_visible_floating_windows():
            win.raise_()
            win.activateWindow()
