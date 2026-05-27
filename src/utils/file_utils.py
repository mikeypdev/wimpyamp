"""
File utilities for WimPyAmp application.

This module provides utilities for file operations, including case-insensitive
file lookups which are important for cross-platform compatibility.
"""

import os
import zipfile


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
