# REGION.TXT File Specification

## 1. Overview

The `REGION.TXT` file is a crucial component of Winamp skins, serving two primary purposes:

1.  **Defining Complex Window Shapes:** It allows the main window and equalizer window to have non-rectangular, "skinned" shapes by defining one or more polygons that create a mask for the window. Anything inside the polygons is visible and clickable; anything outside is transparent.
2.  **Mapping Clickable Hotspots:** It can define rectangular areas (hotspots) and map them to specific UI element names. This is used to define the boundaries of non-standard buttons or other interactive elements.

A parser must be able to handle both formats, although they are typically used for different purposes.

---

## 2. Format 1: Polygonal Window Shapes

This format uses an INI-style structure to define lists of polygons for different window states. This is primarily used to define the overall shape of the main window or the equalizer.

### 2.1. File Format

The file is parsed as an INI file with sections, keys, and values.

*   **Sections:** Define the window state, such as `[Normal]` for the standard window view or `[WindowShade]` for the compact view.
*   **Keys:**
    *   `NumPoints`: A comma-separated list of integers. Each integer specifies the number of vertices (points) for a single polygon. The number of integers in this list determines the number of polygons for that section.
    *   `PointList`: A single, long, comma-separated or space-separated list of numbers representing all `x,y` coordinates for all polygons in the section. The points for each polygon are listed sequentially.
*   **Comments:** Lines starting with a semicolon (`;`) are ignored.

### 2.2. Parsing Logic

The parsing process should follow these steps, as inspired by the reference `regionParser.ts`:

1.  Parse the file as an INI-structured text. Blank lines and lines starting with `;` should be ignored.
2.  For each section (e.g., `[Normal]`):
    a. Read the `NumPoints` and `PointList` values. If either is missing, skip the section.
    b. Split the `NumPoints` string by commas to get an array of point counts (e.g., `["4", "8"]`).
    c. Split the `PointList` string by both commas and spaces to get a flat array of all coordinate values (e.g., `["0","1","275","1",...]`).
    d. Iterate through the point counts. For each count `n`:
        i. Read the next `n*2` values from the coordinate array to form a polygon.
        ii. Store the polygon as a list of `(x, y)` tuples or a similar structure.
3.  The final data structure should map each section name to a list of its parsed polygons.

### 2.3. Example

**`REGION.TXT` content:**

```ini
; This defines the main window shape with two separate polygons.
[Normal]
NumPoints = 4, 8
PointList = 0,1, 275,1, 275,14, 0,14,     1,14, 2,14, 2,114, 273,114, 273,14, 274,14, 274,115, 1,115
```

**Parsed Data Structure (Conceptual Python):**

```python
{
  "Normal": [
    # Polygon 1 (4 points)
    [(0, 1), (275, 1), (275, 14), (0, 14)],
    # Polygon 2 (8 points)
    [(1, 14), (2, 14), (2, 114), (273, 114), (273, 14), (274, 14), (274, 115), (1, 115)]
  ]
}
```

---

## 3. Format 2: Rectangular Hotspots

While not present in the default skin's `REGION.TXT`, this format is used by other skins to define rectangular clickable regions. It uses a line-based format.

### 3.1. File Format

*   Each line defines one rectangular region and associates it with one or more UI element names.
*   The format for each line is: `Rect <x1>,<y1>,<x2>,<y2>;<ElementName1>,<ElementName2>,...`
*   **`Rect`**: A literal keyword.
*   **`<x1>,<y1>,<x2>,<y2>`**: The top-left and bottom-right coordinates of the rectangle.
*   **`;`**: A semicolon separator.
*   **`<ElementName1>,...`**: A comma-separated list of identifiers that this region maps to.

### 3.2. Parsing Logic

1.  Read the file line by line.
2.  Ignore empty lines and lines not starting with `Rect`.
3.  For each valid line, use a regular expression like `^Rect (\d+),(\d+),(\d+),(\d+);(.*)` to capture the coordinates and the element list string.
4.  Parse the coordinates into a rectangle structure (e.g., `(left, top, right, bottom)`).
5.  Split the element list string by commas to get a list of associated names.
6.  The recommended data structure is a dictionary where keys are the element names and values are the corresponding rectangle. Since multiple names can map to the same rectangle, you can either duplicate the rectangle for each name or map each name to a shared rectangle object.

### 3.3. Example

**`region.txt` content for hotspots:**

```
Rect 10,20,30,40;MyButton_Normal,MyButton_Pressed
Rect 50,20,70,40;NextTrackButton
```

**Parsed Data Structure (Conceptual Python):**

```python
{
  "MyButton_Normal": (10, 20, 30, 40),
  "MyButton_Pressed": (10, 20, 30, 40),
  "NextTrackButton": (50, 20, 70, 40)
}
```

## 4. Implementation Notes

*   A parser should be robust enough to handle potential whitespace variations, such as extra spaces around commas.
*   It's possible a single file could contain both formats, though unlikely. A simple heuristic could be to check if the file content contains `[Normal]` or `[WindowShade]` to decide which parsing strategy to apply. For this project, it's safer to assume two separate parsers or a single parser that can distinguish between the two formats based on line content.
*   The coordinate system originates from the top-left corner (0,0) of the main bitmap (`MAIN.BMP`).
