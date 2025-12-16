import json
import sys
import os


from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QPainter, QColor, QPainterPath, QPen
from PySide6.QtCore import Qt, QPoint, QRect, QPointF

from ..core.skin_parser import SkinParser
from ..core.sprite_manager import SpriteManager
from ..utils.color import MAGENTA_TRANSPARENCY_RGB
from ..utils.region_utils import apply_region_mask_to_widget


class EqualizerWindow(QWidget):
    def __init__(
        self, parent=None, skin_data=None, sprite_manager=None, audio_engine=None
    ):
        super().__init__(parent)
        self.setWindowTitle("WimPyAmp Equalizer")
        # Set window flags for completely borderless window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.X11BypassWindowManagerHint)

        # Set a transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.skin_data = skin_data
        self.sprite_manager = sprite_manager
        self.audio_engine = audio_engine  # Store reference to audio engine
        self.extracted_skin_dir = (
            self.skin_data.extracted_skin_dir if self.skin_data else None
        )
        self.eq_spec_json = self.skin_data.eq_spec_json if self.skin_data else None

        if self.eq_spec_json:
            default_size = self.eq_spec_json["window"]["default_size"]
            self.setGeometry(0, 0, default_size["w"], default_size["h"])
        else:
            # Fallback if spec is not loaded
            self.setGeometry(0, 0, 275, 116)
            print("WARNING: EQ spec not loaded, using default geometry.")

        # Store button states
        self.on_button_state = "unpressed"
        self.auto_button_state = "unpressed"
        self.presets_button_state = "unpressed"
        self.close_button_state = "unpressed"
        self.slider_values = [50] * 11  # 1 preamp + 10 bands, 0-100 range for now

        # Window dragging state
        self._dragging_window = False
        self._drag_start_position = QPoint()

        self.dragging_slider_index = -1  # -1 if no slider is being dragged
        self.slider_names = [
            "preamp_slider",
            "60hz_slider",
            "170hz_slider",
            "310hz_slider",
            "600hz_slider",
            "1khz_slider",
            "3khz_slider",
            "6khz_slider",
            "12khz_slider",
            "14khz_slider",
            "16khz_slider",
        ]

        self.is_eq_on = False
        self.is_auto_on = False

        # Initialize EQ values from audio engine if available
        if self.audio_engine:
            self._init_eq_values_from_engine()

        # Add docking state and related attributes
        # When window is opened in default position (typically below main window), consider it docked
        self.is_docked = True  # Start as docked by default
        self.docking_offset = QPoint(0, 0)  # Offset from docking position when undocked
        self.dock_margin = 10  # pixels of tolerance for docking

        # Apply region mask if available
        self.apply_region_mask()

    def apply_region_mask(self):
        """Apply the region mask to the window based on the region.txt data."""
        if self.skin_data and self.skin_data.region_data:
            # For equalizer, use the "Equalizer" state from region data
            apply_region_mask_to_widget(
                self, self.skin_data.region_data, state="Equalizer"
            )
        else:
            # Clear any existing mask if no region data exists
            self.clearMask()

    def _init_eq_values_from_engine(self):
        """Initialize EQ slider values from the audio engine."""
        if not self.audio_engine:
            return

        # Set initial EQ on/off state
        self.is_eq_on = self.audio_engine.is_eq_on
        self.on_button_state = "selected" if self.is_eq_on else "unpressed"

        # Convert audio engine's EQ bands back to slider values (0-100)
        # Preamp: ranges from -12dB to +12dB (Winamp standard), convert to 0-100
        preamp_db = self.audio_engine.eq_bands.get("preamp", 0.0)
        self.slider_values[0] = int(((preamp_db + 12.0) / 24.0) * 100)

        # Frequency bands: 60hz, 170hz, 310hz, 600hz, 1khz, 3khz, 6khz, 12khz, 14khz, 16khz
        freq_bands = [
            "60hz",
            "170hz",
            "310hz",
            "600hz",
            "1khz",
            "3khz",
            "6khz",
            "12khz",
            "14khz",
            "16khz",
        ]
        for i, band_name in enumerate(freq_bands):
            band_db = self.audio_engine.eq_bands.get(band_name, 0.0)
            self.slider_values[i + 1] = int(((band_db + 12.0) / 24.0) * 100)

    def mousePressEvent(self, event):
        # Bring all related windows to foreground when clicked
        if hasattr(self, "main_window") and self.main_window:
            self.main_window.bring_all_windows_to_foreground()

        if event.button() == Qt.LeftButton:
            # Check for button interaction first (before titlebar dragging)
            # Close button - check first since it's in the titlebar area
            close_button_dest = self.eq_spec_json["destinations"]["close_button"]
            close_button_rect = QRect(
                close_button_dest["x"],
                close_button_dest["y"],
                close_button_dest["w"],
                close_button_dest["h"],
            )
            if close_button_rect.contains(event.pos()):
                self.close_button_state = "pressed"
                self.update()
                return

            # On button
            on_button_dest = self.eq_spec_json["destinations"]["on_button"]
            on_button_rect = QRect(
                on_button_dest["x"],
                on_button_dest["y"],
                on_button_dest["w"],
                on_button_dest["h"],
            )
            if on_button_rect.contains(event.pos()):
                self.on_button_state = (
                    "selected_depressed" if self.is_eq_on else "depressed"
                )
                self.update()
                return

            # Auto button
            auto_button_dest = self.eq_spec_json["destinations"]["auto_button"]
            auto_button_rect = QRect(
                auto_button_dest["x"],
                auto_button_dest["y"],
                auto_button_dest["w"],
                auto_button_dest["h"],
            )
            if auto_button_rect.contains(event.pos()):
                self.auto_button_state = (
                    "selected_depressed" if self.is_auto_on else "depressed"
                )
                self.update()
                return

            # Presets button
            presets_button_dest = self.eq_spec_json["destinations"]["presets_button"]
            presets_button_rect = QRect(
                presets_button_dest["x"],
                presets_button_dest["y"],
                presets_button_dest["w"],
                presets_button_dest["h"],
            )
            if presets_button_rect.contains(event.pos()):
                self.presets_button_state = "pressed"
                self.update()
                return

            # Check for slider interaction
            for i, slider_name in enumerate(self.slider_names):
                slider_dest = self.eq_spec_json["destinations"][slider_name]
                slider_rect = QRect(
                    slider_dest["x"],
                    slider_dest["y"],
                    slider_dest["w"],
                    slider_dest["h"],
                )

                if slider_rect.contains(event.pos()):
                    self.dragging_slider_index = i
                    self._update_slider_value_from_mouse(event.pos().y())
                    self.update()
                    return

            # Check if click is on titlebar for window dragging (only if not on buttons)
            # Titlebar is at the top of the window, typically 14 pixels high
            titlebar_rect = QRect(0, 0, self.width(), 14)
            if titlebar_rect.contains(event.pos()):
                # If click is in titlebar but not on any button, enable dragging
                self._dragging_window = True
                self._drag_start_position = (
                    event.globalPos() - self.frameGeometry().topLeft()
                )
                return

        super().mousePressEvent(event)

    def focusInEvent(self, event):
        """Called when the equalizer window receives focus."""
        # Bring all related windows to foreground when equalizer gains focus
        if hasattr(self, "main_window") and self.main_window:
            self.main_window.bring_all_windows_to_foreground()
        super().focusInEvent(event)

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
        if self.dragging_slider_index != -1:
            self._update_slider_value_from_mouse(event.pos().y())
            self.update()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._dragging_window:
                self._dragging_window = False
                return
            # Release slider
            if self.dragging_slider_index != -1:
                self.dragging_slider_index = -1
                self.update()
                return

            # Check if we should reset button states based on where the mouse was released
            # For all buttons, if released outside their area, reset the corresponding state
            # Close button
            close_button_dest = self.eq_spec_json["destinations"]["close_button"]
            close_button_rect = QRect(
                close_button_dest["x"],
                close_button_dest["y"],
                close_button_dest["w"],
                close_button_dest["h"],
            )
            if close_button_rect.contains(event.pos()):
                # Close the window when the close button is clicked
                self.close()  # Close the window - state will be reset after closing anyway
                return
            else:
                # If mouse was released outside the close button, reset its state
                self.close_button_state = "unpressed"
                self.update()

            # On button - only process if not on close button
            on_button_dest = self.eq_spec_json["destinations"]["on_button"]
            on_button_rect = QRect(
                on_button_dest["x"],
                on_button_dest["y"],
                on_button_dest["w"],
                on_button_dest["h"],
            )
            if on_button_rect.contains(event.pos()):
                self.is_eq_on = not self.is_eq_on
                self.on_button_state = "selected" if self.is_eq_on else "unpressed"
                # Update the audio engine with the new EQ on/off state
                if self.audio_engine:
                    self.audio_engine.toggle_eq(self.is_eq_on)
                self.update()
                return

            # Auto button - only process if not on other buttons
            auto_button_dest = self.eq_spec_json["destinations"]["auto_button"]
            auto_button_rect = QRect(
                auto_button_dest["x"],
                auto_button_dest["y"],
                auto_button_dest["w"],
                auto_button_dest["h"],
            )
            if auto_button_rect.contains(event.pos()):
                self.is_auto_on = not self.is_auto_on
                self.auto_button_state = "selected" if self.is_auto_on else "unpressed"
                self.update()
                return

            # Presets button - only process if not on other buttons
            presets_button_dest = self.eq_spec_json["destinations"]["presets_button"]
            presets_button_rect = QRect(
                presets_button_dest["x"],
                presets_button_dest["y"],
                presets_button_dest["w"],
                presets_button_dest["h"],
            )
            if presets_button_rect.contains(event.pos()):
                self.presets_button_state = "unpressed"
                self.update()
                return

        super().mouseReleaseEvent(event)

    def enterEvent(self, event):
        """Called when the mouse enters the widget."""
        # Handle potential hover effects for buttons if needed in the future
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Called when the mouse leaves the widget."""
        # Reset button states when mouse leaves the window
        if self.close_button_state != "unpressed":
            self.close_button_state = "unpressed"
            self.update()
        super().leaveEvent(event)

    def _update_slider_value_from_mouse(self, mouse_y):
        if self.dragging_slider_index == -1:
            return

        slider_name = self.slider_names[self.dragging_slider_index]
        slider_dest = self.eq_spec_json["destinations"][slider_name]

        # Max Y for knob (bottom of slider - knob height)
        knob_height = self.eq_spec_json["sprites"]["EQMAIN"]["slider_thumb"]["h"]
        max_knob_y = slider_dest["y"] + slider_dest["h"] - knob_height
        min_knob_y = slider_dest["y"]

        # Clamp mouse_y to the slider's vertical range
        clamped_mouse_y = max(min_knob_y, min(mouse_y, max_knob_y + knob_height))

        # Calculate value (0-100) from Y position
        # In Winamp, 0 is at the bottom, 100 is at the top.
        # So, a higher Y (lower on screen) means a lower value.

        # Normalize mouse_y to a 0-1 range within the slider's active area
        # The active area for the knob is from min_knob_y to max_knob_y
        normalized_y = (clamped_mouse_y - min_knob_y) / (max_knob_y - min_knob_y)

        # Invert the normalized_y because 0 is at the bottom (max_knob_y) and 1 is at the top (min_knob_y)
        value = (1 - normalized_y) * 100

        self.slider_values[self.dragging_slider_index] = max(0, min(100, int(value)))

        # Send the updated EQ values to the audio engine
        self._send_eq_values_to_engine()

    def _send_eq_values_to_engine(self):
        """Send current EQ slider values to the audio engine."""
        if not self.audio_engine:
            return

        # Map slider values to EQ bands
        # Slider values are 0-100, convert to -12dB to +12dB range (Winamp standard)
        # 0 -> -12dB, 50 -> 0dB, 100 -> +12dB
        eq_bands = {}

        # Preamp slider (index 0) - maps to 'preamp'
        eq_bands["preamp"] = (
            self.slider_values[0] / 100.0
        ) * 24.0 - 12.0  # -12dB to +12dB

        # Frequency bands
        freq_bands = [
            "60hz",
            "170hz",
            "310hz",
            "600hz",
            "1khz",
            "3khz",
            "6khz",
            "12khz",
            "14khz",
            "16khz",
        ]
        for i, band_name in enumerate(freq_bands):
            slider_value = self.slider_values[i + 1]  # +1 because index 0 is preamp
            eq_bands[band_name] = (slider_value / 100.0) * 24.0 - 12.0  # -12dB to +12dB

        # Update the audio engine with new EQ values
        self.audio_engine.set_eq(eq_bands)
        # Enable EQ if any band is not 0dB or if the EQ is turned on
        self.audio_engine.toggle_eq(self.is_eq_on)

    def paintEvent(self, event):
        painter = QPainter(self)
        if (
            not self.extracted_skin_dir
            or not self.sprite_manager
            or not self.eq_spec_json
        ):
            print("ERROR: Missing skin data, sprite manager, or EQ spec.")
            painter.end()
            return

        # Draw background
        background_spec = self.eq_spec_json["sprites"]["EQMAIN"]["background"]
        background_pixmap = self.sprite_manager.load_sprite(
            os.path.join(self.extracted_skin_dir, "EQMAIN.BMP"),
            background_spec["x"],
            background_spec["y"],
            background_spec["w"],
            background_spec["h"],
            transparency_color=MAGENTA_TRANSPARENCY_RGB,
        )
        painter.drawPixmap(0, 0, background_pixmap)

        # Draw titlebar
        titlebar_spec = self.eq_spec_json["sprites"]["EQMAIN"][
            "title_bar_selected"
        ]  # Assuming selected for now
        titlebar_dest = self.eq_spec_json["destinations"]["titlebar"]
        titlebar_pixmap = self.sprite_manager.load_sprite(
            os.path.join(self.extracted_skin_dir, "EQMAIN.BMP"),
            titlebar_spec["x"],
            titlebar_spec["y"],
            titlebar_spec["w"],
            titlebar_spec["h"],
            transparency_color=MAGENTA_TRANSPARENCY_RGB,
        )
        painter.drawPixmap(titlebar_dest["x"], titlebar_dest["y"], titlebar_pixmap)

        # Draw buttons
        self._draw_button(painter, "on_button", self.on_button_state)
        self._draw_button(painter, "auto_button", self.auto_button_state)
        self._draw_button(painter, "presets_button", self.presets_button_state)
        self._draw_button(painter, "close_button", self.close_button_state)

        # Draw reset buttons
        self._draw_reset_button(painter, "plus_12db_reset")
        self._draw_reset_button(painter, "zero_db_reset")
        self._draw_reset_button(painter, "minus_12db_reset")

        # Draw sliders
        self._draw_slider(painter, "preamp_slider", self.slider_values[0])
        self._draw_slider(painter, "60hz_slider", self.slider_values[1])
        self._draw_slider(painter, "170hz_slider", self.slider_values[2])
        self._draw_slider(painter, "310hz_slider", self.slider_values[3])
        self._draw_slider(painter, "600hz_slider", self.slider_values[4])
        self._draw_slider(painter, "1khz_slider", self.slider_values[5])
        self._draw_slider(painter, "3khz_slider", self.slider_values[6])
        self._draw_slider(painter, "6khz_slider", self.slider_values[7])
        self._draw_slider(painter, "12khz_slider", self.slider_values[8])
        self._draw_slider(painter, "14khz_slider", self.slider_values[9])
        self._draw_slider(painter, "16khz_slider", self.slider_values[10])

        # Draw minidisplay
        self._draw_minidisplay(painter)

        painter.end()

    def _draw_minidisplay(self, painter):
        graph_background_spec = self.eq_spec_json["sprites"]["EQMAIN"][
            "graph_background"
        ]
        graph_background_pixmap = self.sprite_manager.load_sprite(
            os.path.join(self.extracted_skin_dir, "EQMAIN.BMP"),
            graph_background_spec["x"],
            graph_background_spec["y"],
            graph_background_spec["w"],
            graph_background_spec["h"],
            transparency_color=MAGENTA_TRANSPARENCY_RGB,
        )
        # The minidisplay is located at (86, 16) on the EQ window
        graph_dest_x = 86
        graph_dest_y = 16
        painter.drawPixmap(graph_dest_x, graph_dest_y, graph_background_pixmap)

        # Load graph_line_colors
        graph_line_colors_spec = self.eq_spec_json["sprites"]["EQMAIN"][
            "graph_line_colors"
        ]
        graph_line_colors_pixmap = self.sprite_manager.load_sprite(
            os.path.join(self.extracted_skin_dir, "EQMAIN.BMP"),
            graph_line_colors_spec["x"],
            graph_line_colors_spec["y"],
            graph_line_colors_spec["w"],
            graph_line_colors_spec["h"],
            transparency_color=MAGENTA_TRANSPARENCY_RGB,
        )

        # Extract colors from graph_line_colors_pixmap
        colors = []
        image = graph_line_colors_pixmap.toImage()
        for y in range(image.height()):
            colors.append(QColor(image.pixel(0, y)))

        # Map slider values to graph points (excluding preamp)
        # The spline will be drawn for the 10 frequency bands
        spline_slider_values = self.slider_values[1:]  # Exclude preamp

        points = []
        graph_width = graph_background_spec["w"]
        graph_height = graph_background_spec["h"]

        # X-coordinates for the 10 frequency band sliders across the 113 pixels
        # The graph is 113 pixels wide. The 10 sliders should span this width.
        # The first frequency band slider (60hz) is at x=0, last at x=112
        x_coords = [
            i * (graph_width - 1) / (len(spline_slider_values) - 1)
            for i in range(len(spline_slider_values))
        ]

        for i, value in enumerate(spline_slider_values):
            # Map slider value (0-100) to Y-coordinate (0-18)
            # 0 is at the bottom (y=18), 100 is at the top (y=0)
            graph_y = (1 - (value / 100)) * (graph_height - 1)
            points.append(QPointF(graph_dest_x + x_coords[i], graph_dest_y + graph_y))

        # Draw preamp line
        preamp_line_spec = self.eq_spec_json["sprites"]["EQMAIN"]["preamp_line"]
        preamp_line_pixmap = self.sprite_manager.load_sprite(
            os.path.join(self.extracted_skin_dir, "EQMAIN.BMP"),
            preamp_line_spec["x"],
            preamp_line_spec["y"],
            preamp_line_spec["w"],
            preamp_line_spec["h"],
            transparency_color=MAGENTA_TRANSPARENCY_RGB,
        )
        # Calculate Y position for preamp line based on preamp slider value
        preamp_value = self.slider_values[0]
        preamp_graph_y = int((1 - (preamp_value / 100)) * (graph_height - 1))
        painter.drawPixmap(
            graph_dest_x, graph_dest_y + preamp_graph_y, preamp_line_pixmap
        )

        # Draw spline
        if len(points) > 1:
            painter.setRenderHint(QPainter.Antialiasing)

            # Iterate through segments
            for i in range(len(points) - 1):
                # Current segment is from points[i] to points[i+1]
                # We need 4 points: p_prev, p_current, p_next, p_next_next

                p_current = points[i]
                p_next = points[i + 1]

                # Determine p_prev
                if i == 0:
                    p_prev = points[0]  # Use the first point as its own predecessor
                else:
                    p_prev = points[i - 1]

                # Determine p_next_next
                if i + 2 >= len(points):
                    p_next_next = points[
                        len(points) - 1
                    ]  # Use the last point as its own successor
                else:
                    p_next_next = points[i + 2]

                # Catmull-Rom to Bezier conversion
                c1 = QPointF(
                    p_current.x() + (p_next.x() - p_prev.x()) / 6,
                    p_current.y() + (p_next.y() - p_prev.y()) / 6,
                )
                c2 = QPointF(
                    p_next.x() - (p_next_next.x() - p_current.x()) / 6,
                    p_next.y() - (p_next_next.y() - p_current.y()) / 6,
                )

                # Create a path for the current segment
                segment_path = QPainterPath()
                segment_path.moveTo(p_current)
                segment_path.cubicTo(c1, c2, p_next)

                # Determine color based on the average Y of the segment
                avg_y_segment = int((p_current.y() + p_next.y()) / 2) - graph_dest_y
                avg_y_segment = max(0, min(avg_y_segment, graph_height - 1))

                painter.setPen(QPen(colors[avg_y_segment], 1))
                painter.drawPath(segment_path)

    def _draw_button(self, painter, button_name, state):
        if button_name == "presets_button":
            if state == "pressed":
                sprite_name = "presets_button_selected"
            else:
                sprite_name = "presets_button"
        elif button_name == "close_button":
            # Handle the close button which has special active state sprites
            if state == "pressed":
                sprite_name = "close_button_active"  # Use active state when pressed
            else:
                sprite_name = "close_button"  # Use normal state when unpressed
        else:
            sprite_key = button_name.replace("_button", "")
            if state == "unpressed":
                sprite_name = f"{sprite_key}_button"
            elif state == "pressed":
                sprite_name = f"{sprite_key}_button_depressed"
            elif state == "selected":
                sprite_name = f"{sprite_key}_button_selected"
            elif state == "selected_depressed":
                sprite_name = f"{sprite_key}_button_selected_depressed"
            else:
                sprite_name = f"{sprite_key}_button"  # Fallback

        sprite_info = self.eq_spec_json["sprites"]["EQMAIN"][sprite_name]
        dest = self.eq_spec_json["destinations"][button_name]
        pixmap = self.sprite_manager.load_sprite(
            os.path.join(self.extracted_skin_dir, "EQMAIN.BMP"),
            sprite_info["x"],
            sprite_info["y"],
            sprite_info["w"],
            sprite_info["h"],
            transparency_color=MAGENTA_TRANSPARENCY_RGB,
        )
        painter.drawPixmap(dest["x"], dest["y"], pixmap)

    def _draw_reset_button(self, painter, button_name):
        # For now, these are just regions on the background, no separate sprites
        # We will draw a transparent rectangle to indicate their clickable area
        # painter.fillRect(self.eq_spec_json["destinations"][button_name]["x"], self.eq_spec_json["destinations"][button_name]["y"], self.eq_spec_json["destinations"][button_name]["w"], self.eq_spec_json["destinations"][button_name]["h"], QColor(100, 100, 100, 50)) # For debugging
        pass

    def _draw_slider(self, painter, slider_name, value):
        slider_dest = self.eq_spec_json["destinations"][slider_name]

        # Determine which slider bar sprite to use based on the value
        # The slider_bars are ordered from -20db to +20db.
        # Value is 0-100. We need to map this to the 28 slider_bars.
        # 0-100 -> 0-27 index
        # Map value (0-100) to slider_bars index (0-26)
        slider_bar_index = round(value / 100 * 26)
        slider_bar_spec = self.eq_spec_json["sprites"]["EQMAIN"]["slider_bars"][
            slider_bar_index
        ]
        slider_bar_pixmap = self.sprite_manager.load_sprite(
            os.path.join(self.extracted_skin_dir, "EQMAIN.BMP"),
            slider_bar_spec["x"],
            slider_bar_spec["y"],
            slider_bar_spec["w"],
            slider_bar_spec["h"],
            transparency_color=MAGENTA_TRANSPARENCY_RGB,
        )
        painter.drawPixmap(slider_dest["x"], slider_dest["y"], slider_bar_pixmap)

        # Draw the slider thumb
        knob_sprite_info = self.eq_spec_json["sprites"]["EQMAIN"]["slider_thumb"]
        knob_pixmap = self.sprite_manager.load_sprite(
            os.path.join(self.extracted_skin_dir, "EQMAIN.BMP"),
            knob_sprite_info["x"],
            knob_sprite_info["y"],
            knob_sprite_info["w"],
            knob_sprite_info["h"],
            transparency_color=MAGENTA_TRANSPARENCY_RGB,
        )

        # Calculate knob position based on slider value (0-100)
        # The slider bar height is 63 pixels.
        # Top of the slider is slider_dest["y"]
        # Bottom of the slider is slider_dest["y"] + slider_dest["h"]
        # Knob height is knob_pixmap.height()

        # Max Y for knob (bottom of slider - knob height)
        max_knob_y = slider_dest["y"] + slider_dest["h"] - knob_pixmap.height()
        # Min Y for knob (top of slider)
        min_knob_y = slider_dest["y"]

        # Map value (0-100) to Y position (max_knob_y to min_knob_y)
        # In Winamp, 0 is at the bottom, 100 is at the top.
        knob_y = max_knob_y - (value / 100) * (max_knob_y - min_knob_y)

        knob_x = slider_dest["x"] + (slider_dest["w"] - knob_pixmap.width()) // 2
        painter.drawPixmap(knob_x, int(knob_y), knob_pixmap)

    def moveEvent(self, event):
        """Handle window movement to save position to preferences."""
        super().moveEvent(event)

        # Save the EQ window position to preferences
        # Always save position regardless of docking state, as docked positions are also meaningful
        if hasattr(self, "main_window"):
            if hasattr(self.main_window, "preferences") and not getattr(
                self.main_window, "_is_shutting_down", False
            ):
                self.main_window.preferences.set_eq_window_position(self.x(), self.y())

    def closeEvent(self, event):
        """Override close event to delegate to main window for centralized state management."""
        # Only update main window's state if not in global shutdown
        if (
            not getattr(self.main_window, "_is_shutting_down", False)
            and hasattr(self, "main_window")
            and self.main_window
            and hasattr(self.main_window, "hide_equalizer_window")
        ):

            # Call the main window's centralized method to hide the equalizer window
            # This ensures consistent state management from a single source of truth
            self.main_window.hide_equalizer_window()

        # Accept the close event to actually close the window
        event.accept()

    def update_skin(self, skin_data, sprite_manager):
        """Update the equalizer window with new skin data."""
        self.skin_data = skin_data
        self.sprite_manager = sprite_manager
        self.extracted_skin_dir = (
            self.skin_data.extracted_skin_dir if self.skin_data else None
        )
        self.eq_spec_json = self.skin_data.eq_spec_json if self.skin_data else None

        if self.eq_spec_json:
            default_size = self.eq_spec_json["window"]["default_size"]
            self.setGeometry(self.x(), self.y(), default_size["w"], default_size["h"])
        else:
            # Fallback if spec is not loaded
            print("WARNING: EQ spec not loaded, using default geometry.")

        # Apply region mask if available
        self.apply_region_mask()

        self.update()  # Repaint with new skin


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Setup a minimal environment for testing
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    skin_path = os.path.join(project_root, "resources", "default_skin", "base-2.91.wsz")
    eq_spec_path = os.path.join(
        project_root, "resources", "specs", "eq_window_spec.json"
    )

    skin_parser = SkinParser(skin_path)
    skin_data = skin_parser.parse()

    # Load eq_spec_json separately and add to skin_data
    with open(eq_spec_path, "r") as f:
        skin_data.eq_spec_json = json.load(f)

    sprite_manager = SpriteManager()

    eq_window = EqualizerWindow(None, skin_data, sprite_manager)
    eq_window.show()
    sys.exit(app.exec_())
