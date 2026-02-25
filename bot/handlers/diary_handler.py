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
from datetime import date as date_type
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
    """Receive new diary entry title, then ask for date."""
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
                entries = []
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

    # Save entry title and ask for date
    context.user_data["new_entry_title"] = text

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    today = date.today()
    tomorrow = today + timedelta(days=1)
    day_after = today + timedelta(days=2)

    buttons = [
        [InlineKeyboardButton(f"📅 Today ({today.strftime('%d %b')})", callback_data="edate_today")],
        [InlineKeyboardButton(f"📅 Tomorrow ({tomorrow.strftime('%d %b')})", callback_data="edate_tomorrow")],
        [InlineKeyboardButton(f"📅 {day_after.strftime('%d %b %Y')}", callback_data="edate_2days")],
        [InlineKeyboardButton(f"📅 Custom Date / Apni date likhein", callback_data="edate_custom")],
    ]

    await update.message.reply_text(
        f"{E_CALENDAR} <b>Select Date / Date Chunein</b>\n\n"
        f"{E_MEMO} Entry: <i>{text}</i>\n\n"
        f"Kis date ke liye schedule karein?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return DiaryStates.ADD_ENTRY_DATE


async def add_entry_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle date selection for new diary entry."""
    query = update.callback_query
    await query.answer()
    data = query.data

    today = date.today()

    if data == "edate_today":
        entry_date = today
    elif data == "edate_tomorrow":
        entry_date = today + timedelta(days=1)
    elif data == "edate_2days":
        entry_date = today + timedelta(days=2)
    elif data == "edate_custom":
        await query.edit_message_text(
            f"{E_CALENDAR} <b>Enter Date / Date Likhein</b>\n\n"
            f"DD/MM/YYYY format mein likhein:\n"
            f"<i>Example: 28/02/2026</i>",
            parse_mode="HTML",
        )
        return DiaryStates.ADD_ENTRY_DATE  # Stay in same state for text input
    else:
        entry_date = today

    context.user_data["new_entry_date"] = entry_date.isoformat()

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = [
        [InlineKeyboardButton("🕘 9:00 AM", callback_data="etime_09:00")],
        [InlineKeyboardButton("🕛 12:00 PM", callback_data="etime_12:00")],
        [InlineKeyboardButton("🕒 3:00 PM", callback_data="etime_15:00")],
        [InlineKeyboardButton("🕕 6:00 PM", callback_data="etime_18:00")],
        [InlineKeyboardButton("⏭ No Time / Skip", callback_data="etime_skip")],
    ]

    title = context.user_data.get("new_entry_title", "")
    await query.edit_message_text(
        f"{E_CLOCK} <b>Select Time / Samay Chunein</b>\n\n"
        f"{E_MEMO} Entry: <i>{title}</i>\n"
        f"{E_CALENDAR} Date: <b>{entry_date.strftime('%d %b %Y')}</b>\n\n"
        f"Kis time ke liye?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return DiaryStates.ADD_ENTRY_TIME


async def add_entry_date_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle custom date typed by user for new diary entry."""
    text = update.message.text.strip()
    try:
        parsed = datetime.strptime(text, "%d/%m/%Y")
        entry_date = parsed.date()
    except ValueError:
        await update.message.reply_text(
            f"{E_CROSS} Invalid date format. Please use DD/MM/YYYY\n"
            f"<i>Example: 28/02/2026</i>",
            parse_mode="HTML",
        )
        return DiaryStates.ADD_ENTRY_DATE

    context.user_data["new_entry_date"] = entry_date.isoformat()

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = [
        [InlineKeyboardButton("🕘 9:00 AM", callback_data="etime_09:00")],
        [InlineKeyboardButton("🕛 12:00 PM", callback_data="etime_12:00")],
        [InlineKeyboardButton("🕒 3:00 PM", callback_data="etime_15:00")],
        [InlineKeyboardButton("🕕 6:00 PM", callback_data="etime_18:00")],
        [InlineKeyboardButton("⏭ No Time / Skip", callback_data="etime_skip")],
    ]

    title = context.user_data.get("new_entry_title", "")
    await update.message.reply_text(
        f"{E_CLOCK} <b>Select Time / Samay Chunein</b>\n\n"
        f"{E_MEMO} Entry: <i>{title}</i>\n"
        f"{E_CALENDAR} Date: <b>{entry_date.strftime('%d %b %Y')}</b>\n\n"
        f"Kis time ke liye?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return DiaryStates.ADD_ENTRY_TIME


async def add_entry_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle time selection and save the diary entry."""
    query = update.callback_query
    await query.answer()
    data = query.data

    time_str = ""
    if data == "etime_skip":
        time_display = "No specific time"
    else:
        time_str = data.replace("etime_", "")
        # Convert 24h to display
        hour = int(time_str.split(":")[0])
        ampm = "AM" if hour < 12 else "PM"
        display_hour = hour if hour <= 12 else hour - 12
        if display_hour == 0:
            display_hour = 12
        time_display = f"{display_hour}:{time_str.split(':')[1]} {ampm}"

    title = context.user_data.get("new_entry_title", "Untitled")
    entry_date_str = context.user_data.get("new_entry_date", date.today().isoformat())
    entry_date = date.fromisoformat(entry_date_str)

    telegram_id = update.effective_user.id
    payload = {
        "adm_telegram_id": telegram_id,
        "title": title,
        "date": entry_date_str,
        "time": time_str if time_str else None,  # HH:MM format for scheduled_time
        "priority": "today" if entry_date == date.today() else "upcoming",
    }

    result = await api_client.add_diary_entry(payload)
    if result.get("error"):
        logger.warning("Diary add API failed: %s", result)

    await query.edit_message_text(
        f"{E_CHECK} <b>Entry Added!</b>\n\n"
        f"{E_MEMO} {title}\n"
        f"{E_CALENDAR} {entry_date.strftime('%d %b %Y')}\n"
        f"{E_CLOCK} {time_display}\n\n"
        f"Entry add ho gayi hai {E_SPARKLE}",
        parse_mode="HTML",
    )

    # Clean up temp data
    context.user_data.pop("new_entry_title", None)
    context.user_data.pop("new_entry_date", None)

    # Show updated diary
    diary_resp = await api_client.get_diary_entries(telegram_id)
    entries = diary_resp.get("entries", diary_resp.get("data", []))
    if diary_resp.get("error"):
        entries = []
    context.user_data["diary_entries"] = entries

    diary_text = format_diary(entries)
    sent_msg = await query.message.reply_text(
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
                CallbackQueryHandler(cancel_diary, pattern=r"^cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_entry_text),
            ],
            DiaryStates.ADD_ENTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_entry_text),
            ],
            DiaryStates.ADD_ENTRY_DATE: [
                CallbackQueryHandler(add_entry_date, pattern=r"^edate_"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_entry_date_text),
            ],
            DiaryStates.ADD_ENTRY_TIME: [
                CallbackQueryHandler(add_entry_time, pattern=r"^etime_"),
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
