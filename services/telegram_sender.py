from __future__ import annotations

import logging
from pathlib import Path

from telegram import Message, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from utils.errors import TelegramSendError
from utils.media import (
    get_media_info,
    is_audio_file,
    is_image_file,
    is_video_file,
)

logger = logging.getLogger(__name__)


class TelegramSender:
    """
    Handles sending downloaded media files to Telegram.

    Automatically detects:
    - Video
    - Audio
    - Image
    - Generic document
    """

    async def send_media(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        file_path: Path,
        caption: str | None = None,
        thumbnail: str | None = None,
    ) -> Message | None:
        if not update.message:
            raise TelegramSendError("Telegram message is unavailable.")

        if not file_path.exists():
            raise TelegramSendError("Media file no longer exists.")

        try:
            media_info = get_media_info(file_path)

            if is_video_file(file_path):
                return await self._send_video(
                    update=update,
                    file_path=file_path,
                    caption=caption,
                    thumbnail=thumbnail,
                    duration=media_info.get("duration"),
                )

            if is_audio_file(file_path):
                return await self._send_audio(
                    update=update,
                    file_path=file_path,
                    caption=caption,
                    duration=media_info.get("duration"),
                )

            if is_image_file(file_path):
                return await self._send_photo(
                    update=update,
                    file_path=file_path,
                    caption=caption,
                )

            return await self._send_document(
                update=update,
                file_path=file_path,
                caption=caption,
            )

        except TelegramSendError:
            raise

        except Exception as exc:
            logger.exception(
                "Failed to send media to Telegram: %s",
                file_path,
            )
            raise TelegramSendError(
                "Telegram could not send this media file."
            ) from exc

    async def _send_video(
        self,
        update: Update,
        file_path: Path,
        caption: str | None = None,
        thumbnail: str | None = None,
        duration: float | None = None,
    ) -> Message:
        await update.message.chat.send_action(
            action=ChatAction.UPLOAD_VIDEO
        )

        kwargs = {
            "video": file_path,
            "caption": caption,
            "supports_streaming": True,
        }

        if duration is not None:
            kwargs["duration"] = max(0, int(duration))

        # Telegram accepts a local file as thumbnail.
        # Remote thumbnail URLs are intentionally not downloaded here.
        if thumbnail and Path(thumbnail).exists():
            kwargs["thumbnail"] = thumbnail

        message = await update.message.reply_video(**kwargs)

        return message

    async def _send_audio(
        self,
        update: Update,
        file_path: Path,
        caption: str | None = None,
        duration: float | None = None,
    ) -> Message:
        await update.message.chat.send_action(
            action=ChatAction.UPLOAD_AUDIO
        )

        kwargs = {
            "audio": file_path,
            "caption": caption,
        }

        if duration is not None:
            kwargs["duration"] = max(0, int(duration))

        message = await update.message.reply_audio(**kwargs)

        return message

    async def _send_photo(
        self,
        update: Update,
        file_path: Path,
        caption: str | None = None,
    ) -> Message:
        await update.message.chat.send_action(
            action=ChatAction.UPLOAD_PHOTO
        )

        message = await update.message.reply_photo(
            photo=file_path,
            caption=caption,
        )

        return message

    async def _send_document(
        self,
        update: Update,
        file_path: Path,
        caption: str | None = None,
    ) -> Message:
        await update.message.chat.send_action(
            action=ChatAction.UPLOAD_DOCUMENT
        )

        message = await update.message.reply_document(
            document=file_path,
            caption=caption,
        )

        return message
