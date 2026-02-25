"""
Performance stats handler for the ADM Platform Telegram Bot.
Shows personal performance metrics with visual progress bars.
"""

import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from utils.api_client import api_client
from utils.formatters import (
    format_stats,
    error_not_registered,
    error_generic,
    header,
    section_divider,
    thin_divider,
    E_CHART, E_FIRE, E_ROCKET, E_TROPHY, E_MEDAL,
    E_STAR, E_CHECK, E_CROSS, E_SPARKLE, E_TARGET,
    E_PHONE, E_MEMO, E_PEOPLE, E_PERSON, E_MUSCLE,
    E_GREEN_CIRCLE, E_YELLOW_CIRCLE, E_RED_CIRCLE,
    E_BOOK, E_BRAIN, E_CALENDAR, E_CLOCK, E_BULB,
    E_SHIELD, E_DIAMOND, E_CROWN,
)
from utils.voice import send_voice_response

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Progress bar helper
# ---------------------------------------------------------------------------

def _progress_bar(value: int, max_val: int, length: int = 10) -> str:
    """Create a text-based progress bar using block characters."""
    if max_val <= 0:
        return "\u2591" * length + " 0%"

    ratio = min(value / max_val, 1.0)
    filled = int(ratio * length)
    empty = length - filled

    bar = "\u2588" * filled + "\u2591" * empty
    pct = int(ratio * 100)

    return f"{bar} {pct}%"


def _mini_bar(value: int, max_val: int) -> str:
    """Create a compact progress indicator."""
    if max_val <= 0:
        return "\u25CB" * 5

    ratio = min(value / max_val, 1.0)
    filled = int(ratio * 5)
    empty = 5 - filled

    return "\u25CF" * filled + "\u25CB" * empty


