"""
Beautiful message formatting utilities for the ADM Platform Telegram Bot.
Supports Hindi + English with proper emojis and spacing for mobile readability.
"""

from datetime import datetime, date
from typing import Optional


# ---------------------------------------------------------------------------
# Reusable emoji constants
# ---------------------------------------------------------------------------
E_WAVE = "\U0001F44B"        # wave
E_STAR = "\u2B50"             # star
E_CHECK = "\u2705"            # green check
E_CROSS = "\u274C"            # red cross
E_CLOCK = "\U0001F551"       # clock
E_CALENDAR = "\U0001F4C5"    # calendar
E_FIRE = "\U0001F525"        # fire
E_ROCKET = "\U0001F680"      # rocket
E_TROPHY = "\U0001F3C6"      # trophy
E_CHART = "\U0001F4C8"       # chart increasing
E_PHONE = "\U0001F4DE"       # telephone
E_PERSON = "\U0001F464"      # bust in silhouette
E_PEOPLE = "\U0001F465"      # busts
E_BOOK = "\U0001F4D6"        # open book
E_BULB = "\U0001F4A1"        # light bulb
E_BELL = "\U0001F514"        # bell
E_PIN = "\U0001F4CC"         # pushpin
E_MEMO = "\U0001F4DD"        # memo
E_HEART = "\u2764\uFE0F"     # red heart
E_SHIELD = "\U0001F6E1\uFE0F"  # shield
E_MONEY = "\U0001F4B0"       # money bag
E_TARGET = "\U0001F3AF"      # target
E_MUSCLE = "\U0001F4AA"      # flexed bicep
E_HANDSHAKE = "\U0001F91D"   # handshake
E_PENCIL = "\u270F\uFE0F"    # pencil
E_WARNING = "\u26A0\uFE0F"   # warning
E_RED_CIRCLE = "\U0001F534"  # red circle
E_YELLOW_CIRCLE = "\U0001F7E1"  # yellow circle
E_GREEN_CIRCLE = "\U0001F7E2"   # green circle
E_BLUE_CIRCLE = "\U0001F535"    # blue circle
E_SPARKLE = "\u2728"         # sparkles
E_SUNRISE = "\U0001F305"     # sunrise
E_BRAIN = "\U0001F9E0"       # brain
E_CLAP = "\U0001F44F"        # clapping
E_THUMBSUP = "\U0001F44D"    # thumbs up
E_CHAT = "\U0001F4AC"        # speech bubble
E_HOUSE = "\U0001F3E0"       # house
E_CAR = "\U0001F697"         # car
E_BABY = "\U0001F476"        # baby
E_ELDER = "\U0001F9D3"       # older person
E_FAMILY = "\U0001F468\u200D\U0001F469\u200D\U0001F467\u200D\U0001F466"
E_GRADUATION = "\U0001F393"  # graduation cap
E_MEDAL = "\U0001F3C5"       # medal
E_INBOX = "\U0001F4E5"       # inbox tray
E_LINK = "\U0001F517"        # link
E_GEAR = "\u2699\uFE0F"      # gear
E_MIC = "\U0001F3A4"         # microphone
E_DIAMOND = "\U0001F48E"     # gem stone
E_CROWN = "\U0001F451"       # crown


# ---------------------------------------------------------------------------
# Motivational quotes (rotates daily)
# ---------------------------------------------------------------------------
MOTIVATIONAL_QUOTES = [
    f"{E_FIRE} \"Success is not final, failure is not fatal: it is the courage to continue that counts.\"",
    f"{E_ROCKET} \"The harder you work for something, the greater you'll feel when you achieve it.\"",
    f"{E_STAR} \"Believe you can and you're halfway there.\"",
    f"{E_MUSCLE} \"Great things never come from comfort zones.\"",
    f"{E_TROPHY} \"Winners never quit and quitters never win.\"",
    f"{E_TARGET} \"Set your goals high, and don't stop till you get there.\"",
    f"{E_DIAMOND} \"Pressure makes diamonds.\"",
    f"{E_CROWN} \"A champion is defined not by their wins but by how they recover when they fall.\"",
    f"{E_SPARKLE} \"Aapka har ek call kisi ki zindagi badal sakta hai!\" (Your every call can change someone's life!)",
    f"{E_HEART} \"Bima sirf product nahi, parivaar ki suraksha hai.\" (Insurance is not just a product, it's family protection.)",
]


