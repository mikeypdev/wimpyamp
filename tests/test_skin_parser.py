import os
import tempfile
import zipfile
import pytest
from src.core.skin_parser import SkinParser


class TestSkinParserDefaultSkin:
    def test_loads_default_skin(self, default_skin_path):
        parser = SkinParser(default_skin_path)
        skin_data = parser.parse()
        assert skin_data.extracted_skin_dir is not None
        assert skin_data.main_bmp_path is not None
        assert os.path.exists(skin_data.main_bmp_path)

    def test_spec_json_loaded(self, default_skin_path):
        parser = SkinParser(default_skin_path)
        skin_data = parser.parse()
        assert skin_data.spec_json is not None
        assert "sheets" in skin_data.spec_json
        assert "destinations" in skin_data.spec_json

    def test_file_mapping_is_lowercase(self, default_skin_path):
        parser = SkinParser(default_skin_path)
        skin_data = parser.parse()
        for key in skin_data.file_mapping:
            assert key == key.lower()

    def test_get_path_finds_main_bmp(self, default_skin_path):
        parser = SkinParser(default_skin_path)
        skin_data = parser.parse()
        path = skin_data.get_path("main.bmp")
        assert path is not None
        assert os.path.exists(path)

    def test_get_path_case_insensitive(self, default_skin_path):
        parser = SkinParser(default_skin_path)
        skin_data = parser.parse()
        path = skin_data.get_path("MAIN.BMP")
        assert path is not None

    def test_get_path_returns_none_for_missing(self, default_skin_path):
        parser = SkinParser(default_skin_path)
        skin_data = parser.parse()
        assert skin_data.get_path("nonexistent.xyz") is None


class TestSkinParserValidation:
    def test_nonexistent_file(self):
        parser = SkinParser("/tmp/does_not_exist.wsz")
        skin_data = parser.parse()
        assert skin_data.extracted_skin_dir is None

    def test_invalid_zip(self, tmp_path):
        bad_zip = tmp_path / "bad.wsz"
        bad_zip.write_bytes(b"not a zip file")
        parser = SkinParser(str(bad_zip))
        skin_data = parser.parse()
        assert skin_data.extracted_skin_dir is None

    def test_zip_missing_main_bmp(self, tmp_path):
        empty_zip = tmp_path / "empty.wsz"
        with zipfile.ZipFile(str(empty_zip), "w") as zf:
            zf.writestr("readme.txt", "no skin here")
        parser = SkinParser(str(empty_zip))
        skin_data = parser.parse()
        assert skin_data.extracted_skin_dir is None

    def test_path_traversal_zip_rejected(self, tmp_path):
        evil_zip = tmp_path / "evil.wsz"
        with zipfile.ZipFile(str(evil_zip), "w") as zf:
            zf.writestr("../../../tmp/evil.txt", "pwned")
        parser = SkinParser(str(evil_zip))
        # ValueError from zip security propagates through parse
        skin_data = parser.parse()
        assert skin_data.extracted_skin_dir is None

    def test_directory_skin(self, default_skin_dir):
        main_bmp = os.path.join(default_skin_dir, "base-2.91.png")
        if not os.path.exists(main_bmp):
            pytest.skip("default skin dir has no image file")
        parser = SkinParser(default_skin_dir)
        skin_data = parser.parse()
        # Directory mode sets extracted_skin_dir directly
        assert skin_data.extracted_skin_dir == default_skin_dir
