import zipfile
import pytest
from src.utils.file_utils import validate_zip_members, extract_zip_safely


class TestZipSecurity:
    def test_safe_members_pass(self, tmp_path):
        zip_path = tmp_path / "safe.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("main.bmp", "data")
            zf.writestr("subdir/text.bmp", "data")
        dest = str(tmp_path / "out")
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            members = validate_zip_members(zf, dest)
        assert "main.bmp" in members
        assert "subdir/text.bmp" in members

    def test_traversal_rejected(self, tmp_path):
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("../../../etc/passwd", "data")
        dest = str(tmp_path / "out")
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            with pytest.raises(ValueError, match="escapes"):
                validate_zip_members(zf, dest)

    def test_absolute_path_rejected(self, tmp_path):
        zip_path = tmp_path / "abs.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("/tmp/evil.txt", "data")
        dest = str(tmp_path / "out")
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            with pytest.raises(ValueError, match="escapes"):
                validate_zip_members(zf, dest)

    def test_extract_zip_safely_works(self, tmp_path):
        zip_path = tmp_path / "good.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("hello.txt", "world")
        dest = str(tmp_path / "out")
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            extract_zip_safely(zf, dest)
        assert (tmp_path / "out" / "hello.txt").read_text() == "world"

    def test_extract_zip_safely_blocks_traversal(self, tmp_path):
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(str(zip_path), "w") as zf:
            zf.writestr("../../evil.txt", "data")
        dest = str(tmp_path / "out")
        with zipfile.ZipFile(str(zip_path), "r") as zf:
            with pytest.raises(ValueError):
                extract_zip_safely(zf, dest)
