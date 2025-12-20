"""
File utilities for WimPyAmp application.

This module provides utilities for file operations, including case-insensitive
file lookups which are important for cross-platform compatibility.
"""

import os
from typing import Optional


def find_file_case_insensitive(directory: str, filename: str) -> Optional[str]:
    """
    Find a file in a directory with case-insensitive matching.

    Args:
        directory: The directory to search in
        filename: The filename to look for (case-insensitive)

    Returns:
        The actual filename with correct case if found, None otherwise
    """
    if not os.path.isdir(directory):
        return None

    filename_lower = filename.lower()

    for entry in os.listdir(directory):
        if entry.lower() == filename_lower:
            entry_path = os.path.join(directory, entry)
            if os.path.isfile(entry_path):
                return entry_path

    return None
