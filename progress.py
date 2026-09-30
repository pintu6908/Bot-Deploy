from __future__ import annotations

import asyncio
import time
from typing import Optional

from telegram import Message


def format_bytes(value: Optional[float]) -> str:
    """Convert bytes into a human-readable size."""

    if value is None or value < 0:
        return "Unknown"

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ]

    size = float(value)

    for unit in units:
        if size < 1024:
            return f"{size:.1f} {unit}"

        size /= 1024

    return f"{size:.1f} PB"


def format_speed(bytes_per_second: Optional[float]) -> str:
    """Format download speed."""

    if not bytes_per_second or bytes_per_second <= 0:
        return "—"

    return f"{format_bytes(bytes_per_second)}/s"


def format_eta(seconds: Optional[float]) -> str:
    """Format estimated remaining time."""

    if seconds is None or seconds < 0:
        return "—"

    seconds = int(seconds)

    if seconds < 60:
        return f"{seconds}s"

    minutes, seconds = divmod(seconds, 60)

    if minutes < 60:
        return f"{minutes}m {seconds}s"

    hours, minutes = divmod(minutes, 60)

    return f"{hours}h {minutes}m"


def make_progress_bar(
    percent: float,
    length: int = 12,
) -> str:
    """
    Create a simple text progress bar.

    Example:
    ███████░░░░░ 58%
    """

    percent = max(
        0.0,
        min(100.0, percent),
    )

    filled = round(
        length * percent / 100
    )

    empty = length - filled

    return (
        "█" * filled
        + "░" * empty
    )


def build_progress_text(
    *,
    status: str,
    percent: Optional[float] = None,
    downloaded: Optional[float] = None,
    total: Optional[float] = None,
    speed: Optional[float] = None,
    eta: Optional[float] = None,
) -> str:
    """Build a Telegram-friendly progress message."""

    lines = [
        f"📥 {status}",
        "",
    ]

    if percent is not None:
        percent = max(
            0.0,
            min(100.0, percent),
        )

        lines.append(
            f"{make_progress_bar(percent)} "
            f"{percent:.1f}%"
        )

    if downloaded is not None:
        downloaded_text = format_bytes(
            downloaded
        )

        if total is not None and total > 0:
            total_text = format_bytes(total)

            lines.append(
                f"📦 {downloaded_text} / {total_text}"
            )
        else:
            lines.append(
                f"📦 {downloaded_text}"
            )

    if speed is not None:
        lines.append(
            f"⚡ Speed: {format_speed(speed)}"
        )

    if eta is not None:
        lines.append(
            f"⏳ ETA: {format_eta(eta)}"
        )

    return "\n".join(lines)


class TelegramProgress:
    """
    Rate-limited Telegram progress updater.

    This prevents the bot from editing a Telegram message
    hundreds of times per second.
    """

    def __init__(
        self,
        message: Message,
        update_interval: float = 2.0,
    ) -> None:
        self.message = message
        self.update_interval = max(
            0.5,
            update_interval,
        )

        self.last_update = 0.0
        self.last_text = ""

        self._lock = asyncio.Lock()

    async def update(
        self,
        *,
        status: str,
        percent: Optional[float] = None,
        downloaded: Optional[float] = None,
        total: Optional[float] = None,
        speed: Optional[float] = None,
        eta: Optional[float] = None,
        force: bool = False,
    ) -> None:
        """
        Update the Telegram message if enough time has passed.
        """

        text = build_progress_text(
            status=status,
            percent=percent,
            downloaded=downloaded,
            total=total,
            speed=speed,
            eta=eta,
        )

        now = time.monotonic()

        if not force:
            if now - self.last_update < self.update_interval:
                return

            if text == self.last_text:
                return

        async with self._lock:
            now = time.monotonic()

            if not force:
                if (
                    now - self.last_update
                    < self.update_interval
                ):
                    return

                if text == self.last_text:
                    return

            try:
                await self.message.edit_text(text)

            except Exception:
                # Telegram may reject an edit when the message
                # has not changed or when a temporary API issue
                # occurs. Do not crash the download task.
                return

            self.last_update = now
            self.last_text = text

    async def complete(
        self,
        text: str = "✅ Download completed!",
    ) -> None:
        """Force a final progress update."""

        try:
            await self.message.edit_text(text)

        except Exception:
            return

        self.last_update = time.monotonic()
        self.last_text = text

    async def error(
        self,
        text: str = "❌ Something went wrong.",
    ) -> None:
        """Show a final error message."""

        try:
            await self.message.edit_text(text)

        except Exception:
            return

        self.last_update = time.monotonic()
        self.last_text = text
