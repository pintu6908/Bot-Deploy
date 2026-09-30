from __future__ import annotations


class MediaBotError(Exception):
    """Base exception for the media bot."""

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
    ) -> None:
        super().__init__(message)

        self.user_message = (
            user_message
            or message
        )


# ============================================================
# URL ERRORS
# ============================================================

class UnsupportedPlatformError(MediaBotError):
    """The supplied URL is not supported."""

    def __init__(
        self,
        message: str = "Unsupported platform.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "❌ Unsupported link.\n\n"
                "Please send a public TeraBox or "
                "Instagram media link."
            ),
        )


class InvalidURLError(MediaBotError):
    """The supplied URL is invalid."""

    def __init__(
        self,
        message: str = "Invalid URL.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "❌ That doesn't look like a valid "
                "media link.\n\n"
                "Please send the complete URL."
            ),
        )


# ============================================================
# RESOLVER ERRORS
# ============================================================

class ResolverError(MediaBotError):
    """Base resolver error."""

    def __init__(
        self,
        message: str = "Media resolver failed.",
        user_message: str | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message=(
                user_message
                or (
                    "❌ I couldn't resolve this link "
                    "right now.\n\n"
                    "Please try again later."
                )
            ),
        )


class GatewayUnavailableError(ResolverError):
    """The external gateway/resolver is unavailable."""

    def __init__(
        self,
        message: str = "Resolver gateway unavailable.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "⚠️ The media service is temporarily "
                "unavailable.\n\n"
                "Please try again in a few moments."
            ),
        )


class GatewayResponseError(ResolverError):
    """The gateway returned an unexpected response."""

    def __init__(
        self,
        message: str = "Invalid gateway response.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "❌ The media service returned an "
                "unexpected response.\n\n"
                "Please try another link."
            ),
        )


class MediaNotFoundError(ResolverError):
    """The requested media could not be found."""

    def __init__(
        self,
        message: str = "Media not found.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "❌ Media not found.\n\n"
                "The link may be expired, removed, "
                "or unavailable."
            ),
        )


class PrivateMediaError(ResolverError):
    """The media requires private/authenticated access."""

    def __init__(
        self,
        message: str = "Private or authenticated media.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "🔒 This media is private or requires "
                "login.\n\n"
                "Only publicly accessible media is supported."
            ),
        )


# ============================================================
# DOWNLOAD ERRORS
# ============================================================

class DownloadError(MediaBotError):
    """Base download error."""

    def __init__(
        self,
        message: str = "Download failed.",
        user_message: str | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message=(
                user_message
                or (
                    "❌ Download failed.\n\n"
                    "Please try again."
                )
            ),
        )


class DownloadTimeoutError(DownloadError):
    """Download timed out."""

    def __init__(
        self,
        message: str = "Download timed out.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "⏱️ The download timed out.\n\n"
                "Please try again."
            ),
        )


class FileTooLargeError(DownloadError):
    """Downloaded media exceeds configured limit."""

    def __init__(
        self,
        size_mb: float,
        max_mb: int,
    ) -> None:
        super().__init__(
            (
                f"Media is too large: "
                f"{size_mb:.2f} MB > {max_mb} MB"
            ),
            user_message=(
                "📦 This file is too large for the "
                "current bot limit.\n\n"
                f"Maximum allowed: {max_mb} MB"
            ),
        )


class EmptyFileError(DownloadError):
    """Downloaded file is empty or missing."""

    def __init__(
        self,
        message: str = "Downloaded file is empty.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "❌ The downloaded media is empty "
                "or unavailable."
            ),
        )


class CancelledError(MediaBotError):
    """User cancelled the current operation."""

    def __init__(
        self,
        message: str = "Operation cancelled.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "🛑 Operation cancelled."
            ),
        )


# ============================================================
# TELEGRAM ERRORS
# ============================================================

class TelegramSendError(MediaBotError):
    """Telegram rejected or failed to send media."""

    def __init__(
        self,
        message: str = "Telegram media upload failed.",
    ) -> None:
        super().__init__(
            message,
            user_message=(
                "❌ Telegram couldn't send this media.\n\n"
                "The file may be too large or use an "
                "unsupported format."
            ),
        )


# ============================================================
# ERROR FORMATTER
# ============================================================

def get_user_error_message(
    error: Exception,
) -> str:
    """
    Convert an exception into a safe user-facing message.

    Internal exceptions should never expose API keys,
    tokens, URLs containing secrets, or Python tracebacks.
    """

    if isinstance(
        error,
        MediaBotError,
    ):
        return error.user_message

    return (
        "❌ Something went wrong while processing "
        "your request.\n\n"
        "Please try again."
    )
