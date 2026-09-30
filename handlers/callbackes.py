from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from telegram import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import ContextTypes

from config import (
    CLEANUP_AFTER_SEND,
    DOWNLOAD_DIR,
    MAX_DOWNLOAD_MB,
)
from services import MediaDownloader, TelegramSender
from utils.cleanup import cleanup_job_directory
from utils.errors import MediaBotError
from utils.progress import TelegramProgress

logger = logging.getLogger(__name__)

downloader = MediaDownloader()
sender = TelegramSender()


async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Handle Play, Download and Cancel callback buttons.
    """

    query = update.callback_query

    if not query:
        return

    await query.answer()

    data = query.data or ""

    if ":" not in data:
        await query.edit_message_text(
            "❌ Invalid button action."
        )
        return

    action, job_id = data.split(":", 1)

    if action == "cancel":
        await cancel_media(query, context, job_id)
        return

    if action == "play":
        await process_media(
            query=query,
            context=context,
            job_id=job_id,
            mode="play",
        )
        return

    if action == "download":
        await process_media(
            query=query,
            context=context,
            job_id=job_id,
            mode="download",
        )
        return

    await query.edit_message_text(
        "❌ Unknown action."
    )


async def process_media(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    job_id: str,
    mode: str,
) -> None:
    """
    Download the resolved media and send it to Telegram.
    """

    if context.chat_data is None:
        await query.edit_message_text(
            "❌ Media session expired. Please send the link again."
        )
        return

    job = context.chat_data.get("media_job")

    if not job:
        await query.edit_message_text(
            "❌ Media session expired.\n\n"
            "Please send the link again."
        )
        return

    if job.get("job_id") != job_id:
        await query.edit_message_text(
            "❌ This button has expired."
        )
        return

    media_url = job.get("media_url")

    if not media_url:
        await query.edit_message_text(
            "❌ No downloadable media URL was returned."
        )
        return

    chat_id = query.message.chat_id if query.message else None

    if chat_id is None:
        return

    job_directory = (
        Path(DOWNLOAD_DIR)
        / f"{chat_id}_{uuid.uuid4().hex[:12]}"
    )

    job_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    progress = TelegramProgress(
        message=query.message,
        enabled=True,
    )

    action_text = (
        "▶️ Preparing playable video..."
        if mode == "play"
        else "⬇️ Preparing your download..."
    )

    try:
        await query.edit_message_text(
            f"{action_text}\n\n"
            "⏳ Starting download..."
        )

        filename = job.get("filename")

        file_path = await downloader.download(
            url=media_url,
            output_dir=job_directory,
            filename=filename,
            progress=progress,
        )

        size_mb = file_path.stat().st_size / (
            1024 * 1024
        )

        if size_mb > MAX_DOWNLOAD_MB:
            raise MediaBotError(
                "Downloaded file exceeds the configured size limit."
            )

        caption = _build_caption(job)

        # Delete the status message before sending the media.
        try:
            await query.message.delete()
        except Exception:
            logger.debug(
                "Could not delete status message.",
                exc_info=True,
            )

        await sender.send_media(
            update=Update(
                update_id=0,
                message=query.message,
            ),
            context=context,
            file_path=file_path,
            caption=caption,
            thumbnail=job.get("thumbnail_url"),
        )

    except MediaBotError as exc:
        logger.warning(
            "Media processing failed: %s",
            exc,
        )

        try:
            await query.edit_message_text(
                "❌ <b>Media processing failed</b>\n\n"
                "The file could not be downloaded or sent.\n"
                "Please try again.",
                parse_mode="HTML",
            )
        except Exception:
            pass

    except asyncio.CancelledError:
        logger.info(
            "Media job cancelled: %s",
            job_id,
        )

        try:
            await query.edit_message_text(
                "❌ Download cancelled."
            )
        except Exception:
            pass

    except Exception:
        logger.exception(
            "Unexpected media processing error: %s",
            job_id,
        )

        try:
            await query.edit_message_text(
                "⚠️ Something went wrong while processing the media."
            )
        except Exception:
            pass

    finally:
        if CLEANUP_AFTER_SEND:
            await cleanup_job_directory(
                job_directory
            )

        # Remove the completed job from chat state.
        if context.chat_data is not None:
            current_job = context.chat_data.get(
                "media_job"
            )

            if (
                current_job
                and current_job.get("job_id") == job_id
            ):
                context.chat_data.pop(
                    "media_job",
                    None,
                )


async def cancel_media(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    job_id: str,
) -> None:
    """Cancel the current media session."""

    if context.chat_data is not None:
        job = context.chat_data.get("media_job")

        if job and job.get("job_id") == job_id:
            context.chat_data.pop(
                "media_job",
                None,
            )

    try:
        await query.edit_message_text(
            "❌ <b>Cancelled</b>\n\n"
            "You can send another media link whenever you want.",
            parse_mode="HTML",
        )
    except Exception:
        logger.debug(
            "Could not update cancelled message.",
            exc_info=True,
        )


def _build_caption(job: dict) -> str:
    """Build a clean Telegram caption."""

    platform = str(
        job.get("platform") or "Media"
    ).title()

    title = str(
        job.get("title") or "Media"
    ).strip()

    filename = str(
        job.get("filename") or ""
    ).strip()

    lines = [
        f"🎬 <b>{_escape_html(title)}</b>",
        "",
        f"🌐 Source: <b>{_escape_html(platform)}</b>",
    ]

    if filename:
        lines.append(
            f"📁 <code>{_escape_html(filename)}</code>"
        )

    return "\n".join(lines)


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
