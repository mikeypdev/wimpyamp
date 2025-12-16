# Window Snapping Specification

This document defines the window snapping behavior for the WimPyAmp application.

## Overview
Window snapping (also called window docking or window alignment) is a UI feature that helps users align windows by automatically "snapping" them to each other when they come close to alignment. This specification defines the rules for when and how windows should snap to each other.

## Movement and Docking Rules
When windows are docked to each other, they follow specific movement rules:

- If a window is docked to another window, and that window is moved, the docked window will move with the other window
- If a window is not docked with any other window, it will not move position when any other window is moved

## Snapping Rules

### 1. Edge Proximity Detection
- **Horizontal edges**: Snap when the horizontal distance between any two horizontal edges (top or bottom) is ≤ 10 pixels
- **Vertical edges**: Snap when the vertical distance between any two vertical edges (left or right) is ≤ 10 pixels
- **Center alignment**: Snap when the center points of windows are within 15 pixels of each other (horizontally or vertically)

### 2. Snapping Behavior

#### 2.1 Horizontal Edge Snapping
- When any horizontal edge of Window A comes within 10 pixels of any horizontal edge of Window B, snap Window A's edge to Window B's edge
- Vertical position remains unchanged during horizontal edge snapping
- Example: If the top edge of the playlist window comes near the bottom edge of the main window, they should horizontally align (top of playlist = bottom of main)

#### 2.2 Vertical Edge Snapping  
- When any vertical edge of Window A comes within 10 pixels of any vertical edge of Window B, snap Window A's edge to Window B's edge
- Horizontal position remains unchanged during vertical edge snapping
- Example: If the left edge of the equalizer window comes near the left edge of the main window, they should vertically align (left edges aligned)

#### 2.3 Center Alignment
- When the horizontal center of Window A comes within 15 pixels of the horizontal center of Window B, snap centers horizontally
- When the vertical center of Window A comes within 15 pixels of the vertical center of Window B, snap centers vertically

### 3. Priority System
1. **Edge-to-edge alignment** (highest priority)
2. **Edge-to-center alignment** (medium priority)
3. **Center-to-center alignment** (lowest priority)

### 4. Multi-Edge Snapping
- Windows can snap simultaneously along both horizontal and vertical edges if both conditions are met
- Example: If the top edge of playlist window aligns with bottom edge of main window AND the left edges align, both alignments should persist

### 5. Distance Thresholds
- **Snapping sensitivity**: 10 pixels for edges, 15 pixels for centers
- **Unsnapping threshold**: 25 pixels (when dragging away, windows un-snap if moved more than 25 pixels from snapped position)

### 6. Reference Windows
- When the main window is moved, all docked windows move with it
- For manual dragging of child windows, the main window is always included in snapping calculations
- Additional windows may snap to each other as well (playlist to equalizer, etc.)

### 7. Visual Feedback
- When windows are about to snap (within threshold), provide visual feedback (e.g., temporary overlay lines or highlight)
- This feedback should show where the alignment will occur

### 8. Snap Persistence
- Once snapped, the alignment is maintained until the user explicitly drags the window far enough to un-snap (25+ pixels)
- Snapped windows maintain their relative positioning if the main window moves

## Example Scenarios

### Scenario 1: Bottom Docking
- User drags playlist window near bottom of main window
- When top edge of playlist window is within 10px of bottom edge of main window, snap
- Playlist window maintains left alignment with main window

### Scenario 2: Side Docking
- User drags equalizer window near left edge of main window  
- When left edge of equalizer window is within 10px of left edge of main window, snap vertically
- Equalizer window maintains top alignment with main window

### Scenario 3: Multiple Alignments
- User positions equalizer window so both left edge aligns with main window left edge AND top edge aligns with main window top edge
- Both alignments are maintained simultaneously

### Scenario 4: Unsnapping
- User drags snapped playlist window away from main window
- When moved 25+ pixels from docked position, unsnap occurs
- Window maintains new position

## Technical Implementation Notes

### Snapping Detection Algorithm
1. Calculate potential snap positions for all relevant edge combinations
2. Filter positions within threshold distance
3. Apply priority system to select best snap (or multiple snaps)
4. Apply position adjustment if snap occurs

### Performance Considerations
- Snapping detection should happen during mouse move events (high frequency)
- Algorithm should be optimized for performance
- Only calculate snaps for visible windows