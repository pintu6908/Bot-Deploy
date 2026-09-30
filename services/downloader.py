from __future__ import annotations

import asyncio
import logging
import mimetypes
from pathlib import Path
from urllib.parse import urlparse

import aiohttp

from config import (
    MAX_DOWNLOAD_MB,
    REQUEST_TIMEOUT,
)
from utils.errors import (
    DownloadError,
    DownloadTimeoutError,
    EmptyFileError,
    FileTooLargeError,
)
from utils.media import (
    ensure_directory,
    get_safe_media_path,
    validate_media_file,
)
from utils.progress import TelegramProgress

logger = logging.getLogger(__name__)

MAX_DOWNLOAD_BYTES = MAX_DOWNLOAD_MB * 1024 * 1024


class MediaDownloader:
    """
    Downloads resolved media files to a temporary job directory.

    Features:
    - Streaming download
    - Download size limit
    - Timeout handling
    - Telegram progress updates
    - Safe filenames
    """

    def __init__(self) -> None:
        self.timeout = aiohttp.ClientTimeout(
            total=None,
            connect=REQUEST_TIMEOUT,
            sock_connect=REQUEST_TIMEOUT,
            sock_read=REQUEST_TIMEOUT,
        )

    async def download(
        self,
        url: str,
        output_dir: Path,
        filename: str | None = None,
        progress: TelegramProgress | None = None,
    ) -> Path:
        """
        Download a media URL and return the local file path.
        """

        if not url:
            raise DownloadError("Media URL is empty.")

        ensure_directory(output_dir)

        if not filename:
            filename = self._filename_from_url(url)

        output_path = get_safe_media_path(
            output_dir,
            filename,
        )

        logger.info("Starting media download: %s", url)

        try:
            return await self._download_http(
                url=url,
                output_path=output_path,
                progress=progress,
            )

        except asyncio.TimeoutError as exc:
            self._remove_partial_file(output_path)
            raise DownloadTimeoutError(
                "The media download timed out."
            ) from exc

        except aiohttp.ClientError as exc:
            self._remove_partial_file(output_path)
            raise DownloadError(
                "Unable to connect to the media server."
            ) from exc

        except (DownloadError, FileTooLargeError, EmptyFileError):
            self._remove_partial_file(output_path)
            raise

        except Exception as exc:
            self._remove_partial_file(output_path)
            logger.exception("Unexpected download error")
            raise DownloadError(
                "An unexpected error occurred while downloading the media."
            ) from exc

    async def _download_http(
        self,
        url: str,
        output_path: Path,
        progress: TelegramProgress | None = None,
    ) -> Path:

        headers = {
            "User-Agent": (
                "Mozilla/5.0 "
                "(Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            ),
            "Accept": "*/*",
        }

        async with aiohttp.ClientSession(
            timeout=self.timeout,
            headers=headers,
        ) as session:

            async with session.get(
                url,
                allow_redirects=True,
            ) as response:

                if response.status >= 400:
                    raise DownloadError(
                        f"Media server returned HTTP {response.status}."
                    )

                content_length = response.headers.get("Content-Length")

                total_size: int | None = None

                if content_length:
                    try:
                        total_size = int(content_length)
                    except ValueError:
                        total_size = None

                if (
                    total_size is not None
                    and total_size > MAX_DOWNLOAD_BYTES
                ):
                    raise FileTooLargeError(
                        f"Media exceeds the {MAX_DOWNLOAD_MB} MB limit."
                    )

                downloaded = 0

                with output_path.open("wb") as file:

                    async for chunk in response.content.iter_chunked(
                        1024 * 256
                    ):
                        if not chunk:
                            continue

                        downloaded += len(chunk)

                        if downloaded > MAX_DOWNLOAD_BYTES:
                            raise FileTooLargeError(
                                f"Media exceeds the {MAX_DOWNLOAD_MB} MB limit."
                            )

                        file.write(chunk)

                        if progress:
                            await progress.update(
                                current=downloaded,
                                total=total_size,
                            )

        if not output_path.exists():
            raise EmptyFileError("Downloaded file does not exist.")

        if output_path.stat().st_size <= 0:
            raise EmptyFileError("Downloaded file is empty.")

        validate_media_file(output_path)

        if progress:
            await progress.complete(
                total=output_path.stat().st_size
            )

        logger.info(
            "Download completed | file=%s | size=%d",
            output_path,
            output_path.stat().st_size,
        )

        return output_path

    @staticmethod
    def _filename_from_url(url: str) -> str:
        """
        Try to generate a reasonable filename from the URL.
        """

        try:
            path = urlparse(url).path
            name = Path(path).name

            if name and "." in name:
                return name

        except Exception:
            pass

        content_type = mimetypes.guess_extension(
            "application/octet-stream"
        )

        return f"media{content_type or '.bin'}"

    @staticmethod
    def _remove_partial_file(path: Path) -> None:
        try:
            if path.exists():
                path.unlink()
        except OSError:
            logger.warning(
                "Could not remove partial download: %s",
                path,
                          )
