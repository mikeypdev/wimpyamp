"""
Utility functions for converting region data to PyQt5 masks.
"""

from PySide6.QtGui import QPolygon, QRegion
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QWidget
from typing import List, Tuple, Dict, Optional, Any


def apply_region_mask_to_widget(
    widget: QWidget,
    region_data: Dict[str, Any],
    state: str = "Normal",
    window_width: Optional[int] = None,
    window_height: Optional[int] = None,
):
    """
    Applies a region mask to a widget based on the parsed region data.

    Args:
        widget: The QWidget to apply the mask to
        region_data: The parsed region data from region_parser
        state: The window state to use (e.g., "Normal", "WindowShade", "Equalizer")
        window_width: Width of the window (if None, uses widget.width())
        window_height: Height of the window (if None, uses widget.height())
    """
    if not region_data or region_data.get("format") != "polygons":
        # If no region data or it's hotspots format, clear any existing mask
        widget.clearMask()
        return

    polygons_data = region_data.get("data", {})
    polygons = polygons_data.get(state, [])  # type: ignore

    if not polygons:
        widget.clearMask()
        return

    # Get window dimensions
    if window_width is None:
        window_width = widget.width()
    if window_height is None:
        window_height = widget.height()

    # Create a QRegion that will be the combination of all polygons
    combined_region = QRegion()

    for polygon in polygons:
        if len(polygon) < 3:  # Need at least 3 points for a polygon
            continue

        # Create Qt polygon from the list of points
        qt_polygon = QPolygon()
        for x, y in polygon:
            qt_polygon.append(QPoint(x, y))

        # Create region from polygon and add it to combined region
        polygon_region = QRegion(qt_polygon)
        combined_region = combined_region.united(polygon_region)

    # Apply the combined region as the mask
    widget.setMask(combined_region)


def convert_polygons_to_qregion(
    polygons: List[List[Tuple[int, int]]], window_width: int, window_height: int
) -> QRegion:
    """
    Converts a list of polygons to a QRegion.

    Args:
        polygons: List of polygons, where each polygon is a list of (x, y) tuples
        window_width: Width of the containing window
        window_height: Height of the containing window

    Returns:
        QRegion that represents the union of all polygons
    """
    combined_region = QRegion()

    for polygon in polygons:
        if len(polygon) < 3:  # Need at least 3 points for a polygon
            continue

        # Create Qt polygon from the list of points
        qt_polygon = QPolygon()
        for x, y in polygon:
            qt_polygon.append(QPoint(x, y))

        # Create region from polygon and add it to combined region
        polygon_region = QRegion(qt_polygon)
        combined_region = combined_region.united(polygon_region)

    return combined_region
