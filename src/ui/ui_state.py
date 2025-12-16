from __future__ import annotations
from dataclasses import dataclass


@dataclass
class UIState:
    """A dataclass to hold the UI state of the main window."""

    volume: float = 0.5
    balance: float = 0.0
    position: float = 0.0
    playlist_button_on: bool = False
    eq_button_on: bool = False
    is_previous_pressed: bool = False
    is_play_pressed: bool = False
    is_pause_pressed: bool = False
    is_stop_pressed: bool = False
    is_next_pressed: bool = False
    is_eject_pressed: bool = False
    is_eq_pressed: bool = False
    is_playlist_pressed: bool = False
    is_shuffle_pressed: bool = False
    is_repeat_pressed: bool = False
    is_volume_dragged: bool = False
    is_balance_dragged: bool = False
    shuffle_on: bool = False
    repeat_on: bool = False
    current_track_title: str = "Not Playing"
    duration: float = 0.0
    is_stereo: bool = True
    bitrate: int = 128
    sample_rate: int = 44
    is_vbr: bool = False
    is_playing: bool = False
    is_paused: bool = False
    is_options_pressed: bool = False
    is_always_on_top_pressed: bool = False
    is_file_info_pressed: bool = False
    is_double_size_pressed: bool = False
    is_visualization_menu_pressed: bool = False
    dragging_position: bool = False
    album_art_visible: bool = False
