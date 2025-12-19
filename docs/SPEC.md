# WimPyAmp - Specification

## Overview
A cross-platform desktop application that renders Winamp Classic skins with pixel-perfect accuracy, including all UI elements, interactions, and visual states.

## Core Requirements

### 1. Skin Format Support
- **Primary**: Winamp Classic skins (.wsz format - ZIP archives containing BMP files)
- **Secondary**: Modern skin formats (future consideration)
- **Fallback**: Default skin included in project

### 2. Required UI Elements

#### Main Window (275x116px base)
- **Background**: Main window background from `main.bmp`
- **Titlebar**: Window controls (minimize, shade, close) from `titlebar.bmp`
- **Transport Controls**: Previous, Play, Pause, Stop, Next, Eject from `cbuttons.bmp`
- **Status Indicators**: Play/Pause/Stop indicators from `playpaus.bmp`
- **Time Display**: Minutes/seconds using `numbers.bmp` or `nums_ex.bmp` digits
- **Song Title**: Scrolling text display using `text.bmp` glyphs showing track metadata
- **Visualization Area**: Placeholder for spectrum analyzer/oscilloscope
- **Audio Info**: Bitrate and sample rate display from loaded track metadata
- **Volume & Balance Controls**: Sliders with 28-step frames from `volume.bmp`
- **Position Bar**: Seek bar with draggable thumb from `posbar.bmp`
- **Toggle Buttons**: Shuffle, Repeat, EQ, Playlist from `shufrep.bmp` (UI present, functionality for playlist/EQ planned)
- **Stereo/Mono Indicators**: Audio channel status from `monoster.bmp` (not currently implemented)

#### Additional Windows (Phase 2)
- **Equalizer Window**: 10-band equalizer with presets (UI implemented, functionality planned)
- **Playlist Editor**: Song list management (UI implemented, functionality planned)
- **Mini-Browser**: Web integration (deprecated but included for completeness) (not currently implemented)

### 3. Technical Specifications

