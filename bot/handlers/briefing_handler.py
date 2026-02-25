"""
Morning briefing handler for the ADM Platform Telegram Bot.
Fetches and displays the morning briefing with priority agents, follow-ups,
new assignments, and performance stats.
"""

import logging

from telegram import Update
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from utils.api_client import api_client
from utils.formatters import (
    format_morning_briefing,
    error_not_registered,
    error_generic,
    E_SUNRISE, E_FIRE, E_SPARKLE, E_CHECK, E_WARNING,
    E_PHONE, E_PERSON, E_PIN, E_RED_CIRCLE, E_YELLOW_CIRCLE,
    E_GREEN_CIRCLE, E_BELL, E_CHART, E_MEMO, E_ROCKET,
    E_BULB, E_MUSCLE, E_CALENDAR, E_BOOK, E_BRAIN,
    E_STAR, E_SHIELD, E_CLOCK, E_PEOPLE,
    E_MONEY, E_HEART, E_CLAP, E_TARGET,
    greeting, get_daily_quote, header, section_divider,
)
from utils.keyboards import briefing_action_keyboard
from utils.voice import send_voice_response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# /briefing command
# ---------------------------------------------------------------------------

async def briefing_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /briefing command - show morning briefing."""
    telegram_id = update.effective_user.id
    user = update.effective_user

    # Get profile
    profile = await api_client.get_adm_profile(telegram_id)

    if profile and not profile.get("error"):
        name = profile.get("name", user.first_name or "ADM")
    else:
        name = user.first_name or "ADM"

    # Show loading message
    loading_msg = await update.message.reply_text(
        f"{E_SUNRISE} <b>Loading your briefing...</b>\n\n"
        f"<i>Aapki briefing tayyar ho rahi hai...</i>",
        parse_mode="HTML",
    )

    # Fetch briefing data from API
    briefing_resp = await api_client.get_morning_briefing(telegram_id)

    if briefing_resp and not briefing_resp.get("error"):
        briefing_data = briefing_resp
        # Ensure adm_name is set
        if not briefing_data.get("adm_name"):
            briefing_data["adm_name"] = name

        # Format the briefing
        briefing_text = format_morning_briefing(briefing_data)

        # Delete loading message and send briefing
        try:
            await loading_msg.delete()
        except Exception:
            pass

        sent_msg = await update.message.reply_text(
            briefing_text,
            parse_mode="HTML",
            reply_markup=briefing_action_keyboard(),
        )
        await send_voice_response(sent_msg, briefing_text)
    else:
        # No data available
        try:
            await loading_msg.delete()
        except Exception:
            pass

        await update.message.reply_text(
            f"{E_SUNRISE} <b>No briefing data available.</b>\n\n"
            f"Please check your connection or add data via the dashboard.",
            parse_mode="HTML",
        )


# ---------------------------------------------------------------------------
# Briefing action callbacks (handled globally in telegram_bot.py)
# ---------------------------------------------------------------------------

async def briefing_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle briefing action button presses."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "brief_call":
        telegram_id = update.effective_user.id

        # Get priority agents
        priority_resp = await api_client.get_priority_agents(telegram_id)
        agents = priority_resp.get("agents", priority_resp.get("data", []))

        if not agents or priority_resp.get("error"):
            await query.edit_message_text(
                f"{E_PHONE} <b>No priority agents data available.</b>\n\n"
                f"Please check your connection or add agents via the dashboard.",
                parse_mode="HTML",
            )
            return

        lines = [
            f"{E_PHONE} <b>Priority Agents to Call</b>\n",
            f"<i>Sabse pehle in agents ko call karein:</i>\n",
        ]

        for i, agent in enumerate(agents[:5], 1):
            agent_name = agent.get("name", "Unknown")
            phone = agent.get("phone", "N/A")
            reason = agent.get("reason", "Follow-up due")

            lines.append(f"\n{i}. {E_PERSON} <b>{agent_name}</b>")
            lines.append(f"   {E_PHONE} {phone}")
            lines.append(f"   {E_PIN} <i>{reason}</i>")

        lines.append(f"\n\n{E_MUSCLE} <b>Start calling! Har call se aap closer hain success ke!</b>")

        call_text = "\n".join(lines)
        await query.edit_message_text(
            call_text,
            parse_mode="HTML",
        )
        await send_voice_response(query.message, call_text)
        return

    # For cmd_diary and cmd_train, we inform the user to use the command
    if data == "cmd_diary":
        await query.edit_message_text(
            f"{E_CALENDAR} Use /diary command to open your schedule.\n"
            f"Diary kholne ke liye /diary type karein.",
            parse_mode="HTML",
        )
        return

    if data == "cmd_train":
        await query.edit_message_text(
            f"{E_BOOK} Use /train command to start product training.\n"
            f"Training shuru karne ke liye /train type karein.",
            parse_mode="HTML",
        )
        return