def get_daily_quote() -> str:
    """Return a motivational quote based on the day of the year."""
    day = datetime.now().timetuple().tm_yday
    return MOTIVATIONAL_QUOTES[day % len(MOTIVATIONAL_QUOTES)]


# ---------------------------------------------------------------------------
# Header / section helpers
# ---------------------------------------------------------------------------

def header(title: str, emoji: str = "") -> str:
    """Create a bold header line."""
    if emoji:
        return f"{emoji} <b>{title}</b>"
    return f"<b>{title}</b>"


def section_divider() -> str:
    return "\n" + "\u2500" * 28 + "\n"


def thin_divider() -> str:
    return "\n\u2508" * 14 + "\n"


# ---------------------------------------------------------------------------
# Greeting
# ---------------------------------------------------------------------------

def greeting(name: str) -> str:
    """Generate a time-aware greeting."""
    hour = datetime.now().hour
    if hour < 12:
        prefix = f"{E_SUNRISE} Good Morning / Suprabhat"
    elif hour < 17:
        prefix = f"\u2600\uFE0F Good Afternoon / Namaskar"
    else:
        prefix = f"\U0001F307 Good Evening / Shubh Sandhya"
    return f"{prefix}, <b>{name}</b>! {E_WAVE}"


# ---------------------------------------------------------------------------
# Welcome / Registration
# ---------------------------------------------------------------------------

def welcome_message() -> str:
    """Welcome message for new users."""
    return (
        f"{E_SPARKLE}{E_SPARKLE}{E_SPARKLE}\n\n"
        f"{header('Welcome to ADM Platform', E_SHIELD)}\n"
        f"<b>Axis Max Life Insurance</b>\n\n"
        f"{E_ROCKET} Your personal assistant for:\n\n"
        f"  {E_PEOPLE} Agent management\n"
        f"  {E_CHAT} Feedback capture\n"
        f"  {E_CALENDAR} Daily scheduling\n"
        f"  {E_BOOK} Product training\n"
        f"  {E_CHART} Performance tracking\n"
        f"  {E_BULB} AI-powered answers\n\n"
        f"{thin_divider()}"
        f"Let's get you registered! {E_PENCIL}\n\n"
        f"Please enter your <b>full name</b>:"
    )


def registration_success(name: str, web_username: str = "", employee_id: str = "") -> str:
    """Registration success message."""
    web_info = ""
    if web_username:
        password_hint = employee_id if employee_id else "your Telegram ID"
        web_info = (
            f"\n{header('Web Dashboard Login', E_GEAR)}\n\n"
            f"  {E_PERSON} Username: <b>{web_username}</b>\n"
            f"  {E_STAR} Password: <b>{password_hint}</b>\n"
            f"  (You can change this later)\n\n"
        )
    return (
        f"{E_CHECK} <b>Registration Successful!</b>\n\n"
        f"Welcome aboard, <b>{name}</b>! {E_CLAP}\n\n"
        f"Aapka ADM Platform account ready hai.\n"
        f"(Your ADM Platform account is ready.)\n"
        f"{web_info}"
        f"{header('Quick Start', E_STAR)}\n\n"
        f"  /briefing  - {E_SUNRISE} Morning briefing\n"
        f"  /agents    - {E_PEOPLE} Your agents list\n"
        f"  /feedback  - {E_CHAT} Capture feedback\n"
        f"  /diary     - {E_CALENDAR} Your schedule\n"
        f"  /train     - {E_BOOK} Learn products\n"
        f"  /ask       - {E_BRAIN} Ask anything\n"
        f"  /stats     - {E_CHART} Performance\n"
        f"  /log       - {E_MEMO} Log interaction\n"
        f"  /help      - {E_BULB} All commands\n\n"
        f"{E_FIRE} Let's make today count!"
    )


# ---------------------------------------------------------------------------
# Help message
# ---------------------------------------------------------------------------

