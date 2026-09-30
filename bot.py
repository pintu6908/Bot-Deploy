from __future__ import annotations

import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import (
    BOT_TOKEN,
    LOG_LEVEL,
    get_config_summary,
    validate_config,
)
from handlers import (
    callback_handler,
    config_command,
    help_command,
    media_url_handler,
    ping_command,
    start_command,
    status_command,
)


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=getattr(
        logging,
        LOG_LEVEL,
        logging.INFO,
    ),
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("media_bot")


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """
    Global Telegram error handler.

    Never sends internal tracebacks or secrets to users.
    """

    error = context.error

    logger.error(
        "Unhandled Telegram error: %r",
        error,
        exc_info=(
            type(error),
            error,
            error.__traceback__,
        )
        if error
        else None,
    )


# ============================================================
# APPLICATION
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

    # --------------------------------------------------------
    # Basic commands
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Admin commands
    # --------------------------------------------------------

    application.add_handler(
        CommandHandler(
            "status",
            status_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "config",
            config_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "ping",
            ping_command,
        )
    )

    # --------------------------------------------------------
    # Inline button callbacks
    # --------------------------------------------------------

    application.add_handler(
        CallbackQueryHandler(
            callback_handler,
        )
    )

    # --------------------------------------------------------
    # Normal text messages
    # --------------------------------------------------------

    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            media_url_handler,
        )
    )

    # --------------------------------------------------------
    # Global error handler
    # --------------------------------------------------------

    application.add_error_handler(
        error_handler
    )

    return application


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    """Start the bot."""

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

    summary = get_config_summary()

    logger.info(
        "Configuration: %s",
        summary,
    )

    application = create_application()

    logger.info(
        "Bot is running."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
