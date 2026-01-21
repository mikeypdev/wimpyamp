"""
mac_media_integration.py

macOS media integration module for WimPyAmp application.
Uses PyObjC to interface with macOS Media Player framework for
system-level media controls in Control Center and menu bar.
"""

import platform
from typing import TYPE_CHECKING, Optional


def is_macos():
    current_system = platform.system()
    print(f"Current platform: {current_system}")
    return current_system == "Darwin"


def check_pyobjc_availability():
    """Check if PyObjC is available by attempting to import required modules."""
    if platform.system() != "Darwin":
        return False

    try:
        # Try to import the required modules - these are used in actual functionality
        import MediaPlayer  # type: ignore[import-untyped]

        # Check that the specific attributes exist
        attrs_needed = [
            "MPNowPlayingInfoCenter",
            "MPNowPlayingInfoPropertyElapsedPlaybackTime",
            "MPRemoteCommandCenter",
            "MPNowPlayingPlaybackStatePlaying",
            "MPNowPlayingPlaybackStatePaused",
            "MPNowPlayingPlaybackStateStopped",
            "MPMediaItemPropertyTitle",
            "MPMediaItemPropertyArtist",
            "MPMediaItemPropertyAlbumTitle",
            "MPMediaItemPropertyPlaybackDuration",
        ]

        for attr in attrs_needed:
            if not hasattr(MediaPlayer, attr):
                print(f"Missing MediaPlayer attribute: {attr}")
                return False

        return True
    except ImportError as e:
        print(f"ImportError during PyObjC availability check: {e}")
        return False
    except Exception as e:
        print(f"Other error during PyObjC availability check: {e}")
        return False


if TYPE_CHECKING:
    from ..ui.main_window import MainWindow


