"""
Reusable InlineKeyboard builders for the ADM Platform Telegram Bot.
All keyboards are built using python-telegram-bot v20+ InlineKeyboardButton/Markup.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from utils.formatters import (
    E_PHONE, E_CHAT, E_CAR, E_CHECK, E_CROSS, E_CLOCK,
    E_CALENDAR, E_GREEN_CIRCLE, E_YELLOW_CIRCLE, E_RED_CIRCLE,
    E_BLUE_CIRCLE, E_GEAR, E_MONEY, E_CHART, E_BOOK,
    E_PERSON, E_BRAIN, E_WARNING, E_SHIELD, E_HEART,
    E_PEOPLE, E_TARGET, E_THUMBSUP, E_PENCIL, E_MEMO,
    E_FIRE, E_STAR, E_BABY, E_ELDER, E_GRADUATION,
    E_FAMILY, E_HOUSE, format_agent_button_label,
)


# ---------------------------------------------------------------------------
# Helper to build grids
# ---------------------------------------------------------------------------

def _build_grid(buttons: list[InlineKeyboardButton], cols: int = 2) -> list[list[InlineKeyboardButton]]:
    """Arrange buttons into a grid with `cols` columns."""
    return [buttons[i:i + cols] for i in range(0, len(buttons), cols)]


# ---------------------------------------------------------------------------
# Main menu / Help keyboard
# ---------------------------------------------------------------------------

def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(f"{E_FIRE} Briefing", callback_data="cmd_briefing"),
        InlineKeyboardButton(f"{E_CALENDAR} Diary", callback_data="cmd_diary"),
        InlineKeyboardButton(f"{E_PEOPLE} Agents", callback_data="cmd_agents"),
        InlineKeyboardButton(f"{E_CHAT} Feedback", callback_data="cmd_feedback"),
        InlineKeyboardButton(f"{E_MEMO} Log", callback_data="cmd_log"),
        InlineKeyboardButton(f"{E_BOOK} Train", callback_data="cmd_train"),
        InlineKeyboardButton(f"{E_BRAIN} Ask AI", callback_data="cmd_ask"),
        InlineKeyboardButton(f"{E_CHART} Stats", callback_data="cmd_stats"),
    ]
    return InlineKeyboardMarkup(_build_grid(buttons, cols=2))


# ---------------------------------------------------------------------------
# Agent selection keyboard
# ---------------------------------------------------------------------------

def agent_list_keyboard(
    agents: list[dict],
    callback_prefix: str = "agent",
    page: int = 1,
    total_pages: int = 1,
    show_search: bool = True,
) -> InlineKeyboardMarkup:
    """Build agent selection keyboard with pagination."""
    buttons = []
    for agent in agents:
        agent_id = agent.get("id", agent.get("agent_code", ""))
        label = format_agent_button_label(agent)
        buttons.append(
            InlineKeyboardButton(label, callback_data=f"{callback_prefix}_{agent_id}")
        )

    rows = _build_grid(buttons, cols=1)

    # Pagination row
    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton("\u25C0 Previous", callback_data=f"{callback_prefix}_page_{page - 1}")
        )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton("Next \u25B6", callback_data=f"{callback_prefix}_page_{page + 1}")
        )
    if nav_row:
        rows.append(nav_row)

    # Search button
    if show_search:
        rows.append([
            InlineKeyboardButton(f"\U0001F50D Search Agent", callback_data=f"{callback_prefix}_search")
        ])

    # Cancel
    rows.append([InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")])

    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Feedback flow keyboards
# ---------------------------------------------------------------------------

def contact_type_keyboard() -> InlineKeyboardMarkup:
    """Contact type selection."""
    buttons = [
        [InlineKeyboardButton(f"{E_PHONE} Call", callback_data="contact_call")],
        [InlineKeyboardButton(f"{E_CHAT} WhatsApp", callback_data="contact_whatsapp")],
        [InlineKeyboardButton(f"{E_CAR} Visit", callback_data="contact_visit")],
        [InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def outcome_keyboard() -> InlineKeyboardMarkup:
    """Contact outcome selection."""
    buttons = [
        [InlineKeyboardButton(f"{E_CHECK} Connected", callback_data="outcome_connected")],
        [InlineKeyboardButton(f"{E_CROSS} Not Answered", callback_data="outcome_not_answered")],
        [InlineKeyboardButton(f"{E_CLOCK} Busy", callback_data="outcome_busy")],
        [InlineKeyboardButton(f"{E_PHONE} Callback Requested", callback_data="outcome_callback")],
        [InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def feedback_category_keyboard() -> InlineKeyboardMarkup:
    """Feedback category selection (top-level)."""
    buttons = [
        [InlineKeyboardButton(f"{E_GEAR} System Issues", callback_data="fcat_system")],
        [InlineKeyboardButton(f"{E_MONEY} Commission Concerns", callback_data="fcat_commission")],
        [InlineKeyboardButton(f"{E_CHART} Market Conditions", callback_data="fcat_market")],
        [InlineKeyboardButton(f"{E_BOOK} Product Complexity", callback_data="fcat_product")],
        [InlineKeyboardButton(f"{E_HEART} Personal Reasons", callback_data="fcat_personal")],
        [InlineKeyboardButton(f"{E_TARGET} Competition", callback_data="fcat_competition")],
        [InlineKeyboardButton(f"{E_WARNING} Support Issues", callback_data="fcat_support")],
        [InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


# Subcategory keyboards per category
_SUBCATEGORIES = {
    "system": [
        ("Portal Down", "fsub_portal_down"),
        ("Login Issues", "fsub_login_issues"),
        ("Slow Performance", "fsub_slow_perf"),
        ("App Crash", "fsub_app_crash"),
    ],
    "commission": [
        ("Delayed Payment", "fsub_delayed_pay"),
        ("Low Rate", "fsub_low_rate"),
        ("Unclear Structure", "fsub_unclear_struct"),
    ],
    "market": [
        ("Low Demand", "fsub_low_demand"),
        ("Customer Resistance", "fsub_cust_resist"),
        ("Competition", "fsub_competition"),
    ],
    "product": [
        ("Too Many Products", "fsub_too_many"),
        ("Hard to Explain", "fsub_hard_explain"),
        ("No Training", "fsub_no_training"),
    ],
    "personal": [
        ("Health", "fsub_health"),
        ("Family", "fsub_family"),
        ("Other Job", "fsub_other_job"),
        ("Lost Interest", "fsub_lost_interest"),
    ],
    "competition": [
        ("LIC", "fsub_lic"),
        ("Other Private", "fsub_other_private"),
        ("Banks", "fsub_banks"),
    ],
    "support": [
        ("No ADM Support", "fsub_no_adm"),
        ("Late Responses", "fsub_late_resp"),
        ("No Materials", "fsub_no_materials"),
    ],
}


def feedback_subcategory_keyboard(category: str) -> InlineKeyboardMarkup:
    """Build subcategory keyboard for a given category."""
    subs = _SUBCATEGORIES.get(category, [])
    buttons = [[InlineKeyboardButton(label, callback_data=cb)] for label, cb in subs]
    buttons.append([InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def followup_keyboard() -> InlineKeyboardMarkup:
    """Follow-up scheduling options."""
    buttons = [
        [InlineKeyboardButton(f"{E_CALENDAR} Tomorrow", callback_data="followup_tomorrow")],
        [InlineKeyboardButton(f"{E_CALENDAR} In 3 Days", callback_data="followup_3days")],
        [InlineKeyboardButton(f"{E_CALENDAR} In 1 Week", callback_data="followup_1week")],
        [InlineKeyboardButton(f"{E_CALENDAR} In 2 Weeks", callback_data="followup_2weeks")],
        [InlineKeyboardButton(f"{E_CROSS} No Follow-up", callback_data="followup_none")],
        [InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def notes_keyboard() -> InlineKeyboardMarkup:
    """Prompt for notes or skip."""
    buttons = [
        [InlineKeyboardButton(f"{E_PENCIL} Type Notes", callback_data="notes_type")],
        [InlineKeyboardButton(f"\U0001F3A4 Send Voice Note", callback_data="notes_voice")],
        [InlineKeyboardButton(f"\u23E9 Skip", callback_data="notes_skip")],
    ]
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Generic confirm / cancel."""
    buttons = [
        [
            InlineKeyboardButton(f"{E_CHECK} Confirm / Haan", callback_data="confirm_yes"),
            InlineKeyboardButton(f"{E_CROSS} Cancel / Nahi", callback_data="confirm_no"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Interaction logging keyboards
# ---------------------------------------------------------------------------

def interaction_topic_keyboard() -> InlineKeyboardMarkup:
    """What was discussed?"""
    buttons = [
        [InlineKeyboardButton(f"{E_SHIELD} Product Info", callback_data="topic_product")],
        [InlineKeyboardButton(f"{E_MONEY} Commission Query", callback_data="topic_commission")],
        [InlineKeyboardButton(f"{E_GEAR} System Help", callback_data="topic_system")],
        [InlineKeyboardButton(f"{E_FIRE} Re-engagement", callback_data="topic_reengage")],
        [InlineKeyboardButton(f"{E_BOOK} Training", callback_data="topic_training")],
        [InlineKeyboardButton(f"{E_PENCIL} Other", callback_data="topic_other")],
        [InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def interaction_outcome_keyboard() -> InlineKeyboardMarkup:
    """Interaction outcome."""
    buttons = [
        [InlineKeyboardButton(f"{E_GREEN_CIRCLE} Positive", callback_data="ioutcome_positive")],
        [InlineKeyboardButton(f"{E_YELLOW_CIRCLE} Neutral", callback_data="ioutcome_neutral")],
        [InlineKeyboardButton(f"{E_RED_CIRCLE} Negative", callback_data="ioutcome_negative")],
        [InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Training keyboards
# ---------------------------------------------------------------------------

def training_category_keyboard() -> InlineKeyboardMarkup:
    """Training module category selection."""
    buttons = [
        [InlineKeyboardButton(f"{E_SHIELD} Term Insurance", callback_data="tcat_term")],
        [InlineKeyboardButton(f"{E_MONEY} Savings Plans", callback_data="tcat_savings")],
        [InlineKeyboardButton(f"{E_CHART} ULIPs", callback_data="tcat_ulip")],
        [InlineKeyboardButton(f"{E_ELDER} Pension Plans", callback_data="tcat_pension")],
        [InlineKeyboardButton(f"{E_BABY} Child Plans", callback_data="tcat_child")],
        [InlineKeyboardButton(f"{E_PEOPLE} Group Insurance", callback_data="tcat_group")],
        [InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def training_product_keyboard(products: list[dict], category: str) -> InlineKeyboardMarkup:
    """Product selection within a training category."""
    buttons = []
    for prod in products:
        prod_id = prod.get("id", "")
        name = prod.get("name", "Unknown Product")
        buttons.append(
            [InlineKeyboardButton(f"{E_STAR} {name}", callback_data=f"tprod_{prod_id}")]
        )
    buttons.append([InlineKeyboardButton("\u25C0 Back to Categories", callback_data="tcat_back")])
    buttons.append([InlineKeyboardButton(f"{E_CROSS} Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)


def quiz_start_keyboard() -> InlineKeyboardMarkup:
    """Option to start quiz after product summary."""
    buttons = [
        [InlineKeyboardButton(f"{E_BRAIN} Take Quiz / Quiz Dein", callback_data="quiz_start")],
        [InlineKeyboardButton("\u25C0 Back to Products", callback_data="quiz_back")],
        [InlineKeyboardButton(f"{E_CROSS} Done / Ho Gaya", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def quiz_answer_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    """Quiz answer buttons."""
    labels = ["A", "B", "C", "D"]
    buttons = []
    for i, opt in enumerate(options):
        label = labels[i] if i < len(labels) else str(i + 1)
        # Truncate long option text for button
        display = opt if len(opt) <= 40 else opt[:37] + "..."
        buttons.append(
            [InlineKeyboardButton(f"{label}. {display}", callback_data=f"quiz_ans_{i}")]
        )
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Diary keyboards
# ---------------------------------------------------------------------------

def diary_action_keyboard() -> InlineKeyboardMarkup:
    """Actions for the diary view."""
    buttons = [
        [InlineKeyboardButton(f"{E_PENCIL} Add Entry / Entry Daalein", callback_data="diary_add")],
        [InlineKeyboardButton(f"{E_CHECK} Mark Complete / Poora Karein", callback_data="diary_complete")],
        [InlineKeyboardButton(f"{E_CALENDAR} Reschedule / Badlein", callback_data="diary_reschedule")],
        [InlineKeyboardButton(f"\U0001F4C6 Another Date", callback_data="diary_other_date")],
        [InlineKeyboardButton(f"{E_CROSS} Close / Band Karein", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


def diary_entry_select_keyboard(entries: list[dict], action: str) -> InlineKeyboardMarkup:
    """Select a diary entry for completion or rescheduling."""
    buttons = []
    for entry in entries:
        entry_id = entry.get("id", "")
        title = entry.get("title", "Untitled")
        if len(title) > 35:
            title = title[:32] + "..."
        buttons.append(
            [InlineKeyboardButton(f"{E_MEMO} {title}", callback_data=f"dentry_{action}_{entry_id}")]
        )
    buttons.append([InlineKeyboardButton(f"\u25C0 Back", callback_data="diary_back")])
    return InlineKeyboardMarkup(buttons)


def reschedule_keyboard() -> InlineKeyboardMarkup:
    """Reschedule date options."""
    buttons = [
        [InlineKeyboardButton(f"{E_CALENDAR} Tomorrow", callback_data="resched_tomorrow")],
        [InlineKeyboardButton(f"{E_CALENDAR} In 3 Days", callback_data="resched_3days")],
        [InlineKeyboardButton(f"{E_CALENDAR} Next Week", callback_data="resched_1week")],
        [InlineKeyboardButton(f"\u25C0 Back", callback_data="diary_back")],
    ]
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Briefing action keyboard
# ---------------------------------------------------------------------------

def briefing_action_keyboard() -> InlineKeyboardMarkup:
    """Actions after viewing briefing."""
    buttons = [
        [InlineKeyboardButton(f"{E_PHONE} Call Priority Agent", callback_data="brief_call")],
        [InlineKeyboardButton(f"{E_CALENDAR} Open Diary", callback_data="cmd_diary")],
        [InlineKeyboardButton(f"{E_BOOK} Start Training", callback_data="cmd_train")],
        [InlineKeyboardButton(f"{E_CHECK} Got it! / Samajh Gaya!", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(buttons)


# ---------------------------------------------------------------------------
# Yes / No
# ---------------------------------------------------------------------------

def yes_no_keyboard(prefix: str = "yn") -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(f"{E_CHECK} Yes / Haan", callback_data=f"{prefix}_yes"),
            InlineKeyboardButton(f"{E_CROSS} No / Nahi", callback_data=f"{prefix}_no"),
        ],
    ]
    return InlineKeyboardMarkup(buttons)
