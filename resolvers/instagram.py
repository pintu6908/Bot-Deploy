from __future__ import annotations

import asyncio
import logging
from typing import Any

import yt_dlp

from utils.errors import (
    InvalidURLError,
    MediaNotFoundError,
    PrivateMediaError,
    ResolverError,
)
from utils.url_detector import (
    is_instagram_url,
    looks_like_instagram_media_url,
)

from resolvers.terabox import MediaResult


logger = logging.getLogger("media_bot.instagram")


class InstagramResolver:
    """
    Resolve publicly accessible Instagram media URLs.

    Supported examples:
        https://www.instagram.com/reel/...
        https://www.instagram.com/p/...
        https://www.instagram.com/reels/...

    This resolver does not attempt to bypass:
        - private accounts
        - login requirements
        - OTP
        - authentication controls
    """

    platform = "instagram"

    def __init__(
        self,
        timeout: int = 60,
    ) -> None:
        self.timeout = timeout

    # ========================================================
    # PUBLIC API
    # ========================================================

    async def resolve(
        self,
        url: str,
    ) -> MediaResult:
        """Resolve an Instagram public media URL."""

        if not url or not is_instagram_url(url):
            raise InvalidURLError(
                "URL is not an Instagram URL."
            )

        if not looks_like_instagram_media_url(url):
            raise InvalidURLError(
                "URL does not look like an Instagram "
                "post or reel URL."
            )

        try:
            info = await asyncio.wait_for(
                asyncio.to_thread(
                    self._extract_info,
                    url,
                ),
                timeout=self.timeout,
            )

        except asyncio.TimeoutError as exc:
            raise ResolverError(
                "Instagram extraction timed out.",
                user_message=(
                    "⏱️ Instagram took too long to respond.\n\n"
                    "Please try again."
                ),
            ) from exc

        except yt_dlp.utils.DownloadError as exc:
            message = str(exc)

            if self._looks_private(message):
                raise PrivateMediaError(
                    "Instagram media appears to require "
                    "authentication."
                ) from exc

            logger.warning(
                "Instagram extraction failed: %s",
                message,
            )

            raise MediaNotFoundError(
                "Instagram media could not be extracted."
            ) from exc

        except Exception as exc:
            logger.exception(
                "Unexpected Instagram resolver error."
            )

            raise ResolverError(
                "Unexpected Instagram resolver error."
            ) from exc

        if not isinstance(info, dict):
            raise ResolverError(
                "Instagram extractor returned invalid data."
            )

        media_url = self._select_media_url(
            info
        )

        if not media_url:
            raise MediaNotFoundError(
                "No usable Instagram media URL was found."
            )

        title = (
            info.get("title")
            or info.get("description")
            or "Instagram Media"
        )

        thumbnail = info.get(
            "thumbnail"
        )

        filename = self._build_filename(
            info
        )

        mime_type = info.get(
            "ext"
        )

        if mime_type:
            mime_type = (
                f"video/{mime_type}"
            )

        return MediaResult(
            platform=self.platform,
            source_url=url,
            title=str(title)[:500],
            media_url=media_url,
            thumbnail_url=(
                str(thumbnail)
                if thumbnail
                else None
            ),
            filename=filename,
            mime_type=mime_type,
            size=self._number(
                info.get("filesize")
            )
            or self._number(
                info.get("filesize_approx")
            ),
            duration=self._number(
                info.get("duration")
            ),
            direct_play=True,
        )

    # ========================================================
    # YT-DLP EXTRACTION
    # ========================================================

    @staticmethod
    def _extract_info(
        url: str,
    ) -> dict[str, Any]:
        """
        Extract metadata without downloading the media.

        The actual download will be handled later by the
        downloader service.
        """

        options = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "noplaylist": True,

            # Do not use cookies or account credentials.
            "cookiefile": None,

            # Keep network behaviour conservative.
            "retries": 2,
            "fragment_retries": 2,
        }

        with yt_dlp.YoutubeDL(
            options
        ) as ydl:

            info = ydl.extract_info(
                url,
                download=False,
            )

        if not info:
            raise yt_dlp.utils.DownloadError(
                "No media information returned."
            )

        return info

    # ========================================================
    # MEDIA URL SELECTION
    # ========================================================

    @staticmethod
    def _select_media_url(
        info: dict[str, Any],
    ) -> str | None:
        """
        Select a direct media URL.

        Prefer a combined format when available so the
        resulting URL can be used directly for playback.
        """

        direct_url = info.get("url")

        if isinstance(
            direct_url,
            str,
        ) and direct_url.startswith(
            ("http://", "https://")
        ):
            return direct_url

        formats = info.get(
            "formats"
        )

        if not isinstance(
            formats,
            list,
        ):
            return None

        candidates = []

        for fmt in formats:
            if not isinstance(
                fmt,
                dict,
            ):
                continue

            url = fmt.get("url")

            if not isinstance(
                url,
                str,
            ):
                continue

            if not url.startswith(
                ("http://", "https://")
            ):
                continue

            candidates.append(fmt)

        if not candidates:
            return None

        # Prefer formats containing both video and audio.
        combined = [
            fmt
            for fmt in candidates
            if fmt.get("vcodec") not in {
                None,
                "none",
            }
            and fmt.get("acodec") not in {
                None,
                "none",
            }
        ]

        pool = combined or candidates

        # Prefer higher resolution while keeping the logic
        # deterministic.
        pool.sort(
            key=lambda item: (
                InstagramResolver._number(
                    item.get("height")
                ) or 0,
                InstagramResolver._number(
                    item.get("tbr")
                ) or 0,
            ),
            reverse=True,
        )

        return pool[0].get("url")

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _build_filename(
        info: dict[str, Any],
    ) -> str:

        ext = str(
            info.get("ext")
            or "mp4"
        ).lower()

        if not ext.isalnum():
            ext = "mp4"

        video_id = (
            info.get("id")
            or "instagram_media"
        )

        return (
            f"instagram_{video_id}.{ext}"
        )

    @staticmethod
    def _number(
        value: Any,
    ) -> int | float | None:

        if isinstance(
            value,
            bool,
        ):
            return None

        if isinstance(
            value,
            (int, float),
        ):
            return value

        if isinstance(
            value,
            str,
        ):
            try:
                return float(value)

            except ValueError:
                return None

        return None

    @staticmethod
    def _looks_private(
        message: str,
    ) -> bool:

        message = message.lower()

        indicators = (
            "login required",
            "log in",
            "private",
            "authentication",
            "sign in",
            "cookie",
            "requested content is not available",
        )

        return any(
            item in message
            for item in indicators
        )
