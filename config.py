import os
from pathlib import Path

from dotenv import load_dotenv


# Load local .env when running locally.
# On Railway, environment variables are provided automatically.
load_dotenv()


def get_env(name: str, default: str = "") -> str:
    """Read an environment variable and strip surrounding whitespace."""
    return os.getenv(name, default).strip()


def get_bool(name: str, default: bool = False) -> bool:
    """Read a boolean environment variable."""
    value = get_env(name)

    if not value:
        return default

    return value.lower() in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }


def get_int(name: str, default: int) -> int:
    """Read an integer environment variable safely."""
    value = get_env(name)

    if not value:
        return default

    try:
        return int(value)
    except ValueError:
        return default


# ============================================================
# TELEGRAM
# ============================================================

BOT_TOKEN = get_env("BOT_TOKEN")
ADMIN_ID = get_int("ADMIN_ID", 0)


# ============================================================
# TERABOX GATEWAY
# ============================================================

TERABOX_GATEWAY_URL = get_env("TERABOX_GATEWAY_URL")
TERABOX_GATEWAY_API_KEY = get_env("TERABOX_GATEWAY_API_KEY")


# ============================================================
# INSTAGRAM RESOLVER
# ============================================================

INSTAGRAM_RESOLVER_URL = get_env("INSTAGRAM_RESOLVER_URL")
INSTAGRAM_API_KEY = get_env("INSTAGRAM_API_KEY")


# ============================================================
# DOWNLOAD SETTINGS
# ============================================================

DOWNLOAD_DIR = Path(
    get_env("DOWNLOAD_DIR", "/tmp/telegram_media")
)

MAX_DOWNLOAD_MB = get_int(
    "MAX_DOWNLOAD_MB",
    2000,
)

MAX_CONCURRENT_DOWNLOADS = get_int(
    "MAX_CONCURRENT_DOWNLOADS",
    2,
)


# ============================================================
# BOT BEHAVIOUR
# ============================================================

CLEANUP_AFTER_SEND = get_bool(
    "CLEANUP_AFTER_SEND",
    True,
)

SHOW_PROGRESS = get_bool(
    "SHOW_PROGRESS",
    True,
)

BOT_LANGUAGE = get_env(
    "BOT_LANGUAGE",
    "en",
)


# ============================================================
# NETWORK / LOGGING
# ============================================================

REQUEST_TIMEOUT = get_int(
    "REQUEST_TIMEOUT",
    60,
)

LOG_LEVEL = get_env(
    "LOG_LEVEL",
    "INFO",
).upper()


# ============================================================
# DIRECTORY SETUP
# ============================================================

DOWNLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# VALIDATION
# ============================================================

def validate_config() -> None:
    """
    Validate required configuration before starting the bot.
    """

    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. "
            "Add BOT_TOKEN to Railway Variables or .env."
        )

    if ADMIN_ID <= 0:
        raise RuntimeError(
            "ADMIN_ID is missing or invalid. "
            "Set your numeric Telegram user ID."
        )


def mask_secret(value: str) -> str:
    """
    Safely mask a secret for logging.
    Never print complete tokens/API keys.
    """

    if not value:
        return "(not set)"

    if len(value) <= 8:
        return "********"

    return (
        value[:4]
        + "..."
        + value[-4:]
    )


def get_config_summary() -> dict:
    """
    Return a safe configuration summary.
    Secrets are masked.
    """

    return {
        "bot_token": mask_secret(BOT_TOKEN),
        "admin_id": ADMIN_ID,

        "terabox_gateway": (
            TERABOX_GATEWAY_URL
            if TERABOX_GATEWAY_URL
            else "(not configured)"
        ),

        "terabox_api_key": mask_secret(
            TERABOX_GATEWAY_API_KEY
        ),

        "instagram_resolver": (
            INSTAGRAM_RESOLVER_URL
            if INSTAGRAM_RESOLVER_URL
            else "(not configured)"
        ),

        "instagram_api_key": mask_secret(
            INSTAGRAM_API_KEY
        ),

        "download_dir": str(DOWNLOAD_DIR),
        "max_download_mb": MAX_DOWNLOAD_MB,
        "max_concurrent_downloads": MAX_CONCURRENT_DOWNLOADS,
        "cleanup_after_send": CLEANUP_AFTER_SEND,
        "show_progress": SHOW_PROGRESS,
        "bot_language": BOT_LANGUAGE,
        "request_timeout": REQUEST_TIMEOUT,
        "log_level": LOG_LEVEL,
    }
