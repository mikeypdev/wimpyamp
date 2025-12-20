from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Tuple, Any


@dataclass
class SkinData:
    """A dataclass to hold all the data related to a skin."""

    extracted_skin_dir: Optional[str] = None
    original_skin_path: Optional[str] = None
    main_bmp_path: Optional[str] = None
    spec_json: Dict[str, Any] = field(default_factory=dict)
    eq_spec_json: Dict[str, Any] = field(default_factory=dict)
    playlist_spec_json: Dict[str, Any] = field(default_factory=dict)
    viscolor_data: List[Tuple[int, int, int]] = field(default_factory=list)
    region_data: Optional[Dict[str, Any]] = None
    file_mapping: Dict[str, str] = field(default_factory=dict)

    def get_path(self, filename: str) -> str | None:
        """
        Gets the full, case-correct path for a given skin file.
        The lookup is case-insensitive.
        """
        if not self.extracted_skin_dir:
            return None

        # The keys in file_mapping are already lowercase
        actual_filename = self.file_mapping.get(filename.lower())

        if actual_filename:
            import os

            return os.path.join(self.extracted_skin_dir, actual_filename)

        return None
