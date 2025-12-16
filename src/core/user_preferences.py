#!/usr/bin/env python3
"""
User Preferences Module for WimPyAmp

This module handles loading, saving, and managing user preferences for the WimPyAmp
music player application. Preferences are stored in JSON format and include
settings like window positions, skin selection, and playlist display options.
"""

import os
import json
import tempfile
import sys
from typing import Dict, Any, Optional

# Import appdirs for cross-platform user data directory
try:
    import appdirs  # type: ignore

    APP_DIRS_AVAILABLE = True
except ImportError:
    APP_DIRS_AVAILABLE = False
    print("WARNING: appdirs module not available. Using fallback user data directory.")


class UserPreferences:
    """Main class for managing user preferences."""

    def __init__(self):
        """Initialize the UserPreferences instance."""
        self.prefs = {"version": "1.0", "window_layout": {}, "playlist_settings": {}}
        self.prefs_file_path = self._get_prefs_file_path()
        self._ensure_prefs_directory_exists()
        self.load()

    def _get_prefs_file_path(self) -> str:
        """Get the full path to the preferences file."""
        if APP_DIRS_AVAILABLE:
            user_data_dir = appdirs.user_data_dir("WimPyAmp")
        else:
            # Fallback: use ~/.wimpyamp on Unix-like systems
            user_data_dir = os.path.expanduser("~/.wimpyamp")

        return os.path.join(user_data_dir, "user_prefs.json")

    def _ensure_prefs_directory_exists(self):
        """Ensure the preferences directory exists."""
        prefs_dir = os.path.dirname(self.prefs_file_path)
        os.makedirs(prefs_dir, exist_ok=True)

    def load(self) -> bool:
        """Load preferences from file.

        Returns:
            bool: True if preferences were loaded successfully, False otherwise.
        """
        try:
            if os.path.exists(self.prefs_file_path):
                with open(self.prefs_file_path, "r", encoding="utf-8") as f:
                    loaded_prefs = json.load(f)

                # Validate and migrate if needed
                if self._validate_and_migrate(loaded_prefs):
                    self.prefs = loaded_prefs
                    # Initialize defaults for comparison
                    self._defaults = {"window_layout": {"main": {"x": 100, "y": 100}}}
                    return True

        except (json.JSONDecodeError, IOError, OSError) as e:
            print(f"ERROR: Failed to load preferences: {e}")

        # If loading fails, use defaults
        self._initialize_defaults()
        return False

    def _validate_and_migrate(self, prefs_data: Dict[str, Any]) -> bool:
        """Validate preferences data and migrate if needed.

        Args:
            prefs_data: The loaded preferences data

        Returns:
            bool: True if validation/migration succeeded, False otherwise.
        """
        # Check if required fields exist
        if not isinstance(prefs_data, dict):
            return False

        # Check version and migrate if needed
        current_version = prefs_data.get("version", "1.0")

        # For now, we only support version 1.0
        if current_version != "1.0":
            print(f"WARNING: Unsupported preferences version: {current_version}")
            return False

        return True

    def _initialize_defaults(self):
        """Initialize preferences with default values."""
        # Only store version in the base structure
        # Other preferences are only added when they differ from defaults
        self.prefs = {"version": "1.0"}
        # Store defaults separately for comparison
        self._defaults = {"window_layout": {"main": {"x": 100, "y": 100}}}

    def _save_if_changed(self) -> bool:
        """Save preferences to file only if they differ from defaults.

        Returns:
            bool: True if preferences were saved successfully, False otherwise.
        """
        # Check if we only have the version field (no custom preferences)
        if len(self.prefs) == 1 and "version" in self.prefs:
            # Only version is present, which means no custom preferences
            # Delete the preferences file if it exists
            try:
                if os.path.exists(self.prefs_file_path):
                    os.remove(self.prefs_file_path)
                return True
            except OSError as e:
                print(f"ERROR: Failed to remove preferences file: {e}")
                return False

        # We have custom preferences, save them
        return self.save()

    def save(self) -> bool:
        """Save preferences to file using atomic write operation.

        Returns:
            bool: True if preferences were saved successfully, False otherwise.
        """
        try:
            # Create a temporary file for atomic write
            temp_dir = os.path.dirname(self.prefs_file_path)
            temp_fd, temp_path = tempfile.mkstemp(dir=temp_dir, prefix=".user_prefs_")

            try:
                with os.fdopen(temp_fd, "w", encoding="utf-8") as temp_file:
                    json.dump(self.prefs, temp_file, indent=2, ensure_ascii=False)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())

                # Atomic rename operation
                if os.path.exists(self.prefs_file_path):
                    # Create backup before overwriting
                    backup_path = self.prefs_file_path + ".backup"
                    if os.path.exists(backup_path):
                        os.remove(backup_path)
                    os.rename(self.prefs_file_path, backup_path)

                os.rename(temp_path, self.prefs_file_path)

                # Clean up backup after successful save
                backup_path = self.prefs_file_path + ".backup"
                if os.path.exists(backup_path):
                    os.remove(backup_path)

                return True

            except Exception as e:
                # Clean up temp file if something went wrong
                try:
                    os.remove(temp_path)
                except OSError:
                    pass
                raise e

        except (IOError, OSError) as e:
            print(f"ERROR: Failed to save preferences: {e}")
            return False

    # Skin-related methods
    def get_current_skin(self) -> Optional[str]:
        """Get the currently selected skin path.

        Returns:
            str or None: The path to the current skin, or None if using default skin.
        """
        return self.prefs.get("current_skin")

    def set_current_skin(self, skin_path: str):
        """Set the current skin path.

        Args:
            skin_path: Path to the skin file or directory.
        """
        # Check if this is the default skin path
        default_skin_path = self._get_default_skin_path()

        if skin_path == default_skin_path:
            # Don't store default skin in preferences
            if "current_skin" in self.prefs:
                del self.prefs["current_skin"]
                self._save_if_changed()
        else:
            # Store the custom skin path
            self.prefs["current_skin"] = skin_path
            self._save_if_changed()

    # Playlist settings methods
    def get_playlist_settings(self) -> Dict[str, Any]:
        """Get the current playlist settings.

        Returns:
            dict: The playlist settings with display options.
        """
        # Return the stored playlist settings if they exist, otherwise return defaults
        if "playlist_settings" in self.prefs:
            return self.prefs["playlist_settings"]
        else:
            # Return default playlist settings
            return {
                "display_options": {
                    "track_filename": True,
                    "track_number": False,
                    "song_name": False,
                    "artist": False,
                    "album_artist": False,
                    "album_name": False,
                }
            }

    def set_playlist_settings(self, settings: Dict[str, Any]):
        """Set the playlist settings.

        Args:
            settings: Dictionary containing playlist settings.
        """
        # Check if the settings differ from defaults
        default_settings = {
            "display_options": {
                "track_filename": True,
                "track_number": False,
                "song_name": False,
                "artist": False,
                "album_artist": False,
                "album_name": False,
            }
        }

        # Compare the settings with defaults
        if settings == default_settings:
            # Settings are the same as defaults, remove from preferences
            if "playlist_settings" in self.prefs:
                del self.prefs["playlist_settings"]
                self._save_if_changed()
        else:
            # Settings differ from defaults, store them
            self.prefs["playlist_settings"] = settings
            self._save_if_changed()

    def get_main_window_position(self) -> Optional[Dict[str, int]]:
        """Get the main window position if stored in preferences.

        Returns:
            dict or None: Dictionary with 'x' and 'y' keys, or None if not stored.
        """
        if "window_layout" in self.prefs and "main" in self.prefs["window_layout"]:
            return self.prefs["window_layout"]["main"]
        return None

    def set_main_window_position(self, x: int, y: int):
        """Set the main window position in preferences.

        Args:
            x: X coordinate of window position
            y: Y coordinate of window position
        """
        if not self.prefs.get("window_layout"):
            self.prefs["window_layout"] = {}

        # Only store if different from defaults
        default_position = {"x": 100, "y": 100}
        if x != default_position["x"] or y != default_position["y"]:
            self.prefs["window_layout"]["main"] = {"x": x, "y": y}
            self._save_if_changed()
        else:
            # Remove if same as defaults
            if "window_layout" in self.prefs and "main" in self.prefs["window_layout"]:
                del self.prefs["window_layout"]["main"]
                if not self.prefs[
                    "window_layout"
                ]:  # If empty, remove the whole section
                    del self.prefs["window_layout"]
                self._save_if_changed()

    def get_eq_window_visibility(self) -> Optional[bool]:
        """Get the EQ window visibility from preferences.

        Returns:
            bool or None: True if EQ window should be visible, False if not, None if not stored.
        """
        if "window_layout" in self.prefs and "equalizer" in self.prefs["window_layout"]:
            return self.prefs["window_layout"]["equalizer"].get("visible")
        return None

    def set_eq_window_visibility(self, visible: bool):
        """Set the EQ window visibility in preferences.

        Args:
            visible: True if EQ window should be visible, False otherwise.
        """
        if not self.prefs.get("window_layout"):
            self.prefs["window_layout"] = {}
        if not self.prefs["window_layout"].get("equalizer"):
            self.prefs["window_layout"]["equalizer"] = {}

        # Store visibility if different from default (False)
        if visible:  # Default is False (hidden), so only store if True
            self.prefs["window_layout"]["equalizer"]["visible"] = visible
        else:
            # Remove visibility from preferences if it's False (default)
            if "visible" in self.prefs["window_layout"]["equalizer"]:
                del self.prefs["window_layout"]["equalizer"]["visible"]
            # If equalizer section becomes empty, clean it up
            if not self.prefs["window_layout"]["equalizer"]:
                del self.prefs["window_layout"]["equalizer"]
                if not self.prefs[
                    "window_layout"
                ]:  # If window_layout section becomes empty
                    del self.prefs["window_layout"]

        self._save_if_changed()

    def get_playlist_window_visibility(self) -> Optional[bool]:
        """Get the playlist window visibility from preferences.

        Returns:
            bool or None: True if playlist window should be visible, False if not, None if not stored.
        """
        if "window_layout" in self.prefs and "playlist" in self.prefs["window_layout"]:
            return self.prefs["window_layout"]["playlist"].get("visible")
        return None

    def set_playlist_window_visibility(self, visible: bool):
        """Set the playlist window visibility in preferences.

        Args:
            visible: True if playlist window should be visible, False otherwise.
        """
        if not self.prefs.get("window_layout"):
            self.prefs["window_layout"] = {}
        if not self.prefs["window_layout"].get("playlist"):
            self.prefs["window_layout"]["playlist"] = {}

        # Store visibility if different from default (False)
        if visible:  # Default is False (hidden), so only store if True
            self.prefs["window_layout"]["playlist"]["visible"] = visible
        else:
            # Remove visibility from preferences if it's False (default)
            if "visible" in self.prefs["window_layout"]["playlist"]:
                del self.prefs["window_layout"]["playlist"]["visible"]
            # If playlist section becomes empty, clean it up
            if not self.prefs["window_layout"]["playlist"]:
                del self.prefs["window_layout"]["playlist"]
                if not self.prefs[
                    "window_layout"
                ]:  # If window_layout section becomes empty
                    del self.prefs["window_layout"]

        self._save_if_changed()

    def get_album_art_window_visibility(self) -> Optional[bool]:
        """Get the album art window visibility from preferences.

        Returns:
            bool or None: True if album art window should be visible, False if not, None if not stored.
        """
        if "window_layout" in self.prefs and "album_art" in self.prefs["window_layout"]:
            return self.prefs["window_layout"]["album_art"].get("visible")
        return None

    def set_album_art_window_visibility(self, visible: bool):
        """Set the album art window visibility in preferences.

        Args:
            visible: True if album art window should be visible, False otherwise.
        """
        if not self.prefs.get("window_layout"):
            self.prefs["window_layout"] = {}
        if not self.prefs["window_layout"].get("album_art"):
            self.prefs["window_layout"]["album_art"] = {}

        # Store visibility if different from default (False)
        if visible:  # Default is False (hidden), so only store if True
            self.prefs["window_layout"]["album_art"]["visible"] = visible
        else:
            # Remove visibility from preferences if it's False (default)
            if "visible" in self.prefs["window_layout"]["album_art"]:
                del self.prefs["window_layout"]["album_art"]["visible"]
            # If album_art section becomes empty, clean it up
            if not self.prefs["window_layout"]["album_art"]:
                del self.prefs["window_layout"]["album_art"]
                if not self.prefs[
                    "window_layout"
                ]:  # If window_layout section becomes empty
                    del self.prefs["window_layout"]

        self._save_if_changed()

    def get_eq_window_position(self) -> Optional[Dict[str, int]]:
        """Get the EQ window position from preferences.

        Returns:
            dict or None: Dictionary with 'x' and 'y' keys, or None if not stored.
        """
        if "window_layout" in self.prefs and "equalizer" in self.prefs["window_layout"]:
            eq_data = self.prefs["window_layout"]["equalizer"]
            if "x" in eq_data and "y" in eq_data:
                return {"x": eq_data["x"], "y": eq_data["y"]}
        return None

    def set_eq_window_position(self, x: int, y: int):
        """Set the EQ window position in preferences.

        Args:
            x: X coordinate of window position
            y: Y coordinate of window position
        """
        if not self.prefs.get("window_layout"):
            self.prefs["window_layout"] = {}
        if not self.prefs["window_layout"].get("equalizer"):
            self.prefs["window_layout"]["equalizer"] = {}

        # Store position - we don't have defaults, so always store if provided
        self.prefs["window_layout"]["equalizer"]["x"] = x
        self.prefs["window_layout"]["equalizer"]["y"] = y
        self._save_if_changed()

    def get_playlist_window_position(self) -> Optional[Dict[str, int]]:
        """Get the playlist window position from preferences.

        Returns:
            dict or None: Dictionary with 'x' and 'y' keys, or None if not stored.
        """
        if "window_layout" in self.prefs and "playlist" in self.prefs["window_layout"]:
            playlist_data = self.prefs["window_layout"]["playlist"]
            if "x" in playlist_data and "y" in playlist_data:
                return {"x": playlist_data["x"], "y": playlist_data["y"]}
        return None

    def set_playlist_window_position(self, x: int, y: int):
        """Set the playlist window position in preferences.

        Args:
            x: X coordinate of window position
            y: Y coordinate of window position
        """
        if not self.prefs.get("window_layout"):
            self.prefs["window_layout"] = {}
        if not self.prefs["window_layout"].get("playlist"):
            self.prefs["window_layout"]["playlist"] = {}

        # Store position - we don't have defaults, so always store if provided
        self.prefs["window_layout"]["playlist"]["x"] = x
        self.prefs["window_layout"]["playlist"]["y"] = y
        self._save_if_changed()

    def get_album_art_window_position(self) -> Optional[Dict[str, int]]:
        """Get the album art window position from preferences.

        Returns:
            dict or None: Dictionary with 'x' and 'y' keys, or None if not stored.
        """
        if "window_layout" in self.prefs and "album_art" in self.prefs["window_layout"]:
            album_art_data = self.prefs["window_layout"]["album_art"]
            if "x" in album_art_data and "y" in album_art_data:
                return {"x": album_art_data["x"], "y": album_art_data["y"]}
        return None

    def set_album_art_window_position(self, x: int, y: int):
        """Set the album art window position in preferences.

        Args:
            x: X coordinate of window position
            y: Y coordinate of window position
        """
        if not self.prefs.get("window_layout"):
            self.prefs["window_layout"] = {}
        if not self.prefs["window_layout"].get("album_art"):
            self.prefs["window_layout"]["album_art"] = {}

        # Store position - we don't have defaults, so always store if provided
        self.prefs["window_layout"]["album_art"]["x"] = x
        self.prefs["window_layout"]["album_art"]["y"] = y
        self._save_if_changed()

    def get_playlist_window_size(self) -> Optional[Dict[str, int]]:
        """Get the playlist window size from preferences.

        Returns:
            dict or None: Dictionary with 'width' and 'height' keys, or None if not stored.
        """
        if "window_layout" in self.prefs and "playlist" in self.prefs["window_layout"]:
            playlist_data = self.prefs["window_layout"]["playlist"]
            if "width" in playlist_data and "height" in playlist_data:
                return {
                    "width": playlist_data["width"],
                    "height": playlist_data["height"],
                }
        return None

    def set_playlist_window_size(self, width: int, height: int):
        """Set the playlist window size in preferences.

        Args:
            width: Width of the window
            height: Height of the window
        """
        if not self.prefs.get("window_layout"):
            self.prefs["window_layout"] = {}
        if not self.prefs["window_layout"].get("playlist"):
            self.prefs["window_layout"]["playlist"] = {}

        # Store size - we don't have defaults, so always store if provided
        self.prefs["window_layout"]["playlist"]["width"] = width
        self.prefs["window_layout"]["playlist"]["height"] = height
        self._save_if_changed()

    def get_album_art_window_size(self) -> Optional[Dict[str, int]]:
        """Get the album art window size from preferences.

        Returns:
            dict or None: Dictionary with 'width' and 'height' keys, or None if not stored.
        """
        if "window_layout" in self.prefs and "album_art" in self.prefs["window_layout"]:
            album_art_data = self.prefs["window_layout"]["album_art"]
            if "width" in album_art_data and "height" in album_art_data:
                return {
                    "width": album_art_data["width"],
                    "height": album_art_data["height"],
                }
        return None

    def set_album_art_window_size(self, width: int, height: int):
        """Set the album art window size in preferences.

        Args:
            width: Width of the window
            height: Height of the window
        """
        if not self.prefs.get("window_layout"):
            self.prefs["window_layout"] = {}
        if not self.prefs["window_layout"].get("album_art"):
            self.prefs["window_layout"]["album_art"] = {}

        # Store size - we don't have defaults, so always store if provided
        self.prefs["window_layout"]["album_art"]["width"] = width
        self.prefs["window_layout"]["album_art"]["height"] = height
        self._save_if_changed()

    def _get_default_skin_path(self) -> str:
        """Get the path to the default skin.

        Returns:
            str: Path to the default skin.
        """
        # This should match the default skin path used in main_window.py
        if getattr(sys, "frozen", False):
            # Running as compiled executable
            application_path = getattr(
                sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))
            )
            return os.path.join(
                application_path, "resources", "default_skin", "base-2.91.wsz"
            )
        else:
            # Running as script in development
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            return os.path.join(
                project_root, "resources", "default_skin", "base-2.91.wsz"
            )


# Global preferences instance
_preferences_instance = None


def get_preferences() -> UserPreferences:
    """Get the global preferences instance.

    Returns:
        UserPreferences: The global preferences instance.
    """
    global _preferences_instance
    if _preferences_instance is None:
        _preferences_instance = UserPreferences()
    return _preferences_instance