def help_message(name: str = "ADM") -> str:
    """Full help message listing all commands."""
    return (
        f"{header('ADM Platform Commands', E_GEAR)}\n\n"
        f"{E_SUNRISE} <b>Daily Operations</b>\n"
        f"  /briefing  - Morning briefing / Subah ki report\n"
        f"  /diary     - Today's schedule / Aaj ka diary\n"
        f"  /agents    - Your agents / Aapke agents\n\n"
        f"{E_CHAT} <b>Capture & Log</b>\n"
        f"  /feedback  - Capture agent feedback\n"
        f"  /log       - Log an interaction\n\n"
        f"{E_BOOK} <b>Learning & AI</b>\n"
        f"  /train     - Product training modules\n"
        f"  /ask       - AI product answers\n\n"
        f"{E_CHART} <b>Performance</b>\n"
        f"  /stats     - Your performance stats\n\n"
        f"{E_GEAR} <b>General</b>\n"
        f"  /voice     - Toggle voice notes on/off \U0001F50A\n"
        f"  /help      - Show this menu\n"
        f"  /start     - Restart / Register\n\n"
        f"{thin_divider()}"
        f"\U0001F50A <i>/voice ON karo toh har response voice mein bhi milega!</i>\n"
        f"{E_BULB} <i>Type /ask followed by your question in Hindi or English</i>"
    )


# ---------------------------------------------------------------------------
# Agent formatting
# ---------------------------------------------------------------------------

def format_agent_list(agents: list[dict], page: int = 1, total_pages: int = 1) -> str:
    """Format agent list for display."""
    if not agents:
        return (
            f"{E_PEOPLE} <b>Your Agents</b>\n\n"
            f"No agents assigned yet.\n"
            f"Abhi tak koi agent assign nahi hua."
        )

    lines = [f"{E_PEOPLE} <b>Your Agents</b> (Page {page}/{total_pages})\n"]

    for agent in agents:
        status = agent.get("status", "unknown")
        name = agent.get("name", "Unknown")
        code = agent.get("agent_code", "")
        last_active = agent.get("last_active", "N/A")

        # Status indicator
        if status == "active":
            icon = E_GREEN_CIRCLE
        elif status == "at_risk":
            icon = E_YELLOW_CIRCLE
        elif status == "inactive":
            icon = E_RED_CIRCLE
        else:
            icon = E_BLUE_CIRCLE

        lines.append(f"\n{icon} <b>{name}</b>")
        lines.append(f"   Code: <code>{code}</code>")
        lines.append(f"   Last active: {last_active}")

    return "\n".join(lines)


def format_agent_button_label(agent: dict) -> str:
    """Format agent name for inline keyboard button."""
    status = agent.get("status", "unknown")
    name = agent.get("name", "Unknown")
    if status == "active":
        return f"{E_GREEN_CIRCLE} {name}"
    elif status == "at_risk":
        return f"{E_YELLOW_CIRCLE} {name}"
    elif status == "inactive":
        return f"{E_RED_CIRCLE} {name}"
    return f"{E_BLUE_CIRCLE} {name}"


# ---------------------------------------------------------------------------
# Feedback formatting
# ---------------------------------------------------------------------------

def format_feedback_summary(data: dict) -> str:
    """Format a feedback entry for confirmation."""
    agent_name = data.get("agent_name", "Unknown")
    contact_type = data.get("contact_type", "N/A")
    outcome = data.get("outcome", "N/A")
    category = data.get("category", "N/A")
    subcategory = data.get("subcategory", "N/A")
    notes = data.get("notes", "No notes")
    followup = data.get("followup_date", "Not set")

    contact_icons = {"Call": E_PHONE, "WhatsApp": E_CHAT, "Visit": E_CAR}
    c_icon = contact_icons.get(contact_type, E_PHONE)

    return (
        f"{header('Feedback Summary', E_MEMO)}\n\n"
        f"{E_PERSON} <b>Agent:</b> {agent_name}\n"
        f"{c_icon} <b>Contact:</b> {contact_type}\n"
        f"{E_TARGET} <b>Outcome:</b> {outcome}\n"
        f"{E_PIN} <b>Category:</b> {category}\n"
        f"   {E_LINK} <b>Sub-category:</b> {subcategory}\n"
        f"{E_PENCIL} <b>Notes:</b> {notes}\n"
        f"{E_CALENDAR} <b>Follow-up:</b> {followup}\n\n"
        f"<i>Is this correct? / Kya ye sahi hai?</i>"
    )


def feedback_saved() -> str:
    return (
        f"{E_CHECK} <b>Feedback Saved Successfully!</b>\n\n"
        f"Feedback record ho gaya hai.\n"
        f"Follow-up reminder set kar diya gaya hai.\n\n"
        f"{E_THUMBSUP} Great work! Keep connecting with your agents."
    )


