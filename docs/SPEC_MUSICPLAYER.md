# WimPyAmp Music Player Specification

## Overview
This specification defines the complete music playback functionality for the WimPyAmp application, based on the original Winamp Classic design patterns with modern extensibility considerations. The application should provide pixel-perfect rendering of Winamp skins while implementing full audio playback capabilities.

## Core Music Playback Features

### Basic Playback Controls
- **Play**: Start playback of the current track
- **Pause**: Temporarily halt playback (toggle functionality)
- **Stop**: Halt playback and reset to beginning of track
- **Previous**: Navigate to previous track in playlist (basic implementation, advanced playlist management planned)
- **Next**: Navigate to next track in playlist (basic implementation, advanced playlist management planned)
- **Eject**: Open file browser for loading new tracks

### Playback State Indicators
- **Play/Pause/Stop Indicator**: Visual status indicators showing current playback state
- **Time Display**: Elapsed/remaining time in MM:SS format (position tracking implemented)
- **Work Indicator**: Shows when the player is actively loading/processing media
- **Visualization Area**: Placeholder for audio waveform or spectrum visualization (visualization planned for future)

### Audio Controls
- **Volume Slider**: Horizontal bar for adjusting playback volume (0-100%)
- **Balance Control**: Stereo balance control implementation (basic functionality)
- **Mono/Stereo Toggle**: Switch between mono and stereo output modes (not currently implemented)

### Playlist Management
- **Playlist Button**: Toggle visibility of playlist editor window (UI implemented, functionality planned)
- **Current Track Display**: Show current track title in main window with metadata support
- **Track Information**: Display bitrate and sample rate information from metadata
- **Shuffle Mode**: Randomize playback order toggle (not currently implemented)
- **Repeat Mode**: Loop single track or entire playlist toggle (not currently implemented)

## Equalizer Features
- **Status**: Not currently implemented, planned for future enhancement
- **10-Band Equalizer**: Individual controls for frequencies: 60Hz, 170Hz, 310Hz, 600Hz, 1KHz, 3KHz, 6KHz, 12KHz, 14KHz, 16KHz (planned)
- **Preamp Control**: Master gain adjustment (-12dB to +12dB) (planned)
- **Auto Mode**: Automatic equalization based on track characteristics (planned)
- **Presets**: Predefined equalizer settings (Classical, Rock, Jazz, etc.) (planned)
- **On/Off Toggle**: Enable/disable equalizer processing (planned)

## Audio Visualization
- **Status**: Placeholder implemented, advanced visualization planned for future enhancement
- **Real-time Spectrum Analyzer**: Frequency domain visualization (planned)
- **Waveform Display**: Time domain visualization (planned)
- **Multiple Visualization Modes**: Support for different visualization types (planned)
- **Responsive Design**: Visualization adapts to available space in skin (planned)

## File Format Support
- **Audio Formats**: MP3, WAV, OGG (formats supported by pygame mixer), with ability to expand to others
- **Playlist Formats**: Not currently implemented (planned for future)
- **Metadata Reading**: ID3 tags for MP3, with support for other formats via mutagen

## User Interface Elements

### Main Window Components
- **Title Bar**: Draggable window header with minimize/close controls
- **Transport Controls**: Play, pause, stop, previous, next, eject buttons (eject now opens file dialog)
- **Position Bar**: Seek bar for current track progress with draggable thumb
- **Text Display**: Current track title with metadata, bitrate, sample rate
  - **Track Numbering**: Song titles are preceded by their playlist position number followed by a period, such as "1." or "12."
  - **Duration Display**: Track titles are followed by the total track length in [min:sec] format, such as [2:34]
  - **Complete Format**: Full display format is: "{playlist_number}. {track_title} [{duration}]", e.g. "1. Artist - Song Title [3:45]"
  - **Text Overflow Behavior**: When the complete string exceeds available UI space, the text rotates from right to left one character at a time
  - **Rotation Continuity**: At the end of the complete string rotation, three asterisks "***" are appended before the beginning of the string reappears
  - **Rotation Cycle**: The rotation shows the complete formatted string (track number, title, duration) followed by "***" and continues the cycle seamlessly
- **Status Indicators**: Visual states for playback buttons

### Window Management
- **EQ Window**: Equalizer controls in separate floating window (UI implemented, functionality planned)
- **Playlist Editor**: Track listing and management window (UI implemented, functionality planned)
- **Mini Mode**: Compact player interface for space-constrained environments (not currently implemented)
- **Shade Mode**: Minimal UI showing only essential controls (not currently implemented)

## Technical Requirements

### Audio Engine
- **Backend**: Cross-platform audio backend using Python libraries with native performance
- **Actual Implementation**: Use `pygame.mixer` for audio playback with `mutagen` for metadata handling
- **Alternative Backend**: Sounddevice available as secondary option, with `numpy` for audio processing if needed
- **Playback Quality**: Support for common audio formats with standard quality
- **Gapless Playback**: Not currently implemented, future enhancement
- **Buffer Management**: Standard pygame buffer management
- **Sample Rate Handling**: Automatic handling by pygame mixer
- **Volume Control**: Linear volume adjustment (0.0 to 1.0) through pygame
- **Pan Control**: Basic pan control (stored as value, advanced panning requires custom processing)
- **Threading**: Use separate threads for position tracking to avoid UI blocking
- **Audio Queue Management**: Basic single track loading (playlist functionality planned for future)
- **Format Decoders**: Support formats compatible with pygame mixer (MP3, WAV, OGG)

