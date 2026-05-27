from src.core.region_parser import (
    parse_region_file,
    parse_ini_format,
    parse_hotspots_format,
)


class TestParseRegionFile:
    def test_ini_format_detected(self):
        content = "[Normal]\nNumPoints=3\nPointList=0,0 275,0 275,116"
        result = parse_region_file(content)
        assert result["format"] == "polygons"
        assert "Normal" in result["data"]

    def test_hotspots_format_detected(self):
        content = "Rect 0, 0, 275, 116; Button1"
        result = parse_region_file(content)
        assert result["format"] == "hotspots"
        assert "Button1" in result["data"]

    def test_empty_content(self):
        result = parse_region_file("")
        assert result["format"] == "hotspots"
        assert result["data"] == {}


class TestIniFormat:
    def test_single_polygon(self):
        content = "[Normal]\nNumPoints=4\nPointList=0,0 100,0 100,50 0,50"
        result = parse_ini_format(content)
        assert "Normal" in result
        assert len(result["Normal"]) == 1
        assert len(result["Normal"][0]) == 4
        assert result["Normal"][0][0] == (0, 0)
        assert result["Normal"][0][2] == (100, 50)

    def test_multiple_polygons(self):
        content = "[Normal]\nNumPoints=3,3\nPointList=0,0 10,0 10,10 20,20 30,20 30,30"
        result = parse_ini_format(content)
        assert len(result["Normal"]) == 2
        assert len(result["Normal"][0]) == 3
        assert len(result["Normal"][1]) == 3

    def test_multiple_sections(self):
        content = (
            "[Normal]\nNumPoints=3\nPointList=0,0 100,0 100,50\n"
            "[WindowShade]\nNumPoints=4\nPointList=0,0 275,0 275,14 0,14"
        )
        result = parse_ini_format(content)
        assert "Normal" in result
        assert "WindowShade" in result
        assert len(result["Normal"][0]) == 3
        assert len(result["WindowShade"][0]) == 4

    def test_missing_numpoints(self):
        content = "[Normal]\nPointList=0,0 10,0 10,10"
        result = parse_ini_format(content)
        assert result["Normal"] == []

    def test_missing_pointlist(self):
        content = "[Normal]\nNumPoints=3"
        result = parse_ini_format(content)
        assert result["Normal"] == []

    def test_comments_and_empty_lines_ignored(self):
        content = "; comment\n\n[Normal]\n; another comment\n\nNumPoints=3\nPointList=0,0 10,0 10,10"
        result = parse_ini_format(content)
        assert len(result["Normal"][0]) == 3

    def test_not_enough_coordinates(self):
        content = "[Normal]\nNumPoints=5\nPointList=0,0 10,0 10,10"
        result = parse_ini_format(content)
        # Not enough coordinates for 5 points, parser stops gracefully
        assert len(result["Normal"]) == 0

    def test_invalid_numpoints(self):
        content = "[Normal]\nNumPoints=abc\nPointList=0,0 10,0"
        result = parse_ini_format(content)
        assert result["Normal"] == []


class TestHotspotsFormat:
    def test_single_rect_single_element(self):
        content = "Rect 10, 20, 100, 50; MyButton"
        result = parse_hotspots_format(content)
        assert "MyButton" in result
        assert result["MyButton"] == (10, 20, 100, 50)

    def test_single_rect_multiple_elements(self):
        content = "Rect 0, 0, 275, 116; Element1, Element2"
        result = parse_hotspots_format(content)
        assert "Element1" in result
        assert "Element2" in result
        assert result["Element1"] == result["Element2"]

    def test_multiple_rects(self):
        content = (
            "Rect 0, 0, 100, 50; ButtonA\n"
            "Rect 100, 0, 200, 50; ButtonB"
        )
        result = parse_hotspots_format(content)
        assert "ButtonA" in result
        assert "ButtonB" in result

    def test_empty_lines_ignored(self):
        content = "\n\nRect 0, 0, 10, 10; X\n\n"
        result = parse_hotspots_format(content)
        assert "X" in result