#### Image Processing
- **Format Support**: BMP (1/4/8/24-bit), PNG fallback
- **Palette Handling**: Preserve indexed color palettes
- **Transparency**: Key color detection (#FF00FF, top-left pixel, or skin.ini specified)
- **Color Depth**: Convert to 32-bit RGBA for composition

#### Sprite Extraction
- **Exact Coordinates**: Use pixel-perfect coordinates from specification
- **Sprite States**: Normal and pressed variants for all interactive elements
- **Overlap Handling**: Proper z-order for overlapping elements (shuffle/repeat, mono/stereo)

#### Rendering Pipeline
1. Load and parse skin archive
2. Extract and cache sprites with transparency
3. Composite layers in correct order
4. Handle high-DPI displays (device pixel ratio scaling)
5. Update on state changes (button presses, slider movements)

### 4. Interaction Model

#### Button States
- **Normal**: Default appearance
- **Pressed**: Visual feedback on mouse down
- **Hover**: Optional visual feedback on mouse over
- **Active**: Toggle state for shuffle/repeat/EQ/playlist

#### Slider Controls
- **Volume**: 0-100%, 28 visual steps
- **Balance**: Left-Center-Right, 28 visual steps
- **Position**: 0-100% of track duration, draggable thumb

#### Text Rendering
- **Fixed-width fonts**: 5x6 pixel characters from `text.bmp`
- **Numeric display**: 9x13 pixel digits from `numbers.bmp` or `nums_ex.bmp`
- **Scrolling**: Smooth text scrolling for long song titles

### 5. Platform Recommendations

#### Option A: Python + PyQt/PySide
**Pros:**
- Rapid development with extensive GUI widgets
- Excellent image processing (QImage, QPixmap)
- Cross-platform deployment
- Rich documentation and community

**Cons:**
- Larger runtime footprint
- GIL limitations for heavy processing

**Tech Stack:**
```
Python 3.13+ with venv (virtual environment)
PyQt5/PySide
Pillow (for advanced image processing)
zipfile (for .wsz extraction)
```

## 6. Recommended Implementation Approach

**Phase 1: Core Renderer (Python + PyQt)**
- Start with Python for rapid prototyping
- Implement basic sprite loading and rendering
- Get main window displaying correctly
- Add basic interaction handling

**Phase 2: Full Feature Set**
- Complete all UI elements
- Implement proper state management
- Add keyboard shortcuts
- Support for multiple skins

**Phase 3: Advanced Features**
- Equalizer window
- Playlist editor
- Visualization effects
- Skin customization tools

**Phase 4: Optimization & Polish**
- Performance optimizations
- High-DPI support
- Accessibility features
- Cross-platform testing

### 7. File Structure
```
winamp-skin-viewer/
├── src/
│   ├── core/
│   │   ├── skin_parser.py      # .wsz extraction and parsing
│   │   ├── sprite_manager.py   # Sprite caching and management
│   │   └── renderer.py         # Main rendering engine
│   ├── ui/
│   │   ├── main_window.py      # Main window implementation
│   │   ├── controls.py         # Custom control widgets
│   │   └── visualization.py    # Audio visualization
│   └── utils/
│       ├── color.py            # Color/palette utilities
│       └── geometry.py         # Coordinate calculations
├── resources/
│   ├── default_skin/           # Fallback skin
│   └── fonts/                 # Additional fonts if needed
├── tests/
│   ├── test_skin_parser.py
│   ├── test_renderer.py
│   └── test_interactions.py
├── docs/
│   ├── skin_format.md          # Skin format documentation
│   └── api_reference.md        # API documentation
└── requirements.txt
```

### 8. Success Criteria

#### Minimum Viable Product
- [ ] Load and display basic Winamp Classic skin
- [ ] All main window elements visible and positioned correctly
- [ ] Basic button interactions work
- [ ] Volume and position sliders functional
- [ ] Time display updates correctly

#### Complete Implementation
- [x] All UI elements implemented and interactive
- [x] Multiple skin support with file browser
- [x] Basic audio playback controls (play, pause, stop)
- [x] Volume and balance controls with pygame backend
- [x] Track loading via file browser (eject button)
- [x] Position seeking functionality
- [x] Metadata display for loaded tracks
- [ ] Equalizer window functionality (UI implemented, functionality planned)
- [ ] Playlist window functionality (UI implemented, functionality planned)
- [ ] Keyboard shortcuts and hotkeys
- [ ] High-DPI display support
- [ ] Cross-platform compatibility (Windows, macOS, Linux)

#### Advanced Features
- [ ] Audio visualization effects
- [ ] Advanced playlist management
- [ ] Equalizer functionality
- [ ] Skin creation/editing tools
- [ ] Plugin system for extensions
- [ ] Modern skin format support
- [ ] Mobile version consideration

### 9. Development Timeline

**Sprint 1 (2 weeks):** Core parsing and basic rendering
**Sprint 2 (2 weeks):** Main window completion and interactions
**Sprint 3 (2 weeks):** Additional windows and advanced features
**Sprint 4 (1 week):** Polish, testing, and optimization

### 10. Next Steps

1. **Choose Platform**: Evaluate team skills and project requirements
2. **Setup Development Environment**: Install required tools and libraries
3. **Create Basic Parser**: Implement .wsz file extraction
4. **Implement Renderer**: Get first sprite displaying on screen
5. **Iterate**: Build features incrementally with regular testing

---

*This specification is based on Winamp Classic Skin Specification v1.2.1 and includes all necessary technical details for implementation. See the `docs/` folder for complete technical specifications:*
- *`Winamp Classic Skin Parsing & Rendering Spec.rtf` - Detailed implementation guide*
- *`Classic Skins Spec.pdf` - Authoritative skin format specification*
