from src.core.skin_parser import SkinParser


def test_default_skin_loads_without_errors(default_skin_path):
    parser = SkinParser(default_skin_path)
    skin_data = parser.parse()
    assert skin_data.extracted_skin_dir is not None
    assert skin_data.spec_json is not None
    assert skin_data.main_bmp_path is not None
    assert (
        "main.bmp" in skin_data.file_mapping
        or "MAIN.BMP".lower() in skin_data.file_mapping
    )
