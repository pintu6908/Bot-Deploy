from __future__ import annotations

import mimetypes
import re
from pathlib import Path
from typing import Optional


# ============================================================
# CONSTANTS
# ============================================================

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".webm",
    ".mov",
    ".avi",
    ".m4v",
    ".3gp",
    ".ts",
}

AUDIO_EXTENSIONS = {
    ".mp3",
    ".m4a",
    ".aac",
    ".wav",
    ".ogg",
    ".opus",
    ".flac",
}

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif",
}


# ============================================================
# FILE SIZE
# ============================================================

def get_file_size(path: str | Path) -> int:
    """
    Return file size in bytes.

    Returns 0 if the file does not exist.
    """

    file_path = Path(path)

    try:
        return file_path.stat().st_size
    except (FileNotFoundError, OSError):
        return 0


def format_file_size(size: Optional[int]) -> str:
    """Convert bytes into a readable file size."""

    if size is None or size < 0:
        return "Unknown"

    if size == 0:
        return "0 B"

    units = (
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    )

    value = float(size)

    for unit in units:
        if value < 1024:
            return f"{value:.2f} {unit}"

        value /= 1024

    return f"{value:.2f} PB"


# ============================================================
# MIME TYPE
# ============================================================

def get_mime_type(
    path: str | Path,
) -> str:
    """
    Detect MIME type from filename.

    Falls back to application/octet-stream.
    """

    file_path = Path(path)

    mime_type, _ = mimetypes.guess_type(
        file_path.name
    )

    if mime_type:
        return mime_type

    return "application/octet-stream"


def is_video_file(
    path: str | Path,
) -> bool:
    """Return True if the file appears to be a video."""

    extension = Path(path).suffix.lower()

    if extension in VIDEO_EXTENSIONS:
        return True

    return get_mime_type(path).startswith(
        "video/"
    )


def is_audio_file(
    path: str | Path,
) -> bool:
    """Return True if the file appears to be audio."""

    extension = Path(path).suffix.lower()

    if extension in AUDIO_EXTENSIONS:
        return True

    return get_mime_type(path).startswith(
        "audio/"
    )


def is_image_file(
    path: str | Path,
) -> bool:
    """Return True if the file appears to be an image."""

    extension = Path(path).suffix.lower()

    if extension in IMAGE_EXTENSIONS:
        return True

    return get_mime_type(path).startswith(
        "image/"
    )


# ============================================================
# FILENAME SAFETY
# ============================================================

def sanitize_filename(
    filename: str,
    fallback: str = "media",
    max_length: int = 120,
) -> str:
    """
    Make a filename safe for Linux/Railway filesystem use.

    This does not execute or interpret the filename.
    """

    if not filename:
        filename = fallback

    filename = str(filename).strip()

    # Remove path separators and control characters.
    filename = filename.replace("/", "_")
    filename = filename.replace("\\", "_")

    filename = re.sub(
        r"[\x00-\x1f\x7f]",
        "",
        filename,
    )

    # Replace characters that can cause filesystem issues.
    filename = re.sub(
        r'[<>:"|?*]',
        "_",
        filename,
    )

    # Collapse whitespace.
    filename = re.sub(
        r"\s+",
        " ",
        filename,
    ).strip()

    # Prevent hidden/dot-only filenames.
    filename = filename.lstrip(".")

    if not filename:
        filename = fallback

    # Preserve extension when truncating.
    path = Path(filename)

    suffix = path.suffix

    if suffix and len(filename) > max_length:
        stem_limit = max(
            1,
            max_length - len(suffix),
        )

        filename = (
            path.stem[:stem_limit]
            + suffix
        )
    else:
        filename = filename[:max_length]

    return filename


# ============================================================
# EXTENSION HELPERS
# ============================================================

def ensure_extension(
    filename: str,
    extension: str,
) -> str:
    """
    Add an extension if filename does not already have one.
    """

    extension = extension.strip()

    if not extension:
        return filename

    if not extension.startswith("."):
        extension = "." + extension

    if Path(filename).suffix:
        return filename

    return filename + extension.lower()


def extension_from_mime(
    mime_type: Optional[str],
) -> str:
    """Return a suitable extension for a MIME type."""

    if not mime_type:
        return ""

    extension = mimetypes.guess_extension(
        mime_type.split(";")[0].strip()
    )

    return extension or ""


# ============================================================
# MEDIA INFO
# ============================================================

def get_media_info(
    path: str | Path,
) -> dict:
    """
    Return basic information about a local media file.
    """

    file_path = Path(path)

    size = get_file_size(file_path)
    mime_type = get_mime_type(file_path)

    return {
        "path": str(file_path),
        "filename": file_path.name,
        "extension": file_path.suffix.lower(),
        "size": size,
        "size_human": format_file_size(size),
        "mime_type": mime_type,
        "is_video": is_video_file(file_path),
        "is_audio": is_audio_file(file_path),
        "is_image": is_image_file(file_path),
    }


# ============================================================
# FILE VALIDATION
# ============================================================

def file_exists(
    path: str | Path,
) -> bool:
    """Check whether a path points to a regular file."""

    try:
        return Path(path).is_file()
    except (OSError, TypeError):
        return False


def validate_file_size(
    path: str | Path,
    max_size_mb: int,
) -> tuple[bool, int]:
    """
    Check whether a file is within the configured limit.

    Returns:
        (is_valid, actual_size_bytes)
    """

    size = get_file_size(path)

    if size <= 0:
        return False, size

    max_bytes = max_size_mb * 1024 * 1024

    return size <= max_bytes, size


# ============================================================
# DIRECTORY HELPERS
# ============================================================

def ensure_directory(
    directory: str | Path,
) -> Path:
    """Create a directory if necessary."""

    path = Path(directory)

    path.mkdir(
        parents=True,
        exist_ok=True,
    )

    return path


# ============================================================
# SAFE PATH CREATION
# ============================================================

def build_media_path(
    directory: str | Path,
    filename: str,
) -> Path:
    """
    Build a safe media path inside the supplied directory.

    The filename is sanitized before being used.
    """

    directory_path = ensure_directory(
        directory
    )

    safe_name = sanitize_filename(
        filename
    )

    return directory_path / safe_name
