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

SUB_MENU_ITEMS = {
    "add": [
        ("add_url", "PLEDIT_ADD_URL_BUTTON", "_load_url_to_playlist"),
        ("add_dir", "PLEDIT_ADD_DIR_BUTTON", "_load_directory_to_playlist"),
        ("add_file", "PLEDIT_ADD_FILE_BUTTON", "_load_file_to_playlist"),
    ],
    "remove": [
        ("remove_duplicates", "PLEDIT_MISC_REMOVE_BUTTON", "_remove_duplicate_tracks"),
        ("remove_all", "PLEDIT_REMOVE_ALL_BUTTON", "_remove_all_tracks"),
        ("crop", "PLEDIT_CROP_BUTTON", "_crop_playlist"),
        ("remove_selected", "PLEDIT_REMOVE_FILE_BUTTON", "remove_playlist_item"),
    ],
    "select": [
        ("invert_selection", "PLEDIT_INVERT_SELECTION_BUTTON", "_invert_selection"),
        ("select_none", "PLEDIT_SELECT_NONE_BUTTON", "_select_none"),
        ("select_all", "PLEDIT_SELECT_ALL_BUTTON", "_select_all"),
    ],
    "misc": [
        ("sort_list", "PLEDIT_SORT_LIST_BUTTON", "_show_sort_dialog"),
        ("file_info", "PLEDIT_FILE_INFO_BUTTON", "_show_file_info"),
        ("misc_options", "PLEDIT_MISC_OPTIONS_BUTTON", "_show_misc_options"),
    ],
    "list": [
        ("new_list", "PLEDIT_NEW_LIST_BUTTON", "_new_playlist"),
        ("save_list", "PLEDIT_SAVE_LIST_BUTTON", "_save_playlist"),
        ("load_list", "PLEDIT_LOAD_LIST_BUTTON", "_load_playlist_from_file"),
    ],
}

SUB_MENU_DECORATION_SPRITES = {
    "add": "PLEDIT_DECORATION_BAR_ADD",
    "remove": "PLEDIT_DECORATION_BAR_REMOVE",
    "select": "PLEDIT_DECORATION_BAR_SELECT",
    "misc": "PLEDIT_DECORATION_BAR_MISC",
    "list": "PLEDIT_DECORATION_BAR_LIST",
}

# Default colors
DEFAULT_NORMAL_BG_COLOR = "#000000"
DEFAULT_SELECTED_BG_COLOR = "#0000C6"
DEFAULT_NORMAL_TEXT_COLOR = "#00FF00"
DEFAULT_CURRENT_TEXT_COLOR = "#FFFFFF"
DEFAULT_FONT_NAME = "Arial"
