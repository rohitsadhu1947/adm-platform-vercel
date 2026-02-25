"""
Diary / Schedule management conversation handler for the ADM Platform Telegram Bot.
View, add, complete, and reschedule diary entries.
"""

import logging
from datetime import datetime, timedelta, date

from telegram import Update
from telegram.ext import (
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from bot_config import DiaryStates
from utils.api_client import api_client
from utils.formatters import (
    format_diary,
    error_generic,
    cancelled,
    E_CALENDAR, E_CHECK, E_CROSS, E_PENCIL, E_CLOCK,
    E_PERSON, E_MEMO, E_SPARKLE,
    E_RED_CIRCLE, E_YELLOW_CIRCLE, E_GREEN_CIRCLE,
)
from utils.keyboards import (
    diary_action_keyboard,
    diary_entry_select_keyboard,
    reschedule_keyboard,
)
from utils.voice import send_voice_response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entry: /diary or /schedule
# ---------------------------------------------------------------------------

async def diary_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show today's diary / schedule."""
    telegram_id = update.effective_user.id

    diary_resp = await api_client.get_diary_entries(telegram_id)
    entries = diary_resp.get("entries", diary_resp.get("data", []))

    if diary_resp.get("error"):
        await update.message.reply_text(
            f"{E_CALENDAR} <b>No diary entries yet.</b>\n\n"
            f"Please check your connection or add entries via the dashboard.\n"
            f"You can also use the Add button below to create a new entry.",
            parse_mode="HTML",
            reply_markup=diary_action_keyboard(),
        )
        context.user_data["diary_entries"] = []
        return DiaryStates.VIEW_DIARY

    context.user_data["diary_entries"] = entries

    diary_text = format_diary(entries)
    sent_msg = await update.message.reply_text(
        diary_text,
        parse_mode="HTML",
        reply_markup=diary_action_keyboard(),
    )
    await send_voice_response(sent_msg, diary_text)
    return DiaryStates.VIEW_DIARY


# ---------------------------------------------------------------------------
# Diary actions
# ---------------------------------------------------------------------------

async def diary_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle diary action button presses."""
    query = update.callback_query
    await query.answer()
    data = query.data

    entries = context.user_data.get("diary_entries", [])

    if data == "diary_add":
        await query.edit_message_text(
            f"{E_PENCIL} <b>Add Diary Entry</b>\n\n"
            f"Type the entry title / description:\n"
            f"Entry ka title ya description likhen:\n\n"
            f"<i>Example: Call Agent Rajesh about renewal</i>",
            parse_mode="HTML",
        )
        return DiaryStates.ADD_ENTRY

    if data == "diary_complete":
        incomplete = [e for e in entries if not e.get("completed", False)]
        if not incomplete:
            await query.edit_message_text(
                f"{E_CHECK} <b>All entries completed!</b>\n\n"
                f"Sab entries poori ho chuki hain. {E_SPARKLE}\n\n"
                f"Use /diary to refresh.",
                parse_mode="HTML",
            )
            return ConversationHandler.END

        await query.edit_message_text(
            f"{E_CHECK} <b>Mark as Complete</b>\n\n"
            f"Select entry to complete / Poora karne ke liye chunein:",
            parse_mode="HTML",
            reply_markup=diary_entry_select_keyboard(incomplete, action="complete"),
        )
        return DiaryStates.ENTRY_DETAILS

    if data == "diary_reschedule":
        incomplete = [e for e in entries if not e.get("completed", False)]
        if not incomplete:
            await query.edit_message_text(
                f"{E_CALENDAR} No entries to reschedule.\n"
                f"Reschedule karne ke liye koi entry nahi hai.",
                parse_mode="HTML",
            )
            return ConversationHandler.END

        await query.edit_message_text(
            f"{E_CALENDAR} <b>Reschedule Entry</b>\n\n"
            f"Select entry to reschedule / Badalne ke liye chunein:",
            parse_mode="HTML",
            reply_markup=diary_entry_select_keyboard(incomplete, action="resched"),
        )
        return DiaryStates.RESCHEDULE

    if data == "diary_other_date":
        await query.edit_message_text(
            f"{E_CALENDAR} <b>View Another Date</b>\n\n"
            f"Enter date in DD/MM/YYYY format:\n"
            f"(e.g., 25/01/2025)",
            parse_mode="HTML",
        )
        return DiaryStates.VIEW_DIARY

    if data == "diary_back":
        # Refresh diary view
        telegram_id = update.effective_user.id
        diary_resp = await api_client.get_diary_entries(telegram_id)
        entries = diary_resp.get("entries", diary_resp.get("data", []))
        if diary_resp.get("error"):
            entries = []
        context.user_data["diary_entries"] = entries

        diary_text = format_diary(entries)
        await query.edit_message_text(
            diary_text,
            parse_mode="HTML",
            reply_markup=diary_action_keyboard(),
        )
        return DiaryStates.VIEW_DIARY

    return DiaryStates.VIEW_DIARY


# ---------------------------------------------------------------------------
# Add entry
# ---------------------------------------------------------------------------

async def add_entry_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive new diary entry text."""
    text = update.message.text.strip()

    # Check if it looks like a date (for "other date" flow)
    if "/" in text and len(text) <= 12:
        try:
            parsed = datetime.strptime(text, "%d/%m/%Y")
            telegram_id = update.effective_user.id
            date_str = parsed.strftime("%Y-%m-%d")
            diary_resp = await api_client.get_diary_entries(telegram_id, date=date_str)
            entries = diary_resp.get("entries", diary_resp.get("data", []))
            if diary_resp.get("error"):
                entries = []  # No demo entries for arbitrary dates
            context.user_data["diary_entries"] = entries

            diary_text = format_diary(entries, date_str=parsed.strftime("%d %b %Y"))
            await update.message.reply_text(
                diary_text,
                parse_mode="HTML",
                reply_markup=diary_action_keyboard(),
            )
            return DiaryStates.VIEW_DIARY
        except ValueError:
            pass

    # It's a new entry title
    telegram_id = update.effective_user.id
    payload = {
        "adm_telegram_id": telegram_id,
        "title": text,
        "date": date.today().isoformat(),
        "priority": "today",
    }

    result = await api_client.add_diary_entry(payload)

    if result.get("error"):
        logger.warning("Diary add API failed: %s", result)

    await update.message.reply_text(
        f"{E_CHECK} <b>Entry Added!</b>\n\n"
        f"{E_MEMO} {text}\n"
        f"{E_CALENDAR} {date.today().strftime('%d %b %Y')}\n\n"
        f"Entry add ho gayi hai {E_SPARKLE}",
        parse_mode="HTML",
    )

    # Show updated diary
    diary_resp = await api_client.get_diary_entries(telegram_id)
    entries = diary_resp.get("entries", diary_resp.get("data", []))
    if diary_resp.get("error"):
        entries = []
    context.user_data["diary_entries"] = entries

    diary_text = format_diary(entries)
    sent_msg = await update.message.reply_text(
        diary_text,
        parse_mode="HTML",
        reply_markup=diary_action_keyboard(),
    )
    await send_voice_response(sent_msg, diary_text)
    return DiaryStates.VIEW_DIARY


# ---------------------------------------------------------------------------
# Complete / Reschedule entry
# ---------------------------------------------------------------------------

async def entry_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle entry complete or reschedule selection."""
    query = update.callback_query
    await query.answer()
    data = query.data  # e.g., "dentry_complete_ENTRY123" or "dentry_resched_ENTRY123"

    parts = data.replace("dentry_", "").split("_", 1)
    action = parts[0]
    entry_id = parts[1] if len(parts) > 1 else ""

    if action == "complete":
        result = await api_client.update_diary_entry(entry_id, {"completed": True})

        if result.get("error"):
            logger.warning("Diary complete API failed: %s", result)

        await query.edit_message_text(
            f"{E_CHECK} <b>Entry Completed!</b> {E_SPARKLE}\n\n"
            f"Bahut achha! Entry poori ho gayi.\n\n"
            f"Use /diary to see updated schedule.",
            parse_mode="HTML",
        )
        return ConversationHandler.END

    if action == "resched":
        context.user_data["resched_entry_id"] = entry_id
        await query.edit_message_text(
            f"{E_CALENDAR} <b>Reschedule to when?</b>\n\n"
            f"Naya date chunein:",
            parse_mode="HTML",
            reply_markup=reschedule_keyboard(),
        )
        return DiaryStates.RESCHEDULE

    return DiaryStates.VIEW_DIARY


async def reschedule_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle reschedule date selection."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "diary_back":
        return await diary_action(update, context)

    days_map = {
        "resched_tomorrow": 1,
        "resched_3days": 3,
        "resched_1week": 7,
    }

    days = days_map.get(data, 1)
    new_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    new_date_display = (datetime.now() + timedelta(days=days)).strftime("%d %b %Y")

    entry_id = context.user_data.get("resched_entry_id", "")
    if entry_id:
        result = await api_client.update_diary_entry(entry_id, {"date": new_date})

        if result.get("error"):
            logger.warning("Diary reschedule API failed: %s", result)

        await query.edit_message_text(
            f"{E_CALENDAR} <b>Entry Rescheduled!</b>\n\n"
            f"New date: <b>{new_date_display}</b>\n\n"
            f"Entry reschedule ho gayi. Use /diary to see updated schedule.",
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text(error_generic(), parse_mode="HTML")

    context.user_data.pop("resched_entry_id", None)
    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

async def cancel_diary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.pop("diary_entries", None)
    context.user_data.pop("resched_entry_id", None)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(cancelled(), parse_mode="HTML")
    else:
        await update.message.reply_text(cancelled(), parse_mode="HTML")

    return ConversationHandler.END


# ---------------------------------------------------------------------------
# Build ConversationHandler
# ---------------------------------------------------------------------------

def build_diary_handler() -> ConversationHandler:
    """Build the /diary (/schedule) conversation handler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("diary", diary_command),
            CommandHandler("schedule", diary_command),
        ],
        states={
            DiaryStates.VIEW_DIARY: [
                CallbackQueryHandler(diary_action, pattern=r"^diary_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_entry_text),
            ],
            DiaryStates.ADD_ENTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_entry_text),
            ],
            DiaryStates.ENTRY_DETAILS: [
                CallbackQueryHandler(entry_action, pattern=r"^dentry_"),
                CallbackQueryHandler(diary_action, pattern=r"^diary_"),
            ],
            DiaryStates.RESCHEDULE: [
                CallbackQueryHandler(reschedule_action, pattern=r"^resched_"),
                CallbackQueryHandler(diary_action, pattern=r"^diary_"),
                CallbackQueryHandler(entry_action, pattern=r"^dentry_"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_diary),
            CallbackQueryHandler(cancel_diary, pattern=r"^cancel$"),
        ],
        name="diary",
        persistent=True,
    )
