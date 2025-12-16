"""
Parser for Winamp REGION.TXT files.

This module handles both formats of REGION.TXT files:
1. INI-style format for polygonal window shapes
2. Line-based format for rectangular hotspots
"""

import re
from typing import Dict, List, Tuple, Any


def parse_region_file(
    content: str,
) -> Dict[str, Any]:
    """
    Parses a REGION.TXT file content and returns the appropriate data structure
    based on the format detected.

    Args:
        content: The content of the REGION.TXT file

    Returns:
        Dictionary containing parsed region data. Format depends on the input:
        - For INI format: {"format": "polygons", "data": {...}} where data maps
          section names to lists of polygons (each polygon is a list of (x,y) tuples)
        - For hotspots format: {"format": "hotspots", "data": {...}} where data maps
          element names to rectangles (x1, y1, x2, y2)
    """
    # Detect which format to use based on content
    if _is_ini_format(content):
        polygons = parse_ini_format(content)
        return {"format": "polygons", "data": polygons}
    else:
        hotspots = parse_hotspots_format(content)
        return {"format": "hotspots", "data": hotspots}


def _is_ini_format(content: str) -> bool:
    """
    Checks if the content follows the INI-style format for polygonal window shapes.
    This is determined by the presence of section headers like [Normal], [WindowShade], etc.
    """
    lines = content.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            # Check if it looks like a window state section
            section_name = line[1:-1].strip().lower()
            if section_name in ["normal", "windowshade", "mini", "equalizer"]:
                return True
    return False


def parse_ini_format(content: str) -> Dict[str, List[List[Tuple[int, int]]]]:
    """
    Parses the INI-style format for polygonal window shapes.

    Args:
        content: The content of the REGION.TXT file in INI format

    Returns:
        Dictionary mapping section names to lists of polygons, where each polygon
        is a list of (x, y) tuples.
    """
    # ConfigParser expects an [section] header, so we add a dummy one if needed
    # But we'll parse manually to handle the format more flexibly
    result = {}

    lines = content.strip().split("\n")
    current_section = None
    section_data: Dict[str, str] = {}

    for line in lines:
        line = line.strip()

        # Skip comments and empty lines
        if line.startswith(";") or not line:
            continue

        # Check for section header
        if line.startswith("[") and line.endswith("]"):
            if current_section is not None:
                # Process the previous section
                result[current_section] = _process_polygon_section(section_data)
            current_section = line[1:-1]
            section_data = {}
        elif current_section and "=" in line:
            # Parse key=value pair
            key, value = line.split("=", 1)
            key = key.strip().lower()
            value = value.strip()
            section_data[key] = value

    # Process the last section if it exists
    if current_section is not None:
        result[current_section] = _process_polygon_section(section_data)

    return result


def _process_polygon_section(
    section_data: Dict[str, str],
) -> List[List[Tuple[int, int]]]:
    """
    Processes a single section's NumPoints and PointList to create polygons.

    Args:
        section_data: Dictionary containing 'numpoints' and 'pointlist' keys

    Returns:
        List of polygons, where each polygon is a list of (x, y) tuples
    """
    if "numpoints" not in section_data or "pointlist" not in section_data:
        return []

    # Parse NumPoints
    numpoints_str = section_data["numpoints"]
    try:
        point_counts = [int(x.strip()) for x in numpoints_str.split(",") if x.strip()]
    except ValueError:
        # If we can't parse point counts as integers, return empty list
        return []

    # Parse PointList
    pointlist_str = section_data["pointlist"]
    # Split by both commas and spaces
    all_coords_raw = [
        x.strip() for x in re.split(r"[,\s]+", pointlist_str) if x.strip()
    ]
    try:
        all_coords = [int(coord) for coord in all_coords_raw]
    except ValueError:
        # If we can't parse coordinates as integers, return empty list
        return []

    # Generate polygons
    polygons = []
    coord_idx = 0

    for count in point_counts:
        if coord_idx + count * 2 > len(all_coords):
            # Not enough coordinates for this polygon, skip it
            break

        polygon = []
        for i in range(count):
            if coord_idx + 1 < len(all_coords):
                x = all_coords[coord_idx]
                y = all_coords[coord_idx + 1]
                polygon.append((x, y))
                coord_idx += 2

        polygons.append(polygon)

    return polygons


def parse_hotspots_format(content: str) -> Dict[str, Tuple[int, int, int, int]]:
    """
    Parses the line-based format for rectangular hotspots.

    Args:
        content: The content of the REGION.TXT file in hotspots format

    Returns:
        Dictionary mapping element names to rectangles (x1, y1, x2, y2)
    """
    result = {}

    lines = content.strip().split("\n")
    rect_pattern = r"^Rect\s+(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*;\s*(.*)$"

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Look for Rect lines
        match = re.match(rect_pattern, line, re.IGNORECASE)
        if match:
            try:
                x1, y1, x2, y2, element_names_str = match.groups()
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)

                # Parse element names
                element_names = [
                    name.strip()
                    for name in element_names_str.split(",")
                    if name.strip()
                ]

                # Create rectangle tuple
                rect = (x1, y1, x2, y2)

                # Map each element name to this rectangle
                for name in element_names:
                    result[name] = rect
            except ValueError:
                # If we can't parse coordinates as integers, skip this line
                continue

    return result
