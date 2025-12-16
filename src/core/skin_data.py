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
