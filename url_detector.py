from __future__ import annotations

import re
from enum import Enum
from urllib.parse import urlparse


class Platform(str, Enum):
    TERABOX = "terabox"
    INSTAGRAM = "instagram"
    UNKNOWN = "unknown"


# ------------------------------------------------------------
# Supported domains
# ------------------------------------------------------------

TERABOX_DOMAINS = {
    "terabox.com",
    "www.terabox.com",
    "terabox.app",
    "www.terabox.app",
    "1024tera.com",
    "www.1024tera.com",
    "teraboxlink.com",
    "www.teraboxlink.com",
}

INSTAGRAM_DOMAINS = {
    "instagram.com",
    "www.instagram.com",
    "m.instagram.com",
}


# ------------------------------------------------------------
# URL extraction
# ------------------------------------------------------------

URL_PATTERN = re.compile(
    r"https?://[^\s<>\"]+",
    re.IGNORECASE,
)


def extract_urls(text: str) -> list[str]:
    """
    Extract HTTP/HTTPS URLs from a Telegram message.

    Returns unique URLs while preserving their original order.
    """

    if not text:
        return []

    found = URL_PATTERN.findall(text)

    urls: list[str] = []
    seen: set[str] = set()

    for url in found:
        # Remove common punctuation accidentally attached
        # to a URL in a sentence.
        url = url.rstrip(
            ".,!?;:)]}>\"'"
        )

        if url and url not in seen:
            seen.add(url)
            urls.append(url)

    return urls


# ------------------------------------------------------------
# Domain helpers
# ------------------------------------------------------------

def normalize_hostname(hostname: str) -> str:
    """
    Normalize a hostname for reliable domain matching.
    """

    hostname = hostname.lower().strip()

    if hostname.endswith("."):
        hostname = hostname[:-1]

    return hostname


def is_domain_or_subdomain(
    hostname: str,
    domain: str,
) -> bool:
    """
    Check whether hostname equals domain or is a subdomain.

    Example:
        m.instagram.com -> instagram.com
    """

    hostname = normalize_hostname(hostname)
    domain = normalize_hostname(domain)

    return (
        hostname == domain
        or hostname.endswith("." + domain)
    )


# ------------------------------------------------------------
# Platform detection
# ------------------------------------------------------------

def detect_platform(url: str) -> Platform:
    """
    Detect the supported platform from a URL.

    This function only identifies the platform.
    It does NOT access the URL.
    """

    if not url:
        return Platform.UNKNOWN

    try:
        parsed = urlparse(url)

    except ValueError:
        return Platform.UNKNOWN

    if parsed.scheme.lower() not in {
        "http",
        "https",
    }:
        return Platform.UNKNOWN

    hostname = normalize_hostname(
        parsed.hostname or ""
    )

    if not hostname:
        return Platform.UNKNOWN

    for domain in TERABOX_DOMAINS:
        if is_domain_or_subdomain(
            hostname,
            domain,
        ):
            return Platform.TERABOX

    for domain in INSTAGRAM_DOMAINS:
        if is_domain_or_subdomain(
            hostname,
            domain,
        ):
            return Platform.INSTAGRAM

    return Platform.UNKNOWN


# ------------------------------------------------------------
# Platform checks
# ------------------------------------------------------------

def is_terabox_url(url: str) -> bool:
    """Return True when the URL belongs to TeraBox."""

    return detect_platform(url) == Platform.TERABOX


def is_instagram_url(url: str) -> bool:
    """Return True when the URL belongs to Instagram."""

    return detect_platform(url) == Platform.INSTAGRAM


def is_supported_url(url: str) -> bool:
    """Return True for any supported platform URL."""

    return detect_platform(url) != Platform.UNKNOWN


# ------------------------------------------------------------
# Instagram path validation
# ------------------------------------------------------------

INSTAGRAM_MEDIA_PATHS = (
    "/p/",
    "/reel/",
    "/reels/",
    "/tv/",
)


def looks_like_instagram_media_url(
    url: str,
) -> bool:
    """
    Check whether an Instagram URL looks like a normal
    media URL such as /p/ or /reel/.

    This is only a lightweight validation step.
    """

    if not is_instagram_url(url):
        return False

    try:
        path = urlparse(url).path.lower()

    except ValueError:
        return False

    return any(
        path.startswith(prefix)
        for prefix in INSTAGRAM_MEDIA_PATHS
    )


# ------------------------------------------------------------
# Human-readable platform name
# ------------------------------------------------------------

def platform_display_name(
    platform: Platform,
) -> str:
    """Return a user-friendly platform name."""

    names = {
        Platform.TERABOX: "TeraBox",
        Platform.INSTAGRAM: "Instagram",
        Platform.UNKNOWN: "Unknown",
    }

    return names[platform]


# ------------------------------------------------------------
# URL information
# ------------------------------------------------------------

def get_url_info(url: str) -> dict:
    """
    Return structured information about a URL.

    Example:

    {
        "url": "...",
        "platform": "instagram",
        "platform_name": "Instagram",
        "supported": True
    }
    """

    platform = detect_platform(url)

    return {
        "url": url,
        "platform": platform.value,
        "platform_name": platform_display_name(
            platform
        ),
        "supported": (
            platform != Platform.UNKNOWN
        ),
    }
