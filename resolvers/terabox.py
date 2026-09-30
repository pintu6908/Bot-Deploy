from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

import aiohttp

from config import (
    REQUEST_TIMEOUT,
    TERABOX_GATEWAY_API_KEY,
    TERABOX_GATEWAY_URL,
)
from utils.errors import (
    GatewayResponseError,
    GatewayUnavailableError,
    InvalidURLError,
    MediaNotFoundError,
    PrivateMediaError,
)
from utils.url_detector import is_terabox_url


logger = logging.getLogger("media_bot.terabox")


# ============================================================
# NORMALIZED MEDIA RESULT
# ============================================================

@dataclass
class MediaResult:
    """Normalized media information returned by a resolver."""

    platform: str
    source_url: str

    title: str = "TeraBox Media"
    media_url: str | None = None
    thumbnail_url: str | None = None

    filename: str | None = None
    mime_type: str | None = None

    size: int | None = None
    duration: float | None = None

    direct_play: bool = False


# ============================================================
# TERABox RESOLVER
# ============================================================

class TeraBoxResolver:
    """
    Resolve public TeraBox sharing links through a configured
    TeraBox Gateway service.

    The Gateway URL is intentionally configurable because the
    exact API contract can differ between Gateway projects.

    No TeraBox login credentials are handled here.
    """

    platform = "terabox"

    def __init__(
        self,
        gateway_url: str | None = None,
        api_key: str | None = None,
        timeout: int | None = None,
    ) -> None:

        self.gateway_url = (
            gateway_url or TERABOX_GATEWAY_URL
        ).strip().rstrip("/")

        self.api_key = (
            api_key
            if api_key is not None
            else TERABOX_GATEWAY_API_KEY
        ).strip()

        self.timeout_seconds = (
            timeout
            if timeout is not None
            else REQUEST_TIMEOUT
        )

    # --------------------------------------------------------
    # Public API
    # --------------------------------------------------------

    async def resolve(
        self,
        url: str,
    ) -> MediaResult:
        """
        Resolve a TeraBox public sharing URL.

        Raises:
            InvalidURLError
            GatewayUnavailableError
            GatewayResponseError
            MediaNotFoundError
            PrivateMediaError
        """

        if not url or not is_terabox_url(url):
            raise InvalidURLError(
                "URL is not recognized as a TeraBox URL."
            )

        if not self.gateway_url:
            raise GatewayUnavailableError(
                "TERABOX_GATEWAY_URL is not configured."
            )

        payload = await self._request_gateway(
            url
        )

        return self._normalize_response(
            source_url=url,
            payload=payload,
        )

    # --------------------------------------------------------
    # Gateway request
    # --------------------------------------------------------

    async def _request_gateway(
        self,
        source_url: str,
    ) -> Any:
        """
        Call the configured Gateway.

        The current implementation tries a small set of
        conventional API paths. The exact endpoint can be
        restricted to one known path later once the Gateway
        contract is confirmed.
        """

        timeout = aiohttp.ClientTimeout(
            total=self.timeout_seconds
        )

        headers = {
            "Accept": "application/json",
            "User-Agent": (
                "TelegramMediaBot/1.0"
            ),
        }

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        # Common resolver endpoint names.
        # These are attempted only when the configured Gateway
        # does not itself include an API path.
        candidate_urls = self._candidate_endpoints()

        last_error: Exception | None = None

        try:
            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers,
            ) as session:

                for endpoint in candidate_urls:
                    try:
                        logger.info(
                            "Requesting TeraBox Gateway: %s",
                            endpoint,
                        )

                        async with session.post(
                            endpoint,
                            json={
                                "url": source_url,
                            },
                        ) as response:

                            content_type = (
                                response.headers.get(
                                    "Content-Type",
                                    "",
                                ).lower()
                            )

                            body = await response.text()

                            if response.status >= 500:
                                last_error = RuntimeError(
                                    f"Gateway HTTP "
                                    f"{response.status}"
                                )
                                continue

                            if response.status in {
                                401,
                                403,
                            }:
                                raise PrivateMediaError(
                                    "Gateway rejected "
                                    "authenticated access."
                                )

                            if response.status == 404:
                                last_error = RuntimeError(
                                    "Gateway endpoint "
                                    "returned 404."
                                )
                                continue

                            if response.status >= 400:
                                last_error = RuntimeError(
                                    f"Gateway HTTP "
                                    f"{response.status}: "
                                    f"{body[:300]}"
                                )
                                continue

                            if (
                                "application/json"
                                not in content_type
                            ):
                                last_error = GatewayResponseError(
                                    "Gateway did not return JSON."
                                )
                                continue

                            try:
                                return await response.json(
                                    content_type=None
                                )

                            except Exception as exc:
                                last_error = exc
                                continue

                    except asyncio.TimeoutError as exc:
                        last_error = exc
                        continue

                    except aiohttp.ClientError as exc:
                        last_error = exc
                        continue

        except aiohttp.ClientError as exc:
            raise GatewayUnavailableError(
                str(exc)
            ) from exc

        if last_error:
            logger.error(
                "TeraBox Gateway failed: %s",
                last_error,
            )

        raise GatewayUnavailableError(
            "No usable TeraBox Gateway endpoint "
            "responded successfully."
        )

    # --------------------------------------------------------
    # Candidate endpoints
    # --------------------------------------------------------

    def _candidate_endpoints(self) -> list[str]:
        """
        Build possible Gateway endpoints.

        If TERABOX_GATEWAY_URL already contains a path such as
        /api/resolve, use it directly.

        Otherwise try common resolver paths.
        """

        base = self.gateway_url

        parsed_path = ""

        try:
            from urllib.parse import urlparse

            parsed_path = (
                urlparse(base).path or ""
            ).rstrip("/")

        except Exception:
            parsed_path = ""

        # If the configured URL already looks like a concrete
        # endpoint, don't append additional paths.
        endpoint_markers = (
            "/api/",
            "/resolve",
            "/download",
            "/v1/",
        )

        if any(
            marker in parsed_path
            for marker in endpoint_markers
        ):
            return [base]

        candidates = [
            urljoin(
                base + "/",
                "api/resolve",
            ),
            urljoin(
                base + "/",
                "resolve",
            ),
            urljoin(
                base + "/",
                "api",
            ),
        ]

        # Preserve order while removing duplicates.
        return list(
            dict.fromkeys(candidates)
        )

    # --------------------------------------------------------
    # Response normalization
    # --------------------------------------------------------

    def _normalize_response(
        self,
        *,
        source_url: str,
        payload: Any,
    ) -> MediaResult:
        """
        Normalize different Gateway JSON response structures.

        Supported common forms include:

        {
            "url": "...",
            "download_url": "...",
            "title": "..."
        }

        or:

        {
            "data": {
                "url": "...",
                "thumbnail": "..."
            }
        }

        or:

        {
            "data": [
                {...}
            ]
        }
        """

        if not isinstance(payload, dict):
            raise GatewayResponseError(
                "Gateway response is not a JSON object."
            )

        # Handle explicit API-level errors.
        if self._looks_like_error(payload):
            message = self._extract_error(payload)

            raise MediaNotFoundError(
                message
            )

        data = payload.get("data")

        if isinstance(data, list):
            if not data:
                raise MediaNotFoundError(
                    "Gateway returned an empty media list."
                )

            data = data[0]

        if isinstance(data, dict):
            merged = {
                **payload,
                **data,
            }
        else:
            merged = payload

        media_url = self._find_first_string(
            merged,
            (
                "download_url",
                "downloadUrl",
                "direct_url",
                "directUrl",
                "media_url",
                "mediaUrl",
                "video_url",
                "videoUrl",
                "url",
            ),
        )

        thumbnail_url = self._find_first_string(
            merged,
            (
                "thumbnail",
                "thumbnail_url",
                "thumbnailUrl",
                "thumb",
                "cover",
                "cover_url",
                "coverUrl",
            ),
        )

        title = self._find_first_string(
            merged,
            (
                "title",
                "name",
                "filename",
                "file_name",
            ),
        ) or "TeraBox Media"

        filename = self._find_first_string(
            merged,
            (
                "filename",
                "file_name",
                "fileName",
            ),
        )

        mime_type = self._find_first_string(
            merged,
            (
                "mime_type",
                "mimeType",
                "content_type",
                "contentType",
            ),
        )

        size = self._find_number(
            merged,
            (
                "size",
                "file_size",
                "fileSize",
                "content_length",
                "contentLength",
            ),
        )

        duration = self._find_number(
            merged,
            (
                "duration",
                "duration_seconds",
                "durationSeconds",
            ),
        )

        if not media_url:
            raise MediaNotFoundError(
                "Gateway returned no direct media URL."
            )

        return MediaResult(
            platform=self.platform,
            source_url=source_url,
            title=title,
            media_url=media_url,
            thumbnail_url=thumbnail_url,
            filename=filename,
            mime_type=mime_type,
            size=size,
            duration=duration,
            direct_play=True,
        )

    # --------------------------------------------------------
    # JSON helpers
    # --------------------------------------------------------

    @staticmethod
    def _find_first_string(
        data: dict,
        keys: tuple[str, ...],
    ) -> str | None:

        for key in keys:
            value = data.get(key)

            if isinstance(value, str):
                value = value.strip()

                if value:
                    return value

        return None

    @staticmethod
    def _find_number(
        data: dict,
        keys: tuple[str, ...],
    ) -> int | float | None:

        for key in keys:
            value = data.get(key)

            if isinstance(value, bool):
                continue

            if isinstance(
                value,
                (int, float),
            ):
                return value

            if isinstance(value, str):
                try:
                    return float(value)

                except ValueError:
                    continue

        return None

    @staticmethod
    def _looks_like_error(
        payload: dict,
    ) -> bool:

        if payload.get("success") is False:
            return True

        status = payload.get("status")

        if isinstance(status, str):
            if status.lower() in {
                "error",
                "failed",
                "failure",
            }:
                return True

        return False

    @staticmethod
    def _extract_error(
        payload: dict,
    ) -> str:

        for key in (
            "error",
            "message",
            "detail",
            "reason",
        ):
            value = payload.get(key)

            if isinstance(value, str):
                return value[:500]

            if isinstance(value, dict):
                message = value.get(
                    "message"
                )

                if isinstance(
                    message,
                    str,
                ):
                    return message[:500]

        return "TeraBox media could not be resolved."
