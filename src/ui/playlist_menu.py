"""Menu manager for the playlist window."""

from PySide6.QtCore import QRect
from .playlist_constants import DEFAULT_BUTTON_HEIGHT, SUB_MENU_HEIGHTS


class MenuManager:
    def __init__(self, window, playlist_spec):
        self.window = window
        self.playlist_spec = playlist_spec

        # State for menus
        self.add_menu_open = False
        self.remove_menu_open = False
        self.select_menu_open = False
        self.misc_menu_open = False
        self.list_menu_open = False
        self.hovered_sub_menu_button_id = None

    def close_all_menus(self):
        """Close all open sub-menus."""
        self.add_menu_open = False
        self.remove_menu_open = False
        self.select_menu_open = False
        self.misc_menu_open = False
        self.list_menu_open = False
        self.hovered_sub_menu_button_id = None
        self.window.update()

    def toggle_menu(self, button_id):
        """Toggle a specific menu."""
        # Close all menus first
        self.close_all_menus()

        # Open the requested menu
        if button_id == "add":
            self.add_menu_open = True
        elif button_id == "remove":
            self.remove_menu_open = True
        elif button_id == "select":
            self.select_menu_open = True
        elif button_id == "misc":
            self.misc_menu_open = True
        elif button_id == "list":
            self.list_menu_open = True

        self.window.update()

    def get_menu_rect(self, button_id):
        """Get the bounding rectangle for a menu."""
        button_data = next(
            (
                b
                for b in self.playlist_spec["layout"]["controls"]["button_bar"][
                    "buttons"
                ]
                if b["id"] == button_id
            ),
            None,
        )
        if not button_data:
            return QRect()

        button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]
        button_bar_x = button_bar_spec["position"]["x"]
        button_bar_y = self.window.height() - 28  # Consistent with paintEvent

        main_button_x = button_bar_x + button_data["x"]
        main_button_y = button_bar_y + button_data["y"]
        main_button_height = DEFAULT_BUTTON_HEIGHT

        sub_menu_height = SUB_MENU_HEIGHTS.get(button_id, 3 * DEFAULT_BUTTON_HEIGHT)
        sub_menu_start_y = (main_button_y + main_button_height) - sub_menu_height

        # Bounding box for menu (buttons + decoration bar)
        return QRect(main_button_x - 3, sub_menu_start_y, 22 + 3, sub_menu_height)

    def is_menu_open(self, button_id):
        """Check if a specific menu is open."""
        if button_id == "add":
            return self.add_menu_open
        elif button_id == "remove":
            return self.remove_menu_open
        elif button_id == "select":
            return self.select_menu_open
        elif button_id == "misc":
            return self.misc_menu_open
        elif button_id == "list":
            return self.list_menu_open
        return False

    def handle_outside_click(self, pos):
        """Handle clicks outside of open menus."""
        menu_closed = False

        for button_id in ["add", "remove", "select", "misc", "list"]:
            if self.is_menu_open(button_id):
                menu_rect = self.get_menu_rect(button_id)
                if not menu_rect.contains(pos):
                    self.close_all_menus()
                    menu_closed = True
                    break

        return menu_closed
