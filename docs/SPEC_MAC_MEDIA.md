# macOS Media Integration Specification

## Overview

This document outlines the requirements and implementation plan for adding macOS system integration to WimPyAmp. The goal is to enable system-level media controls and metadata display in macOS Control Center and menu bar, similar to other native macOS music players.

## Requirements

### Core Features
- Display current track metadata (title, artist, album) in macOS Control Center and menu bar
- Show album artwork in system media controls
- Enable playback controls (play/pause, next, previous) from Control Center, menu bar, and media keys
- Show current playback position and duration in system UI
- Support seeking via system controls
- Properly handle application lifecycle (setup and cleanup)

### Technical Requirements
- Only activate on macOS systems (Darwin platform)
- Use PyObjC framework to interface with macOS Media Player framework
- Maintain compatibility with existing Windows/Linux functionality
- Graceful degradation if PyObjC is not available

## Dependencies

### Mandatory Dependencies
- `pyobjc-core` - Python to Objective-C bridge
- `pyobjc-framework-MediaPlayer` - Access to macOS Media Player APIs

### Optional Dependencies
- `pyobjc-framework-Quartz` - For Touch Bar support (if desired)

### Platform Conditionals
Dependencies should only be required on macOS platforms, with conditional installation.

## Implementation Plan

### 1. New Module: `src/utils/mac_media_integration.py`

Create a new module with the `MacMediaIntegration` class to handle all macOS-specific functionality.

```python
class MacMediaIntegration:
    def __init__(self, main_window):
        """Initialize the macOS media integration with a reference to main window"""
    
    def update_now_playing_info(self):
        """Update track metadata in system Now Playing info center"""
    
    def update_playback_state(self):
        """Update current position, duration, and playback state"""
    
    def setup_remote_commands(self):
        """Register handlers for system remote commands"""
    
    def cleanup(self):
        """Clean up resources when application closes"""
```

### 2. Integration with MainWindow

Modify `src/ui/main_window.py` to conditionally initialize and use the media integration:

```python
import platform

# In MainWindow.__init__()
self.mac_media_integration = None
if platform.system() == "Darwin":  # macOS
    try:
        from ..utils.mac_media_integration import MacMediaIntegration
        self.mac_media_integration = MacMediaIntegration(self)
    except ImportError:
        pass  # pyobjc not available

# In update methods, notify macOS integration:
def update_playback_position(self, position, duration):
    # ... existing code ...
    if hasattr(self, 'mac_media_integration') and self.mac_media_integration:
        self.mac_media_integration.update_playback_state()
```

### 3. Connection Points

The integration will use existing functionality in the AudioEngine class:

- **Metadata**: Access via `audio_engine.get_metadata()` for title, artist, album, duration
- **Album Art**: Access via `audio_engine.get_album_art()`
- **Playback State**: Access via `audio_engine.get_playback_state()` for play/pause status
- **Playback Control**: Connect to existing methods like `play()`, `pause()`, `stop()`, `next_track()`, `prev_track()`
- **Position Updates**: Use existing `playback_callback` mechanism to update system UI

### 4. Event Handling

- When a new track is loaded: Update Now Playing info with new metadata and artwork
- During playback: Periodically update playback position and state
- When playback state changes (play/pause): Update system playback state
- When system remote commands are received: Call corresponding audio engine methods
- When application closes: Clean up the media integration resources

### 5. Conditional Loading

- Use `platform.system() == "Darwin"` to detect macOS
- Make PyObjC dependencies optional and only required on macOS
- Add graceful error handling if PyObjC is not installed on macOS
- Ensure no impact on Windows/Linux functionality

## Technical Details

### Now Playing Information
- Use `MPNowPlayingInfoCenter.defaultCenter()` to update metadata
- Required metadata: Title, Artist, Album
- Optional: Artwork, Duration, Current Time

### Remote Commands
- Use `MPRemoteCommandCenter.sharedCommandCenter()` to register handlers
- Implement: Play, Pause, Next Track, Previous Track, Seek
- Map to existing audio engine methods

### Album Art Handling
- Convert image data from audio engine to proper format for system
- Handle various image formats embedded in audio files
- Fallback to default artwork if none available

## Testing Strategy

### Unit Tests
- Mock PyObjC framework for testing on non-macOS systems
- Test metadata update methods
- Test command handler registration

### Integration Tests
- Verify metadata displays correctly in Control Center
- Test playback controls work from system UI
- Test application lifecycle management

## Distribution Considerations

### PyInstaller Build
- Ensure macOS integration module is properly handled
- Include PyObjC dependencies in macOS distribution
- Update build scripts with platform-specific requirements