from __future__ import annotations

import logging
import uuid
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from services import ResolverService
from utils.errors import (
    InvalidURLError,
    MediaBotError,
    PrivateMediaError,
    UnsupportedPlatformError,
)
from utils.url_detector import (
    detect_platform,
    extract_urls,
    is_supported_url,
)

logger = logging.getLogger(__name__)

resolver_service = ResolverService()


async def media_url_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle normal text messages containing media URLs.
    """

    if not update.message:
        return

    text = (update.message.text or "").strip()

    if not text:
        return

    urls = extract_urls(text)

    if not urls:
        await update.message.reply_text(
            "❌ I couldn't find a supported URL.\n\n"
            "Please send a public TeraBox or Instagram link."
        )
        return

    # Use the first supported URL from the message.
    source_url = None

    for url in urls:
        if is_supported_url(url):
            source_url = url
            break

    if not source_url:
        await update.message.reply_text(
            "❌ Unsupported link.\n\n"
            "Currently supported:\n"
            "• TeraBox\n"
            "• Instagram"
        )
        return

    platform = detect_platform(source_url)

    status_message = await update.message.reply_text(
        "🔎 <b>Checking your link...</b>\n\n"
        f"Platform: <b>{platform.value.title()}</b>\n"
        "Please wait...",
        parse_mode="HTML",
        disable_web_page_preview=True,
    )

    try:
        result = await resolver_service.resolve(source_url)

        # Generate a short temporary job ID.
        job_id = uuid.uuid4().hex[:12]

        # Store the resolved result in Telegram's per-user chat data.
        if context.chat_data is not None:
            context.chat_data["media_job"] = {
                "job_id": job_id,
                "source_url": result.source_url,
                "platform": result.platform,
                "title": result.title,
                "media_url": result.media_url,
                "thumbnail_url": result.thumbnail_url,
                "filename": result.filename,
                "mime_type": result.mime_type,
                "size": result.size,
                "duration": result.duration,
                "direct_play": result.direct_play,
            }

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "▶️ Play",
                        callback_data=f"play:{job_id}",
                    ),
                    InlineKeyboardButton(
                        "⬇️ Download",
                        callback_data=f"download:{job_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "❌ Cancel",
                        callback_data=f"cancel:{job_id}",
                    )
                ],
            ]
        )

        info_lines = [
            "✅ <b>Media found!</b>",
            "",
            f"🌐 Platform: <b>{result.platform.title()}</b>",
        ]

        if result.title:
            info_lines.append(
                f"🎬 Title: <b>{_escape_html(result.title)}</b>"
            )

        if result.filename:
            info_lines.append(
                f"📁 File: <code>{_escape_html(result.filename)}</code>"
            )

        if result.size:
            info_lines.append(
                f"💾 Size: <b>{_format_size(result.size)}</b>"
            )

        if result.duration:
            info_lines.append(
                f"⏱ Duration: <b>{_format_duration(result.duration)}</b>"
            )

        info_lines.extend(
            [
                "",
                "Choose what you want to do:",
            ]
        )

        await status_message.edit_text(
            "\n".join(info_lines),
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True,
        )

    except PrivateMediaError:
        await status_message.edit_text(
            "🔒 <b>Private or protected media</b>\n\n"
            "This bot only supports publicly accessible media.",
            parse_mode="HTML",
        )

    except (InvalidURLError, UnsupportedPlatformError):
        await status_message.edit_text(
            "❌ <b>Unsupported link</b>\n\n"
            "Please send a valid public TeraBox or Instagram media URL.",
            parse_mode="HTML",
        )

    except MediaBotError as exc:
        logger.warning(
            "Media resolution failed: %s",
            exc,
        )

        await status_message.edit_text(
            "❌ <b>Could not resolve this media</b>\n\n"
            "The link may be unavailable, expired, private, "
            "or the resolver service may be temporarily unavailable.",
            parse_mode="HTML",
        )

    except Exception:
        logger.exception("Unexpected media handler error")

        await status_message.edit_text(
            "⚠️ <b>Something went wrong</b>\n\n"
            "Please try the link again later.",
            parse_mode="HTML",
        )


def _format_size(size: int) -> str:
    """Convert bytes to a readable size."""

    value = float(size)

    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"

        value /= 1024

    return f"{value:.1f} PB"


def _format_duration(duration: float) -> str:
    """Convert seconds to HH:MM:SS or MM:SS."""

    seconds = max(0, int(duration))

    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"


def _escape_html(value: str) -> str:
    """Escape user/media-provided text for Telegram HTML."""

    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        )
