from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes


START_TEXT = """👋 <b>Welcome to Media Downloader Bot!</b>

🎬 Send me a public media link and I'll detect it automatically.

<b>Supported:</b>
• TeraBox
• Instagram

<b>Available actions:</b>
▶️ Play
⬇️ Download

Just paste your link here.

⚠️ Private, login-protected, or inaccessible content isn't supported.
"""


HELP_TEXT = """📖 <b>How to use</b>

1️⃣ Copy a public TeraBox or Instagram media link.
2️⃣ Send the link to this bot.
3️⃣ Wait while the media is resolved.
4️⃣ Choose <b>▶️ Play</b> or <b>⬇️ Download</b>.

<b>Commands</b>
/start — Start the bot
/help — Show this help

<b>Supported Instagram links</b>
• Posts
• Reels
• Videos

<b>TeraBox</b>
• Public sharing links

⚠️ The bot does not bypass private accounts,
login requirements, OTP, or access restrictions.
"""


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start."""

    if not update.message:
        return

    user = update.effective_user
    first_name = user.first_name if user else "there"

    text = START_TEXT.replace(
        "👋 <b>Welcome",
        f"👋 <b>Welcome {first_name}",
        1,
    )

    await update.message.reply_text(
        text,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /help."""

    if not update.message:
        return

    await update.message.reply_text(
        HELP_TEXT,
        parse_mode="HTML",
        disable_web_page_preview=True,
    )
