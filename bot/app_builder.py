"""
Application singleton builder for Vercel webhook mode.

Builds a python-telegram-bot Application with:
- PostgresPersistence (state survives cold starts)
- All 7 ConversationHandlers (persistent=True)
- All simple command handlers and callback handlers
- Error handler

The Application is created once and reused across Vercel function
invocations within the same container (warm starts).
"""

import logging
import os
import sys

# Ensure bot directory is on path for imports
BOT_DIR = os.path.dirname(os.path.abspath(__file__))
if BOT_DIR not in sys.path:
    sys.path.insert(0, BOT_DIR)

from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters as tg_filters,
)

from config import config
from persistence import PostgresPersistence

# Handler imports
from handlers.start_handler import build_start_handler, help_command
from handlers.feedback_handler import build_feedback_handler
from handlers.diary_handler import build_diary_handler
from handlers.interaction_handler import build_interaction_handler
from handlers.training_handler import build_training_handler
from handlers.briefing_handler import briefing_command, briefing_callback
from handlers.ask_handler import build_ask_handler
from handlers.stats_handler import stats_command, stats_callback
from handlers.case_handler import build_cases_handler

# Import command/callback handlers from telegram_bot.py
from telegram_bot import (
    agents_command,
    tickets_command,
    version_command,
    main_menu_callback,
    close_ticket_callback,
    view_case_from_notification,
    error_handler,
)
from utils.voice import voice_command
from utils.formatters import E_WARNING

logger = logging.getLogger(__name__)

# Module-level singleton
_application: Application = None
_initialized = False


async def _post_init(application: Application) -> None:
    """Set bot commands after initialization."""
    commands = [
        BotCommand("start", "Register / Restart"),
        BotCommand("briefing", "Morning briefing / Subah ki report"),
        BotCommand("diary", "Today's schedule / Aaj ka diary"),
        BotCommand("agents", "Your agents / Aapke agents"),
        BotCommand("feedback", "Capture agent feedback"),
        BotCommand("log", "Log an interaction"),
        BotCommand("train", "Product training modules"),
        BotCommand("ask", "AI product answers"),
        BotCommand("stats", "Your performance stats"),
        BotCommand("cases", "Case history per agent"),
        BotCommand("tickets", "View your open tickets"),
        BotCommand("voice", "Toggle voice notes on/off"),
        BotCommand("help", "Show all commands"),
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Bot commands set successfully.")
    except Exception as exc:
        logger.warning("Could not set bot commands: %s", exc)


async def _unhandled_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle stray text that no ConversationHandler claimed."""
    if not update.message or not update.message.text:
        return
    logger.warning(
        "CATCH-ALL: Unhandled text from user %s: %s",
        update.effective_user.id if update.effective_user else "unknown",
        update.message.text[:100],
    )
    await update.message.reply_text(
        f"{E_WARNING} <b>I didn't understand that.</b>\n\n"
        f"Please use a command to get started:\n"
        f"/log \u2014 Log an interaction\n"
        f"/feedback \u2014 Capture feedback\n"
        f"/cases \u2014 View case history\n"
        f"/help \u2014 See all commands",
        parse_mode="HTML",
    )


async def get_application(session_factory) -> Application:
    """Get or create the Application singleton with all handlers registered.

    Args:
        session_factory: SQLAlchemy SessionLocal factory for PostgresPersistence
    """
    global _application, _initialized

    if _application is not None and _initialized:
        return _application

    logger.info("Building Application singleton with PostgresPersistence...")

    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set!")

    persistence = PostgresPersistence(session_factory)

    _application = (
        Application.builder()
        .token(token)
        .persistence(persistence)
        .build()
    )

    # ------------------------------------------------------------------
    # Register ConversationHandlers (order matters - first match wins)
    # CRITICAL: /start is registered LAST so other handlers get priority
    # ------------------------------------------------------------------
    _application.add_handler(build_feedback_handler())
    _application.add_handler(build_interaction_handler())
    _application.add_handler(build_diary_handler())
    _application.add_handler(build_training_handler())
    _application.add_handler(build_ask_handler())
    _application.add_handler(build_cases_handler())
    _application.add_handler(build_start_handler())  # LAST

    # ------------------------------------------------------------------
    # Simple command handlers
    # ------------------------------------------------------------------
    _application.add_handler(CommandHandler("help", help_command))
    _application.add_handler(CommandHandler("briefing", briefing_command))
    _application.add_handler(CommandHandler("agents", agents_command))
    _application.add_handler(CommandHandler("stats", stats_command))
    _application.add_handler(CommandHandler("voice", voice_command))
    _application.add_handler(CommandHandler("tickets", tickets_command))
    _application.add_handler(CommandHandler("version", version_command))

    # ------------------------------------------------------------------
    # Callback query handlers
    # ------------------------------------------------------------------
    _application.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^cmd_"))
    _application.add_handler(CallbackQueryHandler(briefing_callback, pattern=r"^brief_"))
    _application.add_handler(CallbackQueryHandler(stats_callback, pattern=r"^stats_"))
    _application.add_handler(CallbackQueryHandler(close_ticket_callback, pattern=r"^close_ticket:"))
    _application.add_handler(CallbackQueryHandler(view_case_from_notification, pattern=r"^view_case:"))

    # ------------------------------------------------------------------
    # Catch-all and error handlers
    # ------------------------------------------------------------------
    _application.add_handler(
        MessageHandler(tg_filters.TEXT & ~tg_filters.COMMAND, _unhandled_text),
        group=99,
    )
    _application.add_error_handler(error_handler)

    # Initialize the application (loads persistence data from Neon)
    await _application.initialize()

    # Set bot commands
    await _post_init(_application)

    _initialized = True
    logger.info("Application singleton ready with %d handlers.", len(_application.handlers.get(0, [])))

    return _application
