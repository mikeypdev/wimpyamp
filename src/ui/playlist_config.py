"""Configuration manager for the playlist window."""


class PlaylistConfig:
    def __init__(self, playlist_spec_json):
        self.spec = playlist_spec_json

    def get_spec(self):
        """Get the loaded specification."""
        return self.spec
