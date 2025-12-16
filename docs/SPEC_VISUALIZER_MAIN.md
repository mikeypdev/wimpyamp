# Winamp Classic Visualizer Specification

## 1. Overview

This specification defines the implementation of the audio visualization system for the WimPyAmp music player, focusing on compatibility with Winamp Classic skins and their `viscolor.txt` color configuration files.

### 1.1 Reference

A reference implementation is available in the Webamp project at: [visualizer reference](https://raw.githubusercontent.com/captbaritone/webamp/refs/heads/master/packages/webamp/js/components/VisPainter.ts)

## 2. Visualization Area

The visualization area in Winamp Classic's main window is precisely defined:

- **Position**: (24, 43) - relative to main window top-left
- **Size**: 76px wide × 16px high
- **Total Area**: 1,216 pixels
- **Spec Reference**: From the Classic Skins specification

## 3. viscolor.txt Format

The `viscolor.txt` file is a critical component of Winamp Classic skins that defines visualization colors. The file contains exactly 24 lines, each representing an RGB color value in comma-separated format.

### 3.1 File Structure
```
R1,G1,B1
R2,G2,B2
R3,G3,B3
...
R24,G24,B24
```

Each R, G, B value ranges from 0-255 representing the red, green, and blue components respectively.

### 3.2 Color Assignment

The 24 colors are assigned as follows according to Classic Skins Spec and Webamp implementation:

- **Color #0** (Line 1): Background color for the visualization area
- **Color #1** (Line 2): Dots in the background of the visualization area
- **Colors #2-17** (Lines 3-18): Spectrum analyzer colors. Row 2 is the peak value, the highest part of the graphical bar that is visible. This means that when you hit a high frequency, the top of the bar becomes the color specified. As you move from row to row, you can color each level of the frequency spectrum a different color to signify the peak levels of the frequencies in the file you are playing at that moment.
- **Colors #18-22** (Lines 19-23): Oscilloscope waveform colors for different intensity levels.  They function in the same fashion as the Spectrum Analyzer. Row 18 controls the colors that is displayed at the troughs and the row 22 is the color that is displayed at the crest. Each row between 18 and 22 sets a different level of the whole wave.
- **Color #23** (Line 24): Peak color for spectrum analyzer (used for the last peak value)
- **Color #24** (Line 25): Reserved/unused or additional effect colors

## 4. Visualization Modes

Winamp Classic supports three visualization states:

### 4.1 Spectrum Analyzer Mode (Bar)

The spectrum analyzer visualizes audio frequency data as a series of vertical bars.

- **Display Type**: Frequency domain visualization.
- **Bar Count**: 19 vertical frequency bands.
- **Bar and Gutter Size**: The 76px wide visualization area is filled by: a 1px gutter on the far left, followed by 19 bars of 3px width, with a 1px gutter separating each bar. This creates a uniform, pixel-perfect layout. `(1px + 19*3px + 18*1px = 76px)`.
- **Bar Structure**: Each vertical bar is 16 pixels high and represents a specific frequency range. The bar's height is drawn as a stack of 1-pixel-high, solid-colored segments, giving it a blocky, non-gradient appearance.
- **Amplitude Mapping**: The number of visible segments (from 0 to 16) in a bar is proportional to the volume (amplitude) of its corresponding frequency range. The mapping should be logarithmic to ensure that quiet sounds are visible (1-2 pixels high) and that only very loud audio will cause the bar to reach its maximum height.
- **Color Mapping**: The colors of the 16 segments are mapped from `viscolor.txt`.
  - **Colors #2-17** (Lines 3-18) define the colors for the 16 vertical levels of the bars.
  - Color #17 is at the bottom (level 1), and color #2 is at the top (level 16).
- **Peak Indicators**:
  - Each of the 19 bands has a 1-pixel-tall "peak indicator" that marks the highest amplitude the band has recently reached.
  - This indicator uses **Color #23** (Line 24) from `viscolor.txt`.
  - The peak indicator has a slow "falloff," meaning it remains visible at its last position for a short period (e.g., 1-2 seconds) before dropping to the current bar height if the current height is lower.
- **Falloff Effect**: To create a smooth visual effect, the main bars also have a falloff behavior. When the audio amplitude decreases, the bar height does not drop instantly. Instead, it falls at a controlled rate, which is faster than the peak indicator's falloff. This creates a lively and responsive feel.
- **Frequency Range**: The 19 bands cover a typical audio frequency spectrum (e.g., 20Hz to 20kHz) on a logarithmic scale, which provides better visual representation of how humans perceive sound.
- **Background**: The area behind the bars uses **Color #0** (Line 1) for the background and **Color #1** (Line 2) for the optional grid of dots.

### 4.2 Oscilloscope Mode

The oscilloscope visualizes the raw audio waveform in the time domain, showing its amplitude over a short period.

- **Display Type**: Time-domain visualization.
- **Data Source**: The waveform is a mono mixdown of the audio channels. The data represents the instantaneous amplitude of the audio signal, where a value of 128 is the center-line (silence), 0 is the trough, and 255 is the crest.
- **Drawing Style**: The waveform is rendered as a continuous, solid line, several pixels thick, that moves vertically with the audio's amplitude.
- **Color Mapping**: The color of the line changes based on its vertical amplitude, using **Colors #18-22** from `viscolor.txt`.
  - Color #18 (Line 19) is used for the lowest points (troughs) of the wave.
  - Color #22 (Line 23) is used for the highest points (crests).
  - Colors #19-21 are used for the intermediate amplitudes, creating a gradient effect on the waveform's line.
- **Vertical Centering**: The waveform is centered vertically within the 16-pixel high visualization area. Silence is represented by a line at the vertical midpoint.
- **Resolution**: The full 76-pixel width of the visualization area is used to display the time slice of the waveform.

### 4.3 Off State

- **Display Type**: Visualization is disabled
- **Appearance**: Visualization area shows only the background with color #0, and optionally background dots in color #1
- **Usage**: When visualization is turned off in Winamp Classic, the area remains blank except for the defined background

## 5. Implementation Requirements

### 5.1 Color Loading & Management

- Parse `viscolor.txt` from the skin package during skin loading process
- Store the 24 RGB values as accessible color objects (e.g., QColor in PyQt)
- Handle missing `viscolor.txt` gracefully with default color scheme (blue-to-red gradient)
- Validate RGB values are within 0-255 range
- Provide fallback colors if file format is invalid
- Properly map colors as follows:
  - Color #0 (line 1): Background color for visualization area
  - Color #1 (line 2): Dots in the background of the visualization area
  - Colors #2-17 (lines 3-18): Spectrum analyzer colors as described in Color Assigments
  - Colors #18-22 (lines 19-23): Oscilloscope waveform colors for different intensity levels as described in Color Assignments
  - Color #23 (line 24): Peak color for spectrum analyzer (peak indicators)
  - Color #24 (line 25): Reserved/unused or additional effect colors

### 5.4 Visualization Rendering Requirements

- Render visualizations at a rate that represents the currently playing audio, within performance contraints
- Apply proper scaling to fit visualization data within the 76×16 pixel area
- Use color palette from viscolor.txt to colorize visualization elements
- Support visualization mode switching with appropriate rendering algorithms
- Optimize rendering performance to maintain responsive UI
- Respect current skin's transparency and palette handling rules

### 5.5 Integration Points

The visualizer must integrate with the existing architecture:

- **Skin Parser**: Load and parse `viscolor.txt` during skin loading
- **Audio Engine**: Receive playback state information for simulation
- **Renderer**: Implement visualization rendering in the main window renderer
- **UI Controls**: Support mode switching if UI allows

## 6. Default Behavior

### 6.1 Missing viscolor.txt
If no `viscolor.txt` file is present in the skin package, the system should default to:
- Standard color scheme with appropriate defaults for each purpose:
  - Color #0: Black (background)
  - Color #1: Dark gray dots (background dots)
  - Colors #2-17: Blue-to-red gradient for spectrum analyzer (from top to bottom of bars)
  - Colors #18-22: Bright colors for oscilloscope waveform (typically white, green, blue, etc.)
  - Color #23: Bright color for peak indicators (typically white or bright yellow)
  - Color #24: Additional bright color for effects

### 6.2 Default Visualization Types
- Spectrum Analyzer as default mode
- Smooth, responsive rendering that matches Winamp Classic's visual style
- Proper handling of both music and silence audio input

## 7. Technical Implementation Strategy

This section outlines the recommended architecture and technical approach for implementing the visualization system.

### 7.1 Architecture: A Mode-Aware Producer-Consumer Model

To ensure a responsive UI and efficient CPU usage, the system must use a multi-threaded, mode-aware producer-consumer pattern.

-   **UI-Driven State:** The main UI thread is the source of truth for the current visualization mode (`SPECTRUM`, `OSCILLOSCOPE`, or `OFF`).
-   **Audio Thread (Producer):** A dedicated background thread handles all audio processing. Crucially, it will only perform the work necessary for the *currently active mode*, which it learns about from the main thread. This prevents wasting CPU cycles on unused calculations (e.g., performing an FFT when the oscilloscope is active).
-   **Main/UI Thread (Consumer):** The main application thread runs the animation loop, tells the audio thread which mode is active, consumes the corresponding data from a shared queue, and renders the output.
-   **Thread-Safe Communication:** A **thread-safe queue** will pass audio data from the producer to the consumer. A separate mechanism (e.g., a shared state variable with a `threading.Lock` or another queue) will be used to communicate the current visualization mode from the consumer to the producer.

### 7.2 Audio Thread Implementation (`src/audio/audio_engine.py`)

1.  **Listen for Mode Changes:** The thread should be able to check the current visualization mode requested by the UI thread.
2.  **Conditional Processing:** In its main loop, the thread will:
    -   If the mode is `SPECTRUM`, it performs the FFT, groups the data into 19 bands, and places the resulting array in the data queue.
    -   If the mode is `OSCILLOSCOPE`, it simply places the raw time-domain data array in the data queue.
    -   If the mode is `OFF`, it does no audio processing and produces no data.
3.  **Data Publishing:** The thread places the data required for the active mode into the shared queue. The data format will differ depending on the mode.

### 7.3 Main UI Thread Implementation (`src/core/renderer.py`, `src/ui/main_window.py`)

1.  **Animation Loop:** A fixed-rate `QTimer` (20-30 FPS) drives the rendering, ensuring smooth animations regardless of the mode.
2.  **State Management:**
    -   The UI maintains the `current_vis_mode` state.
    -   When the mode changes (see Section 10), the UI communicates the new mode to the audio thread.
    -   The renderer maintains the state for the spectrum analyzer (19 bar/peak heights).
3.  **Rendering Logic:** On each timer tick, the renderer will:
    -   Consume data from the queue in a non-blocking way.
    -   Based on `current_vis_mode`, call the appropriate rendering function (`render_spectrum`, `render_oscilloscope`, or `render_off`).
    -   The `render_spectrum` function will also apply the falloff animation logic before drawing.

### 7.4 Reference Implementation Parameters
(This section remains the same as before)

#### Audio Processing
...

#### Animation Physics
...

### 7.5 Oscilloscope Implementation Details
(This section remains the same as before)

#### Audio Processing
...

#### Rendering Technique
...

## 8. Testing Requirements

- Test with various skin packages containing different viscolor.txt files
- Verify proper color mapping in both visualization modes
- Test with different audio formats and simulate different file characteristics
- Verify performance at 20-30 FPS during normal operation
- Test handling of malformed or invalid viscolor.txt files
- Test default color fallback functionality
- Test the mode switching functionality and ensure the audio thread correctly starts/stops processing.

## 9. Compatibility Notes

- Maintain pixel-perfect compatibility with Winamp Classic visualization appearance
- Respect the 76×16 pixel area constraint exactly as specified
- Support the same color indexing and mapping behavior as Winamp Classic
- Ensure visualization modes behave similarly to original Winamp implementation

## 10. User Interaction and State Model

### 10.1 Control Element
- The visualization mode is controlled by the "V" button located in the main window's "clutterbar".
- This button is the bottom-most button in the vertical stack of five buttons on the left side of the main window.

### 10.2 State Machine
- The visualizer has three distinct states: `SPECTRUM`, `OSCILLOSCOPE`, and `OFF`.
- **Initial State:** The application will launch with the visualizer in the `SPECTRUM` state.
- **Transitions:** Each press of the "V" button cycles through the states in the following fixed order:
  1. If the current state is `SPECTRUM`, the next state becomes `OSCILLOSCOPE`.
  2. If the current state is `OSCILLOSCOPE`, the next state becomes `OFF`.
  3. If the current state is `OFF`, the next state becomes `SPECTRUM`.

### 10.3 System Behavior on State Change
- When the state changes, the main UI thread will immediately signal the new mode to both the `Renderer` and the `Audio Engine`.
- The **Renderer** will switch its drawing algorithm for the next frame to match the new mode.
- The **Audio Engine** will adjust its processing loop to only generate the data required for the new mode, saving CPU cycles.

