# User Preferences Specification for WimPyAmp

## Overview
This document specifies the user preferences system for WimPyAmp that will persist user settings between application sessions.

## Storage Location
User preferences will be stored in the standard system location for application data, which is the same location used for temporary skin extraction. This location is determined using `appdirs.user_data_dir('WimPyAmp')` which resolves to:
- **Windows:** `%LOCALAPPDATA%\WimPyAmp\`
- **macOS:** `~/Library/Application Support/WimPyAmp/`
- **Linux:** `~/.local/share/WimPyAmp/` or `$XDG_DATA_HOME/WimPyAmp/`

Preferences file: `user_prefs.json`

## Loading Process
When the application starts:
1. Check for the existence of the user preferences file
2. If the file exists, load and parse the JSON data
3. Apply the loaded preferences to initialize the application state
4. If the file doesn't exist or is corrupted, use default values

## Saving Process
* Preferences are automatically saved when significant UI state changes occur (e.g., window positions, skin selection, playlist settings change)
* There are no default settings, so preference are only written when they have changed

## Preference Categories

### 1. Window Layout and Visibility Status
- Main window position (x, y coordinates)
- Playlist window visibility (true/false)
- Playlist window position (x, y coordinates)
- Playlist window size (width, height)
- Equalizer window visibility (true/false)
- Equalizer window position (x, y coordinates)
- Album art window visibility (true/false)
- Album art window position (x, y coordinates)
- Album art window size (width, height)
- Only the playlist and album art windows can be resized, so do not include size entries for the main or EQ windows
- Docking states are calculated automatically at runtime based on window proximity and are not stored in preferences

### 2. Currently Loaded Skin
- Path or identifier of the currently selected skin (not including the default skin, which is hard-coded and possibly in the app bundle. do not add a prefs entry if the current skin is the default skin)
- Fallback to default skin if specified skin is not found on subsequent launches, or if the skin is invalid, or if there is no skin entry in the prefs
- If the user reverts to the default skin, remove the loaded skin entry in the prefs file

### 3. Playlist Settings (from MISC OPTS option popup)
- Playlist display options (which metadata fields to show):
  - Track Filename (always shown if no other options selected)
  - Track Number
  - Song Name
  - Artist
  - Album Artist
  - Album Name

## Data Model Example

```json
{
  "version": "1.0",
  "window_layout": {
    "main": {
      "x": 100,
      "y": 100
    },
    "playlist": {
      "visible": true,
      "x": 100,
      "y": 216,
      "width": 275,
      "height": 116
    },
    "equalizer": {
      "visible": false,
      "x": 400,
      "y": 100
    },
    "album_art": {
      "visible": false,
      "x": 800,
      "y": 100,
      "width": 275,
      "height": 116
    }
  },
  "current_skin": "/path/to/current/skin.wsz",
  "playlist_settings": {
    "display_options": {
      "track_filename": true,
      "track_number": false,
      "song_name": false,
      "artist": false,
      "album_artist": false,
      "album_name": false
    }
  }
}
```

## Implementation Considerations

1. **Backward Compatibility**: Include a version field to handle future schema changes
2. **Error Handling**: If preferences file is corrupted, log the error and use defaults
3. **File Permissions**: Ensure proper file permissions for the preferences directory
4. **Atomic Write Operations**: Use temporary files and rename operations to avoid corruption during writes
5. **Validation**: Validate preference values on load to ensure they are within expected ranges
6. **Performance**: Avoid excessive disk I/O by debouncing save operations for frequently changing values

## Migration Strategy
If the application is upgraded and the preferences schema changes:
1. Check the version field in the existing preferences file
2. Implement migration functions for each version transition
3. Create backups of the old preferences file before applying migrations
4. Fall back to defaults if migration fails

## Security Considerations
- Preferences file should only be readable/writable by the user
- No sensitive information (passwords, personal data) should be stored in preferences
- Validate file paths to prevent directory traversal attacks
