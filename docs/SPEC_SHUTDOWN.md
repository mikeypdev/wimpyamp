# WimPyAmp Shutdown Specification

This document specifies the reliable shutdown behavior for WimPyAmp, ensuring predictable application termination while preserving user preferences and window states.

## 1. Window Management and Lifecycle

### 1.1 Window Structure
The application maintains a main window with independent floating child windows:

```
MainWindow (top-level, no parent)
├── PlaylistWindow (independent floating window)
├── EqualizerWindow (independent floating window)  
└── AlbumArtWindow (independent floating window)
```

### 1.2 Centralized Window Control
- All window visibility state is managed entirely by the main window
- Child windows delegate visibility changes to the main window
- The main window is the single source of truth for all visibility states
- During shutdown, the main window explicitly closes all tracked windows

### 1.3 Window Creation Pattern
```python
# In MainWindow.__init__():
self.playlist_window = PlaylistWindow(None, skin_data, sprite_manager, text_renderer)
self.playlist_window.set_main_window(self)  # Set main window reference for UI updates
self.playlist_window.hide()  # Start hidden as per current behavior

self.equalizer_window = EqualizerWindow(None, skin_data, sprite_manager, audio_engine)
self.equalizer_window.main_window = self  # Set main window reference for UI updates

self.album_art_window = AlbumArtWindow(None, skin_data, sprite_manager)
self.album_art_window.set_main_window(self)  # Set main window reference for updates
self.album_art_window.hide()  # Start hidden as per current behavior

# Track windows for coordinated shutdown
self._tracked_windows = [self.playlist_window, self.equalizer_window, self.album_art_window]
```

## 2. Native macOS Menu Implementation

### 2.1 Basic Menu Structure
The application shall implement a basic macOS-compliant menu with the following minimum structure:

```
AppName Menu
├── About WimPyAmp
├── Preferences... (Cmd+,)
├── Services
├── Hide WimPyAmp (Cmd+H)
├── Hide Others (Cmd+Alt+H)
├── Show All
└── Quit WimPyAmp (Cmd+Q)
```

### 2.2 Menu Implementation Pattern
```python
from PySide6.QtWidgets import QMenuBar, QAction
from PySide6.QtGui import QKeySequence
from PySide6.QtCore import Qt

# In MainWindow.__init__():
if sys.platform == 'darwin':  # Only on macOS
    self._setup_native_menus()

def _setup_native_menus(self):
    """Setup native macOS menu structure."""
    menubar = self.menuBar()

    # App menu (automatically created on macOS but can be customized)
    app_menu = menubar.addMenu(self.windowTitle())
    about_action = QAction("About WimPyAmp", self)
    about_action.triggered.connect(self._show_about_dialog)
    app_menu.addAction(about_action)

    app_menu.addSeparator()

    prefs_action = QAction("Preferences...", self)
    prefs_action.setShortcut(QKeySequence.StandardKey.Zoom)  # PySide6 equivalent
    prefs_action.triggered.connect(self._show_preferences)
    app_menu.addAction(prefs_action)

    app_menu.addSeparator()

    quit_action = QAction("Quit WimPyAmp", self)
    quit_action.setShortcut(QKeySequence.StandardKey.Quit)  # PySide6 equivalent
    quit_action.triggered.connect(self._initiate_shutdown)
    app_menu.addAction(quit_action)

```

### 2.3 Menu Handler Integration
- All quit menu items (from App menu) shall trigger the same centralized shutdown method
- The quit handler shall be the same method used for cmd+Q and other quit signals

## 3. Predictable Quit Flow

### 3.1 Centralized Quit Handler
The application shall implement a single, reliable quit handler that ensures consistent behavior regardless of how the quit was initiated:

```python
def _initiate_shutdown(self):
    """Single point of entry for all quit operations."""
    # Prevent multiple shutdown attempts
    if getattr(self, '_shutdown_in_progress', False):
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
    for window in getattr(self, '_tracked_windows', []):
        if window and window.isVisible():
            window.close()
    
    # 2. Stop all timers
    if hasattr(self, 'playback_timer'):
        self.playback_timer.stop()
    if hasattr(self, 'track_completion_timer'):
        self.track_completion_timer.stop()
    if hasattr(self, 'visualization_timer'):
        self.visualization_timer.stop()

    # 3. Stop audio engine
    if hasattr(self, 'audio_engine'):
        self.audio_engine.stop()

    # 4. Save current window visibility states to preferences
    self._save_window_visibility_states()

    # 5. Save main window position
    self.preferences.set_main_window_position(self.x(), self.y())
```