# ---------------------------------------------------------------------------
# Interaction logging formatting
# ---------------------------------------------------------------------------

def format_interaction_summary(data: dict) -> str:
    """Format an interaction for confirmation."""
    agent_name = data.get("agent_name", "Unknown")
    topic = data.get("topic", "N/A")
    outcome = data.get("outcome", "N/A")
    followup = data.get("followup_date", "Not set")
    notes = data.get("notes", "No notes")

    outcome_icons = {"Positive": E_GREEN_CIRCLE, "Neutral": E_YELLOW_CIRCLE, "Negative": E_RED_CIRCLE}
    o_icon = outcome_icons.get(outcome, E_BLUE_CIRCLE)

    return (
        f"{header('Interaction Summary', E_HANDSHAKE)}\n\n"
        f"{E_PERSON} <b>Agent:</b> {agent_name}\n"
        f"{E_CHAT} <b>Topic:</b> {topic}\n"
        f"{o_icon} <b>Outcome:</b> {outcome}\n"
        f"{E_PENCIL} <b>Notes:</b> {notes}\n"
        f"{E_CALENDAR} <b>Follow-up:</b> {followup}\n\n"
        f"<i>Confirm and save? / Save karein?</i>"
    )


def interaction_saved() -> str:
    return (
        f"{E_CHECK} <b>Interaction Logged!</b>\n\n"
        f"Record saved. Aapka interaction log ho gaya.\n\n"
        f"{E_MUSCLE} Keep up the great engagement!"
    )


# ---------------------------------------------------------------------------
# Diary / Schedule formatting
# ---------------------------------------------------------------------------

def format_diary(entries: list[dict], date_str: Optional[str] = None) -> str:
    """Format diary entries for display."""
    if date_str is None:
        date_str = date.today().strftime("%d %b %Y")

    if not entries:
        return (
            f"{E_CALENDAR} <b>Diary - {date_str}</b>\n\n"
            f"No entries for today.\n"
            f"Aaj ke liye koi entry nahi hai.\n\n"
            f"Use /diary to add a new entry."
        )

    lines = [
        f"{E_CALENDAR} <b>Diary - {date_str}</b>\n",
        f"{E_RED_CIRCLE} Overdue  {E_YELLOW_CIRCLE} Today  {E_GREEN_CIRCLE} Upcoming\n"
    ]

    for entry in entries:
        title = entry.get("title", "Untitled")
        time_str = entry.get("time", "")
        priority = entry.get("priority", "normal")
        completed = entry.get("completed", False)
        agent_name = entry.get("agent_name", "")

        if completed:
            icon = E_CHECK
        elif priority == "overdue":
            icon = E_RED_CIRCLE
        elif priority == "today":
            icon = E_YELLOW_CIRCLE
        elif priority == "upcoming":
            icon = E_GREEN_CIRCLE
        else:
            icon = E_BLUE_CIRCLE

        line = f"\n{icon} "
        if completed:
            line += f"<s>{title}</s>"
        else:
            line += f"<b>{title}</b>"

        if time_str:
            line += f"\n   {E_CLOCK} {time_str}"
        if agent_name:
            line += f"\n   {E_PERSON} {agent_name}"

        lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Morning briefing
# ---------------------------------------------------------------------------

