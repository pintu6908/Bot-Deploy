from __future__ import annotations

import os
import platform
import time

from telegram import Update
from telegram.ext import ContextTypes

from config import (
    ADMIN_ID,
    BOT_LANGUAGE,
    CLEANUP_AFTER_SEND,
    DOWNLOAD_DIR,
    LOG_LEVEL,
    MAX_CONCURRENT_DOWNLOADS,
    MAX_DOWNLOAD_MB,
    TERABOX_GATEWAY_URL,
    INSTAGRAM_RESOLVER_URL,
)


START_TIME = time.time()


def is_admin(update: Update) -> bool:
    """Check whether the current Telegram user is the admin."""

    user = update.effective_user

    if not user:
        return False

    return user.id == ADMIN_ID


async def status_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show basic bot/server status to the admin."""

    if not update.message:
        return

    if not is_admin(update):
        await update.message.reply_text(
            "⛔ You are not authorized to use this command."
        )
        return

    uptime = _format_uptime(
        time.time() - START_TIME
    )

    await update.message.reply_text(
        "🟢 <b>Bot Status</b>\n\n"
        f"⏱ Uptime: <code>{uptime}</code>\n"
        f"🐍 Python: <code>{platform.python_version()}</code>\n"
        f"🖥 OS: <code>{platform.system()}</code>\n"
        f"💾 Download limit: <code>{MAX_DOWNLOAD_MB} MB</code>\n"
        f"⚡ Concurrent downloads: <code>{MAX_CONCURRENT_DOWNLOADS}</code>\n"
        f"🧹 Cleanup: <code>{CLEANUP_AFTER_SEND}</code>\n"
        f"📝 Log level: <code>{LOG_LEVEL}</code>",
        parse_mode="HTML",
    )


async def config_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show non-secret configuration information."""

    if not update.message:
        return

    if not is_admin(update):
        await update.message.reply_text(
            "⛔ You are not authorized to use this command."
        )
        return

    terabox_status = (
        "configured"
        if TERABOX_GATEWAY_URL
        else "not configured"
    )

    instagram_status = (
        "configured"
        if INSTAGRAM_RESOLVER_URL
        else "not configured"
    )

    await update.message.reply_text(
        "⚙️ <b>Bot Configuration</b>\n\n"
        f"🌐 TeraBox Gateway: <code>{terabox_status}</code>\n"
        f"📸 Instagram Resolver: <code>{instagram_status}</code>\n"
        f"📂 Download directory: <code>{DOWNLOAD_DIR}</code>\n"
        f"📦 Max file size: <code>{MAX_DOWNLOAD_MB} MB</code>\n"
        f"🔢 Max concurrent jobs: <code>{MAX_CONCURRENT_DOWNLOADS}</code>\n"
        f"🧹 Cleanup after send: <code>{CLEANUP_AFTER_SEND}</code>\n"
        f"🌍 Language: <code>{BOT_LANGUAGE}</code>\n"
        f"🐍 Python: <code>{platform.python_version()}</code>\n\n"
        "🔐 API keys and bot tokens are never displayed.",
        parse_mode="HTML",
    )


async def ping_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Simple admin health check."""

    if not update.message:
        return

    if not is_admin(update):
        await update.message.reply_text(
            "⛔ You are not authorized to use this command."
        )
        return

    await update.message.reply_text(
        "🏓 <b>Pong!</b>\n\n"
        "Telegram bot process is responding.",
        parse_mode="HTML",
    )


def _format_uptime(seconds: float) -> str:
    """Convert seconds into a readable uptime string."""

    total_seconds = max(0, int(seconds))

    days, remainder = divmod(
        total_seconds,
        86400,
    )

    hours, remainder = divmod(
        remainder,
        3600,
    )

    minutes, seconds = divmod(
        remainder,
        60,
    )

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours:
        parts.append(f"{hours}h")

    if minutes:
        parts.append(f"{minutes}m")

    parts.append(f"{seconds}s")

    return " ".join(parts)
