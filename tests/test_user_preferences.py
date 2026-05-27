import json
import os
import tempfile
import pytest
from unittest.mock import patch


@pytest.fixture
def prefs_dir(tmp_path):
    return str(tmp_path / "prefs")


@pytest.fixture
def prefs(prefs_dir):
    with patch("src.core.user_preferences.APP_DIRS_AVAILABLE", True), \
         patch("src.core.user_preferences.appdirs.user_data_dir", return_value=prefs_dir):
        from src.core.user_preferences import UserPreferences
        return UserPreferences()


class TestUserPreferencesLoadSave:
    def test_load_creates_defaults_when_no_file(self, prefs):
        assert prefs.prefs["version"] == "1.0"

    def test_save_and_reload_roundtrip(self, prefs, prefs_dir):
        prefs.prefs["current_skin"] = "/some/skin.wsz"
        prefs.save()
        assert os.path.exists(prefs.prefs_file_path)

        with patch("src.core.user_preferences.APP_DIRS_AVAILABLE", True), \
             patch("src.core.user_preferences.appdirs.user_data_dir", return_value=prefs_dir):
            from src.core.user_preferences import UserPreferences
            loaded = UserPreferences()
        assert loaded.prefs.get("current_skin") == "/some/skin.wsz"

    def test_save_writes_valid_json(self, prefs):
        prefs.prefs["window_layout"] = {"main": {"x": 200, "y": 300}}
        prefs.save()
        with open(prefs.prefs_file_path) as f:
            data = json.load(f)
        assert data["window_layout"]["main"]["x"] == 200

    def test_load_rejects_bad_version(self, prefs, prefs_dir):
        os.makedirs(os.path.dirname(prefs.prefs_file_path), exist_ok=True)
        with open(prefs.prefs_file_path, "w") as f:
            json.dump({"version": "99.0"}, f)

        with patch("src.core.user_preferences.APP_DIRS_AVAILABLE", True), \
             patch("src.core.user_preferences.appdirs.user_data_dir", return_value=prefs_dir):
            from src.core.user_preferences import UserPreferences
            loaded = UserPreferences()
        assert loaded.prefs["version"] == "1.0"

    def test_load_handles_corrupt_json(self, prefs, prefs_dir):
        os.makedirs(os.path.dirname(prefs.prefs_file_path), exist_ok=True)
        with open(prefs.prefs_file_path, "w") as f:
            f.write("{invalid json")
        with patch("src.core.user_preferences.APP_DIRS_AVAILABLE", True), \
             patch("src.core.user_preferences.appdirs.user_data_dir", return_value=prefs_dir):
            from src.core.user_preferences import UserPreferences
            loaded = UserPreferences()
        assert loaded.prefs["version"] == "1.0"


class TestSkinPreferences:
    def test_set_and_get_skin(self, prefs):
        prefs.set_current_skin("/path/to/skin.wsz")
        assert prefs.get_current_skin() == "/path/to/skin.wsz"

    def test_default_skin_not_stored(self, prefs):
        prefs.set_current_skin(prefs._get_default_skin_path())
        assert prefs.get_current_skin() is None


class TestWindowPreferences:
    def test_main_window_position(self, prefs):
        prefs.set_main_window_position(250, 150)
        pos = prefs.get_main_window_position()
        assert pos == {"x": 250, "y": 150}

    def test_default_position_not_stored(self, prefs):
        prefs.set_main_window_position(100, 100)
        assert prefs.get_main_window_position() is None

    def test_eq_visibility(self, prefs):
        prefs.set_eq_window_visibility(True)
        assert prefs.get_eq_window_visibility() is True
        prefs.set_eq_window_visibility(False)
        assert prefs.get_eq_window_visibility() is None

    def test_playlist_visibility(self, prefs):
        prefs.set_playlist_window_visibility(True)
        assert prefs.get_playlist_window_visibility() is True
        prefs.set_playlist_window_visibility(False)
        assert prefs.get_playlist_window_visibility() is None
