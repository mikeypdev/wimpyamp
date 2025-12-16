# Album Art Specification for WimPyAmp

## Overview
This specification defines the implementation requirements for album art support in WimPyAmp, a cross-platform Winamp Classic skin renderer.

## Data Sources
Album art can be sourced from two locations, with the following precedence:

1. **Embedded metadata** (highest precedence) - Extracted from the audio file's ID3 tags or equivalent metadata
2. **Local folder images** (secondary precedence) - Located in the same directory as the audio track file
   - Filename search order (in order of preference):
     1. `folder.jpg` (highest preference)
     2. `folder.png`
     3. `cover.jpg`
     4. `cover.png`
     5. `album.jpg`
     6. `album.png`
     7. Album title with common extensions (case-insensitive match, underscores/dashes treated as spaces)
   - Supported file extensions: `.jpg`, `.jpeg`, `.png`, `.bmp`, `.gif`

## Display Mechanics
### Album Art Window
- **Trigger**: Toggled by clicking the "I" icon in the clutter bar
- **Initial Dimensions**: Square window with side length equal to the main player window's height
- **Default Position**: Docked to the right side of the main window
- **Drag Behavior**: User can drag the window to any position, following the same docking and snapping rules as EQ and playlist windows
- **Resize Behavior**: 
  - Corner resize handle in the lower-right corner
  - Resizes in square increments (maintains aspect ratio of 1:1)
  - Similar increment sizing to playlist window

## Refresh Logic
- Album art refreshes automatically when a new track begins playback
- System checks for available album art in the precedence order described above
- If album art image data is corrupt or missing, displays the default placeholder image located at `resources/default_art/default.png`
- If the default placeholder image is missing or corrupt, fills the window with black color

## Visual Requirements
- Album artwork must be displayed in a square aspect ratio regardless of the original image dimensions
- Original image proportions may be preserved through letterboxing or cropping as appropriate
- Default placeholder image dimensions should match the minimum window size requirements

## Technical Constraints
- Window must maintain square aspect ratio at all times during resizing
- Follow existing UI patterns for window management consistent with other floating windows (EQ, Playlist)
- Efficient caching of album art to avoid repeated file operations during playback
- Support for common image formats: JPEG, PNG, BMP, GIF

## Performance Considerations
- Large images (over 2MB) should be scaled down to a reasonable display size before rendering to avoid memory issues
- Implement memory-limited caching with a maximum cache size (e.g., 50MB total) and LRU (Least Recently Used) eviction policy
- Pre-size images to the display window size to avoid unnecessary processing during rendering
- Consider lazy loading for the album art window when it's hidden
- Limit the number of concurrent image loading operations to prevent UI blocking