class MacMediaIntegration:
    """
    macOS media integration class that interfaces with the Media Player framework
    to provide system-level media controls in Control Center and menu bar.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the macOS media integration with a reference to main window.

        Args:
            main_window: Reference to the main window instance
        """
        if platform.system() != "Darwin":
            raise RuntimeError("MacMediaIntegration can only be initialized on macOS")

        # Check availability at runtime
        if not check_pyobjc_availability():
            raise ImportError(
                "PyObjC is required for macOS media integration but is not available"
            )

        # Import required modules inside the method
        from MediaPlayer import (  # type: ignore[import-untyped]
            MPNowPlayingInfoCenter,
            MPRemoteCommandCenter,
        )

        self.main_window = main_window
        self.now_playing_info_center = MPNowPlayingInfoCenter.defaultCenter()
        self.remote_command_center = MPRemoteCommandCenter.sharedCommandCenter()

        # Set up the remote command handlers
        self.setup_remote_commands()

        print("MacMediaIntegration initialized successfully")

    def update_now_playing_info(self):
        """
        Update track metadata in system Now Playing info center.
        """
        if not check_pyobjc_availability():
            return

        # Import required modules inside the method
        from MediaPlayer import (  # type: ignore[import-untyped]
            MPMediaItemPropertyTitle,
            MPMediaItemPropertyArtist,
            MPMediaItemPropertyAlbumTitle,
            MPMediaItemPropertyPlaybackDuration,
            MPMediaItemPropertyArtwork,
            MPNowPlayingInfoPropertyElapsedPlaybackTime,
        )
        from Foundation import NSNumber  # type: ignore[import-untyped]

        # Get current track information from audio engine
        metadata = self.main_window.audio_engine.get_metadata()
        duration = self.main_window.audio_engine.get_duration()
        album_art = self.main_window.audio_engine.get_album_art()

        # Create the now playing info dictionary with ALL required information
        now_playing_info = {}

        # Add required metadata - ensure these are properly set
        if "title" in metadata and metadata["title"] and metadata["title"] != "Unknown":
            now_playing_info[MPMediaItemPropertyTitle] = str(metadata["title"])
        else:
            # Fallback to filename if no title available
            if self.main_window.audio_engine.file_path:
                import os

                now_playing_info[MPMediaItemPropertyTitle] = os.path.splitext(
                    os.path.basename(self.main_window.audio_engine.file_path)
                )[0]
            else:
                now_playing_info[MPMediaItemPropertyTitle] = "Unknown"

        if (
            "artist" in metadata
            and metadata["artist"]
            and metadata["artist"] != "Unknown"
        ):
            now_playing_info[MPMediaItemPropertyArtist] = str(metadata["artist"])
        else:
            now_playing_info[MPMediaItemPropertyArtist] = "Unknown Artist"

        if "album" in metadata and metadata["album"] and metadata["album"] != "Unknown":
            now_playing_info[MPMediaItemPropertyAlbumTitle] = str(metadata["album"])
        else:
            now_playing_info[MPMediaItemPropertyAlbumTitle] = "Unknown Album"

        # Duration handling
        if duration and duration > 0:
            now_playing_info[MPMediaItemPropertyPlaybackDuration] = (
                NSNumber.numberWithFloat_(duration)
            )
        else:
            now_playing_info[MPMediaItemPropertyPlaybackDuration] = (
                NSNumber.numberWithFloat_(0.0)
            )

        # Add elapsed playback time
        current_position = self.main_window.audio_engine.get_current_position()
        now_playing_info[MPNowPlayingInfoPropertyElapsedPlaybackTime] = (
            NSNumber.numberWithFloat_(current_position)
        )

        # Handle album art and add it to the now playing info - this is the key fix
        if album_art and len(album_art) > 0:
            try:
                from Foundation import NSData, NSImage  # type: ignore[import-untyped]
                from MediaPlayer import MPMediaItemArtwork  # type: ignore[import-untyped]

                # Convert album art bytes to NSData
                ns_data = NSData.dataWithBytes_length_(album_art, len(album_art))

                # Create NSImage from the data
                artwork_image = NSImage.alloc().initWithData_(ns_data)

                if artwork_image:
                    print(f"Album art processed, size: {len(album_art)} bytes")

                    # Create MPMediaItemArtwork with the NSImage
                    # The handler function must accept a CGSize parameter as required by the Objective-C API
                    def image_getter(representation_size):
                        return artwork_image

                    # Create the media item artwork object
                    media_artwork = (
                        MPMediaItemArtwork.alloc().initWithBoundsSize_requestHandler_(
                            artwork_image.size(), image_getter
                        )
                    )

                    # Add the artwork to the now playing info
                    now_playing_info[MPMediaItemPropertyArtwork] = media_artwork
                    print("Album art successfully added to now playing info")
                else:
                    print("Failed to create NSImage from album art data")
            except Exception as e:
                print(f"Error processing album art: {e}")
                import traceback

                traceback.print_exc()
        else:
            print("No album art available for this track")

        # Update the system now playing info with metadata (this now includes artwork!)
        print(f"Now Playing Info Keys: {list(now_playing_info.keys())}")
        self.now_playing_info_center.setNowPlayingInfo_(now_playing_info)

        print("Now Playing info updated with all track info including album art")

    def update_playback_state(self):
        """
        Update current position, duration, and playback state.
        """
        if not check_pyobjc_availability():
            return

        # Import required modules inside the method
        from MediaPlayer import (  # type: ignore[import-untyped]
            MPNowPlayingInfoPropertyElapsedPlaybackTime,
            MPNowPlayingPlaybackStatePlaying,
            MPNowPlayingPlaybackStatePaused,
            MPNowPlayingPlaybackStateStopped,
        )
        from Foundation import NSNumber  # type: ignore[import-untyped]

        # Get the current playback position from audio engine
        current_position = self.main_window.audio_engine.get_current_position()

        # Get existing now playing info and update the elapsed playback time
        now_playing_info = self.now_playing_info_center.nowPlayingInfo()
        if now_playing_info is None:
            now_playing_info = {}
            # If there's no existing info, we need to populate it completely
            self.update_now_playing_info()
            now_playing_info = self.now_playing_info_center.nowPlayingInfo() or {}

        now_playing_info[MPNowPlayingInfoPropertyElapsedPlaybackTime] = (
            NSNumber.numberWithFloat_(current_position)
        )

        # Update the system now playing info
        self.now_playing_info_center.setNowPlayingInfo_(now_playing_info)

        # Update playback state (playing/paused)
        playback_state = self.main_window.audio_engine.get_playback_state()
        if playback_state.get("is_playing", False):
            self.now_playing_info_center.setPlaybackState_(
                MPNowPlayingPlaybackStatePlaying
            )
        elif playback_state.get("is_paused", False):
            self.now_playing_info_center.setPlaybackState_(
                MPNowPlayingPlaybackStatePaused
            )
        else:
            self.now_playing_info_center.setPlaybackState_(
                MPNowPlayingPlaybackStateStopped
            )

    def setup_remote_commands(self):
        """
        Register handlers for system remote commands.
        """
        if not check_pyobjc_availability():
            return

        # Import required modules inside the function
        from MediaPlayer import MPRemoteCommandHandlerStatusSuccess, MPRemoteCommandHandlerStatusCommandFailed  # type: ignore[import-untyped]

        # Set up play command handler
        def handle_play_command(_):
            try:
                self.main_window.toggle_play_pause()
                return MPRemoteCommandHandlerStatusSuccess
            except Exception as e:
                print(f"Error handling play command: {e}")
                return MPRemoteCommandHandlerStatusCommandFailed

        # Set up pause command handler
        def handle_pause_command(_):
            try:
                # If currently playing, pause it
                state = self.main_window.audio_engine.get_playback_state()
                if state.get("is_playing", False):
                    self.main_window.audio_engine.pause()
                    self.main_window.ui_state.is_play_pressed = False
                    self.main_window.ui_state.is_pause_pressed = True
                    self.main_window.update()
                return MPRemoteCommandHandlerStatusSuccess
            except Exception as e:
                print(f"Error handling pause command: {e}")
                return MPRemoteCommandHandlerStatusCommandFailed

        # Set up play/pause toggle handler
        def handle_play_pause_command(_):
            try:
                self.main_window.toggle_play_pause()
                return MPRemoteCommandHandlerStatusSuccess
            except Exception as e:
                print(f"Error handling play/pause command: {e}")
                return MPRemoteCommandHandlerStatusCommandFailed

        # Set up next track command handler
        def handle_next_command(_):
            try:
                self.main_window.play_next_track()
                return MPRemoteCommandHandlerStatusSuccess
            except Exception as e:
                print(f"Error handling next command: {e}")
                return MPRemoteCommandHandlerStatusCommandFailed

        # Set up previous track command handler
        def handle_previous_command(_):
            try:
                self.main_window.play_previous_track()
                return MPRemoteCommandHandlerStatusSuccess
            except Exception as e:
                print(f"Error handling previous command: {e}")
                return MPRemoteCommandHandlerStatusCommandFailed

        # Set up change playback position command handler
        def handle_seek_command(commandEvent):
            try:
                new_position = commandEvent.playbackPosition()
                # Convert position to fraction of duration for seeking
                duration = self.main_window.audio_engine.get_duration()
                if duration > 0:
                    position_fraction = new_position / duration
                    self.main_window.audio_engine.seek(position_fraction)
                    return MPRemoteCommandHandlerStatusSuccess
            except Exception as e:
                print(f"Error handling seek command: {e}")
                return MPRemoteCommandHandlerStatusCommandFailed

        # Register the command handlers
        # Import the remote command center inside the function
        from MediaPlayer import MPRemoteCommandCenter  # type: ignore[import-untyped]

        remote_command_center = MPRemoteCommandCenter.sharedCommandCenter()

        remote_command_center.playCommand().addTargetWithHandler_(handle_play_command)
        remote_command_center.pauseCommand().addTargetWithHandler_(handle_pause_command)
        remote_command_center.togglePlayPauseCommand().addTargetWithHandler_(
            handle_play_pause_command
        )
        remote_command_center.nextTrackCommand().addTargetWithHandler_(
            handle_next_command
        )
        remote_command_center.previousTrackCommand().addTargetWithHandler_(
            handle_previous_command
        )
        # Note: Commenting out changePlaybackPositionCommand to reduce complexity
        # If needed, uncomment line below, but note it requires special handling in PyObjC
        # remote_command_center.changePlaybackPositionCommand().addTargetWithHandler_(handle_seek_command)

    def cleanup(self):
        """
        Clean up resources when application closes.
        """
        if not check_pyobjc_availability():
            return

        # Import required modules inside the method
        from MediaPlayer import MPNowPlayingPlaybackStateStopped  # type: ignore[import-untyped]

        # Clear the now playing info
        self.now_playing_info_center.setNowPlayingInfo_(None)
        self.now_playing_info_center.setPlaybackState_(MPNowPlayingPlaybackStateStopped)

        print("MacMediaIntegration cleaned up successfully")


def create_mac_media_integration(main_window) -> Optional["MacMediaIntegration"]:
    """
    Safely create a MacMediaIntegration instance with proper error handling.

    Args:
        main_window: Reference to the main window instance

    Returns:
        MacMediaIntegration instance if on macOS and PyObjC is available, None otherwise
    """
    if not is_macos():
        print("Not running on macOS, skipping media integration")
        return None

    if not check_pyobjc_availability():
        print("PyObjC is not available. macOS media integration will not be loaded.")
        return None

    try:
        integration = MacMediaIntegration(main_window)
        print("MacMediaIntegration successfully initialized and loaded")
        return integration
    except Exception as e:
        print(f"Failed to initialize MacMediaIntegration: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return None
