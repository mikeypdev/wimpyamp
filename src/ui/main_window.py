import sys
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QFileDialog,
    QMenuBar,
)
from PySide6.QtGui import QPainter, QKeySequence, QShortcut, QAction, QFileOpenEvent
from PySide6.QtCore import Qt, QPoint, QRect, QTimer, QDir
import os

from ..core.skin_parser import SkinParser
from ..core.renderer import Renderer
from ..core.user_preferences import get_preferences
from ..utils.text_renderer import TextRenderer
from ..utils.scrolling_text_renderer import ScrollingTextRenderer
from ..utils.region_utils import apply_region_mask_to_widget
from .ui_state import UIState


from .playlist_window import PlaylistWindow
from .equalizer_window import EqualizerWindow
from .album_art_window import AlbumArtWindow

# Import audio engine
from ..audio.audio_engine import AudioEngine

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QPushButton,
    QMessageBox,
    QLabel,
    QHBoxLayout,
    QLineEdit,
)


class PreferencesDialog(QDialog):
    def __init__(self, parent=None, preferences=None):
        super().__init__(parent)
        self.preferences = preferences
        self.setWindowTitle("Preferences")
        self.setFixedSize(400, 150)

        layout = QVBoxLayout()

        # Default Music Path section
        music_path_layout = QHBoxLayout()
        music_path_label = QLabel("Default Music Path:")
        self.music_path_line_edit = QLineEdit()

        # Load current value if available
        current_path = (
            self.preferences.get_default_music_path() if self.preferences else ""
        )
        self.music_path_line_edit.setText(current_path if current_path else "")

        self.browse_music_path_btn = QPushButton("Browse...")
        self.browse_music_path_btn.clicked.connect(self.browse_music_path)

        music_path_layout.addWidget(music_path_label)
        music_path_layout.addWidget(self.music_path_line_edit)
        music_path_layout.addWidget(self.browse_music_path_btn)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_btn = QPushButton("OK")
        self.cancel_btn = QPushButton("Cancel")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        layout.addLayout(music_path_layout)
        layout.addStretch()  # Add some spacing
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def browse_music_path(self):
        """Open a directory dialog to select the default music path."""
        current_path = self.music_path_line_edit.text()
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Default Music Directory",
            current_path if current_path else QDir.homePath(),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )

        if directory:
            self.music_path_line_edit.setText(directory)

    def accept(self):
        """Override accept to save preferences before closing."""
        if self.preferences:
            music_path = self.music_path_line_edit.text().strip()
            self.preferences.set_default_music_path(music_path)
        super().accept()


class SkinSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent  # Store reference to main window
        self.setWindowTitle("Options")
        self.setFixedSize(200, 180)  # Increased size for the additional button

        layout = QVBoxLayout()

        # Create buttons
        self.load_new_skin_btn = QPushButton("Load New Skin")
        self.load_default_skin_btn = QPushButton("Load Default Skin")
        self.preferences_btn = QPushButton(
            "Preferences..."
        )  # New button for preferences
        self.cancel_btn = QPushButton("Close")

        # Connect buttons to accept methods that set result codes
        self.load_new_skin_btn.clicked.connect(lambda: self.done(1))  # Result code 1
        self.load_default_skin_btn.clicked.connect(
            lambda: self.done(2)
        )  # Result code 2
        self.preferences_btn.clicked.connect(
            lambda: self.show_preferences_dialog()
        )  # Show preferences dialog
        self.cancel_btn.clicked.connect(lambda: self.done(0))  # Result code 0 (Cancel)

        # Add buttons to layout
        layout.addWidget(self.load_new_skin_btn)
        layout.addWidget(self.load_default_skin_btn)
        layout.addWidget(self.preferences_btn)  # Add preferences button to layout
        layout.addWidget(self.cancel_btn)

        self.setLayout(layout)

    def show_preferences_dialog(self):
        """Show the preferences dialog with default music path option."""
        from .main_window import PreferencesDialog

        if self.main_window:
            dialog = PreferencesDialog(
                parent=self.main_window, preferences=self.main_window.preferences
            )
            dialog.exec_()
        # Don't close the skin selection dialog after preferences


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WimPyAmp Music Player")

        # Set window flags for completely borderless window
        self.setWindowFlags(Qt.FramelessWindowHint)

        # Enable drag and drop
        self.setAcceptDrops(True)

        # Set a transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Get user preferences
        self.preferences = get_preferences()

        # Load window position from preferences
        main_window_pos = self.preferences.get_main_window_position()
        if main_window_pos:
            self.setGeometry(main_window_pos["x"], main_window_pos["y"], 275, 116)
        else:
            self.setGeometry(100, 100, 275, 116)

        # Determine path to resources based on whether running from source or PyInstaller bundle
        if getattr(sys, "frozen", False):
            # Running as compiled executable
            # Resources are embedded and available via sys._MEIPASS
            application_path = sys._MEIPASS
            self.default_skin_path = os.path.join(
                application_path, "resources", "default_skin", "base-2.91.wsz"
            )
        else:
            # Running as script in development
            project_root = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            self.default_skin_path = os.path.join(
                project_root, "resources", "default_skin", "base-2.91.wsz"
            )

        # Check if there's a preferred skin in user preferences
        preferred_skin = self.preferences.get_current_skin()
        self.skin_path = preferred_skin if preferred_skin else self.default_skin_path

        self.skin_parser = SkinParser(self.skin_path)
        self.skin_data = self.skin_parser.parse()

        # If the preferred skin failed to load, fall back to default
        if not self.skin_data.extracted_skin_dir and preferred_skin:
            print(
                f"WARNING: Preferred skin {preferred_skin} failed to load, falling back to default"
            )
            self.skin_path = self.default_skin_path
            self.skin_parser = SkinParser(self.skin_path)
            self.skin_data = self.skin_parser.parse()
            # Remove the invalid skin from preferences
            self.preferences.set_current_skin(self.default_skin_path)

        self.renderer = Renderer(self)
        self.renderer.set_skin_data(self.skin_data)
        self.text_renderer = TextRenderer(self.skin_data)
        self.scrolling_text_renderer = ScrollingTextRenderer(
            self.text_renderer, self.skin_data
        )

        # Initialize audio engine without visualization
        self.audio_engine = AudioEngine()
        # Set up callback for position updates
        self.audio_engine.playback_callback = self.update_playback_position

        # Initialize UI state
        self.ui_state = UIState()

        # Set up keyboard shortcuts for media controls
        self.setup_media_shortcuts()

        # Window dragging state
        self._dragging_window = False
        self._drag_start_position = QPoint()

        # Set the initial visualization mode in the audio engine to start the processing thread
        if hasattr(self, "audio_engine"):
            self.audio_engine.set_visualization_mode(
                self.renderer.get_visualization_mode()
            )

        # Timer for updating UI during playback
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self.update_ui_from_engine)
        self.playback_timer.start(200)  # Update every 200ms

        # Timer for checking track completion
        self.track_completion_timer = QTimer()
        self.track_completion_timer.timeout.connect(self.check_track_completion)
        self.track_completion_timer.start(500)  # Check every 500ms

        # Timer for updating visualization (~30 FPS)
        self.visualization_timer = QTimer()
        self.visualization_timer.timeout.connect(self.update_visualization)
        self.visualization_timer.start(33)  # ~30 FPS (1000ms / 30fps ≈ 33ms)

        # Ensure proper cleanup when window is closed
        self.closeEvent = self._on_close

        # Playlist functionality
        self.playlist = []  # List of file paths
        self.current_track_index = -1  # Index of currently playing track
        self.current_track_path = None  # Path of currently playing track (to handle playlist changes during playback)

        # Apply region mask if available
        self.apply_region_mask()

        self.show()

        # Initialize the old position for tracking movement deltas
        self._old_main_pos = self.pos()

        # Initialize floating windows
        self.playlist_window = PlaylistWindow(
            None, self.skin_data, self.renderer.sprite_manager, self.text_renderer
        )
        self.playlist_window.set_main_window(
            self
        )  # Set main window reference for docking
        self.playlist_window.hide()

        self.equalizer_window = EqualizerWindow(
            None, self.skin_data, self.renderer.sprite_manager, self.audio_engine
        )
        self.equalizer_window.main_window = (
            self  # Set main window reference for docking
        )

        self.album_art_window = AlbumArtWindow(
            None, self.skin_data, self.renderer.sprite_manager
        )
        self.album_art_window.set_main_window(
            self
        )  # Set main window reference for docking
        self.album_art_window.hide()

        # Track windows for coordinated shutdown
        self._tracked_windows = [
            self.playlist_window,
            self.equalizer_window,
            self.album_art_window,
        ]

        # Add flag to indicate initialization is not complete yet
        # This prevents moving docked child windows during initial preference loading
        self._initialization_complete = False

        # Initialize UI states from preferences (will be implemented later)
        # For now, ensure initial states are properly tracked
        self._initialize_window_visibility_states()

        # Now mark initialization as complete
        self._initialization_complete = True

    def show_playlist_window(self):
        """Show the playlist window and update visibility state."""
        self.ui_state.playlist_button_on = True
        self.ui_state.is_playlist_pressed = True
        # Position the playlist window below the main window when first opened
        playlist_pos_x = self.x()
        playlist_pos_y = self.y() + self.height()
        self.playlist_window.move(playlist_pos_x, playlist_pos_y)
        # Ensure the playlist window is docked when opened in default position
        self.playlist_window.is_docked = True
        self.playlist_window.setVisible(True)
        self._update_window_visibility_preferences()  # Update preferences when manually shown/hidden
        self.update()  # Repaint main window to update button sprite

    def hide_playlist_window(self):
        """Hide the playlist window and update visibility state."""
        self.ui_state.playlist_button_on = False
        self.ui_state.is_playlist_pressed = False
        self.playlist_window.setVisible(False)
        self._update_window_visibility_preferences()  # Update preferences when manually shown/hidden
        self.update()  # Repaint main window to update button sprite

    def show_equalizer_window(self):
        """Show the equalizer window and update visibility state."""
        self.ui_state.eq_button_on = True
        self.ui_state.is_eq_pressed = True
        # Position the equalizer window below the main window when first opened
        eq_pos_x = self.x()
        eq_pos_y = self.y() + self.height()
        self.equalizer_window.move(eq_pos_x, eq_pos_y)
        # Ensure the equalizer window is docked when opened in default position
        self.equalizer_window.is_docked = True
        self.equalizer_window.setVisible(True)
        self._update_window_visibility_preferences()  # Update preferences when manually shown/hidden
        self.update()  # Repaint main window to update button sprite

    def hide_equalizer_window(self):
        """Hide the equalizer window and update visibility state."""
        self.ui_state.eq_button_on = False
        self.ui_state.is_eq_pressed = False
        self.equalizer_window.setVisible(False)
        self._update_window_visibility_preferences()  # Update preferences when manually shown/hidden
        self.update()  # Repaint main window to update button sprite

    def show_album_art_window(self):
        """Show the album art window and update visibility state."""
        self.ui_state.album_art_visible = True
        self.ui_state.is_file_info_pressed = True
        # Show the album art window and refresh its content
        self.album_art_window.show()
        if hasattr(self, "audio_engine") and self.audio_engine:
            self.album_art_window.refresh_album_art(self.audio_engine)
        self._update_window_visibility_preferences()  # Update preferences when manually shown/hidden
        self.update()  # Repaint main window to update button sprite

    def hide_album_art_window(self):
        """Hide the album art window and update visibility state."""
        self.ui_state.album_art_visible = False
        self.ui_state.is_file_info_pressed = False
        self.album_art_window.hide()
        self._update_window_visibility_preferences()  # Update preferences when manually shown/hidden
        self.update()  # Repaint main window to update button sprite

    def _initialize_window_visibility_states(self):
        """Initialize window visibility states from preferences (placeholder implementation).

        This method prepares the codebase for future implementation of loading visibility
        states from user preferences by establishing the pattern for tracking these states.
        """
        # Load EQ window visibility from preferences
        eq_visibility = self.preferences.get_eq_window_visibility()
        if eq_visibility is not None:
            # Set the EQ button state based on saved visibility
            self.ui_state.eq_button_on = eq_visibility
            # Position the EQ window appropriately if it's visible
            if eq_visibility:
                # First, try to load the saved position from preferences
                eq_position = self.preferences.get_eq_window_position()
                if eq_position:
                    # Use saved position
                    self.equalizer_window.move(eq_position["x"], eq_position["y"])
                    # Check if the window is docked based on proximity to main window
                    eq_rect = QRect(
                        eq_position["x"],
                        eq_position["y"],
                        self.equalizer_window.width(),
                        self.equalizer_window.height(),
                    )
                    self.equalizer_window.is_docked = self.is_window_near_main(eq_rect)
                else:
                    # Position the equalizer window below the main window when restored as visible
                    eq_pos_x = self.x()
                    eq_pos_y = self.y() + self.height()
                    self.equalizer_window.move(eq_pos_x, eq_pos_y)
                    # Ensure the equalizer window is docked when opened in default position
                    self.equalizer_window.is_docked = True
            # Show/hide the EQ window based on saved state (after positioning)
            self.equalizer_window.setVisible(eq_visibility)
        else:
            # Default state - EQ window is hidden
            self.ui_state.eq_button_on = False  # EQ starts hidden
            self.equalizer_window.setVisible(False)

        # Load Playlist window visibility from preferences
        playlist_visibility = self.preferences.get_playlist_window_visibility()
        if playlist_visibility is not None:
            # Set the playlist button state based on saved visibility
            self.ui_state.playlist_button_on = playlist_visibility
            # Position the playlist window appropriately if it's visible
            if playlist_visibility:
                # First, try to load the saved size from preferences
                playlist_size = self.preferences.get_playlist_window_size()
                if playlist_size:
                    # Use saved size
                    self.playlist_window.resize(
                        playlist_size["width"], playlist_size["height"]
                    )

                # Then, try to load the saved position from preferences
                playlist_position = self.preferences.get_playlist_window_position()
                if playlist_position:
                    # Use saved position
                    self.playlist_window.move(
                        playlist_position["x"], playlist_position["y"]
                    )
                    # Check if the window is docked based on proximity to main window
                    playlist_rect = QRect(
                        playlist_position["x"],
                        playlist_position["y"],
                        self.playlist_window.width(),
                        self.playlist_window.height(),
                    )
                    self.playlist_window.is_docked = self.is_window_near_main(
                        playlist_rect
                    )
                else:
                    # Position the playlist window below the main window when restored as visible
                    playlist_pos_x = self.x()
                    playlist_pos_y = self.y() + self.height()
                    self.playlist_window.move(playlist_pos_x, playlist_pos_y)
                    # Ensure the playlist window is docked when opened in default position
                    self.playlist_window.is_docked = True
            # Show/hide the playlist window based on saved state (after positioning)
            self.playlist_window.setVisible(playlist_visibility)
        else:
            # Default state - Playlist window is hidden
            self.ui_state.playlist_button_on = False  # Playlist starts hidden
            self.playlist_window.setVisible(False)

        # Load Album Art window visibility from preferences
        album_art_visibility = self.preferences.get_album_art_window_visibility()
        if album_art_visibility is not None:
            # Set the album art visibility state based on saved visibility
            self.ui_state.album_art_visible = album_art_visibility
            # Position the album art window appropriately if it's visible
            if album_art_visibility:
                # First, try to load the saved size from preferences
                album_art_size = self.preferences.get_album_art_window_size()
                if album_art_size:
                    # Use saved size
                    self.album_art_window.resize(
                        album_art_size["width"], album_art_size["height"]
                    )

                # Position the album art window appropriately if it's visible
                # First, try to load the saved position from preferences
                album_art_position = self.preferences.get_album_art_window_position()
                if album_art_position:
                    # Use saved position
                    self.album_art_window.move(
                        album_art_position["x"], album_art_position["y"]
                    )
                    # Check if the window is docked based on proximity to main window
                    album_art_rect = QRect(
                        album_art_position["x"],
                        album_art_position["y"],
                        self.album_art_window.width(),
                        self.album_art_window.height(),
                    )
                    self.album_art_window.is_docked = self.is_window_near_main(
                        album_art_rect
                    )

                # Show/refresh the album art window after positioning
                if hasattr(self, "audio_engine") and self.audio_engine:
                    self.album_art_window.refresh_album_art(self.audio_engine)
            # Show/hide the album art window based on saved state (after positioning)
            self.album_art_window.setVisible(album_art_visibility)
        else:
            # Default state - Album Art window is hidden
            self.ui_state.album_art_visible = False  # Album art starts hidden
            self.album_art_window.setVisible(False)

        # After loading positions from preferences, recalculate docking states
        # to ensure proper docked state based on window proximity
        self._recalculate_docking_states()

    def _update_window_visibility_preferences(self):
        """Update window visibility preferences (implementation for EQ, Playlist and Album Art windows).

        This method saves the EQ, Playlist and Album Art window visibility states to user preferences.
        """
        # Save EQ window visibility to preferences
        self.preferences.set_eq_window_visibility(self.ui_state.eq_button_on)
        # Save Playlist window visibility to preferences
        self.preferences.set_playlist_window_visibility(
            self.ui_state.playlist_button_on
        )
        # Save Album Art window visibility to preferences
        self.preferences.set_album_art_window_visibility(
            self.ui_state.album_art_visible
        )

    def _recalculate_docking_states(self):
        """Recalculate docking states for all floating windows after loading positions.

        This method recalculates the docking state of all floating windows (playlist,
        equalizer, album art) based on their proximity to main window and each other,
        ensuring proper docked state when positions are loaded from preferences.
        """
        # Create a list of all floating windows to check for docking
        floating_windows = []
        if hasattr(self, "playlist_window") and self.playlist_window:
            floating_windows.append(self.playlist_window)
        if hasattr(self, "equalizer_window") and self.equalizer_window:
            floating_windows.append(self.equalizer_window)
        if hasattr(self, "album_art_window") and self.album_art_window:
            floating_windows.append(self.album_art_window)

        # For each floating window, check if it should be considered docked
        for window in floating_windows:
            if window and window.isVisible():
                # Create QRect for the window's current position
                window_rect = QRect(
                    window.x(), window.y(), window.width(), window.height()
                )

                # Check if the window is near the main window or any other docked windows
                is_near_any = self.is_window_near_any_docked_window(
                    window_rect, exclude_window=window
                )

                # Update the window's docked state
                if hasattr(window, "is_docked"):
                    window.is_docked = is_near_any

    def get_docking_zones(self):
        """Get the docking zones around the main window based on the window snapping specification."""
        # Define docking zones around the main window following SPEC_WINDOWS.md
        edge_threshold = 10  # pixels of tolerance for edge snapping
        center_threshold = 15  # pixels of tolerance for center alignment

        # Define all edges for snapping detection
        zones = {}

        # Horizontal edge zones - detect when other window's horizontal edges approach main window's edges
        zones["main_top"] = QRect(
            self.x() - edge_threshold,
            self.y(),
            self.width() + 2 * edge_threshold,
            edge_threshold,
        )
        zones["main_bottom"] = QRect(
            self.x() - edge_threshold,
            self.y() + self.height(),
            self.width() + 2 * edge_threshold,
            edge_threshold,
        )

        # Vertical edge zones - detect when other window's vertical edges approach main window's edges
        zones["main_left"] = QRect(
            self.x(),
            self.y() - edge_threshold,
            edge_threshold,
            self.height() + 2 * edge_threshold,
        )
        zones["main_right"] = QRect(
            self.x() + self.width(),
            self.y() - edge_threshold,
            edge_threshold,
            self.height() + 2 * edge_threshold,
        )

        # Center alignment zones - detect when other window's center approaches main window's center
        main_center_x = self.x() + self.width() // 2
        main_center_y = self.y() + self.height() // 2

        zones["main_center_x"] = QRect(
            main_center_x - center_threshold,
            self.y(),
            2 * center_threshold,
            self.height(),
        )
        zones["main_center_y"] = QRect(
            self.x(),
            main_center_y - center_threshold,
            self.width(),
            2 * center_threshold,
        )

        return zones

    def apply_region_mask(self):
        """Apply the region mask to the window based on the region.txt data."""
        if self.skin_data.region_data:
            # Apply the region mask for the "Normal" state by default
            apply_region_mask_to_widget(
                self, self.skin_data.region_data, state="Normal"
            )
        else:
            # Clear any existing mask if no region data exists
            self.clearMask()

    def get_snap_alignment(self, dragging_window_rect):
        """
        Calculate proper alignment based on the window snapping specification.
        This method determines the best alignment for a dragging window relative to this main window.

        Args:
            dragging_window_rect: QRect representing the current position of the window being dragged

        Returns:
            tuple: (snapped_x, snapped_y, is_snapped) where is_snapped indicates if any snapping occurred
        """
        # Use helper to check snapping to main window and other windows
        return self._get_snap_alignment_to_target(dragging_window_rect, self)

    def _get_snap_alignment_to_target(self, dragging_window_rect, target_window):
        """
        Calculate alignment to a specific target window.

        Args:
            dragging_window_rect: QRect representing the current position of the window being dragged
            target_window: The window to check alignment against

        Returns:
            tuple: (snapped_x, snapped_y, is_snapped) where is_snapped indicates if any snapping occurred
        """
        # Define the thresholds
        edge_threshold = 10  # pixels for edge alignment
        center_threshold = 15  # pixels for center alignment

        # Define important points of the dragging window
        drag_left = dragging_window_rect.left()
        drag_right = dragging_window_rect.right()
        drag_top = dragging_window_rect.top()
        drag_bottom = dragging_window_rect.bottom()
        drag_center_x = dragging_window_rect.center().x()
        drag_center_y = dragging_window_rect.center().y()
        drag_width = dragging_window_rect.width()
        drag_height = dragging_window_rect.height()

        # Define important points of the target window
        target_left = target_window.x()
        target_right = target_window.x() + target_window.width()
        target_top = target_window.y()
        target_bottom = target_window.y() + target_window.height()
        target_center_x = target_window.x() + target_window.width() // 2
        target_center_y = target_window.y() + target_window.height() // 2

        # Variables to store the snap results
        snap_x = dragging_window_rect.x()
        snap_y = dragging_window_rect.y()
        is_snapped = False

        # 1. Horizontal edge alignment (top/bottom alignment)
        # Check for alignment of dragging window's top with target window's edges
        if abs(drag_top - target_bottom) <= edge_threshold:
            snap_y = target_bottom  # Align drag top with target bottom
            is_snapped = True
        elif abs(drag_bottom - target_top) <= edge_threshold:
            snap_y = target_top - drag_height  # Align drag bottom with target top
            is_snapped = True
        elif abs(drag_top - target_top) <= edge_threshold:
            snap_y = target_top  # Align drag top with target top
            is_snapped = True
        elif abs(drag_bottom - target_bottom) <= edge_threshold:
            snap_y = target_bottom - drag_height  # Align drag bottom with target bottom
            is_snapped = True
        elif abs(drag_center_y - target_center_y) <= center_threshold:
            snap_y = target_center_y - drag_height // 2  # Align centers vertically
            is_snapped = True

        # 2. Vertical edge alignment (left/right alignment)
        # Check for alignment of dragging window's left with target window's edges
        if abs(drag_left - target_right) <= edge_threshold:
            snap_x = target_right  # Align drag left with target right
            is_snapped = True
        elif abs(drag_right - target_left) <= edge_threshold:
            snap_x = target_left - drag_width  # Align drag right with target left
            is_snapped = True
        elif abs(drag_left - target_left) <= edge_threshold:
            snap_x = target_left  # Align drag left with target left
            is_snapped = True
        elif abs(drag_right - target_right) <= edge_threshold:
            snap_x = target_right - drag_width  # Align drag right with target right
            is_snapped = True
        elif abs(drag_center_x - target_center_x) <= center_threshold:
            snap_x = target_center_x - drag_width // 2  # Align centers horizontally
            is_snapped = True

        return snap_x, snap_y, is_snapped

    def get_window_snap_alignment(self, dragging_window_rect, exclude_window=None):
        """
        Calculate proper alignment based on the window snapping specification.
        This method determines the best alignment for a dragging window relative to other windows.

        Args:
            dragging_window_rect: QRect representing the current position of the window being dragged
            exclude_window: Optional window to exclude from checking (e.g., if checking for self)

        Returns:
            tuple: (snapped_x, snapped_y, is_snapped) where is_snapped indicates if any snapping occurred
        """
        # Define the thresholds
        edge_threshold = 10  # pixels for edge alignment
        center_threshold = 15  # pixels for center alignment

        # Define important points of the dragging window
        drag_left = dragging_window_rect.left()
        drag_right = dragging_window_rect.right()
        drag_top = dragging_window_rect.top()
        drag_bottom = dragging_window_rect.bottom()
        drag_center_x = dragging_window_rect.center().x()
        drag_center_y = dragging_window_rect.center().y()
        drag_width = dragging_window_rect.width()
        drag_height = dragging_window_rect.height()

        # Variables to store the final snap results
        snap_x = dragging_window_rect.x()
        snap_y = dragging_window_rect.y()
        is_snapped = False

        # Store all potential snaps with their distances for prioritization
        potential_snaps = []

        # Check for snapping to other windows (main window and floating windows)
        # Create a list of potential target windows
        target_windows = [self]  # Always check main window

        # Add other floating windows if they exist and are visible
        if (
            hasattr(self, "playlist_window")
            and self.playlist_window
            and self.playlist_window.isVisible()
        ):
            if self.playlist_window != exclude_window:
                target_windows.append(self.playlist_window)
        if (
            hasattr(self, "equalizer_window")
            and self.equalizer_window
            and self.equalizer_window.isVisible()
        ):
            if self.equalizer_window != exclude_window:
                target_windows.append(self.equalizer_window)
        if (
            hasattr(self, "album_art_window")
            and self.album_art_window
            and self.album_art_window.isVisible()
        ):
            if self.album_art_window != exclude_window:
                target_windows.append(self.album_art_window)

        # Check each target window for potential snapping
        for target_window in target_windows:
            target_left = target_window.x()
            target_right = target_window.x() + target_window.width()
            target_top = target_window.y()
            target_bottom = target_window.y() + target_window.height()
            target_center_x = target_window.x() + target_window.width() // 2
            target_center_y = target_window.y() + target_window.height() // 2

            # 1. Horizontal edge alignment (top/bottom alignment)
            # Calculate distances for each potential snap
            top_to_bottom_dist = abs(drag_top - target_bottom)
            bottom_to_top_dist = abs(drag_bottom - target_top)
            top_to_top_dist = abs(drag_top - target_top)
            bottom_to_bottom_dist = abs(drag_bottom - target_bottom)
            center_y_dist = abs(drag_center_y - target_center_y)

            # Check for alignment of dragging window's top with target window's edges
            if top_to_bottom_dist <= edge_threshold:
                potential_snaps.append(("y", target_bottom, top_to_bottom_dist))
            if bottom_to_top_dist <= edge_threshold:
                potential_snaps.append(
                    ("y", target_top - drag_height, bottom_to_top_dist)
                )
            if top_to_top_dist <= edge_threshold:
                potential_snaps.append(("y", target_top, top_to_top_dist))
            if bottom_to_bottom_dist <= edge_threshold:
                potential_snaps.append(
                    ("y", target_bottom - drag_height, bottom_to_bottom_dist)
                )
            if center_y_dist <= center_threshold:
                potential_snaps.append(
                    ("y", target_center_y - drag_height // 2, center_y_dist)
                )

            # 2. Vertical edge alignment (left/right alignment)
            left_to_right_dist = abs(drag_left - target_right)
            right_to_left_dist = abs(drag_right - target_left)
            left_to_left_dist = abs(drag_left - target_left)
            right_to_right_dist = abs(drag_right - target_right)
            center_x_dist = abs(drag_center_x - target_center_x)

            # Check for alignment of dragging window's left with target window's edges
            if left_to_right_dist <= edge_threshold:
                potential_snaps.append(("x", target_right, left_to_right_dist))
            if right_to_left_dist <= edge_threshold:
                potential_snaps.append(
                    ("x", target_left - drag_width, right_to_left_dist)
                )
            if left_to_left_dist <= edge_threshold:
                potential_snaps.append(("x", target_left, left_to_left_dist))
            if right_to_right_dist <= edge_threshold:
                potential_snaps.append(
                    ("x", target_right - drag_width, right_to_right_dist)
                )
            if center_x_dist <= center_threshold:
                potential_snaps.append(
                    ("x", target_center_x - drag_width // 2, center_x_dist)
                )

        # If we found potential snaps, choose the one with the smallest distance
        if potential_snaps:
            # Sort by distance (closest first)
            sorted_snaps = sorted(potential_snaps, key=lambda x: x[2])

            # Apply the closest snaps for x and y directions (if different directions)
            applied_x = False
            applied_y = False

            for snap_type, snap_pos, dist in sorted_snaps:
                if snap_type == "x" and not applied_x:
                    snap_x = snap_pos
                    applied_x = True
                    is_snapped = True
                elif snap_type == "y" and not applied_y:
                    snap_y = snap_pos
                    applied_y = True
                    is_snapped = True

                # If both x and y are applied, we can stop
                if applied_x and applied_y:
                    break

        return snap_x, snap_y, is_snapped

    def is_window_near_main(self, window_rect):
        """
        Check if a window is still close enough to the main window to be considered docked.

        Args:
            window_rect: QRect representing the position of the window to check

        Returns:
            bool: True if the window is close enough to be considered docked
        """
        # Define the unsnap threshold - if any part of the window is within this distance
        # of any part of the main window, consider it still docked
        unsnap_threshold = 25  # pixels

        # Get main window rect
        main_rect = QRect(self.x(), self.y(), self.width(), self.height())

        # Check if any edges are within the unsnap threshold
        # We calculate the minimum distance between any points of the two rectangles
        # If the rectangles overlap or are within the threshold, consider docked

        # Horizontal distance: distance between rectangles horizontally
        horiz_dist = 0
        if window_rect.right() < main_rect.left():
            horiz_dist = main_rect.left() - window_rect.right()
        elif main_rect.right() < window_rect.left():
            horiz_dist = window_rect.left() - main_rect.right()

        # Vertical distance: distance between rectangles vertically
        vert_dist = 0
        if window_rect.bottom() < main_rect.top():
            vert_dist = main_rect.top() - window_rect.bottom()
        elif main_rect.bottom() < window_rect.top():
            vert_dist = window_rect.top() - main_rect.bottom()

        # Calculate direct distance between closest points of the rectangles
        max_distance = max(horiz_dist, vert_dist)

        # Consider docked if distance is within threshold
        return max_distance <= unsnap_threshold

    def is_window_near_any_docked_window(self, window_rect, exclude_window=None):
        """
        Check if a window is close enough to the main window or any other docked floating window
        to be considered docked.

        Args:
            window_rect: QRect representing the position of the window to check
            exclude_window: Optional window to exclude from checking

        Returns:
            bool: True if the window is close enough to any docked window
        """
        # Define the unsnap threshold - if any part of the window is within this distance
        # of any part of another window, consider it still docked
        unsnap_threshold = 25  # pixels

        # Create a list of potential target windows
        target_windows = [self]  # Always check main window

        # Add other floating windows if they exist and are visible
        if (
            hasattr(self, "playlist_window")
            and self.playlist_window
            and self.playlist_window.isVisible()
        ):
            if self.playlist_window != exclude_window:
                target_windows.append(self.playlist_window)
        if (
            hasattr(self, "equalizer_window")
            and self.equalizer_window
            and self.equalizer_window.isVisible()
        ):
            if self.equalizer_window != exclude_window:
                target_windows.append(self.equalizer_window)
        if (
            hasattr(self, "album_art_window")
            and self.album_art_window
            and self.album_art_window.isVisible()
        ):
            if self.album_art_window != exclude_window:
                target_windows.append(self.album_art_window)

        # Check each target window to see if the specified window rect is near it
        for target_window in target_windows:
            target_rect = QRect(
                target_window.x(),
                target_window.y(),
                target_window.width(),
                target_window.height(),
            )

            # Calculate distance between rectangles
            horiz_dist = 0
            if window_rect.right() < target_rect.left():
                horiz_dist = target_rect.left() - window_rect.right()
            elif target_rect.right() < window_rect.left():
                horiz_dist = window_rect.left() - target_rect.right()

            vert_dist = 0
            if window_rect.bottom() < target_rect.top():
                vert_dist = target_rect.top() - window_rect.bottom()
            elif target_rect.bottom() < window_rect.top():
                vert_dist = window_rect.top() - target_rect.bottom()

            # The minimum distance between the rectangles
            max_distance = max(horiz_dist, vert_dist)

            # If this window is within the threshold of any target window, return True
            if max_distance <= unsnap_threshold:
                return True

        # If not near any target window, return False
        return False

    def bring_all_windows_to_foreground(self):
        """Bring all related windows (main, playlist, equalizer, album art) to the foreground."""
        # Activate the main window first
        self.raise_()
        self.activateWindow()

        # Bring up other visible windows
        if (
            hasattr(self, "playlist_window")
            and self.playlist_window
            and self.playlist_window.isVisible()
        ):
            self.playlist_window.raise_()
            self.playlist_window.activateWindow()
        if (
            hasattr(self, "equalizer_window")
            and self.equalizer_window
            and self.equalizer_window.isVisible()
        ):
            self.equalizer_window.raise_()
            self.equalizer_window.activateWindow()
        if (
            hasattr(self, "album_art_window")
            and self.album_art_window
            and self.album_art_window.isVisible()
        ):
            self.album_art_window.raise_()
            self.album_art_window.activateWindow()

    def update_playback_position(self, position, duration):
        """Callback from audio engine - updates internal state for UI timer."""
        # This callback receives position updates from the audio engine
        # We store this info so the UI timer can use it consistently
        # The actual UI update is still handled by the timer to avoid race conditions
        pass  # The audio engine's current_position is already updated, just let the timer handle the UI update

    def update_ui_from_engine(self):
        """Update UI based on audio engine state."""
        state = self.audio_engine.get_playback_state()

        # Update play/pause/stop state indicators based on actual playback state
        # Play button is pressed if playing
        self.ui_state.is_play_pressed = state["is_playing"] and not state["is_paused"]
        # Pause button is pressed if paused
        self.ui_state.is_pause_pressed = state["is_paused"]
        # Stop button is pressed when playback is stopped (neither playing nor paused), but only after a track has been loaded
        # When no track is loaded, stop button is not pressed (neutral state)
        self.ui_state.is_stop_pressed = (
            not state["is_playing"]
            and not state["is_paused"]
            and self.audio_engine.has_track_loaded()
        )

        # Update volume - only when it's different to avoid flickering
        if abs(self.ui_state.volume - state["volume"]) > 0.001:
            self.ui_state.volume = state["volume"]

        # Update position from audio engine state to ensure consistency
        # This provides a single source of truth for the UI
        # Calculate position as fraction of total duration for UI components
        position_seconds = state["position"]
        duration = state["duration"]
        if duration > 0:
            self.ui_state.position = max(
                0.0, min(1.0, position_seconds / duration if duration > 0 else 0.0)
            )
        else:
            self.ui_state.position = 0.0

        # Trigger repaint if needed
        self.update()

    def set_playlist(self, playlist):
        """Set the playlist with list of file paths."""
        # If we're currently playing a track, try to maintain its position in the new playlist
        if self.current_track_path:
            # Find the new index of the currently playing track in the updated playlist
            try:
                new_index = playlist.index(self.current_track_path)
                self.current_track_index = new_index
            except ValueError:
                # Track is no longer in playlist, reset index and path
                self.current_track_index = -1
                self.current_track_path = None
        elif not playlist:
            # If playlist is being cleared and no track was playing, clear the path anyway
            self.current_track_path = None

        self.playlist = playlist
        self.update_playlist_display()

    def update_playlist_display(self):
        """Update the playlist window display."""
        # Update the playlist file paths in the playlist window
        if hasattr(self, "playlist_window"):
            self.playlist_window.set_playlist_filepaths(self.playlist)

    def play_track_at_index(self, index):
        """Play the track at the specified index in the playlist."""
        if 0 <= index < len(self.playlist):
            filepath = self.playlist[index]
            if self.audio_engine.load_track(filepath):
                # Update display with track information - only artist and title
                metadata = self.audio_engine.get_metadata()
                if metadata:
                    # For the scrolling text renderer, we just need the title and artist
                    # The playlist number and duration will be added by the renderer
                    title = metadata.get("title", "Unknown")
                    artist = metadata.get("artist", "Unknown")
                    # Sanitize the title and artist to remove potentially problematic characters
                    # for the Winamp font renderer
                    title = str(title).replace("\n", " ").replace("\r", " ").strip()
                    artist = str(artist).replace("\n", " ").replace("\r", " ").strip()
                    # Format as "artist - song title" for display
                    self.ui_state.current_track_title = f"{artist} - {title}"
                else:
                    # Fallback to just the filename without extension
                    self.ui_state.current_track_title = os.path.splitext(
                        os.path.basename(filepath)
                    )[0]

                self.audio_engine.play()
                self.current_track_index = index
                self.current_track_path = (
                    filepath  # Track the path of the currently playing track
                )

                # Update playlist window to show currently playing track
                self.playlist_window.set_current_track_index(index)

                # Refresh album art if the window is visible
                if self.album_art_window.isVisible():
                    self.album_art_window.refresh_album_art(self.audio_engine)

                self.update()
                return True
        return False

    def play_next_track(self):
        """Play the next track in the playlist."""
        if self.playlist and self.current_track_index < len(self.playlist) - 1:
            # Play the next track using the current playlist, even if it has changed since playback started
            next_index = self.current_track_index + 1
            if next_index < len(self.playlist):
                self.play_track_at_index(next_index)

            # Refresh album art if the window is visible
            if self.album_art_window.isVisible():
                self.album_art_window.refresh_album_art(self.audio_engine)

    def play_previous_track(self):
        """Play the previous track in the playlist."""
        if self.playlist and self.current_track_index > 0:
            self.play_track_at_index(self.current_track_index - 1)

            # Refresh album art if the window is visible
            if self.album_art_window.isVisible():
                self.album_art_window.refresh_album_art(self.audio_engine)

    def play_selected_track(self, index):
        """Play the track at the given index when clicked in the playlist."""
        self.play_track_at_index(index)

        # Refresh album art if the window is visible
        if self.album_art_window.isVisible():
            self.album_art_window.refresh_album_art(self.audio_engine)

    def _handle_stop_action(self):
        """Handle the stop action from media key or stop button."""
        self.audio_engine.stop()
        self.current_track_path = None
        # Make sure the playlist window knows which track was playing so it can be restarted
        if hasattr(self, "playlist_window") and self.playlist_window:
            self.playlist_window.set_current_track_index(self.current_track_index)

    def check_track_completion(self):
        """Check if the current track has finished playing and advance if needed."""
        # Get current playback state from audio engine
        state = self.audio_engine.get_playback_state()

        # Check if track has finished playing - either still playing but at end, or just stopped at end
        # We check the position against duration to determine if the track completed normally
        # Only auto-advance if the track was playing and has reached the end, or if it just finished playing
        if (
            state["position"] >= state["duration"]
            and state["duration"] > 0
            and self.audio_engine.has_track_loaded()
            and
            # Check if audio engine is no longer playing (meaning it finished naturally)
            not state["is_playing"]
        ):

            # Track has finished naturally, check if we should play the next track
            # Always play the next track in the playlist if there are more tracks,
            # regardless of repeat setting (unless repeat is set to single track)
            if self.current_track_index < len(self.playlist) - 1:
                # Play the next track in the playlist
                self.play_next_track()
            elif (
                self.ui_state.repeat_on
                and self.current_track_index == len(self.playlist) - 1
            ):
                # If repeat is on and we're at the last track, go back to the first (repeat playlist)
                self.play_track_at_index(0)
            else:
                # No more tracks to play, stop playback
                self.ui_state.is_play_pressed = False
                self.ui_state.is_pause_pressed = False
                self.ui_state.is_stop_pressed = True
                self.audio_engine.stop()

                # Clear current track tracking when playback stops
                self.current_track_path = None

                # Refresh album art to show default placeholder when track stops
                if (
                    hasattr(self, "album_art_window")
                    and self.album_art_window.isVisible()
                ):
                    self.album_art_window.refresh_album_art(self.audio_engine)

                self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # Get current track duration from audio engine
        self.ui_state.duration = (
            self.audio_engine.get_duration() if self.audio_engine else 0.0
        )
        self.ui_state.is_stereo = (
            self.audio_engine.is_stereo_track() if self.audio_engine else True
        )
        # Get bitrate, sample rate, and VBR status from audio engine state
        self.ui_state.bitrate = (
            self.audio_engine.bitrate if hasattr(self.audio_engine, "bitrate") else 128
        )
        # Convert sample rate from Hz to kHz (e.g., 44100 Hz → 44 kHz)
        self.ui_state.sample_rate = (
            int(self.audio_engine.sample_rate / 1000)
            if hasattr(self.audio_engine, "sample_rate")
            and self.audio_engine.sample_rate
            else 44
        )
        self.ui_state.is_vbr = (
            self.audio_engine.is_vbr if hasattr(self.audio_engine, "is_vbr") else False
        )

        # Get playback state from audio engine
        playback_state = (
            self.audio_engine.get_playback_state() if self.audio_engine else {}
        )
        self.ui_state.is_playing = playback_state.get("is_playing", False)
        self.ui_state.is_paused = playback_state.get("is_paused", False)

        self.renderer.render(painter, self.ui_state)
        painter.end()

    def mousePressEvent(self, event):
        # Bring all windows to foreground when any part of the main window is clicked
        self.bring_all_windows_to_foreground()

        if event.button() == Qt.LeftButton:
            # Check for close button first (before titlebar dragging, since it's in the titlebar area)
            # Close button is at (264, 3) with size (9, 9) in the titlebar area
            close_button_rect = QRect(264, 3, 9, 9)
            if close_button_rect.contains(event.pos()):
                # Quit the application when close button is clicked
                # Use the proper close event handling to ensure audio engine cleanup
                self.close()
                return

            # Check if click is on titlebar for window dragging
            # Titlebar is at the top of the window, typically 14 pixels high
            titlebar_rect = QRect(0, 0, self.width(), 14)
            if titlebar_rect.contains(event.pos()):
                self._dragging_window = True
                self._drag_start_position = (
                    event.globalPos() - self.frameGeometry().topLeft()
                )
                return

            spec = self.skin_data.spec_json
            main_window_areas = spec["destinations"]["main_window"]["areas"]

            # Check for Volume Slider interaction
            volume_area_spec = main_window_areas["volume_slider"]
            volume_rect = QRect(
                volume_area_spec["x"],
                volume_area_spec["y"],
                volume_area_spec["w"],
                volume_area_spec["h"],
            )
            if volume_rect.contains(event.pos()):
                self.ui_state.is_volume_dragged = True
                self._update_volume_from_mouse(event.pos())
                return

            # Check for Balance Slider interaction
            balance_area_spec = main_window_areas[
                "balance_slider"
            ]  # Use balance_slider area per spec
            balance_rect = QRect(
                balance_area_spec["x"],
                balance_area_spec["y"],
                balance_area_spec["w"],
                balance_area_spec["h"],
            )
            if balance_rect.contains(event.pos()):
                self.ui_state.is_balance_dragged = True
                self._update_balance_from_mouse(event.pos())
                return

            # Check for Position Bar interaction
            position_area_spec = main_window_areas["position_track"]
            position_rect = QRect(
                position_area_spec["x"],
                position_area_spec["y"],
                position_area_spec["w"],
                position_area_spec["h"],
            )
            if position_rect.contains(event.pos()):
                self.ui_state.dragging_position = True
                self._update_position_from_mouse(event.pos())
                return

            # Check for Playlist Button interaction
            playlist_button_area_spec = main_window_areas["playlist_button"]
            playlist_button_rect = QRect(
                playlist_button_area_spec["x"],
                playlist_button_area_spec["y"],
                playlist_button_area_spec["w"],
                playlist_button_area_spec["h"],
            )
            if playlist_button_rect.contains(event.pos()):
                # Toggle playlist window using centralized method
                if self.ui_state.playlist_button_on:
                    self.hide_playlist_window()
                else:
                    self.show_playlist_window()

                return

            # Check for EQ Button interaction
            eq_button_area_spec = main_window_areas["eq_button"]
            eq_button_rect = QRect(
                eq_button_area_spec["x"],
                eq_button_area_spec["y"],
                eq_button_area_spec["w"],
                eq_button_area_spec["h"],
            )
            if eq_button_rect.contains(event.pos()):
                # Toggle equalizer window using centralized method
                if self.ui_state.eq_button_on:
                    self.hide_equalizer_window()
                else:
                    self.show_equalizer_window()

                return

            # Check for Shuffle Button interaction
            shuffle_area_spec = main_window_areas["shuffle_dest"]
            shuffle_rect = QRect(
                shuffle_area_spec["x"],
                shuffle_area_spec["y"],
                shuffle_area_spec["w"],
                shuffle_area_spec["h"],
            )
            if shuffle_rect.contains(event.pos()):
                self.ui_state.shuffle_on = not self.ui_state.shuffle_on
                self.ui_state.is_shuffle_pressed = True
                self.update()
                return

            # Check for Repeat Button interaction
            repeat_area_spec = main_window_areas["repeat_dest"]
            repeat_rect = QRect(
                repeat_area_spec["x"],
                repeat_area_spec["y"],
                repeat_area_spec["w"],
                repeat_area_spec["h"],
            )
            if repeat_rect.contains(event.pos()):
                self.ui_state.repeat_on = not self.ui_state.repeat_on
                self.ui_state.is_repeat_pressed = True
                self.update()
                return

            # Check for control buttons interaction
            controls = main_window_areas["controls"]
            for control in controls:
                control_rect = QRect(
                    control["dest_x"], control["dest_y"], control["w"], control["h"]
                )
                if control_rect.contains(event.pos()):
                    if control["name"] == "previous":
                        self.ui_state.is_previous_pressed = True
                        # Trigger previous track in playlist
                        self.play_previous_track()
                        self.update()
                        return
                    elif control["name"] == "play":
                        self.ui_state.is_play_pressed = True
                        self.ui_state.is_pause_pressed = False  # Reset pause state

                        # If playlist is empty, just start playback if track is loaded
                        if not self.playlist:
                            if (
                                not self.audio_engine.is_playing
                                or self.audio_engine.is_paused
                            ):
                                self.audio_engine.play()
                            self.update()
                            return

                        # Get the selected track from the playlist window
                        selected_track_index = (
                            self.playlist_window.get_selected_track_index()
                        )

                        # If no track is selected, use the first track in the playlist
                        if selected_track_index == -1:
                            selected_track_index = 0

                        # Play the selected track (or first track if none selected)
                        self.play_track_at_index(selected_track_index)
                        self.update()
                        return
                    elif control["name"] == "pause":
                        self.ui_state.is_pause_pressed = True
                        # Toggle pause via audio engine

                        if self.audio_engine.is_playing:
                            self.audio_engine.pause()
                        elif self.audio_engine.is_paused:
                            self.audio_engine.play()
                            # Refresh album art if the window is visible and we're now playing
                            if self.album_art_window.isVisible():
                                self.album_art_window.refresh_album_art(
                                    self.audio_engine
                                )
                        self.update()
                        return
                    elif control["name"] == "stop":
                        self.ui_state.is_stop_pressed = True
                        # Stop playback via audio engine
                        self.audio_engine.stop()
                        self.ui_state.position = 0.0  # Reset position visually
                        # Clear current track path but preserve the index so the same track can be restarted
                        self.current_track_path = None
                        # Update play/pause/stop states
                        self.ui_state.is_play_pressed = False
                        self.ui_state.is_pause_pressed = False
                        # Make sure the playlist window knows which track was playing so it can be restarted
                        if hasattr(self, "playlist_window") and self.playlist_window:
                            self.playlist_window.set_current_track_index(
                                self.current_track_index
                            )
                        self.update()
                        return
                    elif control["name"] == "next":
                        self.ui_state.is_next_pressed = True
                        # Trigger next track in playlist
                        self.play_next_track()
                        self.update()
                        return
                    self.update()
                    return

            # Check for Eject Button interaction
            eject_area_spec = main_window_areas["eject"]
            eject_rect = QRect(
                eject_area_spec["x"],
                eject_area_spec["y"],
                eject_area_spec["w"],
                eject_area_spec["h"],
            )
            if eject_rect.contains(event.pos()):
                self.ui_state.is_eject_pressed = True
                self.update()  # Force repaint to show pressed state immediately
                # Process pending events to ensure UI updates before showing dialog
                QApplication.processEvents()
                # Open file dialog to load a track
                # Use default music path from preferences if available, otherwise use empty string
                default_music_path = self.preferences.get_default_music_path()
                initial_path = default_music_path if default_music_path else ""

                file_path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Open Audio File",
                    initial_path,
                    "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.opus *.aiff *.au);;All Files (*)",
                )

                # Always reset the eject button pressed state after dialog closes
                # regardless of whether a file was selected or dialog was cancelled
                self.ui_state.is_eject_pressed = False

                if file_path:
                    # Add to playlist and play immediately
                    if self.audio_engine.load_track(file_path):
                        # For single file loading via eject, create a new playlist with just this file
                        self.playlist = [file_path]
                        self.current_track_index = 0

                        # Update the playlist window display
                        self.update_playlist_display()

                        # Update the current track title
                        metadata = self.audio_engine.get_metadata()
                        if metadata:
                            # Format as "artist - song title" for display
                            self.ui_state.current_track_title = f"{metadata.get('artist', 'Unknown')} - {metadata.get('title', 'Unknown')}"
                        else:
                            self.ui_state.current_track_title = os.path.basename(
                                file_path
                            )

                        # Start playback
                        self.audio_engine.play()

                        # Update playlist window to show currently playing track
                        self.playlist_window.set_current_track_index(0)

                        # Refresh album art if the window is visible
                        if (
                            hasattr(self, "album_art_window")
                            and self.album_art_window.isVisible()
                        ):
                            self.album_art_window.refresh_album_art(self.audio_engine)
                    else:
                        self.ui_state.current_track_title = "Error loading track"

                self.update()  # Repaint main window if button state changes visually
                return

            # Check for Clutterbar buttons interaction (O, A, I, D, V)
            # The clutterbar is a clickable 8x43 rectangle at position (10, 22)
            # Expand the clickable area to make it easier to click (add some horizontal buffer)
            clutterbar_rect = QRect(
                8, 22, 12, 43
            )  # Expand from 8 to 12 pixels wide with 2px buffer on each side
            if clutterbar_rect.contains(event.pos()):
                # Calculate which button was pressed based on Y coordinate
                y_pos = event.pos().y() - 22  # Relative to clutterbar top

                # More precise calculation: divide 43 pixels into 5 equal sections
                # Each button has height of 43/5 = 8.6 pixels
                # Define exact boundaries to avoid floating point issues
                button_height = 43 / 5  # 8.6 pixels per button

                # Calculate which button was clicked based on precise boundaries
                if 0 <= y_pos < button_height:  # Button 0 (Options)
                    button_index = 0
                elif (
                    button_height <= y_pos < 2 * button_height
                ):  # Button 1 (Always on Top)
                    button_index = 1
                elif (
                    2 * button_height <= y_pos < 3 * button_height
                ):  # Button 2 (File Info)
                    button_index = 2
                elif (
                    3 * button_height <= y_pos < 4 * button_height
                ):  # Button 3 (Double Size)
                    button_index = 3
                elif 4 * button_height <= y_pos < 43:  # Button 4 (Visualization)
                    button_index = 4
                else:
                    button_index = -1  # Outside any button

                if 0 <= button_index < 5:
                    # Set the appropriate button pressed state
                    if button_index == 0:  # 'O' - Options Menu
                        self.ui_state.is_options_pressed = True
                        self.show_skin_selection_dialog()
                    elif button_index == 1:  # 'A' - Always on Top
                        self.ui_state.is_always_on_top_pressed = True
                    elif button_index == 2:  # 'I' - File Info / Album Art
                        # Toggle album art window using centralized method
                        if self.ui_state.album_art_visible:
                            self.hide_album_art_window()
                        else:
                            self.show_album_art_window()

                    elif button_index == 3:  # 'D' - Double Size
                        self.ui_state.is_double_size_pressed = True
                    elif button_index == 4:  # 'V' - Visualization Menu
                        self.ui_state.is_visualization_menu_pressed = True
                        # Cycle through visualization modes: SPECTRUM -> OSCILLOSCOPE -> OFF -> SPECTRUM
                        vis_mode = self.renderer.get_visualization_mode()
                        if vis_mode == "SPECTRUM":
                            new_vis_mode = "OSCILLOSCOPE"
                        elif vis_mode == "OSCILLOSCOPE":
                            new_vis_mode = "OFF"
                        else:  # OFF or any other state
                            new_vis_mode = "SPECTRUM"

                        # Update the renderer with the new visualization mode
                        self.renderer.set_visualization_mode(new_vis_mode)
                        # Also update the audio engine with the new visualization mode
                        self.audio_engine.set_visualization_mode(new_vis_mode)
                    self.update()
                    return

        # Hot-about (Winamp info) clickable area
        try:
            spec = self.skin_data.spec_json
            main_window_areas = spec["destinations"]["main_window"]["areas"]
            hot_about_spec = main_window_areas.get("hot_about")
            if hot_about_spec:
                hot_about_rect = QRect(
                    hot_about_spec["x"],
                    hot_about_spec["y"],
                    hot_about_spec["w"],
                    hot_about_spec["h"],
                )
                if hot_about_rect.contains(event.pos()):
                    # Use app-level handler if available, otherwise show QMessageBox directly
                    try:
                        app = QApplication.instance()
                        if hasattr(app, "_show_about_dialog"):
                            app._show_about_dialog()
                        else:
                            QMessageBox.about(
                                self,
                                "About WimPyAmp",
                                "WimPyAmp\n\nVersion: 0.0.0\n\nA lightweight Winamp-style music player.\n\n© WimPyAmp Project",
                            )
                    except Exception:
                        QMessageBox.about(self, "About WimPyAmp", "WimPyAmp")
                    return
        except Exception:
            # If anything goes wrong while checking hot_about, fall back to default handling
            pass

        super().mousePressEvent(event)

    def focusInEvent(self, event):
        """Called when the window receives focus."""
        # Bring all windows to foreground when main window gains focus
        self.bring_all_windows_to_foreground()
        super().focusInEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging_window:
            self.move(event.globalPos() - self._drag_start_position)
            return
        if self.ui_state.is_volume_dragged:
            self._update_volume_from_mouse(event.pos())
            return
        if self.ui_state.is_balance_dragged:
            self._update_balance_from_mouse(event.pos())
            return
        if self.ui_state.dragging_position:
            self._update_position_from_mouse(event.pos())
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._dragging_window:
                self._dragging_window = False
                return
            if self.ui_state.is_volume_dragged:
                self.ui_state.is_volume_dragged = False
                self.update()
                return
            if self.ui_state.is_balance_dragged:
                self.ui_state.is_balance_dragged = False
                self.update()
                return
            if self.ui_state.dragging_position:
                self.ui_state.dragging_position = False
                self.update()
                return

            # Reset pressed states for control buttons, but keep play/pause/stop states reflecting actual playback
            if self.ui_state.is_previous_pressed:
                self.ui_state.is_previous_pressed = False
                self.update()
                return
            # Don't automatically reset play/pause/stop - their state reflects actual playback status
            # Update these states based on the actual audio engine state instead
            if self.ui_state.is_next_pressed:
                self.ui_state.is_next_pressed = False
                self.update()
                return
            if self.ui_state.is_eject_pressed:
                self.ui_state.is_eject_pressed = False
                self.update()
                return

            # Reset pressed states for EQ and Playlist buttons
            if self.ui_state.is_eq_pressed:
                self.ui_state.is_eq_pressed = False
                self.update()
                return
            if self.ui_state.is_playlist_pressed:
                self.ui_state.is_playlist_pressed = False
                self.update()
                return

            # Reset pressed states for Shuffle and Repeat buttons
            if self.ui_state.is_shuffle_pressed:
                self.ui_state.is_shuffle_pressed = False
                self.update()
                return
            if self.ui_state.is_repeat_pressed:
                self.ui_state.is_repeat_pressed = False
                self.update()
                return

            # Reset pressed states for Clutterbar buttons
            if self.ui_state.is_options_pressed:
                self.ui_state.is_options_pressed = False
                self.update()
                return
            if self.ui_state.is_always_on_top_pressed:
                self.ui_state.is_always_on_top_pressed = False
                self.update()
                return
            if self.ui_state.is_file_info_pressed:
                self.ui_state.is_file_info_pressed = False
                self.update()
                return
            if self.ui_state.is_double_size_pressed:
                self.ui_state.is_double_size_pressed = False
                self.update()
                return
            if self.ui_state.is_visualization_menu_pressed:
                self.ui_state.is_visualization_menu_pressed = False
                self.update()
                return

        super().mouseReleaseEvent(event)

    def _update_volume_from_mouse(self, mouse_pos):
        spec = self.skin_data.spec_json
        volume_area_spec = spec["destinations"]["main_window"]["areas"]["volume_slider"]

        slider_width = volume_area_spec["w"]
        relative_x = mouse_pos.x() - volume_area_spec["x"]

        relative_x = max(0, min(relative_x, slider_width))

        self.ui_state.volume = relative_x / slider_width
        self.audio_engine.set_volume(self.ui_state.volume)
        self.update()

    def _update_balance_from_mouse(self, mouse_pos):
        spec = self.skin_data.spec_json
        balance_area_spec = spec["destinations"]["main_window"]["areas"][
            "balance_slider"
        ]  # Use balance_slider area per spec

        slider_width = balance_area_spec["w"]
        relative_x = mouse_pos.x() - balance_area_spec["x"]

        relative_x = max(0, min(relative_x, slider_width))

        # Convert slider position (0 to 1) to balance value (-1 to 1)
        # where 0.0 is center, -1.0 is full left, 1.0 is full right
        normalized_position = relative_x / slider_width  # 0 to 1
        self.ui_state.balance = (
            normalized_position * 2
        ) - 1  # Convert to -1 to 1 range
        self.audio_engine.set_balance(self.ui_state.balance)
        self.update()

    def _update_position_from_mouse(self, mouse_pos):
        spec = self.skin_data.spec_json
        position_area_spec = spec["destinations"]["main_window"]["areas"][
            "position_track"
        ]

        slider_width = position_area_spec["w"]
        relative_x = mouse_pos.x() - position_area_spec["x"]

        relative_x = max(0, min(relative_x, slider_width))

        # Calculate the position as a fraction (0.0 to 1.0) of the total duration
        position_fraction = relative_x / slider_width
        self.ui_state.position = position_fraction
        self.audio_engine.seek(position_fraction)
        self.update()

    def moveEvent(self, event):
        """Handle window movement to keep docked windows in the right position."""
        super().moveEvent(event)

        # Calculate the movement delta
        dx, dy = 0, 0
        if hasattr(self, "_old_main_pos"):
            dx = self.x() - self._old_main_pos.x()
            dy = self.y() - self._old_main_pos.y()

        # Update the stored position for next time
        self._old_main_pos = self.pos()

        # Save main window position to preferences
        self.preferences.set_main_window_position(self.x(), self.y())

        # Handle all docked child windows
        # Only move child windows after initialization is complete to avoid moving them before their positions are set from preferences
        if getattr(self, "_initialization_complete", False):
            child_windows = []
            if hasattr(self, "playlist_window"):
                child_windows.append(self.playlist_window)
            if hasattr(self, "equalizer_window"):
                child_windows.append(self.equalizer_window)
            if hasattr(self, "album_art_window"):
                child_windows.append(self.album_art_window)

            # Process each docked child window
            for child_window in child_windows:
                if child_window and child_window.isVisible():
                    # Only move the child window if it's currently marked as docked
                    if getattr(child_window, "is_docked", False):
                        # Move the child window by the same delta as the main window movement
                        new_x = child_window.x() + dx
                        new_y = child_window.y() + dy
                        child_window.move(new_x, new_y)

                    # Check if the child window is still near the main window or other docked windows to maintain docked state
                    child_rect = QRect(
                        child_window.x(),
                        child_window.y(),
                        child_window.width(),
                        child_window.height(),
                    )
                    is_still_near = self.is_window_near_any_docked_window(
                        child_rect, exclude_window=child_window
                    )
                    # Update docked state based on proximity to any docked window
                    child_window.is_docked = is_still_near

    def load_new_skin(self, skin_path):
        """Load a new skin from the specified path."""
        try:
            # Create a new SkinParser instance for the new skin
            new_skin_parser = SkinParser(skin_path)
            new_skin_data = new_skin_parser.parse()

            if not new_skin_data.extracted_skin_dir:
                print(f"ERROR: Failed to load skin from {skin_path}")
                return

            # Update the current skin parser and data
            self.skin_parser = new_skin_parser
            self.skin_data = new_skin_data

            # Update the skin path
            self.skin_path = skin_path

            # Save the new skin preference
            self.preferences.set_current_skin(skin_path)

            # Clear the sprite manager cache to ensure fresh sprites are loaded
            self.renderer.sprite_manager.clear_cache()

            # Preserve the current visualization mode before updating skin data
            current_vis_mode = self.renderer.get_visualization_mode()

            # Update the renderer with the new skin data
            self.renderer.set_skin_data(self.skin_data)

            # Restore the visualization mode after updating skin data
            self.renderer.set_visualization_mode(current_vis_mode)

            # Update the text renderers
            self.text_renderer = TextRenderer(self.skin_data)
            self.scrolling_text_renderer = ScrollingTextRenderer(
                self.text_renderer, self.skin_data
            )

            # Also update the playlist window with the new skin
            if hasattr(self, "playlist_window") and self.playlist_window:
                self.playlist_window.update_skin(
                    self.skin_data, self.renderer.sprite_manager, self.text_renderer
                )

            # Also update the equalizer window with the new skin
            if hasattr(self, "equalizer_window") and self.equalizer_window:
                self.equalizer_window.update_skin(
                    self.skin_data, self.renderer.sprite_manager
                )

            # Update the window size based on the new skin (main.bmp size may be different)
            if self.skin_data.main_bmp_path:
                from PIL import Image

                img = Image.open(self.skin_data.main_bmp_path)
                current_pos = self.pos()  # Keep the current position
                self.setGeometry(
                    current_pos.x(), current_pos.y(), img.width, img.height
                )

            # Apply region mask if available
            self.apply_region_mask()

            # Repaint the window with the new skin
            self.update()

        except Exception as e:
            print(f"ERROR: Failed to load new skin: {e}")

    def show_skin_selection_dialog(self):
        """Show the skin selection dialog and handle the result."""
        dialog = SkinSelectionDialog(self)
        result = dialog.exec_()

        if result == 1:  # Load New Skin
            # Open file dialog to load a new skin
            skin_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Winamp Skin",
                "",
                "Winamp Skins (*.wsz *.zip);;Winamp Skins (*.wsz);;ZIP Files (*.zip);;All Files (*)",
            )

            if skin_path:
                self.load_new_skin(skin_path)
        elif result == 2:  # Load Default Skin
            # Load the default skin
            self.load_new_skin(self.default_skin_path)
            # Remove the saved skin preference to use default skin going forward
            # Setting to default skin path will automatically remove the entry
            self.preferences.set_current_skin(self.default_skin_path)

    def update_visualization(self):
        """Update visualization by getting data from audio engine and updating renderer."""
        if hasattr(self, "audio_engine") and self.audio_engine:
            # Get visualization data from the queue if available
            try:
                # Get all available visualization data (non-blocking)
                while True:
                    vis_data = self.audio_engine.vis_data_queue.get_nowait()
                    # Update the renderer with the visualization data
                    self.renderer.update_visualization_data(vis_data)
            except Exception:
                # Queue is empty, which is fine
                pass

            # Trigger a repaint to show the updated visualization
            self.update()

    def setup_media_shortcuts(self):
        """Set up keyboard shortcuts for media controls."""
        # Create shortcuts for media controls using PyQt5
        # Space key as primary play/pause control (works on all platforms, including macOS)
        space_shortcut = QShortcut(QKeySequence("Space"), self)
        space_shortcut.activated.connect(self.toggle_play_pause)

        # Alternative media keys - may require system permissions on macOS
        try:
            # Play/Pause key
            play_pause_shortcut = QShortcut(QKeySequence("Media Play"), self)
            play_pause_shortcut.activated.connect(self.toggle_play_pause)

            # Next track key
            next_shortcut = QShortcut(QKeySequence("Media Next"), self)
            next_shortcut.activated.connect(self.play_next_track)

            # Previous track key
            prev_shortcut = QShortcut(QKeySequence("Media Previous"), self)
            prev_shortcut.activated.connect(self.play_previous_track)

            # Stop key
            stop_shortcut = QShortcut(QKeySequence("Media Stop"), self)
            stop_shortcut.activated.connect(self._handle_stop_action)
        except Exception:
            # If Media keys are not supported on this system, just use space bar as primary control
            print(
                "Media keys not supported on this system, use Space bar for play/pause"
            )

        # Using only regular PyQt5 keyboard shortcuts for media keys
        # These work without requiring system permissions on macOS

    def toggle_play_pause(self):
        """Toggle between play and pause states."""
        if self.audio_engine.is_paused:
            # If paused, resume playback
            self.audio_engine.play()
            self.ui_state.is_play_pressed = True
            self.ui_state.is_pause_pressed = False
        elif self.audio_engine.is_playing:
            # If playing, pause
            self.audio_engine.pause()
            self.ui_state.is_play_pressed = False
            self.ui_state.is_pause_pressed = True
        else:
            # If stopped, start playing (or resume if there's a loaded track)
            if self.audio_engine.has_track_loaded():
                self.audio_engine.play()
                self.ui_state.is_play_pressed = True
                self.ui_state.is_pause_pressed = False
            else:
                # If no track loaded, try to play the first track in playlist
                if self.playlist:
                    selected_track_index = (
                        self.playlist_window.get_selected_track_index()
                    )
                    if selected_track_index == -1:
                        selected_track_index = 0
                    self.play_track_at_index(selected_track_index)

    def load_and_play_file(self, file_path):
        """
        Load and play a file passed from command line or file opening event.

        New behavior:
        - If it's a playlist file (.m3u, .m3u8, .pls), load it like the Load Playlist menu option
        - If no track is currently playing AND playlist is empty, keep current behavior (load and play)
        - If a track is playing, add the new file to the bottom of the playlist but don't interrupt playback
        - If no track is playing BUT playlist is not empty, add to playlist and play the new track
        """
        if not os.path.isfile(file_path):
            print(f"File not found: {file_path}")
            return False

        # Check if it's a playlist file
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension in [".m3u", ".m3u8", ".pls"]:
            return self.load_playlist_file(file_path)

        # Check current playback state
        current_state = self.audio_engine.get_playback_state()
        is_playing = current_state["is_playing"]
        is_stopped = not is_playing and not current_state["is_paused"]

        # If nothing is playing and playlist is empty, use original behavior
        if is_stopped and len(self.playlist) == 0:
            # Original behavior: add to playlist and play immediately
            if self.audio_engine.load_track(file_path):
                # For single file loading, create a new playlist with just this file
                self.playlist = [file_path]
                self.current_track_index = 0

                # Update the playlist window display
                self.update_playlist_display()

                # Update the current track title
                metadata = self.audio_engine.get_metadata()
                if metadata:
                    # Format as "artist - song title" for display
                    self.ui_state.current_track_title = f"{metadata.get('artist', 'Unknown')} - {metadata.get('title', 'Unknown')}"
                else:
                    self.ui_state.current_track_title = os.path.basename(file_path)

                # Start playback
                self.audio_engine.play()

                # Update playlist window to show currently playing track
                if hasattr(self, "playlist_window"):
                    self.playlist_window.set_current_track_index(0)

                # Refresh album art if the window is visible
                if (
                    hasattr(self, "album_art_window")
                    and self.album_art_window.isVisible()
                ):
                    self.album_art_window.refresh_album_art(self.audio_engine)

                return True
            else:
                self.ui_state.current_track_title = "Error loading track"
                return False
        else:
            # Add the file to the bottom of the playlist
            if file_path not in self.playlist:  # Avoid duplicates
                self.playlist.append(file_path)
                self.update_playlist_display()

                # If a track is playing, just add to playlist and return
                if is_playing:
                    print(
                        f"Added {os.path.basename(file_path)} to playlist (not interrupting current track)"
                    )
                    return True

                # If no track is playing but playlist was not empty, play the newly added track
                # Find the index of the newly added track (it's at the end)
                new_index = len(self.playlist) - 1
                if self.play_track_at_index(new_index):
                    print(f"Now playing {os.path.basename(file_path)}")
                    return True
                else:
                    self.ui_state.current_track_title = "Error loading track"
                    return False
            else:
                print(f"File {file_path} already exists in playlist, skipping")
                return True

    def load_directory(self, directory_path):
        """Load all media files from a directory and its subdirectories."""
        if not os.path.isdir(directory_path):
            print(f"Directory not found: {directory_path}")
            return False

        # Define supported media file extensions
        media_extensions = {
            ".mp3",
            ".wav",
            ".ogg",
            ".flac",
            ".m4a",
            ".aac",
            ".wma",
            ".mp4",
            ".m3u",
            ".pls",
            ".opus",
            ".aiff",
            ".au",
        }

        # Collect files from the directory and its subdirectories
        new_files_collected = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in media_extensions:
                    full_path = os.path.join(root, file)
                    new_files_collected.append(full_path)

        # Sort the new files by filename
        new_files_collected.sort(key=lambda path: os.path.basename(path).lower())

        # Add sorted new files to the playlist
        if new_files_collected:
            self.playlist = new_files_collected
            self.current_track_index = 0  # Set first track as current

            # Update the playlist window display
            self.update_playlist_display()

            # Update the current track title with the first track
            if self.playlist:
                first_file = self.playlist[0]
                # Try to load the first track metadata to display
                if self.audio_engine.load_track(first_file):
                    metadata = self.audio_engine.get_metadata()
                    if metadata:
                        # Format as "artist - song title" for display
                        self.ui_state.current_track_title = f"{metadata.get('artist', 'Unknown')} - {metadata.get('title', 'Unknown')}"
                    else:
                        self.ui_state.current_track_title = os.path.basename(first_file)

            # Update playlist window to show currently playing track
            if hasattr(self, "playlist_window"):
                self.playlist_window.set_current_track_index(0)

            # Refresh album art if the window is visible
            if hasattr(self, "album_art_window") and self.album_art_window.isVisible():
                self.album_art_window.refresh_album_art(self.audio_engine)

            return True
        else:
            print(f"No media files found in directory: {directory_path}")
            return False

    def load_playlist_file(self, playlist_file_path):
        """
        Load a playlist file (.m3u, .m3u8, or .pls) similar to the Load Playlist menu option.
        This mimics the functionality from the playlist window's Load Playlist function.
        """
        if not os.path.isfile(playlist_file_path):
            print(f"Playlist file not found: {playlist_file_path}")
            return False

        new_filepaths = []
        file_extension = os.path.splitext(playlist_file_path)[1].lower()

        try:
            if file_extension in [".m3u", ".m3u8"]:
                # Parse M3U file format
                with open(playlist_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if (
                        line
                        and not line.startswith("#EXTM3U")
                        and not line.startswith("#EXTINF")
                    ):
                        # This is a file path
                        # Resolve relative paths relative to the playlist file's directory
                        if not os.path.isabs(line):
                            line = os.path.join(
                                os.path.dirname(playlist_file_path), line
                            )
                        new_filepaths.append(line)
                    elif line.startswith("#EXTINF"):
                        # This is metadata, skip to the next line which should be the file path
                        i += 1
                        if i < len(lines):
                            path_line = lines[i].strip()
                            if path_line:
                                # Resolve relative paths relative to the playlist file's directory
                                if not os.path.isabs(path_line):
                                    path_line = os.path.join(
                                        os.path.dirname(playlist_file_path), path_line
                                    )
                                new_filepaths.append(path_line)
                    i += 1
            elif file_extension == ".pls":
                # Parse PLS (Playlist) file format
                # PLS format: [playlist], File1=/path/to/file, Title1=song title, Length1=duration, NumberOfEntries=total count
                with open(playlist_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                pls_entries = {}
                for line in lines:
                    line = line.strip()
                    if line.lower().startswith("file") and "=" in line:
                        # Parse FileN=filepath
                        key, value = line.split("=", 1)
                        # Extract the number from keys like File1, File2, etc.
                        key_lower = key.lower()
                        if key_lower.startswith("file") and len(key_lower) > 4:
                            file_num = key_lower[4:]  # Get the number after "file"
                            if file_num.isdigit():
                                pls_entries[file_num] = pls_entries.get(file_num, {})
                                # Resolve relative paths relative to the playlist file's directory
                                resolved_path = (
                                    value
                                    if os.path.isabs(value)
                                    else os.path.join(
                                        os.path.dirname(playlist_file_path), value
                                    )
                                )
                                pls_entries[file_num]["file"] = resolved_path
                    elif line.lower().startswith("title") and "=" in line:
                        # Parse TitleN=title
                        key, value = line.split("=", 1)
                        # Extract the number from keys like Title1, Title2, etc.
                        key_lower = key.lower()
                        if key_lower.startswith("title") and len(key_lower) > 5:
                            title_num = key_lower[5:]  # Get the number after "title"
                            if title_num.isdigit():
                                pls_entries[title_num] = pls_entries.get(title_num, {})
                                pls_entries[title_num]["title"] = value

                # Add entries in numerical order
                for file_num in sorted(pls_entries.keys(), key=int):
                    entry = pls_entries[file_num]
                    if "file" in entry:
                        new_filepaths.append(entry["file"])

            else:
                # Plain text file with one file path per line (just in case)
                with open(playlist_file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            # Resolve relative paths relative to the playlist file's directory
                            if not os.path.isabs(line):
                                line = os.path.join(
                                    os.path.dirname(playlist_file_path), line
                                )
                            new_filepaths.append(line)

            # Update the main window's playlist
            if new_filepaths:
                self.playlist = new_filepaths
                self.current_track_index = -1  # No track playing yet

                # Update the playlist window display
                self.update_playlist_display()

                # If there are tracks in the playlist, start playing the first one
                if self.playlist:
                    first_track_index = 0
                    if self.play_track_at_index(first_track_index):
                        print(
                            f"Loaded playlist and started playing: {os.path.basename(self.playlist[first_track_index])}"
                        )
                        return True
                    else:
                        # If we can't play the first track, still consider the playlist loaded
                        print(
                            f"Playlist loaded with {len(self.playlist)} tracks, but first track failed to play"
                        )
                        return True
                else:
                    print("Playlist loaded but is empty")
                    return True
            else:
                print("No valid file paths found in playlist file")
                return False

        except Exception as e:
            print(f"Error loading playlist file {playlist_file_path}: {str(e)}")
            return False

    def dragEnterEvent(self, event):
        """Handle drag enter event to accept files and directories."""
        # Check if the drag contains URLs (files/directories)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Handle drag move event."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle drop event to load files or directories."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            for url in urls:
                # Get the local file path from the URL
                file_path = url.toLocalFile()
                if os.path.isfile(file_path):
                    # If it's a file, load and play it
                    self.load_and_play_file(file_path)
                elif os.path.isdir(file_path):
                    # If it's a directory, load all audio files from it
                    self.load_directory(file_path)

            event.acceptProposedAction()
        else:
            event.ignore()

    def _on_close(self, event):
        """Properly clean up the audio engine and tracked windows when closing the application."""
        # Set a shutdown flag to prevent child windows from updating preferences
        # during application shutdown
        self._is_shutting_down = True

        # Close all tracked child windows first
        for window in getattr(self, "_tracked_windows", []):
            if window and window.isVisible():
                window.close()

        # Save the current window visibility states before closing
        # This ensures that visibility preferences are saved with the current state
        # rather than being reset when child windows are automatically closed
        self._update_window_visibility_preferences()

        # Also make sure to save main window position
        self.preferences.set_main_window_position(self.x(), self.y())

        # Stop audio engine
        if hasattr(self, "audio_engine") and self.audio_engine:
            self.audio_engine.stop()

        # Stop and clean up visualization timer
        if hasattr(self, "visualization_timer"):
            self.visualization_timer.stop()

        event.accept()

    def _initiate_shutdown(self):
        """Single point of entry for all quit operations."""
        # Prevent multiple shutdown attempts
        if getattr(self, "_shutdown_in_progress", False):
            return

        self._shutdown_in_progress = True

        # Set global shutdown flag to prevent other operations during shutdown
        self._is_shutting_down = True

        # Perform coordinated shutdown sequence
        self._perform_coordinated_shutdown()

        # Finally, close the main window
        self.close()

    def _perform_coordinated_shutdown(self):
        """Coordinate the shutdown sequence in a predictable order."""
        # 1. Close all tracked child windows first
        for window in getattr(self, "_tracked_windows", []):
            if window and window.isVisible():
                window.close()

        # 2. Stop all timers
        if hasattr(self, "playback_timer"):
            self.playback_timer.stop()
        if hasattr(self, "track_completion_timer"):
            self.track_completion_timer.stop()
        if hasattr(self, "visualization_timer"):
            self.visualization_timer.stop()

        # 3. Stop audio engine
        if hasattr(self, "audio_engine"):
            self.audio_engine.stop()

        # 4. Save current window visibility states to preferences
        self._save_window_visibility_states()

        # 5. Save main window position
        self.preferences.set_main_window_position(self.x(), self.y())

    def _save_window_visibility_states(self):
        """Save all window visibility states from main UI state during shutdown."""
        # Save all visibility states from the central UI state
        self.preferences.set_eq_window_visibility(self.ui_state.eq_button_on)
        self.preferences.set_playlist_window_visibility(
            self.ui_state.playlist_button_on
        )
        self.preferences.set_album_art_window_visibility(
            self.ui_state.album_art_visible
        )

        # Save all window positions (only for windows that were visible at shutdown)
        if self.ui_state.eq_button_on and hasattr(self, "equalizer_window"):
            self.preferences.set_eq_window_position(
                self.equalizer_window.x(), self.equalizer_window.y()
            )
        if self.ui_state.playlist_button_on and hasattr(self, "playlist_window"):
            self.preferences.set_playlist_window_position(
                self.playlist_window.x(), self.playlist_window.y()
            )
        if self.ui_state.album_art_visible and hasattr(self, "album_art_window"):
            self.preferences.set_album_art_window_position(
                self.album_art_window.x(), self.album_art_window.y()
            )


def main():
    import sys
    from PySide6.QtGui import QKeySequence
    from PySide6.QtCore import Qt

    # Custom application class to handle file opening events
    class WimPyAmpApp(QApplication):
        def __init__(self, sys_argv):
            super().__init__(sys_argv)

        def _setup_native_menus(self):
            """Setup native macOS application menu."""
            # Create a temporary main window to get the title
            # (we'll reference the actual main window later)
            self.aboutToQuit.connect(self._cleanup_menu_resources)

            # Create the main menu bar - this creates system-level menus on macOS
            # even though we don't attach it to a visible window
            menubar = QMenuBar()

            # App menu (automatically becomes the app menu on macOS)
            app_menu = menubar.addMenu(
                "WimPyAmp"
            )  # Use app name instead of window title since we're frameless

            # About action
            about_action = QAction("About WimPyAmp", self)
            about_action.triggered.connect(self._show_about_dialog)
            app_menu.addAction(about_action)

            app_menu.addSeparator()

            # Preferences action
            prefs_action = QAction("Preferences...", self)
            prefs_action.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_Comma))
            prefs_action.triggered.connect(self._show_preferences)
            app_menu.addAction(prefs_action)

            app_menu.addSeparator()

            # Quit action - connect to the main window's shutdown method when available
            quit_action = QAction("Quit WimPyAmp", self)
            quit_action.setShortcut(QKeySequence(Qt.CTRL | Qt.Key_Q))
            quit_action.triggered.connect(self._initiate_shutdown)
            app_menu.addAction(quit_action)

            self._app_menu = menubar  # Keep reference to prevent garbage collection

        def _initiate_shutdown(self):
            """Initiate shutdown by calling main window's shutdown method."""
            if hasattr(self, "main_window") and self.main_window:
                try:
                    # Try to call the shutdown method on main window
                    if hasattr(self.main_window, "_initiate_shutdown"):
                        self.main_window._initiate_shutdown()
                    else:
                        # Fallback: just close the main window
                        self.main_window.close()
                except Exception:
                    # If anything goes wrong, just quit the app
                    pass
            else:
                # If main window doesn't exist, quit the app directly
                self.quit()

        def _cleanup_menu_resources(self):
            """Clean up menu resources on app exit."""
            if hasattr(self, "_app_menu"):
                self._app_menu.deleteLater()
                delattr(self, "_app_menu")

        def _show_preferences(self):
            """Show the preferences dialog."""
            if hasattr(self, "main_window") and self.main_window:
                self.main_window.show_skin_selection_dialog()

        def _show_about_dialog(self):
            """Show an About dialog for the application.

            Use embedded VERSION file when running frozen (PyInstaller bundles).
            During development, read VERSION from the project root.
            """
            version = "0.0.0"
            try:
                if getattr(sys, "frozen", False):
                    # When frozen by PyInstaller, VERSION can be included in sys._MEIPASS
                    meipass = getattr(sys, "_MEIPASS", None)
                    if meipass:
                        version_path = os.path.join(meipass, "VERSION")
                        if os.path.exists(version_path):
                            with open(version_path, "r") as vf:
                                version = vf.read().strip() or version
                else:
                    # Development: read VERSION from project root
                    project_root = os.path.dirname(
                        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    )
                    version_path = os.path.join(project_root, "VERSION")
                    if os.path.exists(version_path):
                        with open(version_path, "r") as vf:
                            version = vf.read().strip() or version
            except Exception:
                pass

            about_html = (
                f"<h2>WimPyAmp</h2>Version: {version}<br><br>"
                '<a href="https://github.com/mikeypdev/wimpyamp">https://github.com/mikeypdev/wimpyamp</a><br><br>'
                "©2025 Mike Perry"
            )

            # Use a custom QMessageBox to allow clickable link
            dlg = QMessageBox()
            dlg.setWindowTitle("About WimPyAmp")
            dlg.setTextFormat(Qt.RichText)
            dlg.setText(about_html)
            dlg.setStandardButtons(QMessageBox.Ok)
            dlg.setTextInteractionFlags(Qt.TextBrowserInteraction)
            # Open links in system browser
            for child in dlg.findChildren(QLabel):
                child.setOpenExternalLinks(True)
            dlg.exec_()

        def event(self, event):
            # On macOS, handle file opening events
            if isinstance(event, QFileOpenEvent):
                if hasattr(self, "main_window"):
                    file_path = event.file()  # Get the file path from the event
                    if os.path.isfile(file_path):
                        self.main_window.load_and_play_file(file_path)
                    elif os.path.isdir(file_path):
                        self.main_window.load_directory(file_path)
            return super().event(event)

    # Use our custom app class
    app = WimPyAmpApp(sys.argv)

    # Check for command line arguments (files or directories to open)
    file_paths = []
    dir_paths = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            # Check if argument is a file or directory path (not an option flag)
            if not arg.startswith("-"):
                if os.path.isfile(arg):
                    file_paths.append(arg)
                elif os.path.isdir(arg):
                    dir_paths.append(arg)

    window = MainWindow()
    # Store reference to main window so the app can access it
    app.main_window = window

    # Setup native menus for macOS AFTER window exists
    if sys.platform == "darwin":  # Only on macOS
        app._setup_native_menus()

    # Load directory if provided as command line argument (takes priority)
    if dir_paths:
        # Load the first directory
        window.load_directory(dir_paths[0])
    # Otherwise load files if provided as command line arguments
    elif file_paths:
        # Load each file sequentially using the new smart behavior
        for file_path in file_paths:
            window.load_and_play_file(file_path)

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
