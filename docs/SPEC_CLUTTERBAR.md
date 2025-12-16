# Clutterbar Specification

This document outlines the specification for the Clutterbar UI element within the Winamp main window.

## Overview

The Clutterbar is a set of 5 toggle buttons providing quick access to various options and menus. The button sprites are sourced as a single composite image from `TITLEBAR.BMP` and rendered onto the main window area.

## Source Asset: `TITLEBAR.BMP`

The entire Clutterbar is treated as a single vertical strip of 8x43 pixels. Different versions of this strip are stored in `TITLEBAR.BMP` to represent the various states of the buttons.

*   **Normal State (Visible):**
    *   Coordinates: `(x: 304, y: 0)`
    *   Size: `8x43` pixels
    *   Description: This is the default appearance of the Clutterbar when all buttons are in their un-pushed, "off" state.

*   **Invisible State (Hidden):**
    *   Coordinates: `(x: 312, y: 0)`
    *   Size: `8x43` pixels
    *   Description: This sprite is used when the "Always show clutterbar" option in Winamp's display settings is unchecked. It typically appears as a blank or patterned strip.

## Rendering Logic

The Clutterbar is rendered as a single 8x43 pixel sprite. When a user clicks a button, or when a toggleable state (like 'Always on Top') is active, the application selects a different 8x43 pixel sprite from `TITLEBAR.BMP`. This new sprite shows the corresponding button in its 'pressed' or 'active' state while the others remain in their 'un-pushed' state.

## Button Definitions & Pressed States

Each button corresponds to a specific "pressed" version of the Clutterbar sprite. When a button is activated, the entire 8x43 strip is replaced with the corresponding sprite from the coordinates below.

| Letter | Function                 | Pressed State Sprite Coordinates (in `TITLEBAR.BMP`) |
| :----: | :----------------------- | :--------------------------------------------------- |
|  **O** | Options Menu             | `(x: 304, y: 44)`, size: `8x43`                       |
|  **A** | Enable Always on Top     | `(x: 312, y: 44)`, size: `8x43`                       |
|  **I** | File Info Box            | `(x: 320, y: 44)`, size: `8x43`                       |
|  **D** | Enable Double Size Mode  | `(x: 328, y: 44)`, size: `8x43`                       |
|  **V** | Visualization Menu       | `(x: 336, y: 44)`, size: `8x43`                       |

## Destination (Main Window)

The Clutterbar sprite is rendered onto the main window background (`MAIN.BMP`) at the following coordinates:

*   **Position:** `(x: 10, y: 22)`
*   **Clickable Area ("Hot Area"):** The interactive area is an 8x43 rectangle at the same position. Some specifications note this hot area can be 1 pixel larger in all directions.
