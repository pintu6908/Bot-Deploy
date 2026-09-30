from __future__ import annotations

import asyncio
import logging
import shutil
from pathlib import Path
from typing import Iterable


logger = logging.getLogger("media_bot.cleanup")


# ============================================================
# SINGLE FILE
# ============================================================

def remove_file(
    path: str | Path | None,
) -> bool:
    """
    Safely remove a single file.

    Returns True if removed, False if it did not exist
    or could not be removed.
    """

    if not path:
        return False

    file_path = Path(path)

    try:
        if not file_path.exists():
            return False

        if not file_path.is_file():
            return False

        file_path.unlink()

        logger.debug(
            "Removed temporary file: %s",
            file_path,
        )

        return True

    except OSError as exc:
        logger.warning(
            "Could not remove file %s: %s",
            file_path,
            exc,
        )

        return False


# ============================================================
# DIRECTORY
# ============================================================

def remove_directory(
    path: str | Path | None,
) -> bool:
    """
    Safely remove a directory and its contents.

    Use only for bot-owned temporary directories.
    """

    if not path:
        return False

    directory = Path(path)

    try:
        if not directory.exists():
            return False

        if not directory.is_dir():
            return False

        shutil.rmtree(directory)

        logger.debug(
            "Removed temporary directory: %s",
            directory,
        )

        return True

    except OSError as exc:
        logger.warning(
            "Could not remove directory %s: %s",
            directory,
            exc,
        )

        return False


# ============================================================
# MULTIPLE FILES
# ============================================================

def cleanup_files(
    paths: Iterable[str | Path],
) -> int:
    """
    Remove multiple files.

    Returns the number of successfully removed files.
    """

    removed = 0

    for path in paths:
        if remove_file(path):
            removed += 1

    return removed


# ============================================================
# USER TEMP DIRECTORY
# ============================================================

def cleanup_job_directory(
    base_directory: str | Path,
    job_id: str,
) -> bool:
    """
    Remove a single bot job directory.

    Expected structure:

        /tmp/telegram_media/
            <job_id>/
                video.mp4
                thumbnail.jpg
    """

    base = Path(base_directory)

    # job_id should be generated internally by the bot.
    # Reject suspicious path components.
    safe_job_id = Path(job_id).name

    if safe_job_id != job_id:
        logger.warning(
            "Rejected unsafe job ID: %r",
            job_id,
        )
        return False

    job_directory = base / safe_job_id

    return remove_directory(
        job_directory
    )


# ============================================================
# EMPTY DIRECTORY CLEANUP
# ============================================================

def cleanup_empty_directories(
    base_directory: str | Path,
) -> int:
    """
    Remove empty directories inside the supplied
    bot-owned temporary directory.

    Files are never deleted by this function.
    """

    base = Path(base_directory)

    if not base.exists() or not base.is_dir():
        return 0

    removed = 0

    try:
        directories = sorted(
            (
                item
                for item in base.rglob("*")
                if item.is_dir()
            ),
            key=lambda item: len(item.parts),
            reverse=True,
        )

        for directory in directories:
            try:
                directory.rmdir()

                removed += 1

            except OSError:
                # Directory is not empty or another process
                # currently uses it.
                continue

    except OSError as exc:
        logger.warning(
            "Could not scan temporary directory %s: %s",
            base,
            exc,
        )

    return removed


# ============================================================
# ASYNC WRAPPERS
# ============================================================

async def async_remove_file(
    path: str | Path | None,
) -> bool:
    """Async wrapper for remove_file."""

    return await asyncio.to_thread(
        remove_file,
        path,
    )


async def async_remove_directory(
    path: str | Path | None,
) -> bool:
    """Async wrapper for remove_directory."""

    return await asyncio.to_thread(
        remove_directory,
        path,
    )


async def async_cleanup_files(
    paths: Iterable[str | Path],
) -> int:
    """Async wrapper for cleanup_files."""

    return await asyncio.to_thread(
        cleanup_files,
        paths,
    )


async def async_cleanup_job_directory(
    base_directory: str | Path,
    job_id: str,
) -> bool:
    """Async wrapper for cleanup_job_directory."""

    return await asyncio.to_thread(
        cleanup_job_directory,
        base_directory,
        job_id,
    )