# ---------------------------------------------------------------------------
# /stats command
# ---------------------------------------------------------------------------

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command - show performance dashboard."""
    telegram_id = update.effective_user.id
    user = update.effective_user

    # Get profile
    profile = await api_client.get_adm_profile(telegram_id)

    if profile and not profile.get("error"):
        name = profile.get("name", user.first_name or "ADM")
    else:
        name = user.first_name or "ADM"

    # Fetch stats from API
    stats_resp = await api_client.get_adm_stats(telegram_id)

    if stats_resp and not stats_resp.get("error"):
        stats_data = stats_resp
        if not stats_data.get("adm_name"):
            stats_data["adm_name"] = name

        # Build the detailed stats message
        stats_text = _format_detailed_stats(stats_data)

        # Stats action keyboard
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(f"{E_CALENDAR} This Week", callback_data="stats_week"),
                InlineKeyboardButton(f"{E_CHART} This Month", callback_data="stats_month"),
            ],
            [InlineKeyboardButton(f"{E_CHECK} Got it! / Samajh Gaya!", callback_data="stats_done")],
        ])

        sent_msg = await update.message.reply_text(
            stats_text,
            parse_mode="HTML",
            reply_markup=keyboard,
        )
        await send_voice_response(sent_msg, stats_text)
    else:
        await update.message.reply_text(
            f"{E_CHART} <b>No stats data available.</b>\n\n"
            f"Please check your connection or add data via the dashboard.",
            parse_mode="HTML",
        )


def _format_detailed_stats(data: dict) -> str:
    """Format detailed stats with progress bars."""
    name = data.get("adm_name", "ADM")
    period = data.get("period", "This Month")

    # Agent portfolio
    total_agents = data.get("total_agents", 0)
    active = data.get("active_agents", 0)
    at_risk = data.get("at_risk_agents", 0)
    inactive = data.get("inactive_agents", 0)

    # Activity
    total_calls = data.get("total_calls", 0)
    total_feedbacks = data.get("total_feedbacks", 0)
    total_activations = data.get("total_activations", 0)
    activation_rate = data.get("activation_rate", 0)

    # Weekly
    weekly = data.get("weekly", {})
    w_calls = weekly.get("calls", 0)
    w_calls_target = weekly.get("calls_target", 50)
    w_feedbacks = weekly.get("feedbacks", 0)
    w_feedbacks_target = weekly.get("feedbacks_target", 25)
    w_fu_done = weekly.get("follow_ups_completed", 0)
    w_fu_total = weekly.get("follow_ups_total", 10)

    # Training
    training = data.get("training", {})
    t_done = training.get("modules_completed", 0)
    t_total = training.get("modules_total", 10)
    t_avg = training.get("quiz_avg_score", 0)
    t_last = training.get("last_training", "N/A")

    # Pending
    pending_fu = data.get("pending_follow_ups", 0)
    overdue_fu = data.get("overdue_follow_ups", 0)

    # Streaks
    streak = data.get("daily_streak", 0)
    best_streak = data.get("best_streak", 0)

    # Build the message
    lines = [
        f"{E_CHART} <b>Performance Dashboard</b>",
        f"{E_PERSON} <b>{name}</b> | {E_CALENDAR} {period}",
        f"\u2501" * 28,
        "",
        # Agent Portfolio Section
        f"{E_PEOPLE} <b>Agent Portfolio</b>",
        f"",
        f"  Total Agents: <b>{total_agents}</b>",
        f"  {E_GREEN_CIRCLE} Active:   <b>{active}</b>  {_progress_bar(active, total_agents)}",
        f"  {E_YELLOW_CIRCLE} At Risk:  <b>{at_risk}</b>  {_progress_bar(at_risk, total_agents)}",
        f"  {E_RED_CIRCLE} Inactive: <b>{inactive}</b>  {_progress_bar(inactive, total_agents)}",
        "",
        f"\u2501" * 28,
        "",
        # Weekly Progress Section
        f"{E_FIRE} <b>This Week's Progress</b>",
        f"",
        f"  {E_PHONE} Calls:     <b>{w_calls}/{w_calls_target}</b>",
        f"  {_progress_bar(w_calls, w_calls_target, 15)}",
        f"",
        f"  {E_MEMO} Feedbacks: <b>{w_feedbacks}/{w_feedbacks_target}</b>",
        f"  {_progress_bar(w_feedbacks, w_feedbacks_target, 15)}",
        f"",
        f"  {E_CHECK} Follow-ups: <b>{w_fu_done}/{w_fu_total}</b>",
        f"  {_progress_bar(w_fu_done, w_fu_total, 15)}",
        "",
        f"\u2501" * 28,
        "",
        # Monthly Summary
        f"{E_ROCKET} <b>Monthly Summary</b>",
        f"",
        f"  {E_PHONE} Total Calls: <b>{total_calls}</b>",
        f"  {E_MEMO} Total Feedbacks: <b>{total_feedbacks}</b>",
        f"  {E_SPARKLE} Activations: <b>{total_activations}</b>",
        f"  {E_TARGET} Activation Rate: <b>{activation_rate:.1f}%</b>",
        "",
        f"\u2501" * 28,
        "",
        # Training Progress
        f"{E_BOOK} <b>Training Progress</b>",
        f"",
        f"  Modules: <b>{t_done}/{t_total}</b>  {_progress_bar(t_done, t_total)}",
        f"  {E_BRAIN} Avg Quiz Score: <b>{t_avg}%</b>  {_mini_bar(t_avg, 100)}",
        f"  {E_STAR} Last: <i>{t_last}</i>",
        "",
        f"\u2501" * 28,
        "",
        # Pending Items
        f"{E_CLOCK} <b>Pending Items</b>",
        f"",
        f"  {E_CALENDAR} Follow-ups pending: <b>{pending_fu}</b>",
    ]

    if overdue_fu > 0:
        lines.append(f"  {E_RED_CIRCLE} <b>Overdue: {overdue_fu}</b> - Action needed!")
    else:
        lines.append(f"  {E_GREEN_CIRCLE} No overdue items! {E_SPARKLE}")

    lines.extend([
        "",
        f"\u2501" * 28,
        "",
        # Streak
        f"{E_FIRE} <b>Daily Streak:</b> {streak} days {'| Best: ' + str(best_streak) if best_streak > streak else E_CROWN + ' Personal Best!'}",
        "",
    ])

    # Motivational footer
    if activation_rate >= 20:
        lines.append(f"{E_TROPHY} <b>Outstanding performance! Keep it up!</b>")
    elif activation_rate >= 10:
        lines.append(f"{E_MEDAL} <b>Good progress! Push for 20% activation rate!</b>")
    else:
        lines.append(f"{E_MUSCLE} <b>Let's increase those numbers! Har call matters!</b>")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stats callback actions
# ---------------------------------------------------------------------------

async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle stats action button presses."""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "stats_done":
        await query.edit_message_text(
            f"{E_CHECK} <b>Stats reviewed!</b>\n\n"
            f"{E_MUSCLE} Keep pushing for excellence!\n"
            f"Use /stats anytime to check your progress.\n\n"
            f"{E_FIRE} Aaj ka din best banao!",
            parse_mode="HTML",
        )
        return

    if data in ("stats_week", "stats_month"):
        telegram_id = update.effective_user.id
        user = update.effective_user

        profile = await api_client.get_adm_profile(telegram_id)
        name = (profile.get("name", user.first_name) if profile and not profile.get("error") else user.first_name) or "ADM"

        stats_resp = await api_client.get_adm_stats(telegram_id)

        if stats_resp and not stats_resp.get("error"):
            stats_data = stats_resp
            if not stats_data.get("adm_name"):
                stats_data["adm_name"] = name

            # Update period label
            if data == "stats_week":
                stats_data["period"] = "This Week"
            else:
                stats_data["period"] = "This Month"

            stats_text = _format_detailed_stats(stats_data)

            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(f"{E_CALENDAR} This Week", callback_data="stats_week"),
                    InlineKeyboardButton(f"{E_CHART} This Month", callback_data="stats_month"),
                ],
                [InlineKeyboardButton(f"{E_CHECK} Got it!", callback_data="stats_done")],
            ])

            await query.edit_message_text(
                stats_text,
                parse_mode="HTML",
                reply_markup=keyboard,
            )
            await send_voice_response(query.message, stats_text)
        else:
            await query.edit_message_text(
                f"{E_CHART} <b>No stats data available.</b>\n\n"
                f"Please check your connection or add data via the dashboard.",
                parse_mode="HTML",
            )