### 3.2 Centralized Window Visibility Management
All window visibility state changes are managed by the main window:

```python
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

# Similar methods for equalizer and album art windows
```

### 3.3 Child Window Close Events
Child windows delegate visibility state management to the main window:

```python
# In each child window (PlaylistWindow, EqualizerWindow, AlbumArtWindow):
def closeEvent(self, event):
    """Handle close events by delegating to main window for state management."""
    # Only update main window's state if not in global shutdown
    if (not getattr(self.main_window, '_is_shutting_down', False) and
        hasattr(self.main_window, 'ui_state')):
        
        # Delegate visibility state update to main window
        self._delegate_visibility_update_to_main_window()

    # Accept the close event to actually close the window
    event.accept()

def _delegate_visibility_update_to_main_window(self):
    """Child window calls this to inform main window that it was closed."""
    # This calls methods in the main window to update visibility state
    # For example: self.main_window.on_playlist_window_closed() 
    # (implementation depends on window type)
```

### 3.4 Shutdown Order
The shutdown sequence shall follow this predictable order:
1. Main window receives quit signal
2. Main window sets shutdown flag and closes all tracked child windows
3. Main window stops timers and audio engine
4. Main window saves preferences and window states
5. Main window closes
6. QApplication terminates when all windows are closed

## 4. Window Visibility State Preservation

### 4.1 Centralized State Tracking
All visibility state is tracked in the main window's UI state:

```python
# In MainWindow UI state:
class UIState:
    def __init__(self):
        # ... other states ...
        self.playlist_button_on = False  # Whether playlist window is visible
        self.eq_button_on = False        # Whether equalizer window is visible
        self.album_art_visible = False   # Whether album art window is visible
```

### 4.2 Centralized State Persistence
Window visibility states are saved from the main window's UI state:

```python
def _save_window_visibility_states(self):
    """Save all window visibility states from main UI state during shutdown."""
    # Save all visibility states from the central UI state
    self.preferences.set_eq_window_visibility(self.ui_state.eq_button_on)
    # Add other window visibility states as needed
    # self.preferences.set_playlist_window_visibility(self.ui_state.playlist_button_on)
    # self.preferences.set_album_art_visibility(self.ui_state.album_art_visible)

def _update_window_visibility_preferences(self):
    """Update window visibility preferences (only when not shutting down)."""
    # Only update if not in shutdown to prevent conflicts during quit
    if not getattr(self, '_is_shutting_down', False):
        self.preferences.set_eq_window_visibility(self.ui_state.eq_button_on)
        # Add other window visibility updates as needed
```

### 4.3 State Restoration
When loading preferences at startup, window visibility states are applied by the main window:

```python
def _initialize_window_visibility_states(self):
    """Initialize window visibility states from preferences."""
    # Load EQ window visibility from preferences
    eq_visibility = self.preferences.get_eq_window_visibility()
    if eq_visibility is not None:
        self.ui_state.eq_button_on = eq_visibility
        self.equalizer_window.setVisible(eq_visibility)
        # Position and dock according to specification
        if eq_visibility:
            eq_pos_x = self.x()
            eq_pos_y = self.y() + self.height()
            self.equalizer_window.move(eq_pos_x, eq_pos_y)
            self.equalizer_window.is_docked = True
    else:
        # Default state - EQ window is hidden
        self.ui_state.eq_button_on = False
        self.equalizer_window.setVisible(False)
```

### 4.4 Single Source of Truth
Window visibility states shall be managed with a single source of truth:
- All visibility state changes go through the main window
- Child windows only show/hide themselves based on main window commands
- During shutdown, current visibility states are captured and saved from main window state
- This eliminates race conditions and state inconsistencies

## 5. Implementation Verification

### 5.1 Correctness Criteria
- All quit methods (cmd+Q, menu quit, closing main window) result in the same predictable shutdown sequence
- No data loss during shutdown
- Window visibility states are preserved correctly
- Child windows are properly cleaned up
- Application terminates cleanly without hanging processes
- Single source of truth for all visibility states prevents race conditions

### 5.2 Testing Requirements
- Verify cmd+Q triggers centralized quit handler
- Verify menu quit triggers centralized quit handler
- Verify closing main window triggers proper child window cleanup
- Verify window visibility states are preserved across application restarts
- Verify no race conditions during multi-window operations
- Verify child window close events properly update main window state