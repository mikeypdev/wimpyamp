"""
File utilities for WimPyAmp application.

This module provides utilities for file operations, including case-insensitive
file lookups which are important for cross-platform compatibility.
"""

import os
import zipfile
from typing import Optional


def validate_zip_members(zf: zipfile.ZipFile, dest_dir: str) -> list[str]:
    """Validate zip members for safe extraction, rejecting path traversal.

    Args:
        zf: An open ZipFile to validate.
        dest_dir: The intended extraction directory (used for resolving paths).

    Returns:
        A list of safe member names to extract.

    Raises:
        ValueError: If any member would escape the destination directory.
    """
    safe_members = []
    dest_dir = os.path.realpath(dest_dir)
    for info in zf.infolist():
        if info.is_dir():
            continue
        member_path = os.path.realpath(os.path.join(dest_dir, info.filename))
        if not member_path.startswith(dest_dir + os.sep) and member_path != dest_dir:
            raise ValueError(
                f"Unsafe zip member escapes target directory: {info.filename}"
            )
        safe_members.append(info.filename)
    return safe_members


def extract_zip_safely(zf: zipfile.ZipFile, dest_dir: str):
    """Extract a ZipFile safely, validating all members against path traversal.

    Args:
        zf: An open ZipFile to extract.
        dest_dir: The directory to extract into.

    Raises:
        ValueError: If any member would escape the destination directory.
    """
    validate_zip_members(zf, dest_dir)
    zf.extractall(dest_dir)


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
