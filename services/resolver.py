from __future__ import annotations

import logging

from resolvers.instagram import InstagramResolver
from resolvers.terabox import MediaResult, TeraBoxResolver
from utils.errors import (
    InvalidURLError,
    UnsupportedPlatformError,
)
from utils.url_detector import (
    detect_platform,
    is_supported_url,
)

logger = logging.getLogger(__name__)


class ResolverService:
    """
    Central resolver service.

    Detects the platform from a URL and sends it to the
    correct platform-specific resolver.
    """

    def __init__(self) -> None:
        self.terabox = TeraBoxResolver()
        self.instagram = InstagramResolver()

    async def resolve(self, url: str) -> MediaResult:
        """
        Resolve a supported URL into normalized media information.
        """

        url = url.strip()

        if not url:
            raise InvalidURLError("URL is empty.")

        if not is_supported_url(url):
            raise UnsupportedPlatformError(
                "The provided URL is not a supported media URL."
            )

        platform = detect_platform(url)

        logger.info(
            "Resolving media | platform=%s | url=%s",
            platform.value,
            url,
        )

        if platform.value == "terabox":
            return await self.terabox.resolve(url)

        if platform.value == "instagram":
            return await self.instagram.resolve(url)

        raise UnsupportedPlatformError(
            f"Unsupported platform: {platform.value}"
        )

    async def resolve_terabox(self, url: str) -> MediaResult:
        """Resolve a TeraBox URL directly."""
        return await self.terabox.resolve(url)

    async def resolve_instagram(self, url: str) -> MediaResult:
        """Resolve an Instagram URL directly."""
        return await self.instagram.resolve(url)
