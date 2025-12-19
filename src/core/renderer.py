from PySide6.QtGui import QPainter, QColor
from .sprite_manager import SpriteManager
from ..ui.ui_state import UIState
from ..utils.color import MAGENTA_TRANSPARENCY_RGB
from ..utils.text_renderer import TextRenderer
from ..utils.scrolling_text_renderer import ScrollingTextRenderer
from ..utils.sprite_validator import validate_sprite_in_bmp
import os
import math


class Renderer:
    def __init__(self, parent_widget):
        self.parent_widget = parent_widget
        self.sprite_manager = SpriteManager()
        self.skin_data = None
        self.text_renderer = None

        # Visualization state management
        self.current_vis_mode = "SPECTRUM"  # Default to spectrum analyzer
        self.vis_bars = [0] * 19  # Current bar heights for spectrum analyzer
        self.vis_peaks = [0] * 19  # Current peak heights for spectrum analyzer
        self.vis_peak_times = [0] * 19  # Track time for peak falloff
        self.audio_data_queue = []  # Queue for audio data

    def set_skin_data(self, skin_data):
        self.skin_data = skin_data
        if skin_data:
            self.text_renderer = TextRenderer(skin_data)
            self.scrolling_text_renderer = ScrollingTextRenderer(
                self.text_renderer, skin_data
            )
            # Add time_display to the draw_order after text_title
            if self.skin_data.spec_json:
                main_window_spec = self.skin_data.spec_json.get("destinations", {}).get(
                    "main_window", {}
                )
                draw_order = main_window_spec.get("draw_order", [])

                # Check if time_display is already in the draw order
                if "time_display" not in draw_order:
                    # Insert time_display after text_title (or add to end if text_title not found)
                    try:
                        text_title_index = draw_order.index("text_title")
                        draw_order.insert(text_title_index + 1, "time_display")
                    except ValueError:
                        # If text_title is not found in draw_order, just append to the end
                        draw_order.append("time_display")

                # Add clutterbar to the draw order early in the sequence (after titlebar)
                if "clutterbar" not in draw_order:
                    try:
                        titlebar_index = draw_order.index("titlebar")
                        draw_order.insert(titlebar_index + 1, "clutterbar")
                    except ValueError:
                        # If titlebar is not found, just append to the beginning
                        draw_order.insert(0, "clutterbar")

    def _draw_sprite_from_spec(
        self,
        painter,
        sheet_name,
        sprite_id,
        dest_area,
        extracted_skin_dir,
        transparency_color=MAGENTA_TRANSPARENCY_RGB,
        sprite_x=None,
        sprite_y=None,
        sprite_w=None,
        sprite_h=None,
        pattern_index=None,
    ):
        """Helper to draw a sprite given its sheet, sprite ID, and destination area."""
        spec = self.skin_data.spec_json
        sheet_path = os.path.join(extracted_skin_dir, sheet_name)
        if not os.path.exists(sheet_path):
            print(f"WARNING: {sheet_name} not found in {extracted_skin_dir}")
            return

        try:
            if sprite_x is None:
                sprite_spec = spec["sheets"][sheet_name]["sprites"][sprite_id]
                # Check if this sprite has a pattern
                if "pattern" in sprite_spec:
                    # Handle pattern-based sprites like DIGITS
                    pattern = sprite_spec["pattern"]
                    # For digits, the coordinates depend on the pattern_index parameter
                    # The pattern has x, y, w, h as base values with step_x to determine position
                    actual_index = pattern_index if pattern_index is not None else 0
                    sprite_x = int(pattern["x"] + (pattern["step_x"] * actual_index))
                    sprite_y = int(pattern["y"])
                    sprite_w = int(pattern["w"])
                    sprite_h = int(pattern["h"])
                else:
                    # Use the direct sprite coordinates
                    sprite_x = int(sprite_spec["x"])
                    sprite_y = int(sprite_spec["y"])
                    sprite_w = int(sprite_spec["w"])
                    sprite_h = int(sprite_spec["h"])

            # Use sprite validator to check if the sprite coordinates are valid in the actual BMP file
            if not validate_sprite_in_bmp(
                sheet_path, sprite_x, sprite_y, sprite_w, sprite_h
            ):
                print(
                    f"WARNING: Sprite '{sprite_id}' at coordinates ({sprite_x}, {sprite_y}, {sprite_w}x{sprite_h}) is out of bounds in {sheet_path}. Skipping."
                )
                return

            pixmap = self.sprite_manager.load_sprite(
                sheet_path,
                sprite_x,
                sprite_y,
                sprite_w,
                sprite_h,
                transparency_color=transparency_color,
            )

            # Only draw if the pixmap is valid (not empty)
            if not pixmap.isNull():
                painter.drawPixmap(dest_area["x"], dest_area["y"], pixmap)
        except KeyError as e:
            print(
                f"ERROR: Sprite '{sprite_id}' not found in sheet '{sheet_name}' spec: {e}"
            )
        except Exception as e:
            print(f"ERROR drawing sprite {sprite_id} from {sheet_name}: {e}")

    def render(self, painter: QPainter, ui_state: "UIState"):
        if not self.skin_data or not self.skin_data.spec_json or not self.text_renderer:
            return

        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        draw_order = main_window_spec["draw_order"]

        for element_name in draw_order:
            if element_name == "background":
                self._render_background(painter)
            elif element_name == "titlebar":
                self._render_titlebar(painter)
            elif element_name == "clutterbar":
                self._render_clutterbar(painter, ui_state)
            elif element_name == "transport_buttons":
                self._render_transport_buttons(painter, ui_state)
            elif element_name == "eject":
                self._render_eject_button(painter, ui_state)
            elif element_name == "shuffle_repeat_eq_pl":
                self._render_shuffle_repeat_eq_pl(painter, ui_state)
            elif element_name == "mono_stereo":
                self._render_mono_stereo(painter, ui_state)
            elif element_name == "sliders_tracks":
                self._render_sliders_tracks(painter, ui_state)
            elif element_name == "text_title":
                self._render_text_title(painter, ui_state)
            elif element_name == "time_display":
                self._render_time_display(painter, ui_state)
            elif element_name == "work_indicator":
                self._render_work_indicator(painter, ui_state)
            elif element_name == "bitrate_sample":
                self._render_bitrate_sample(painter, ui_state)
            elif element_name == "visualization":
                self._render_visualization(painter)

    def _render_background(self, painter: QPainter):
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        main_bmp_path = os.path.join(extracted_skin_dir, "main.bmp")
        if os.path.exists(main_bmp_path):
            background_pixmap = self.sprite_manager.load_sprite(
                main_bmp_path,
                0,
                0,
                275,
                116,
                transparency_color=MAGENTA_TRANSPARENCY_RGB,
            )
            painter.drawPixmap(0, 0, background_pixmap)
        else:
            print(f"WARNING: main.bmp not found in {extracted_skin_dir}")

    def _render_titlebar(self, painter: QPainter):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        dest_area = main_window_spec["areas"]["titlebar"]
        self._draw_sprite_from_spec(
            painter, "titlebar.bmp", "TITLEBAR_NORMAL", dest_area, extracted_skin_dir
        )

    def _render_clutterbar(self, painter: QPainter, ui_state: UIState):
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        sprite_id = "CLUTTERBAR_NORMAL"
        if ui_state.is_options_pressed:
            sprite_id = "CLUTTERBAR_OPTIONS_PRESSED"
        elif ui_state.is_always_on_top_pressed:
            sprite_id = "CLUTTERBAR_ALWAYS_ON_TOP_PRESSED"
        elif ui_state.is_file_info_pressed:
            sprite_id = "CLUTTERBAR_FILE_INFO_PRESSED"
        elif ui_state.is_double_size_pressed:
            sprite_id = "CLUTTERBAR_DOUBLE_SIZE_PRESSED"
        elif ui_state.is_visualization_menu_pressed:
            sprite_id = "CLUTTERBAR_VISUALIZATION_PRESSED"

        titlebar_bmp_path = os.path.join(extracted_skin_dir, "titlebar.bmp")
        if os.path.exists(titlebar_bmp_path):
            sprite_x, sprite_y = 304, 0
            if sprite_id == "CLUTTERBAR_NORMAL":
                sprite_x, sprite_y = 304, 0
            elif sprite_id == "CLUTTERBAR_OPTIONS_PRESSED":
                sprite_x, sprite_y = 304, 44
            elif sprite_id == "CLUTTERBAR_ALWAYS_ON_TOP_PRESSED":
                sprite_x, sprite_y = 312, 44
            elif sprite_id == "CLUTTERBAR_FILE_INFO_PRESSED":
                sprite_x, sprite_y = 320, 44
            elif sprite_id == "CLUTTERBAR_DOUBLE_SIZE_PRESSED":
                sprite_x, sprite_y = 328, 44
            elif sprite_id == "CLUTTERBAR_VISUALIZATION_PRESSED":
                sprite_x, sprite_y = 336, 44

            clutterbar_pixmap = self.sprite_manager.load_sprite(
                titlebar_bmp_path,
                sprite_x,
                sprite_y,
                8,
                43,
                transparency_color=MAGENTA_TRANSPARENCY_RGB,
            )
            painter.drawPixmap(10, 22, clutterbar_pixmap)

    def _render_transport_buttons(self, painter: QPainter, ui_state: UIState):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        controls = main_window_spec["areas"]["controls"]
        for control in controls:
            dest_area = {
                "x": control["dest_x"],
                "y": control["dest_y"],
                "w": control["w"],
                "h": control["h"],
            }
            current_sprite_id = control["sprite"]
            if control["name"] == "previous" and ui_state.is_previous_pressed:
                current_sprite_id = control["sprite_pressed"]
            elif control["name"] == "play" and ui_state.is_play_pressed:
                current_sprite_id = control["sprite_pressed"]
            elif control["name"] == "pause" and ui_state.is_pause_pressed:
                current_sprite_id = control["sprite_pressed"]
            elif control["name"] == "stop" and ui_state.is_stop_pressed:
                current_sprite_id = control["sprite_pressed"]
            elif control["name"] == "next" and ui_state.is_next_pressed:
                current_sprite_id = control["sprite_pressed"]
            self._draw_sprite_from_spec(
                painter,
                "cbuttons.bmp",
                current_sprite_id,
                dest_area,
                extracted_skin_dir,
            )

    def _render_eject_button(self, painter: QPainter, ui_state: UIState):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        dest_area = main_window_spec["areas"]["eject"]
        eject_sprite_id = "EJECT_PRESSED" if ui_state.is_eject_pressed else "EJECT"
        self._draw_sprite_from_spec(
            painter, "cbuttons.bmp", eject_sprite_id, dest_area, extracted_skin_dir
        )

    def _render_shuffle_repeat_eq_pl(self, painter: QPainter, ui_state: UIState):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        dest_area = main_window_spec["areas"]["shuffle_dest"]
        shuffle_sprite_id = "SHUFFLE_OFF"
        if ui_state.shuffle_on:
            shuffle_sprite_id = "SHUFFLE_ON"
        if ui_state.is_shuffle_pressed:
            shuffle_sprite_id += "_PRESSED"
        self._draw_sprite_from_spec(
            painter, "shufrep.bmp", shuffle_sprite_id, dest_area, extracted_skin_dir
        )
        dest_area = main_window_spec["areas"]["repeat_dest"]
        repeat_sprite_id = "REPEAT_OFF"
        if ui_state.repeat_on:
            repeat_sprite_id = "REPEAT_ON"
        if ui_state.is_repeat_pressed:
            repeat_sprite_id += "_PRESSED"
        self._draw_sprite_from_spec(
            painter, "shufrep.bmp", repeat_sprite_id, dest_area, extracted_skin_dir
        )
        dest_area = main_window_spec["areas"]["eq_button"]
        eq_sprite_id = "EQ_OFF"
        if ui_state.eq_button_on:
            eq_sprite_id = "EQ_ON"
        if ui_state.is_eq_pressed:
            eq_sprite_id += "_PRESSED"
        self._draw_sprite_from_spec(
            painter, "shufrep.bmp", eq_sprite_id, dest_area, extracted_skin_dir
        )
        dest_area = main_window_spec["areas"]["playlist_button"]
        pl_sprite_id = "PL_OFF"
        if ui_state.playlist_button_on:
            pl_sprite_id = "PL_ON"
        if ui_state.is_playlist_pressed:
            pl_sprite_id += "_PRESSED"
        self._draw_sprite_from_spec(
            painter, "shufrep.bmp", pl_sprite_id, dest_area, extracted_skin_dir
        )

    def _render_mono_stereo(self, painter: QPainter, ui_state: UIState):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        if ui_state.is_stereo:
            dest_area = main_window_spec["areas"]["stereo_indicator"]
            self._draw_sprite_from_spec(
                painter, "monoster.bmp", "STEREO_ON", dest_area, extracted_skin_dir
            )
            dest_area = main_window_spec["areas"]["mono_indicator"]
            self._draw_sprite_from_spec(
                painter, "monoster.bmp", "MONO_OFF", dest_area, extracted_skin_dir
            )
        else:
            dest_area = main_window_spec["areas"]["stereo_indicator"]
            self._draw_sprite_from_spec(
                painter, "monoster.bmp", "STEREO_OFF", dest_area, extracted_skin_dir
            )
            dest_area = main_window_spec["areas"]["mono_indicator"]
            self._draw_sprite_from_spec(
                painter, "monoster.bmp", "MONO_ON", dest_area, extracted_skin_dir
            )

    def _render_sliders_tracks(self, painter: QPainter, ui_state: UIState):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        spec = self.skin_data.spec_json
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        dest_area_pos_track = main_window_spec["areas"]["position_track"]
        self._draw_sprite_from_spec(
            painter,
            "posbar.bmp",
            "POSITION_TRACK",
            dest_area_pos_track,
            extracted_skin_dir,
        )
        position_thumb_spec = spec["sheets"]["posbar.bmp"]["sprites"]["POSITION_THUMB"]
        thumb_w_pos = position_thumb_spec["w"]
        thumb_h_pos = position_thumb_spec["h"]
        thumb_dest_x_pos = dest_area_pos_track["x"] + round(
            ui_state.position * (dest_area_pos_track["w"] - thumb_w_pos)
        )
        thumb_dest_y_pos = dest_area_pos_track["y"]
        self._draw_sprite_from_spec(
            painter,
            "posbar.bmp",
            "POSITION_THUMB",
            {
                "x": thumb_dest_x_pos,
                "y": thumb_dest_y_pos,
                "w": thumb_w_pos,
                "h": thumb_h_pos,
            },
            extracted_skin_dir,
            sprite_x=position_thumb_spec["x"],
            sprite_y=position_thumb_spec["y"],
            sprite_w=thumb_w_pos,
            sprite_h=thumb_h_pos,
        )
        dest_area_vol = main_window_spec["areas"]["volume_slider"]
        volume_pattern = spec["sheets"]["volume.bmp"]["sprites"]["VOLUME_FRAMES"][
            "pattern"
        ]
        frame_count = volume_pattern["count"]
        frame_index = math.floor(ui_state.volume * (frame_count - 1))
        vol_sprite_x = volume_pattern["x"]
        vol_sprite_y = volume_pattern["y"] + (frame_index * volume_pattern["step_y"])
        vol_sprite_w = volume_pattern["w"]
        vol_sprite_h = volume_pattern["h"]
        self._draw_sprite_from_spec(
            painter,
            "volume.bmp",
            "VOLUME_FRAMES",
            dest_area_vol,
            extracted_skin_dir,
            sprite_x=vol_sprite_x,
            sprite_y=vol_sprite_y,
            sprite_w=vol_sprite_w,
            sprite_h=vol_sprite_h,
        )
        slider_thumb_spec = spec["sheets"]["volume.bmp"]["sprites"]["SLIDER_NORMAL"]
        thumb_w = slider_thumb_spec["w"]
        thumb_h = slider_thumb_spec["h"]
        thumb_dest_x = dest_area_vol["x"] + math.floor(
            ui_state.volume * (dest_area_vol["w"] - thumb_w)
        )
        thumb_dest_y = dest_area_vol["y"] + 1
        volume_thumb_sprite_id = (
            "SLIDER_PRESSED" if ui_state.is_volume_dragged else "SLIDER_NORMAL"
        )
        volume_thumb_coords = spec["sheets"]["volume.bmp"]["sprites"][
            volume_thumb_sprite_id
        ]
        self._draw_sprite_from_spec(
            painter,
            "volume.bmp",
            volume_thumb_sprite_id,
            {"x": thumb_dest_x, "y": thumb_dest_y, "w": thumb_w, "h": thumb_h},
            extracted_skin_dir,
            sprite_x=volume_thumb_coords["x"],
            sprite_y=volume_thumb_coords["y"],
            sprite_w=thumb_w,
            sprite_h=thumb_h,
        )
        dest_area_balance = main_window_spec["areas"]["balance_slider"]
        original_skin_path = self.skin_data.original_skin_path
        is_default_skin = "base-2.91.wsz" in original_skin_path
        balance_sheet = "balance.bmp"
        balance_sprite_id = "BALANCE_FRAMES"
        if is_default_skin:
            if (
                "volume.bmp" in spec["sheets"]
                and "BALANCE_FRAMES" in spec["sheets"]["volume.bmp"]["sprites"]
            ):
                balance_sheet = "volume.bmp"
                balance_sprite_id = "BALANCE_FRAMES"
                balance_pattern = spec["sheets"][balance_sheet]["sprites"][
                    balance_sprite_id
                ]["pattern"]
            elif (
                "volume.bmp" in spec["sheets"]
                and "VOLUME_FRAMES" in spec["sheets"]["volume.bmp"]["sprites"]
            ):
                balance_sheet = "volume.bmp"
                balance_sprite_id = "VOLUME_FRAMES"
                balance_pattern = spec["sheets"][balance_sheet]["sprites"][
                    balance_sprite_id
                ]["pattern"]
                balance_pattern = balance_pattern.copy()
                balance_pattern["x"] = 15
                balance_pattern["w"] = 38
            else:
                return
        elif (
            "balance.bmp" in spec["sheets"]
            and "BALANCE_FRAMES" in spec["sheets"]["balance.bmp"]["sprites"]
        ):
            balance_pattern = spec["sheets"][balance_sheet]["sprites"][
                balance_sprite_id
            ]["pattern"]
        elif (
            "volume.bmp" in spec["sheets"]
            and "BALANCE_FRAMES" in spec["sheets"]["volume.bmp"]["sprites"]
        ):
            balance_sheet = "volume.bmp"
            balance_sprite_id = "BALANCE_FRAMES"
            balance_pattern = spec["sheets"][balance_sheet]["sprites"][
                balance_sprite_id
            ]["pattern"]
        elif (
            "volume.bmp" in spec["sheets"]
            and "VOLUME_FRAMES" in spec["sheets"]["volume.bmp"]["sprites"]
        ):
            balance_sheet = "volume.bmp"
            balance_sprite_id = "VOLUME_FRAMES"
            balance_pattern = spec["sheets"][balance_sheet]["sprites"][
                balance_sprite_id
            ]["pattern"]
            balance_pattern = balance_pattern.copy()
            balance_pattern["x"] = 15
            balance_pattern["w"] = 38
        else:
            return
        balance_abs = abs(ui_state.balance)
        balance_abs = max(0.0, min(1.0, balance_abs))
        frame_count = balance_pattern["count"]
        max_frame_index = frame_count - 1
        frame_index = math.floor(balance_abs * max_frame_index)
        frame_index = max(0, min(max_frame_index, frame_index))
        original_x = balance_pattern["x"]
        original_y = balance_pattern["y"] + (frame_index * balance_pattern["step_y"])
        original_w = balance_pattern["w"]
        original_h = balance_pattern["h"]
        balance_sprite_x = original_x
        balance_sprite_y = original_y
        balance_sprite_w = original_w
        balance_sprite_h = original_h
        self._draw_sprite_from_spec(
            painter,
            balance_sheet,
            balance_sprite_id,
            dest_area_balance,
            extracted_skin_dir,
            sprite_x=balance_sprite_x,
            sprite_y=balance_sprite_y,
            sprite_w=balance_sprite_w,
            sprite_h=balance_sprite_h,
        )
        thumb_position_normalized = (ui_state.balance + 1) / 2
        thumb_position_normalized = max(0.0, min(1.0, thumb_position_normalized))
        thumb_dest_x_balance = dest_area_balance["x"] + math.floor(
            thumb_position_normalized * (dest_area_balance["w"] - thumb_w)
        )
        thumb_dest_y_balance = dest_area_balance["y"] + math.floor(
            (dest_area_balance["h"] - thumb_h) / 2
        )
        balance_thumb_sprite_id = (
            "SLIDER_PRESSED" if ui_state.is_balance_dragged else "SLIDER_NORMAL"
        )
        thumb_sprite_coords = spec["sheets"][balance_sheet]["sprites"][
            balance_thumb_sprite_id
        ]
        self._draw_sprite_from_spec(
            painter,
            balance_sheet,
            balance_thumb_sprite_id,
            {
                "x": thumb_dest_x_balance,
                "y": thumb_dest_y_balance,
                "w": thumb_w,
                "h": thumb_h,
            },
            extracted_skin_dir,
            sprite_x=thumb_sprite_coords["x"],
            sprite_y=thumb_sprite_coords["y"],
            sprite_w=thumb_w,
            sprite_h=thumb_h,
        )

    def _render_text_title(self, painter: QPainter, ui_state: UIState):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        dest_area = main_window_spec["areas"]["song_title_area"]
        if hasattr(self, "parent_widget") and self.parent_widget:
            main_window = self.parent_widget
            current_track_index = getattr(main_window, "current_track_index", 0)
        else:
            current_track_index = 0
        max_width = dest_area["w"]
        self.scrolling_text_renderer.render_track_title(
            painter,
            ui_state.current_track_title,
            current_track_index,
            ui_state.duration,
            dest_area["x"],
            dest_area["y"],
            max_width,
        )

    def _render_time_display(self, painter: QPainter, ui_state: UIState):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        current_time_seconds = (
            int(ui_state.position * ui_state.duration) if ui_state.duration > 0 else 0
        )
        minutes = current_time_seconds // 60
        seconds = current_time_seconds % 60
        min_ten = minutes // 10
        min_one = minutes % 10
        sec_ten = seconds // 10
        sec_one = seconds % 10

        # Check for nums_ex.bmp first (some skins use this name), fall back to numbers.bmp
        nums_ex_bmp_path = os.path.join(extracted_skin_dir, "nums_ex.bmp")
        numbers_bmp_path = os.path.join(extracted_skin_dir, "numbers.bmp")

        if os.path.exists(nums_ex_bmp_path):
            # Use nums_ex.bmp if it exists
            digit_sheet_name = "nums_ex.bmp"
        elif os.path.exists(numbers_bmp_path):
            # Fall back to numbers.bmp
            digit_sheet_name = "numbers.bmp"
        else:
            # Neither file exists, skip rendering
            return

        dest_area = main_window_spec["areas"]["minute_tens"]
        self._draw_sprite_from_spec(
            painter,
            digit_sheet_name,
            "DIGITS",
            dest_area,
            extracted_skin_dir,
            pattern_index=min_ten,
        )
        dest_area = main_window_spec["areas"]["minute_ones"]
        self._draw_sprite_from_spec(
            painter,
            digit_sheet_name,
            "DIGITS",
            dest_area,
            extracted_skin_dir,
            pattern_index=min_one,
        )
        dest_area = main_window_spec["areas"]["second_tens"]
        self._draw_sprite_from_spec(
            painter,
            digit_sheet_name,
            "DIGITS",
            dest_area,
            extracted_skin_dir,
            pattern_index=sec_ten,
        )
        dest_area = main_window_spec["areas"]["second_ones"]
        self._draw_sprite_from_spec(
            painter,
            digit_sheet_name,
            "DIGITS",
            dest_area,
            extracted_skin_dir,
            pattern_index=sec_one,
        )

    def _render_work_indicator(self, painter: QPainter, ui_state: UIState):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        extracted_skin_dir = self.skin_data.extracted_skin_dir
        dest_area = main_window_spec["areas"]["play_indicator_area"]
        if ui_state.is_playing and not ui_state.is_paused:
            sprite_id = "PLAY_INDICATOR"
        elif ui_state.is_paused:
            sprite_id = "PAUSE_INDICATOR"
        else:
            sprite_id = "STOP_INDICATOR"
        self._draw_sprite_from_spec(
            painter, "playpaus.bmp", sprite_id, dest_area, extracted_skin_dir
        )

    def _render_bitrate_sample(self, painter: QPainter, ui_state: UIState):
        main_window_spec = self.skin_data.spec_json["destinations"]["main_window"]
        if ui_state.is_vbr:
            bitrate_text = "VBR"
        else:
            # Handle high bitrates that exceed 3 digits (Winamp Classic display limitation)
            if ui_state.bitrate > 999:
                # For very high bitrates, show "HI " as Winamp often did for extremely high values
                bitrate_text = "HI "
            else:
                bitrate_text = str(ui_state.bitrate)
        dest_area = main_window_spec["areas"]["bitrate"]
        self.text_renderer.render_text(
            painter, bitrate_text, dest_area["x"], dest_area["y"]
        )
        dest_area = main_window_spec["areas"]["sample_rate"]
        # Show "HI" if sample rate has more than two digits (greater than 99)
        sample_rate_text = (
            "HI" if ui_state.sample_rate > 99 else str(ui_state.sample_rate)
        )
        self.text_renderer.render_text(
            painter, sample_rate_text, dest_area["x"], dest_area["y"]
        )

    def _render_visualization(self, painter: QPainter):
        vis_colors = self.skin_data.viscolor_data
        if len(vis_colors) < 24:
            vis_colors = self._get_default_vis_colors()
        vis_area_x = 24
        vis_area_y = 43
        vis_area_width = 76
        vis_area_height = 16
        bg_color = QColor(*vis_colors[0])
        painter.fillRect(
            vis_area_x, vis_area_y, vis_area_width, vis_area_height, bg_color
        )
        if len(vis_colors) > 1:
            dots_color = QColor(*vis_colors[1])
            painter.setPen(dots_color)
            for x in range(vis_area_x + 2, vis_area_x + vis_area_width, 4):
                for y in range(vis_area_y + 2, vis_area_y + vis_area_height, 4):
                    painter.drawPoint(x, y)
        if self.current_vis_mode == "SPECTRUM":
            self._render_spectrum_analyzer(painter, vis_area_x, vis_area_y, vis_colors)
        elif self.current_vis_mode == "OSCILLOSCOPE":
            self._render_oscilloscope(painter, vis_area_x, vis_area_y, vis_colors)

    def _get_default_vis_colors(self):
        """Generate default visualization colors if viscolor.txt is not available."""
        # Default color scheme matching the skin parser defaults
        colors = []

        # Color #0: Background color (black)
        colors.append((0, 0, 0))

        # Color #1: Background dots (dark gray)
        colors.append((40, 40, 40))

        # Create a gradient from blue to red (16 colors for spectrum analyzer)
        for i in range(16):
            # Interpolate from blue to red
            ratio = i / 15.0 if i > 0 else 0
            r = int(255 * ratio)
            g = 0
            b = int(255 * (1 - ratio))
            colors.append(
                (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            )

        # Oscilloscope colors (typically brighter colors for the waveform display)
        osc_colors = [
            (255, 255, 255),  # White
            (0, 255, 0),  # Green
            (0, 128, 255),  # Light blue
            (255, 0, 255),  # Magenta
            (255, 255, 0),  # Yellow
        ]
        colors.extend(osc_colors)

        colors.append((255, 255, 0))  # Additional color

        # Color #24: Additional bright color
        colors.append((255, 128, 0))  # Orange

        return colors[:24]  # Ensure we have exactly 24 colors

    def set_visualization_mode(self, mode):
        """Set the current visualization mode (SPECTRUM, OSCILLOSCOPE, or OFF)."""
        self.current_vis_mode = mode

    def get_visualization_mode(self):
        """Get the current visualization mode."""
        return self.current_vis_mode

    def update_visualization_data(self, audio_data):
        """Update visualization data from the audio engine."""
        if self.current_vis_mode == "SPECTRUM" and audio_data:
            # Update spectrum analyzer data
            self.update_spectrum_data(audio_data)
        elif (
            self.current_vis_mode == "OSCILLOSCOPE"
            and audio_data is not None
            and audio_data.size > 0
        ):
            # Store oscilloscope data
            self.audio_data_queue = audio_data
        # If mode is OFF, we don't need to process audio data

    def update_spectrum_data(self, fft_data):
        """Update spectrum analyzer bar heights based on FFT data."""
        if len(fft_data) >= 19:
            for i in range(19):
                # fft_data[i] is the normalized amplitude (0.0 to 1.0) from the audio engine
                normalized_amplitude = fft_data[i]

                # Map the 0-1 normalized amplitude to the 16-pixel bar height
                height = int(normalized_amplitude * 16)
                height = min(16, height)  # Ensure it doesn't exceed max height

                # Apply falloff effect for the main bars, as per the spec
                if height < self.vis_bars[i]:
                    # If the new height is lower, make the bar fall gradually (e.g., 1 pixel per frame)
                    self.vis_bars[i] = max(0, self.vis_bars[i] - 1)
                else:
                    # If the new height is higher, jump to it immediately
                    self.vis_bars[i] = height

                # Update peak values with its separate, slower falloff
                if self.vis_bars[i] > self.vis_peaks[i]:
                    self.vis_peaks[i] = self.vis_bars[i]
                    self.vis_peak_times[i] = 0  # Reset peak falloff timer
                else:
                    # Apply peak falloff after a certain time
                    self.vis_peak_times[i] += 1
                    if self.vis_peak_times[i] > 20:  # Adjust falloff delay as needed
                        if self.vis_peaks[i] > 0:
                            self.vis_peaks[i] -= 1  # Gradually decrease peak

    def _render_spectrum_analyzer(self, painter, vis_area_x, vis_area_y, vis_colors):
        """Render the spectrum analyzer with 19 vertical bars."""
        # Each bar is 3px wide with 1px gutters, and 1px left gutter
        # Layout: 1px + 19*3px + 18*1px = 76px
        # Each bar is 16px high

        for i in range(19):
            # Calculate bar position (x = left_gutter + i * (bar_width + gutter) + i)
            bar_x = vis_area_x + 1 + i * 4  # 1px left gutter + i*(3px bar + 1px gutter)
            bar_width = 3
            bar_height = self.vis_bars[i]

            # Draw the bar using colors #2-17 from vis_colors
            # Color #17 is at the bottom (level 1), color #2 is at the top (level 16)
            for h in range(bar_height):
                pixel_y = vis_area_y + (16 - h - 1)  # -1 to get the correct position
                color_idx = 17 - h  # Color index from bottom to top
                if 2 <= color_idx <= 17 and color_idx < len(vis_colors):
                    color = QColor(*vis_colors[color_idx])
                    painter.fillRect(bar_x, pixel_y, bar_width, 1, color)

            # Draw peak indicator if applicable
            if self.vis_peaks[i] > 0 and self.vis_peaks[i] <= 16:
                peak_y = vis_area_y + (
                    16 - self.vis_peaks[i]
                )  # Position of peak from top
                peak_color = QColor(*vis_colors[23])  # Color #23 for peaks
                painter.fillRect(bar_x, peak_y, bar_width, 1, peak_color)

    def _render_oscilloscope(self, painter, vis_area_x, vis_area_y, vis_colors):
        """Render the oscilloscope waveform from the audio data queue."""
        if not hasattr(self, "audio_data_queue") or len(self.audio_data_queue) == 0:
            return

        samples = self.audio_data_queue
        num_samples = len(samples)

        # Define the drawing area
        vis_area_width = 76
        vis_area_height = 16
        center_y = vis_area_y + vis_area_height / 2

        # Determine the step to sample the audio data to fit the 76px width
        step = num_samples / float(vis_area_width)

        last_x = vis_area_x
        last_y = center_y

        for i in range(vis_area_width):
            sample_index = int(i * step)

            # Ensure the index is within bounds
            if sample_index < num_samples:
                # The sample value is typically between -1.0 and 1.0
                sample_value = samples[sample_index]

                # Scale the sample value to the visualization area's height
                # A sample value of 1.0 should be at the top, -1.0 at the bottom
                y_pos = center_y - (
                    sample_value * (vis_area_height / 2.5)
                )  # Use a slight buffer
                y_pos = int(
                    max(vis_area_y, min(vis_area_y + vis_area_height - 1, y_pos))
                )

                # Determine color based on amplitude, mapping sample_value [-1, 1] to color indices [18, 22]
                color_idx_float = 20 + (sample_value * 2)  # Maps [-1, 1] to [18, 22]
                color_idx = int(round(color_idx_float))
                color_idx = max(18, min(22, color_idx))

                if 18 <= color_idx < len(vis_colors):
                    color = QColor(*vis_colors[color_idx])
                    painter.setPen(color)

                # To create a thicker line, we can draw a small vertical line for each point
                # For a continuous line, we draw from the last point to the current one
                if i > 0:
                    painter.drawLine(last_x, last_y, vis_area_x + i, y_pos)

                last_x = vis_area_x + i
                last_y = y_pos
