"""Button bar manager for the playlist window."""

from PySide6.QtCore import QRect


class ButtonBarManager:
    def __init__(self, window, playlist_spec):
        self.window = window
        self.playlist_spec = playlist_spec
        self.pressed_buttons = {}  # Stores {button_id: True/False}

    def get_button_rect(self, button_data):
        """Calculate the rectangle for a button."""
        button_bar_spec = self.playlist_spec["layout"]["controls"]["button_bar"]
        button_bar_x = button_bar_spec["position"]["x"]
        button_bar_y = self.window.height() - 28  # Consistent with paintEvent

        button_pixmap = self.window._get_sprite_pixmap(button_data["sprite"])
        if not button_pixmap:
            return QRect()

        # Special positioning for the LIST button to maintain position relative to right edge
        if button_data["id"] == "list":
            # Maintain the same distance from right edge as in original skin
            # Original button position was button_bar_x (14) + list button x (218) = 232
            # Original window width was approximately 275, button width is 22
            # Right edge of button was at 232 + 22 = 254
            # So right margin was 275 - 254 = 21
            right_margin = 21  # Approximate right margin in original skin

            # Position button maintaining same margin to right edge
            button_x = self.window.width() - button_pixmap.width() - right_margin
        else:
            # Use fixed positioning for other buttons
            button_x = button_bar_x + button_data["x"]

        return QRect(
            button_x,
            button_bar_y + button_data["y"],
            button_pixmap.width(),
            button_pixmap.height(),
        )

    def is_button_pressed(self, button_id):
        """Check if a button is pressed."""
        return self.pressed_buttons.get(button_id, False)

    def set_button_pressed(self, button_id, pressed):
        """Set the pressed state of a button."""
        self.pressed_buttons[button_id] = pressed

    def clear_pressed_buttons(self):
        """Clear all pressed button states."""
        self.pressed_buttons.clear()
