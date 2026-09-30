import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    LOG_LEVEL,
    validate_config,
    get_config_summary,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("media_bot")


# ============================================================
# /START
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start."""

    if not update.message:
        return

    user = update.effective_user

    name = user.first_name if user else "there"

    text = (
        f"👋 Hello {name}!\n\n"
        "🎬 Send me a supported public media link.\n\n"
        "Supported platforms:\n"
        "• TeraBox\n"
        "• Instagram\n\n"
        "I will detect the link automatically "
        "and show the available actions."
    )

    await update.message.reply_text(text)


# ============================================================
# /HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Show help information."""

    if not update.message:
        return

    text = (
        "📖 Help\n\n"
        "Send a public TeraBox or Instagram media URL "
        "directly to this chat.\n\n"
        "The bot will try to:\n"
        "1. Detect the platform\n"
        "2. Resolve the media\n"
        "3. Show media information\n"
        "4. Offer Play/Download actions\n\n"
        "⚠️ Private or login-protected content is not supported."
    )

    await update.message.reply_text(text)


# ============================================================
# URL MESSAGE HANDLER
# ============================================================

async def url_message_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Receive normal text messages.

    Actual URL detection/resolution will be implemented
    in the platform modules added later.
    """

    if not update.message:
        return

    text = update.message.text or ""

    if not text.strip():
        return

    # Temporary response.
    # This will be replaced by the URL router in a later file.
    await update.message.reply_text(
        "🔎 Checking your link...\n\n"
        "The media resolver module is being initialized."
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle unexpected Telegram/application errors."""

    error = context.error

    logger.exception(
        "Unhandled bot error: %s",
        error,
    )


# ============================================================
# APPLICATION CREATION
# ============================================================

def create_application() -> Application:
    """Create and configure the Telegram application."""

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is not configured."
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    # Text messages
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            url_message_handler,
        )
    )

    # Global error handler
    application.add_error_handler(
        error_handler
    )

    return application


# ============================================================
# STARTUP
# ============================================================

def main() -> None:
    """Start the Telegram bot."""

    try:
        validate_config()

    except Exception as exc:
        logger.error(
            "Configuration error: %s",
            exc,
        )
        sys.exit(1)

    logger.info(
        "Starting Telegram media bot..."
    )

    # Only safe, non-secret configuration is logged.
    summary = get_config_summary()

    logger.info(
        "Configuration: %s",
        summary,
    )

    application = create_application()

    logger.info(
        "Bot is running."
    )

    # Long polling works well for a simple Railway worker.
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
