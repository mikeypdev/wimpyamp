"""Constants for the playlist window."""

# File paths
PLAYLIST_SPEC_PATH = "resources/specs/playlist_window_spec.json"

# UI Dimensions
DEFAULT_BUTTON_HEIGHT = 18
DEFAULT_ROW_HEIGHT = 13
SCROLLBAR_GROOVE_HEIGHT = 29
BOTTOM_FILLER_WIDTH = 25

# UI States
MENU_BUTTON_IDS = ["add", "remove", "select", "misc", "list"]
SUB_MENU_HEIGHTS = {
    "add": 3 * DEFAULT_BUTTON_HEIGHT,
    "remove": 4 * DEFAULT_BUTTON_HEIGHT,
    "select": 3 * DEFAULT_BUTTON_HEIGHT,
    "misc": 3 * DEFAULT_BUTTON_HEIGHT,
    "list": 3 * DEFAULT_BUTTON_HEIGHT,
}

# Default colors
DEFAULT_NORMAL_BG_COLOR = "#000000"
DEFAULT_SELECTED_BG_COLOR = "#0000C6"
DEFAULT_NORMAL_TEXT_COLOR = "#00FF00"
DEFAULT_CURRENT_TEXT_COLOR = "#FFFFFF"
DEFAULT_FONT_NAME = "Arial"
