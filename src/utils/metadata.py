"""
Shared metadata extraction utilities for audio files.

Provides a unified interface for extracting metadata from various audio formats
(MP3/ID3, M4A/iTunes, FLAC/Vorbis) using mutagen.
"""

from mutagen import File as MutagenFile

from ..utils.logger import get_logger

logger = get_logger(__name__)

METADATA_KEYS = {
    "title": ["TIT2", "title", "\xa9nam", "TITLE", "©nam"],
    "artist": ["TPE1", "artist", "\xa9ART", "ARTIST", "©ART"],
    "album": ["TALB", "album", "\xa9alb", "ALBUM", "©alb"],
    "album_artist": ["TPE2", "albumartist", "aART", "©aAR"],
}


def safe_extract_metadata(audio_file, keys: list[str]) -> str:
    """Try multiple tag keys to extract a metadata field.

    Args:
        audio_file: A mutagen File object.
        keys: List of tag keys to try, in priority order.

    Returns:
        The extracted value as a string, or "Unknown" if not found.
    """
    result = "Unknown"
    for key in keys:
        try:
            if key in audio_file:
                tag_value = audio_file[key]
                if isinstance(tag_value, list) and len(tag_value) > 0:
                    try:
                        raw_value = tag_value[0]
                        if raw_value is not None:
                            result = str(raw_value).strip()
                        else:
                            result = "Unknown"
                    except (UnicodeDecodeError, TypeError, AttributeError):
                        result = "Unknown"
                elif isinstance(tag_value, list) and len(tag_value) == 0:
                    continue
                else:
                    try:
                        if tag_value is not None:
                            result = str(tag_value).strip()
                        else:
                            result = "Unknown"
                    except (UnicodeDecodeError, TypeError, AttributeError):
                        result = "Unknown"
                break
        except Exception:
            continue
    return result if result else "Unknown"


def extract_common_metadata(audio_file) -> dict:
    """Extract title, artist, album, and album_artist from a mutagen File.

    Args:
        audio_file: A mutagen File object.

    Returns:
        Dictionary with keys: title, artist, album, album_artist.
    """
    return {
        field: safe_extract_metadata(audio_file, keys)
        for field, keys in METADATA_KEYS.items()
    }


def extract_track_number(audio_file) -> str:
    """Extract track number from various audio formats.

    Returns:
        Track number as string, or "Unknown" if not found.
    """
    try:
        if "trkn" in audio_file:
            track_info = audio_file["trkn"]
            if track_info and len(track_info) > 0 and len(track_info[0]) > 0:
                return str(track_info[0][0])
        elif "TRCK" in audio_file:
            track_str = str(audio_file["TRCK"])
            return track_str.split("/")[0].strip()
        elif "tracknumber" in audio_file:
            return str(audio_file["tracknumber"][0]).split("/")[0].strip()
    except (KeyError, TypeError, AttributeError, IndexError):
        pass
    return "Unknown"


def load_metadata_for_file(filepath: str) -> dict:
    """Load metadata from an audio file path.

    Args:
        filepath: Path to the audio file.

    Returns:
        Dictionary with metadata fields. Returns defaults on failure.
    """
    defaults = {
        "title": "Unknown",
        "artist": "Unknown",
        "album": "Unknown",
        "album_artist": "Unknown",
        "tracknumber": "Unknown",
        "duration": 0.0,
    }
    try:
        audio_file = MutagenFile(filepath)
        if audio_file is None:
            return defaults

        metadata = extract_common_metadata(audio_file)
        metadata["tracknumber"] = extract_track_number(audio_file)

        if hasattr(audio_file, "info") and hasattr(audio_file.info, "length"):
            metadata["duration"] = audio_file.info.length

        return metadata
    except (OSError, KeyError, AttributeError, TypeError, ValueError) as e:
        logger.debug(f"Could not load metadata for {filepath}: {e}")
        return defaults