### Equalizer Implementation
- **Status**: Not currently implemented, planned for future enhancement
- **Engine**: Planned: Use `scipy` with real-time capable filtering algorithms (biquad IIR filters)
- **Precision**: Planned: 0.1dB resolution for equalizer bands
- **Implementation**: Planned: Real-time convolution with low-latency design
- **Presets**: Planned: Store and recall equalizer settings using JSON format

### Visualization System
- **Status**: Placeholder implemented, advanced visualization planned for future enhancement
- **Processing Library**: Available: `numpy` for potential FFT calculations and waveform generation
- **Rendering**: Available: OpenGL acceleration via PyQt's OpenGL integration (implementation pending)
- **Real-time Performance**: Target: Maintain 30-60 FPS visualization updates
- **Visualization Types**: Planned: Multiple visualization algorithms (Spectrum Analyzer, Oscilloscope, VU Meter)
- **Synchronization**: Planned: Ensure visualization updates synchronized with audio playback thread

### Audio Architecture
- **Separation of Concerns**: AudioEngine class separate from UI, with clear API
- **Audio Pipeline**: File Input → pygame audio playback (advanced DSP processing planned for future)
- **Event System**: Observer pattern for position updates using callbacks
- **State Management**: Centralized state management for playback, volume, balance, and playlist states
- **Asynchronous Loading**: Basic track loading with metadata extraction
- **Caching Strategy**: Basic file path and metadata caching

### Audio Processing Algorithms
- **Resampling**: Handled by pygame mixer (basic implementation)
- **Volume Control**: Linear scaling through pygame (advanced log scaling planned)
- **Balance Algorithm**: Basic position storage (advanced balancing planned for future)
- **Equalizer Filters**: Not currently implemented
- **Real-time Processing**: Basic processing with pygame backend

### External Dependencies
- **Pygame**: Primary audio playback engine (selected due to compatibility issues with pydub on Python 3.13+)
- **Mutagen**: Metadata handling across formats
- **NumPy**: Available for advanced audio processing
- **Note on Pydub**: Originally planned for audio processing but removed due to audioop compatibility issues with Python 3.13+

### Rendering
- **Skin Compatibility**: Full support for Winamp 2.x skin format (.wsz files)
- **Performance**: Smooth rendering at 60 FPS with minimal CPU usage
- **High DPI**: Support for high-resolution displays with proper scaling
- **Transparency**: Accurate rendering of magenta-keyed transparency

### Playlist Features
- **Drag and Drop**: Add files/folders to playlist via drag and drop
- **Search/Filter**: Find tracks within large playlists
- **Sort Capabilities**: Sort by various criteria (title, artist, album, etc.)
- **Save/Load**: Persist playlists to common formats

## Extensibility Features

### Plugin Architecture
- **Input Plugins**: Support for additional audio codecs via plugins
- **Visualization Plugins**: Extend visualization capabilities with custom modules
- **DSP Plugins**: Support for Winamp-compatible DSP effects
- **Output Plugins**: Support for custom audio output methods

### API Interface
- **Remote Control**: Support for external applications to control playback
- **JSON-RPC Interface**: Programmatic control of player functionality
- **Event System**: Subscribe to playback events and state changes

### Configuration
- **Settings Persistence**: Save user preferences and window positions
- **Hotkeys**: Configurable keyboard shortcuts for common actions
- **Skin Settings**: Support for skin-specific configuration files

## Visualization System

### Waveform Features
- **Balance Support**: Visual representation of stereo balance position
- **Real-time Updates**: 60 FPS visualization updates
- **Multiple Views**: Support for different visualization types (oscilloscope, spectrum analyzer, etc.)
- **Skin Integration**: Visualizations follow skin-defined coordinates and areas

### Visualization Types
- **Spectrum Analyzer**: Frequency domain visualization with logarithmic scale
- **Waveform Display**: Time domain visualization of audio signal
- **Bar Graph**: Vertical bar representation of frequency bands
- **Scope**: Oscilloscope-style visualization of stereo channels

## Audio Processing Pipeline
- **Preprocessing**: Apply equalizer and other DSP effects
- **Volume Control**: Digital volume adjustment with proper gain staging
- **Balance Control**: Stereo balance adjustment with smooth interpolation
- **Output Processing**: Send processed audio to system audio device

## State Management
- **Playback State**: Track current play/pause/stop state
- **Volume/Balance State**: Persist audio control positions
- **Playlist State**: Track current playlist, position, and playback mode
- **Window State**: Remember window positions and visibility

## Error Handling
- **File Loading Errors**: Graceful handling of unsupported or corrupted files
- **Playback Errors**: Recover from audio backend issues
- **Skin Loading Errors**: Fallback to default skin if current skin is invalid
- **Network Errors**: Handle remote stream connection issues

## Performance Requirements
- **Startup Time**: Sub-2 second startup time on modern hardware
- **Memory Usage**: Efficient memory management for large playlists
- **CPU Usage**: Minimal CPU usage during idle playback
- **Battery Efficiency**: Optimized for laptop usage with minimal power drain

## Accessibility
- **Keyboard Navigation**: Full functionality accessible via keyboard
- **Screen Reader Support**: Compatibility with accessibility tools
- **High Contrast Mode**: Support for users with visual impairments
- **Customizable UI Timing**: Adjustable animation and update speeds

## Cross-Platform Support
- **Windows**: Full functionality on Windows 7 and later
- **macOS**: Native look and feel on macOS 10.12 and later
- **Linux**: Support for major Linux distributions with X11/Wayland
- **Consistent Behavior**: Identical functionality across all platforms