def format_morning_briefing(data: dict) -> str:
    """Format the complete morning briefing."""
    name = data.get("adm_name", "ADM")
    priority_agents = data.get("priority_agents", [])
    overdue = data.get("overdue_followups", [])
    new_assignments = data.get("new_assignments", [])
    training_tip = data.get("training_tip", "Focus on understanding customer needs first.")
    yesterday_stats = data.get("yesterday_stats", {})

    lines = [
        f"{E_SUNRISE}{E_SUNRISE}{E_SUNRISE}",
        "",
        greeting(name),
        "",
        get_daily_quote(),
        "",
        section_divider(),
    ]

    # Priority agents
    lines.append(f"{header('Priority Agents Today', E_FIRE)}\n")
    if priority_agents:
        for i, agent in enumerate(priority_agents[:5], 1):
            agent_name = agent.get("name", "Unknown")
            reason = agent.get("reason", "Follow-up due")
            lines.append(f"  {i}. {E_PERSON} <b>{agent_name}</b>")
            lines.append(f"     {E_PIN} {reason}\n")
    else:
        lines.append(f"  {E_CHECK} No priority agents today. Great job!")

    lines.append(section_divider())

    # Overdue follow-ups
    lines.append(f"{header('Overdue Follow-ups', E_WARNING)}\n")
    if overdue:
        for item in overdue[:5]:
            agent_name = item.get("agent_name", "Unknown")
            due = item.get("due_date", "N/A")
            lines.append(f"  {E_RED_CIRCLE} <b>{agent_name}</b> - Due: {due}")
        lines.append(f"\n  <i>Total overdue: {len(overdue)}</i>")
    else:
        lines.append(f"  {E_CHECK} All caught up! Sab up-to-date hai!")

    lines.append(section_divider())

    # New assignments
    lines.append(f"{header('New Agent Assignments', E_BELL)}\n")
    if new_assignments:
        for agent in new_assignments:
            agent_name = agent.get("name", "Unknown")
            code = agent.get("agent_code", "")
            lines.append(f"  {E_SPARKLE} <b>{agent_name}</b> ({code})")
    else:
        lines.append(f"  No new assignments today.")

    lines.append(section_divider())

    # Yesterday's stats
    calls = yesterday_stats.get("calls", 0)
    feedbacks = yesterday_stats.get("feedbacks", 0)
    activations = yesterday_stats.get("activations", 0)

    perf_title = "Yesterday's Performance"
    lines.append(f"{header(perf_title, E_CHART)}\n")
    lines.append(f"  {E_PHONE} Calls made: <b>{calls}</b>")
    lines.append(f"  {E_MEMO} Feedbacks captured: <b>{feedbacks}</b>")
    lines.append(f"  {E_ROCKET} Activations: <b>{activations}</b>")

    lines.append(section_divider())

    # Training tip
    lines.append(f"{header('Training Tip of the Day', E_BULB)}\n")
    lines.append(f"  <i>{training_tip}</i>")

    lines.append(f"\n\n{E_MUSCLE} <b>Let's crush it today! Aaj dhamaal machate hain!</b> {E_FIRE}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Stats formatting
# ---------------------------------------------------------------------------

def format_stats(stats: dict) -> str:
    """Format ADM performance statistics."""
    name = stats.get("adm_name", "ADM")
    period = stats.get("period", "This Month")

    total_agents = stats.get("total_agents", 0)
    active_agents = stats.get("active_agents", 0)
    at_risk_agents = stats.get("at_risk_agents", 0)
    inactive_agents = stats.get("inactive_agents", 0)

    total_calls = stats.get("total_calls", 0)
    total_feedbacks = stats.get("total_feedbacks", 0)
    total_activations = stats.get("total_activations", 0)
    activation_rate = stats.get("activation_rate", 0)

    return (
        f"{header(f'Performance - {name}', E_CHART)}\n"
        f"<i>{period}</i>\n"
        f"{section_divider()}"
        f"{header('Agent Portfolio', E_PEOPLE)}\n\n"
        f"  Total: <b>{total_agents}</b>\n"
        f"  {E_GREEN_CIRCLE} Active: <b>{active_agents}</b>\n"
        f"  {E_YELLOW_CIRCLE} At Risk: <b>{at_risk_agents}</b>\n"
        f"  {E_RED_CIRCLE} Inactive: <b>{inactive_agents}</b>\n"
        f"{section_divider()}"
        f"{header('Activity Summary', E_FIRE)}\n\n"
        f"  {E_PHONE} Calls: <b>{total_calls}</b>\n"
        f"  {E_MEMO} Feedbacks: <b>{total_feedbacks}</b>\n"
        f"  {E_ROCKET} Activations: <b>{total_activations}</b>\n"
        f"  {E_TARGET} Activation Rate: <b>{activation_rate}%</b>\n"
        f"{section_divider()}"
        f"{E_MUSCLE} Keep pushing for excellence!"
    )


# ---------------------------------------------------------------------------
# Training formatting
# ---------------------------------------------------------------------------

def format_product_summary(product: dict) -> str:
    """Format AI-generated product summary."""
    name = product.get("name", "Product")
    category = product.get("category", "")
    features = product.get("key_features", [])
    usps = product.get("usps", [])
    target = product.get("target_audience", "")
    objections = product.get("common_objections", [])

    lines = [
        f"{header(name, E_SHIELD)}\n",
        f"{E_PIN} <i>Category: {category}</i>\n",
    ]

    # Key features
    lines.append(f"\n{header('Key Features', E_STAR)}\n")
    for feat in features:
        lines.append(f"  {E_CHECK} {feat}")

    # USPs
    lines.append(f"\n{header('USPs / Selling Points', E_DIAMOND)}\n")
    for usp in usps:
        lines.append(f"  {E_FIRE} {usp}")

    # Target audience
    lines.append(f"\n{header('Target Audience', E_TARGET)}\n")
    lines.append(f"  {target}")

    # Objection handling
    if objections:
        lines.append(f"\n{header('Common Objections & Responses', E_CHAT)}\n")
        for obj in objections:
            q = obj.get("objection", "")
            a = obj.get("response", "")
            lines.append(f"\n  {E_WARNING} <b>Objection:</b> {q}")
            lines.append(f"  {E_CHECK} <b>Response:</b> {a}")

    return "\n".join(lines)


def format_quiz_question(question: dict, q_num: int, total: int) -> str:
    """Format a quiz question."""
    text = question.get("question", "")
    options = question.get("options", [])

    lines = [
        f"{E_BRAIN} <b>Quiz Question {q_num}/{total}</b>\n",
        f"<i>{text}</i>\n",
    ]

    option_labels = ["A", "B", "C", "D"]
    for i, opt in enumerate(options):
        label = option_labels[i] if i < len(option_labels) else str(i + 1)
        lines.append(f"  <b>{label}.</b> {opt}")

    return "\n".join(lines)


def format_quiz_result(score: int, total: int) -> str:
    """Format quiz result."""
    pct = (score / total * 100) if total > 0 else 0

    if pct == 100:
        emoji = E_TROPHY
        msg = "Perfect Score! Excellent! / Shandar!"
    elif pct >= 70:
        emoji = E_MEDAL
        msg = "Great job! Well done! / Bahut achha!"
    elif pct >= 40:
        emoji = E_THUMBSUP
        msg = "Good try! Keep learning! / Aur mehnat karein!"
    else:
        emoji = E_BOOK
        msg = "Keep studying! Practice makes perfect! / Padhayi jaari rakhein!"

    return (
        f"{emoji} <b>Quiz Result</b>\n\n"
        f"Score: <b>{score}/{total}</b> ({pct:.0f}%)\n\n"
        f"{msg}\n\n"
        f"Use /train to try another module!"
    )


# ---------------------------------------------------------------------------
# Product Q&A formatting
# ---------------------------------------------------------------------------

def format_product_answer(answer: dict) -> str:
    """Format AI product Q&A response."""
    response_text = answer.get("answer", "I could not find an answer.")
    related = answer.get("related_products", [])

    lines = [
        f"{E_BRAIN} <b>AI Answer</b>\n",
        f"{response_text}",
    ]

    if related:
        lines.append(f"\n\n{header('Related Products', E_LINK)}\n")
        for prod in related:
            lines.append(f"  {E_SHIELD} {prod}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Error messages
# ---------------------------------------------------------------------------

def error_generic() -> str:
    return (
        f"{E_WARNING} <b>Oops! Something went wrong.</b>\n\n"
        f"Kuch gadbad ho gayi. Please try again.\n"
        f"Agar problem continue ho toh /help use karein."
    )


def error_not_registered() -> str:
    return (
        f"{E_WARNING} <b>Not Registered</b>\n\n"
        f"Aap abhi registered nahi hain.\n"
        f"Please use /start to register first."
    )


def error_api_down() -> str:
    return (
        f"{E_CROSS} <b>Server Unreachable</b>\n\n"
        f"Backend server se connect nahi ho pa raha.\n"
        f"Please try again in a few minutes.\n\n"
        f"<i>If the problem persists, contact IT support.</i>"
    )


def voice_note_received() -> str:
    return (
        f"{E_MIC} <b>Voice Note Received!</b>\n\n"
        f"Aapka voice note mil gaya hai.\n"
        f"We will process it shortly.\n\n"
        f"<i>Tip: You can also type your message for faster processing.</i>"
    )


# ---------------------------------------------------------------------------
# Cancel / timeout
# ---------------------------------------------------------------------------

def cancelled() -> str:
    return f"{E_CROSS} Operation cancelled. / Operation cancel kar diya gaya.\n\nUse /help to see available commands."


def session_timeout() -> str:
    return (
        f"{E_CLOCK} <b>Session Timed Out</b>\n\n"
        f"Aapka session expire ho gaya.\n"
        f"Please start again with the relevant command."
    )
