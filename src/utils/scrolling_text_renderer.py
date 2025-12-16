from PySide6.QtCore import QTimer
import time


class ScrollingTextRenderer:
    """
    A text renderer that displays track titles with the format:
    "{playlist_number}. {track_title} [{duration}] ***" with continuous scrolling
    from right to left when the text exceeds available space.
    """

    def __init__(self, text_renderer, skin_data):
        self.text_renderer = text_renderer
        self.skin_data = skin_data
        self.scroll_position = 0
        self.scroll_timer = QTimer()
        self.scroll_timer.timeout.connect(self._update_scroll_position)
        self.scroll_timer.setInterval(
            50
        )  # Update every 50ms (about 20 characters/second, four times as fast as original)
        self.scroll_timer.start()

        self.last_render_time = time.time()
        self.is_scrolling = False
        self.current_text = ""
        self.formatted_text = ""

    def _format_track_title(self, track_title, playlist_index, duration):
        """
        Format the track title according to the specification:
        "{playlist_number}. {track_title} [{duration}]"
        """
        # Convert duration (in seconds) to MM:SS format
        try:
            duration_minutes = int(duration // 60)
            duration_seconds = int(duration % 60)
            duration_str = f"{duration_minutes}:{duration_seconds:02d}"
        except (ValueError, TypeError):
            # If duration is invalid, use a default display
            duration_str = "0:00"

        # Format the complete string - playlist numbers start at 1, not 0
        formatted = f"{playlist_index + 1}. {track_title} [{duration_str}]"
        return formatted

    def _calculate_text_width(self, text):
        """
        Calculate the width of text in pixels using the text renderer's glyph width.
        """
        # Each character takes 5 pixels (glyph_width + cell_spacing = 4 + 1 = 5)
        return len(text) * 5

    def _update_scroll_position(self):
        """Update the scroll position for the scrolling text animation."""
        if self.is_scrolling:
            self.scroll_position += 1
            # Reset scroll position when we've scrolled the full length of the extended text
            if self.scroll_position > len(self.formatted_text + " ***") * 5:
                self.scroll_position = 0

    def render_track_title(
        self, painter, track_title, playlist_index, duration, dest_x, dest_y, max_width
    ):
        """
        Render the track title with scrolling functionality when it exceeds max_width.
        """
        # Format the track title according to specification
        self.formatted_text = self._format_track_title(
            track_title, playlist_index, duration
        )

        # Check if all characters in the formatted text are available in the text renderer
        # If any character is not available, we'll render a simplified version
        safe_main_text = self._ensure_safe_text(self.formatted_text)

        # The "***" and space should always be safe since they're standard ASCII characters
        # but we'll make sure they're included in the extended text
        extended_text = safe_main_text + " *** "

        # Calculate the total text width including the "***" suffix
        total_text_width = self._calculate_text_width(extended_text)

        # Check if text exceeds available space
        if total_text_width > max_width:
            # Enable scrolling behavior
            self.is_scrolling = True
            self.current_text = extended_text
        else:
            # No scrolling needed, just render the formatted text (without *** for static display)
            self.is_scrolling = False
            self.current_text = safe_main_text

        if self.is_scrolling:
            # Render scrolling text
            self._render_scrolling_text(painter, dest_x, dest_y, max_width)
        else:
            # Render static text
            self.text_renderer.render_text(painter, safe_main_text, dest_x, dest_y)

    def _ensure_safe_text(self, text):
        """
        Ensure that all characters in the text are available in the text renderer.
        If not, return a sanitized version that only contains supported characters.
        """
        safe_chars = []
        for char in text:
            # Check if the character (upper-cased) exists in the text renderer's mapping
            # For characters that don't have uppercase equivalents (like numbers, punctuation),
            # the uppercasing will return the same character
            upper_char = char.upper()
            if upper_char in self.text_renderer.char_to_coords:
                safe_chars.append(char)
            elif char in self.text_renderer.char_to_coords:
                # Some characters like numbers/punctuation stay the same when uppercased
                # so also check the original character
                safe_chars.append(char)
            else:
                # Skip this character as it's not supported by the font
                # For debugging, we could print which character is being skipped
                # print(f"DEBUG: Skipping unsupported character: '{char}' (ord: {ord(char)})")
                pass  # We could replace with a space or similar, but for now just skip

        return "".join(safe_chars)

    def _render_scrolling_text(self, painter, dest_x, dest_y, max_width):
        """
        Render the text that scrolls from right to left, showing a segment based on scroll position.
        """
        # Calculate how many characters can fit in the available width
        chars_per_segment = max_width // 5  # 5 pixels per character

        # Calculate the starting position in the current text based on scroll position
        start_char_index = (self.scroll_position // 5) % len(self.current_text)

        # Create the visible segment by wrapping around the text
        visible_text = ""
        for i in range(chars_per_segment):
            text_index = (start_char_index + i) % len(self.current_text)
            visible_text += self.current_text[text_index]

        # Render the visible segment
        self.text_renderer.render_text(painter, visible_text, dest_x, dest_y)

    def set_scroll_speed(self, pixels_per_second):
        """
        Set the scroll speed in pixels per second.
        """
        # Update timer interval based on desired speed
        interval_ms = int(
            1000 / max(1, pixels_per_second)
        )  # Ensure minimum 1ms interval
        self.scroll_timer.setInterval(interval_ms)

    def stop_scrolling(self):
        """
        Stop the scrolling animation.
        """
        self.scroll_timer.stop()
        self.is_scrolling = False

    def start_scrolling(self):
        """
        Start the scrolling animation.
        """
        self.scroll_timer.start()
        self.is_scrolling = True
