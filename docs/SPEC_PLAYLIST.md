# WimPyAmp Playlist Window Functionality Specification (`SPEC_PLAYLIST.md`)

This document outlines the functional specification for the Winamp Classic Playlist Editor window. It is derived from `playlist_window_spec.json` and the "Winamp Skinning Tutorial 1.5.0".

## 1. Main Window Structure

The Playlist window is a resizable window composed of four main sections: a Title Bar, the Playlist View, a vertical Scrollbar, and a Bottom Control Bar.

### 1.1. Title Bar

- **Function:** Displays the window title ("Winamp Playlist") and provides standard window controls.
- **States:**
    - **Active:** When the playlist window has focus. Uses `PLEDIT_TOP_*_ACTIVE` sprites.
    - **Inactive:** When the window does not have focus. Uses `PLEDIT_TOP_*_INACTIVE` sprites.
- **Controls:**
    - **Close Button:**
        - **Function:** Closes the playlist window.
        - **States:** `Normal`, `Pressed`.
    - **Windowshade/Maximize Button:**
        - **Function:** Toggles the window between its normal state and "Windowshade" mode. In windowshade mode, only a small title bar is visible.
        - **States:** `Normal`, `Pressed`. There is a known bug in classic Winamp where pressing this button can cause it to shift one pixel to the right.

### 1.2. Playlist View

- **Function:** Displays the list of tracks. The background is a solid color defined in `pledit.txt`.
- **Features:**
    - **Track Listing:** Each row displays the track number, title, and length (e.g., `1. Artist - Title (3:45)`).
    - **Selection:** Supports standard listbox selection:
        - **Single-click:** Selects a single track.
        - **Ctrl+click:** Toggles selection of a single track.
        - **Shift+click:** Selects a range of tracks.
    - **Scrolling:** The view is vertically scrollable.

### 1.3. Vertical Scrollbar

- **Function:** Navigates the Playlist View vertically.
- **Components & Behavior:**
    - **Up/Down Arrow Buttons:** Scrolls the list up or down by a single row.
    - **Scroll Thumb:** Can be dragged to scroll the list. Its vertical position corresponds to the visible portion of the playlist.
    - **Scroll Groove (Track):** The area the thumb moves in. Clicking in the groove above or below the thumb scrolls the list by one page.

### 1.4. Bottom Control Bar

- **Function:** Houses the primary controls for managing the playlist. It also contains a display for playlist status and a resize handle.
- **Components:**
    - **Status Display:** A small area that displays the total number of tracks and the total playlist duration.
    - **Resize Handle:** A triangular graphic in the bottom-right corner that can be dragged to resize the entire window.

## 2. Control Buttons

The five main buttons on the bottom bar (`ADD`, `REM`, `SEL`, `MISC`, `LIST`) function as triggers for popup menus that contain the actual action buttons. Pressing a main button reveals a secondary set of buttons; it does not perform an action itself.

### 2.1. `ADD` Button

- **Function:** Reveals options for adding tracks to the playlist.
- **Popup Buttons:**
    - **`ADD FILE`:** Opens a system file dialog to select and add one or more individual media files.
    - **`ADD DIR`:** Opens a system directory dialog to add all media files within a selected folder and its subfolders.
    - **`ADD URL`:** Opens a dialog box prompting the user to enter a URL for streaming media.

### 2.2. `REM` (Remove) Button

- **Function:** Reveals options for removing tracks from the playlist.
- **Popup Buttons:**
    - **`REM SEL` (Remove Selected):** Removes the currently highlighted track(s) from the playlist.
    - **`CROP`:** Removes all tracks *except* for the currently highlighted one(s).
    - **`REM ALL` (Remove All):** Clears the entire playlist.
    - **`REM DUP` (Remove Duplicates):** Scans the playlist and removes duplicate entries.
    - **`REM DEAD` (Remove Dead Files):** Scans the playlist and removes entries that point to non-existent files.

### 2.3. `SEL` (Select) Button

- **Function:** Reveals options for selecting tracks.
- **Popup Buttons:**
    - **`SEL ALL` (Select All):** Selects all tracks in the playlist.
    - **`INV SEL` (Invert Selection):** Deselects all currently selected tracks and selects all unselected tracks.
    - **`SEL NONE` (Select None):** Deselects all tracks.

### 2.4. `MISC` (Miscellaneous) Button

- **Function:** Reveals miscellaneous playlist management options.
- **Popup Buttons:**
    - **`SORT LIST`:** Opens a dialog or submenu with options to sort the playlist (e.g., by Title, Filename, Path, Randomly).
    - **`FILE INFO`:** Opens the "File Info" dialog for the selected track, displaying its metadata.
    - **`MISC OPTS` (Misc Options):** Opens a preferences dialog for configuring playlist display options, including which metadata fields to show for each song:
        - **Track Filename:** Displays the filename of each track (on by default).
        - **Track Number:** Displays the sequential track number.
        - **Song Name:** Displays the name of the song (title).
        - **Artist:** Displays the artist name.
        - **Album Artist:** Displays the album artist name.
        - **Album Name:** Displays the album name.
        - **Display Behavior:**
            - If no options are checked, always display the filename by default.
            - If more than one option is checked, display " - " between each selected metadata item in the playlist view.

### 2.5. `LIST` Button

- **Function:** Reveals options for managing playlist files.
- **Popup Buttons:**
    - **`NEW LIST`:** Clears the current playlist and starts a new, empty one.
    - **`LOAD LIST`:** Opens a system file dialog to load a saved playlist file (e.g., `.m3u`, `.pls`).
    - **`SAVE LIST`:** Opens a system file dialog to save the current playlist to a file.
