import os
import json
import zipfile
import shutil
import sys  # Moved from _load_spec_files method
from appdirs import user_data_dir  # type: ignore
from .region_parser import parse_region_file
from .skin_data import SkinData


class SkinParser:
    def __init__(self, skin_path):
        self.skin_path = skin_path
        self.skin_data = SkinData(original_skin_path=skin_path)

    def parse(self) -> SkinData:
        if not self._extract_skin_files():
            return self.skin_data

        self._load_spec_files()
        self._load_viscolor_data()
        self._load_region_data()

        main_bmp_full_path = os.path.join(self.skin_data.extracted_skin_dir, "main.bmp")
        if os.path.exists(main_bmp_full_path):
            self.skin_data.main_bmp_path = main_bmp_full_path
        else:
            print(f"WARNING: main.bmp not found in {self.skin_data.extracted_skin_dir}")

        return self.skin_data

    def _extract_skin_files(self) -> bool:
        if os.path.isdir(self.skin_path):
            self.skin_data.extracted_skin_dir = self.skin_path
            return True
        elif self.skin_path.endswith(".wsz") or self.skin_path.endswith(".zip"):
            # Use user data directory instead of the same directory as the skin file
            # This prevents issues when the skin file is in a read-only location like an app bundle
            app_data_dir = user_data_dir("WimPyAmp")
            skins_data_dir = os.path.join(app_data_dir, "skins")
            os.makedirs(skins_data_dir, exist_ok=True)

            # Create a unique name for this skin based on its path to avoid conflicts
            skin_basename = os.path.splitext(os.path.basename(self.skin_path))[0]
            temp_extract_dir = os.path.join(
                skins_data_dir, f"temp_extracted_skin_{skin_basename}"
            )
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)
            os.makedirs(temp_extract_dir, exist_ok=True)

            try:
                with zipfile.ZipFile(self.skin_path, "r") as zf:
                    zf.extractall(temp_extract_dir)

                extracted_items = os.listdir(temp_extract_dir)
                if len(extracted_items) == 1:
                    potential_skin_dir = os.path.join(
                        temp_extract_dir, extracted_items[0]
                    )
                    if os.path.isdir(potential_skin_dir):
                        extracted_skin_dir = potential_skin_dir
                    else:
                        extracted_skin_dir = temp_extract_dir
                else:
                    extracted_skin_dir = temp_extract_dir

                # Validate that this directory contains essential skin files
                if self._validate_skin_directory(extracted_skin_dir):
                    self.skin_data.extracted_skin_dir = extracted_skin_dir
                    return True
                else:
                    print(
                        f"ERROR: {self.skin_path} does not contain valid Winamp skin data."
                    )
                    # Clean up extracted files
                    shutil.rmtree(temp_extract_dir)
                    return False
            except zipfile.BadZipFile:
                print(f"ERROR: {self.skin_path} is not a valid ZIP file.")
                return False
        else:
            print(
                f"ERROR: Unknown skin path type: {self.skin_path}. Must be a directory, .wsz file, or .zip file."
            )
            return False

    def _validate_skin_directory(self, skin_dir: str) -> bool:
        """
        Validates if the given directory contains essential Winamp skin files.
        A valid skin should contain basic UI elements like main.bmp.

        Args:
            skin_dir: Path to the directory containing extracted skin files

        Returns:
            bool: True if the directory contains a valid skin, False otherwise
        """
        # At minimum, a Winamp skin must have main.bmp (the main window background)
        required_files = ["main.bmp"]

        # Check for required files
        for required_file in required_files:
            required_path = os.path.join(skin_dir, required_file)
            if not os.path.exists(required_path):
                print(
                    f"INFO: Required skin file '{required_file}' not found in {skin_dir}"
                )
                return False

        # Additional check: verify that main.bmp is actually an image file
        main_bmp_path = os.path.join(skin_dir, "main.bmp")
        try:
            from PIL import Image

            with Image.open(main_bmp_path) as img:
                # Try to read basic image info to ensure it's a valid image
                img.verify()
            # Reopen after verify since verify() closes the file
            with Image.open(main_bmp_path) as img:
                pass
        except Exception as e:
            print(f"INFO: main.bmp is not a valid image file: {e}")
            return False

        # If main.bmp exists and is a valid image file, we consider it a valid skin
        return True

    def _load_spec_files(self):

        # Determine path to specs based on whether running from source or PyInstaller bundle
        if getattr(sys, "frozen", False):
            # Running as compiled executable - specs are in the temp directory created by PyInstaller
            application_path = sys._MEIPASS
            specs_dir = os.path.join(application_path, "resources", "specs")
        else:
            # Running as script in development
            specs_dir = os.path.join(
                os.path.dirname(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                ),
                "resources",
                "specs",
            )

        spec_files = {
            "spec_json": "winamp_skin_spec.json",
            "eq_spec_json": "eq_window_spec.json",
            "playlist_spec_json": "playlist_window_spec.json",
        }

        for key, filename in spec_files.items():
            path = os.path.join(specs_dir, filename)
            if os.path.exists(path):
                with open(path, "r") as f:
                    setattr(self.skin_data, key, json.load(f))
            else:
                print(f"WARNING: {filename} not found at {path}")

    def _load_viscolor_data(self):
        viscolor_path = os.path.join(self.skin_data.extracted_skin_dir, "viscolor.txt")
        if os.path.exists(viscolor_path):
            self.skin_data.viscolor_data = self._load_viscolor_file(viscolor_path)
        else:
            print(
                f"WARNING: viscolor.txt not found in {self.skin_data.extracted_skin_dir}, using defaults"
            )
            self.skin_data.viscolor_data = self._get_default_viscolor_data()

    def _load_region_data(self):
        region_path = os.path.join(self.skin_data.extracted_skin_dir, "region.txt")
        if os.path.exists(region_path):
            try:
                with open(region_path, "r") as f:
                    region_content = f.read()
                self.skin_data.region_data = parse_region_file(region_content)
            except Exception as e:
                print(f"WARNING: Could not parse region.txt: {e}")
                self.skin_data.region_data = None
        else:
            print(
                f"INFO: region.txt not found in {self.skin_data.extracted_skin_dir}, skipping region parsing"
            )
            self.skin_data.region_data = None

    def get_sprite(self, sheet_name, sprite_id):
        if not self.skin_data.spec_json:
            print("ERROR: Skin specification not loaded.")
            return None

        spec = self.skin_data.spec_json

        if sheet_name not in spec["sheets"]:
            print(f"ERROR: Sheet '{sheet_name}' not found in skin specification.")
            return None

        sheet = spec["sheets"][sheet_name]
        if sprite_id not in sheet["sprites"]:
            print(f"ERROR: Sprite '{sprite_id}' not found in sheet '{sheet_name}'.")
            return None

        sprite_info = sheet["sprites"][sprite_id]

        sheet_path = os.path.join(self.skin_data.extracted_skin_dir, sheet_name)

        return {
            "sheet_path": sheet_path,
            "x": sprite_info["x"],
            "y": sprite_info["y"],
            "w": sprite_info["w"],
            "h": sprite_info["h"],
        }

    def _load_viscolor_file(self, viscolor_path):
        """Load and parse the viscolor.txt file into an array of RGB tuples."""
        try:
            with open(viscolor_path, "r") as f:
                lines = f.readlines()

            colors = []
            for i, line in enumerate(lines[:24]):
                line = line.strip()
                if not line:
                    colors.append((0, 0, 0))
                    continue

                try:
                    color_part = line.split("//")[0].strip().rstrip(",")
                    r, g, b = map(int, color_part.split(","))
                    colors.append(
                        (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
                    )
                except ValueError:
                    print(
                        f"WARNING: Invalid color format in viscolor.txt line {i+1}: {line}"
                    )
                    colors.append((0, 0, 0))

            while len(colors) < 24:
                colors.append((0, 0, 0))

            return colors
        except Exception as e:
            print(f"ERROR: Could not load viscolor.txt: {e}")
            return self._get_default_viscolor_data()

    def _get_default_viscolor_data(self):
        """Generate default viscolor data if viscolor.txt is not available."""
        colors = [(0, 0, 0), (40, 40, 40)]
        for i in range(16):
            ratio = i / 15.0 if i > 0 else 0
            r = int(255 * ratio)
            g = 0
            b = int(255 * (1 - ratio))
            colors.append(
                (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            )

        osc_colors = [
            (255, 255, 255),
            (0, 255, 0),
            (0, 128, 255),
            (255, 0, 255),
            (255, 255, 0),
        ]
        colors.extend(osc_colors)
        colors.append((255, 255, 0))
        colors.append((255, 128, 0))

        return colors[:24]


# Ensure we have exactly 24 colors
