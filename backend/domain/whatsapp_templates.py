"""
domain/whatsapp_templates.py — Bilingual message templates (Hindi + English).

Ported from AARS modules/channel/whatsapp/templates.py and bot.py.
Simplified for standalone use — works for both WhatsApp and Telegram delivery.

All templates have Hindi (hi) and English (en) variants with {placeholder}
variable substitution. Templates cover the full agent engagement lifecycle:
welcome, follow-up, training, quiz, check-in, re-engagement, escalation.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


# ===========================================================================
# Template Definition
# ===========================================================================

@dataclass
class TemplateDefinition:
    """A single message template with language variants."""
    name: str
    category: str  # UTILITY | MARKETING | NOTIFICATION
    variants: dict[str, str]  # lang_code -> template body with {placeholders}
    buttons: list[str] = field(default_factory=list)
    description: str = ""


# Global template registry
TEMPLATES: dict[str, TemplateDefinition] = {}


def _register(t: TemplateDefinition) -> TemplateDefinition:
    """Register a template in the global registry."""
    TEMPLATES[t.name] = t
    return t


# ===========================================================================
# Template Definitions
# ===========================================================================

# --- 1. Welcome New Agent ---
_register(TemplateDefinition(
    name="welcome_new_agent",
    category="UTILITY",
    description="Sent when a new agent is onboarded",
    variants={
        "hi": (
            "{agent_name} ji, {company_name} mein aapka swagat hai!\n"
            "Aapke ADM {adm_name} ji hain — woh jald aapse milenge.\n\n"
            "Shuru karne ke liye, yeh 2 minute ka video dekhein."
        ),
        "en": (
            "Welcome {agent_name}! You are now part of {company_name}.\n"
            "Your ADM is {adm_name} — they will connect with you soon.\n\n"
            "Watch this 2-minute video to get started."
        ),
    },
    buttons=["Video dekhein", "ADM se baat karein"],
))

# --- 2. Training Nudge ---
_register(TemplateDefinition(
    name="training_nudge",
    category="UTILITY",
    description="Nudge to start a training module",
    variants={
        "hi": (
            "{agent_name} ji, aapke liye ek naya lesson taiyaar hai:\n\n"
            "{module_name}\n"
            "{duration} minute\n\n"
            "{module_description}"
        ),
        "en": (
            "{agent_name}, a new lesson is ready for you:\n\n"
            "{module_name}\n"
            "{duration} minutes\n\n"
            "{module_description}"
        ),
    },
    buttons=["Shuru karein", "Baad mein"],
))

# --- 3. Training Quiz ---
_register(TemplateDefinition(
    name="training_quiz",
    category="UTILITY",
    description="Quiz question during training",
    variants={
        "hi": (
            "Chaliye dekhte hain kitna yaad raha!\n\n"
            "Sawaal {question_number}/{total_questions}:\n"
            "{question_text}"
        ),
        "en": (
            "Let's see how much you remember!\n\n"
            "Question {question_number}/{total_questions}:\n"
            "{question_text}"
        ),
    },
    buttons=[],  # Dynamic per question
))

# --- 4. Training Result — High Score ---
_register(TemplateDefinition(
    name="training_result_high",
    category="UTILITY",
    description="Training result for high scorers (80%+)",
    variants={
        "hi": (
            "Shaandaar! Aapne {score}% score kiya!\n"
            "{module_name} complete ho gaya.\n\n"
            "Aap iss topic mein expert ban rahe hain!"
        ),
        "en": (
            "Excellent! You scored {score}%!\n"
            "{module_name} is now complete.\n\n"
            "You are becoming an expert on this topic!"
        ),
    },
))

# --- 5. Training Result — Medium Score ---
_register(TemplateDefinition(
    name="training_result_medium",
    category="UTILITY",
    description="Training result for medium scorers (50-79%)",
    variants={
        "hi": (
            "Accha prayas! {score}% score.\n"
            "{weak_topic} par ek aur baar dekhein toh aur accha hoga."
        ),
        "en": (
            "Good effort! {score}% score.\n"
            "Reviewing {weak_topic} once more will help."
        ),
    },
))

# --- 6. Training Result — Low Score ---
_register(TemplateDefinition(
    name="training_result_low",
    category="UTILITY",
    description="Training result for low scorers (below 50%)",
    variants={
        "hi": (
            "Koi baat nahi, {score}% score aaya.\n"
            "Chaliye {weak_topic} phir se dekhte hain — yeh bahut zaroori topic hai."
        ),
        "en": (
            "No worries, you scored {score}%.\n"
            "Let's review {weak_topic} again — it's an important topic."
        ),
    },
))

# --- 7. Gentle Check-in ---
_register(TemplateDefinition(
    name="gentle_checkin",
    category="UTILITY",
    description="Friendly check-in for agents who have been quiet",
    variants={
        "hi": (
            "{agent_name} ji, kaise hain aap?\n\n"
            "{contextual_message}\n\n"
            "Kya koi cheez hai jismein hum madad kar sakein?"
        ),
        "en": (
            "Hi {agent_name}, how are you?\n\n"
            "{contextual_message}\n\n"
            "Is there anything we can help with?"
        ),
    },
    buttons=["Training chahiye", "ADM se baat karni hai", "Sab theek hai"],
))

# --- 8. Sale Congratulation ---
_register(TemplateDefinition(
    name="sale_congratulation",
    category="UTILITY",
    description="Celebrate when an agent makes a sale",
    variants={
        "hi": (
            "Badhai ho {agent_name} ji!\n\n"
            "Aapki {product_name} policy issue ho gayi!\n"
            "Commission: Rs.{estimated_commission} (estimate)\n\n"
            "Aage aur bhi sales aayengi!"
        ),
        "en": (
            "Congratulations {agent_name}!\n\n"
            "Your {product_name} policy has been issued!\n"
            "Commission: Rs.{estimated_commission} (estimate)\n\n"
            "More sales coming your way!"
        ),
    },
))

# --- 9. License Expiry Reminder ---
_register(TemplateDefinition(
    name="license_expiry_reminder",
    category="UTILITY",
    description="Reminder about upcoming license expiry",
    variants={
        "hi": (
            "{agent_name} ji, aapka IRDAI license {expiry_date} ko expire ho raha hai.\n\n"
            "Renewal ke liye {remaining_hours} ghante training baaki hai.\n"
            "Abhi shuru karein — sab WhatsApp par hi ho jaayega."
        ),
        "en": (
            "{agent_name}, your IRDAI license expires on {expiry_date}.\n\n"
            "{remaining_hours} hours of training remaining for renewal.\n"
            "Start now — everything can be done right here on WhatsApp."
        ),
    },
    buttons=["Training shuru karein", "Details chahiye"],
))

# --- 10. ADM Personalized Message ---
_register(TemplateDefinition(
    name="adm_personalized",
    category="UTILITY",
    description="Personalized message from ADM to agent",
    variants={
        "hi": (
            "{agent_name} ji, main {adm_name}.\n\n"
            "{personalized_message}\n\n"
            "Koi sawaal ho toh bataiye."
        ),
        "en": (
            "{agent_name}, this is {adm_name}.\n\n"
            "{personalized_message}\n\n"
            "Let me know if you have any questions."
        ),
    },
))

# --- 11. Re-engagement Follow-up ---
_register(TemplateDefinition(
    name="reengagement_followup",
    category="UTILITY",
    description="Follow-up message for dormant agent re-engagement",
    variants={
        "hi": (
            "{agent_name} ji, bas ek aur baar check kar rahe the.\n\n"
            "Hamare paas naye training modules aur support available hai.\n"
            "Kabhi bhi reply karein — hum yahan hain aapki madad ke liye."
        ),
        "en": (
            "{agent_name}, just checking in once more.\n\n"
            "We have new training materials and support available for you.\n"
            "Reply anytime — we are here to help."
        ),
    },
    buttons=["Training dekhein", "ADM se milein", "Abhi nahi"],
))

# --- 12. Commission Explainer ---
_register(TemplateDefinition(
    name="commission_explainer",
    category="UTILITY",
    description="Commission structure explanation for concerned agents",
    variants={
        "hi": (
            "{agent_name} ji, hum samajhte hain ki commission zaroori hai.\n\n"
            "Yahan dekhein hamare top agents kaise 2-3x zyada kamate hain:\n"
            "- Term Life: {term_commission}% pehle saal\n"
            "- Health: {health_commission}% pehle saal\n"
            "- ULIP: {ulip_commission}% pehle saal\n\n"
            "Renewals se income badhta jaata hai!"
        ),
        "en": (
            "{agent_name}, we understand commission matters.\n\n"
            "See how our top agents earn 2-3x more:\n"
            "- Term Life: {term_commission}% first year\n"
            "- Health: {health_commission}% first year\n"
            "- ULIP: {ulip_commission}% first year\n\n"
            "Renewal income grows every year!"
        ),
    },
    buttons=["Aur jaanein", "ADM se baat karein"],
))

# --- 13. ADM Nudge (for ADM, not agent) ---
_register(TemplateDefinition(
    name="adm_nudge",
    category="NOTIFICATION",
    description="System nudge sent to ADM about an agent needing attention",
    variants={
        "hi": (
            "Alert: {agent_name} ko aapki zaroorat hai.\n\n"
            "Status: {lifecycle_state}\n"
            "Wajah: {reason}\n\n"
            "Suggested action: {suggested_action}\n\n"
            "Kripya aaj contact karein."
        ),
        "en": (
            "Alert: {agent_name} needs your attention.\n\n"
            "Status: {lifecycle_state}\n"
            "Reason: {reason}\n\n"
            "Suggested action: {suggested_action}\n\n"
            "Please contact them today."
        ),
    },
    buttons=["Call kiya", "Visit kiya", "Baad mein karunga"],
))

# --- 14. Morning Briefing ---
_register(TemplateDefinition(
    name="morning_briefing",
    category="NOTIFICATION",
    description="Daily morning briefing for ADMs",
    variants={
        "hi": (
            "Suprabhat {adm_name} ji!\n"
            "Tarikh: {date}\n\n"
            "Aapka Portfolio:\n"
            "Active: {active_count} | At-risk: {at_risk_count} | Dormant: {dormant_count}\n\n"
            "{priority_section}\n\n"
            "{action_items}"
        ),
        "en": (
            "Good morning {adm_name}!\n"
            "Date: {date}\n\n"
            "Your Portfolio:\n"
            "Active: {active_count} | At-risk: {at_risk_count} | Dormant: {dormant_count}\n\n"
            "{priority_section}\n\n"
            "{action_items}"
        ),
    },
))

# --- 15. Escalation Notice ---
_register(TemplateDefinition(
    name="escalation_notice",
    category="NOTIFICATION",
    description="Escalation alert sent to regional manager or higher",
    variants={
        "hi": (
            "ESCALATION: {agent_name} ka case escalate ho raha hai.\n\n"
            "ADM: {adm_name}\n"
            "Status: {lifecycle_state} ({days_in_state} din se)\n"
            "Wajah: {reason}\n\n"
            "Previous actions:\n{previous_actions}\n\n"
            "Immediate attention required."
        ),
        "en": (
            "ESCALATION: {agent_name}'s case has been escalated.\n\n"
            "ADM: {adm_name}\n"
            "Status: {lifecycle_state} ({days_in_state} days)\n"
            "Reason: {reason}\n\n"
            "Previous actions:\n{previous_actions}\n\n"
            "Immediate attention required."
        ),
    },
))

# --- 16. First Sale Celebration ---
_register(TemplateDefinition(
    name="first_sale_celebration",
    category="UTILITY",
    description="Special celebration for an agent's very first sale",
    variants={
        "hi": (
            "BADHAI HO {agent_name} ji!\n\n"
            "Aapne apni PEHLI policy bech di!\n"
            "Yeh bahut bada kadam hai — aap ab officially ek insurance professional hain.\n\n"
            "Aapke ADM {adm_name} ji bhi bahut khush hain.\n\n"
            "Tips for next sale:\n"
            "1. Apne family aur friends se baat karein\n"
            "2. First customer se referral maangein\n"
            "3. Agle hafte ka target set karein"
        ),
        "en": (
            "CONGRATULATIONS {agent_name}!\n\n"
            "You made your FIRST policy sale!\n"
            "This is a huge milestone — you are now officially an insurance professional.\n\n"
            "Your ADM {adm_name} is very proud.\n\n"
            "Tips for your next sale:\n"
            "1. Talk to your family and friends\n"
            "2. Ask your first customer for referrals\n"
            "3. Set a target for next week"
        ),
    },
))

# --- 17. Product Interest Query ---
_register(TemplateDefinition(
    name="product_interest_query",
    category="UTILITY",
    description="Ask agent which product they want to learn about",
    variants={
        "hi": (
            "Namaste {agent_name} ji!\n\n"
            "Hum aapko products ke baare mein sikhana chahte hain.\n"
            "Konsa product aapko sabse zyada interest karta hai?\n\n"
            "Reply karein:\n"
            "1) Term Life Insurance\n"
            "2) Endowment Plan\n"
            "3) ULIP\n"
            "4) Health Insurance"
        ),
        "en": (
            "Hello {agent_name}!\n\n"
            "We want to help you learn about our products.\n"
            "Which product interests you the most?\n\n"
            "Reply with:\n"
            "1) Term Life Insurance\n"
            "2) Endowment Plan\n"
            "3) ULIP\n"
            "4) Health Insurance"
        ),
    },
))

# --- 18. Success Stories ---
_register(TemplateDefinition(
    name="success_stories",
    category="MARKETING",
    description="Share success stories of other agents",
    variants={
        "hi": (
            "{agent_name} ji, ek inspiring kahani suniye:\n\n"
            "{success_story}\n\n"
            "Aap bhi kar sakte hain! Kya aap shuru karne ke liye taiyaar hain?"
        ),
        "en": (
            "{agent_name}, here is an inspiring story:\n\n"
            "{success_story}\n\n"
            "You can do it too! Are you ready to get started?"
        ),
    },
    buttons=["Haan, shuru karte hain!", "Aur bataiye"],
))

# --- 19. Issue Acknowledgment ---
_register(TemplateDefinition(
    name="issue_acknowledgment",
    category="UTILITY",
    description="Acknowledge agent's reported issue/difficulty",
    variants={
        "hi": (
            "{agent_name} ji, hum samajhte hain ki aapko {issue_description} mein dikkat ho rahi hai.\n\n"
            "Hum iss par kaam kar rahe hain aur jald solution denge.\n"
            "Tab tak, kya koi aur cheez hai jismein madad chahiye?"
        ),
        "en": (
            "{agent_name}, we understand you are facing difficulties with {issue_description}.\n\n"
            "We are working on this and will have a solution soon.\n"
            "In the meantime, is there anything else we can help with?"
        ),
    },
))


# ===========================================================================
# Template Rendering
# ===========================================================================

def render_template(
    template_name: str,
    language: str = "hi",
    params: dict | None = None,
) -> str | None:
    """Render a template with given parameters.

    Args:
        template_name: Name of the template to render.
        language: Language code ('hi' for Hindi, 'en' for English).
        params: Dict of placeholder values to substitute.

    Returns:
        Rendered message string, or None if template not found.
        Unknown placeholders are left as-is.
    """
    template = TEMPLATES.get(template_name)
    if not template:
        return None

    body = template.variants.get(language)
    if body is None:
        # Fall back to Hindi if requested language unavailable
        body = template.variants.get("hi")
    if body is None:
        return None

    if params:
        for key, value in params.items():
            body = body.replace(f"{{{key}}}", str(value))

    return body


def render_template_safe(
    template_name: str,
    language: str = "hi",
    params: dict | None = None,
    default_value: str = "",
) -> str:
    """Render a template, replacing any unfilled placeholders with a default.

    Unlike render_template(), this never returns None and cleans up
    leftover {placeholder} markers.

    Args:
        template_name: Name of the template.
        language: Language code.
        params: Placeholder values.
        default_value: What to replace unfilled placeholders with.

    Returns:
        Rendered string (never None).
    """
    result = render_template(template_name, language, params)
    if result is None:
        return f"[Template '{template_name}' not found]"

    # Replace any remaining {placeholders} with default
    result = re.sub(r"\{(\w+)\}", default_value or "___", result)
    return result


def get_template_buttons(template_name: str) -> list[str]:
    """Return the default button labels for a template."""
    template = TEMPLATES.get(template_name)
    if template:
        return list(template.buttons)
    return []


def get_training_result_template(score: float) -> str:
    """Select the appropriate training result template based on score."""
    if score >= 80:
        return "training_result_high"
    elif score >= 50:
        return "training_result_medium"
    else:
        return "training_result_low"


def list_templates() -> list[dict]:
    """Return metadata about all registered templates.

    Useful for admin dashboards and template management.
    """
    return [
        {
            "name": t.name,
            "category": t.category,
            "description": t.description,
            "languages": list(t.variants.keys()),
            "has_buttons": len(t.buttons) > 0,
            "button_labels": t.buttons,
        }
        for t in TEMPLATES.values()
    ]


# ===========================================================================
# Intent Classification (from bot.py — simplified for multi-channel use)
# ===========================================================================

class Intent:
    """Detected intents from incoming agent messages."""
    STOP = "stop"
    TRAINING_REQUEST = "training_request"
    ADM_REQUEST = "adm_request"
    PRODUCT_QUESTION = "product_question"
    COMMISSION_QUESTION = "commission_question"
    COMPLAINT = "complaint"
    GREETING = "greeting"
    QUIZ_ANSWER = "quiz_answer"
    POSITIVE_CONFIRMATION = "positive_confirmation"
    NEGATIVE_CONFIRMATION = "negative_confirmation"
    UNKNOWN = "unknown"


# Intent detection patterns (Hindi + English)
_INTENT_PATTERNS = {
    Intent.STOP: re.compile(
        r"\b(stop|band|rok|ruko|unsubscribe|opt.?out|nahi\s+chahiye|mat\s+bhejo)\b",
        re.IGNORECASE,
    ),
    Intent.TRAINING_REQUEST: re.compile(
        r"\b(training|lesson|sikho|sikhna|course|module|learn|padhai)\b",
        re.IGNORECASE,
    ),
    Intent.ADM_REQUEST: re.compile(
        r"\b(adm|manager|sir|madam|baat\s+karni|call\s+kar|milna)\b",
        re.IGNORECASE,
    ),
    Intent.PRODUCT_QUESTION: re.compile(
        r"\b(product|policy|plan|term|endowment|ulip|health|pension|bima|beema)\b",
        re.IGNORECASE,
    ),
    Intent.COMMISSION_QUESTION: re.compile(
        r"\b(commission|payment|paise|paisa|income|earning|kamana|kamai)\b",
        re.IGNORECASE,
    ),
    Intent.COMPLAINT: re.compile(
        r"\b(complaint|problem|issue|mushkil|dikkat|pareshani|galat|wrong)\b",
        re.IGNORECASE,
    ),
    Intent.GREETING: re.compile(
        r"\b(hi|hello|hey|namaste|namaskar|good\s+morning|good\s+evening)\b",
        re.IGNORECASE,
    ),
    Intent.POSITIVE_CONFIRMATION: re.compile(
        r"\b(yes|haan|ha|theek|okay|ok|sure|done|kar\s+diya|ho\s+gaya)\b",
        re.IGNORECASE,
    ),
    Intent.NEGATIVE_CONFIRMATION: re.compile(
        r"\b(no|nahi|naa|later|baad\s+mein|abhi\s+nahi|cancel)\b",
        re.IGNORECASE,
    ),
}


def classify_intent(text: str) -> str:
    """Classify the intent of an incoming text message.

    Checks patterns in priority order (STOP highest).
    Works for both WhatsApp and Telegram messages.

    Args:
        text: The message text to classify.

    Returns:
        An Intent constant string.
    """
    text = (text or "").strip()
    if not text:
        return Intent.UNKNOWN

    # Priority order — STOP first
    priority_order = [
        Intent.STOP,
        Intent.COMMISSION_QUESTION,
        Intent.COMPLAINT,
        Intent.PRODUCT_QUESTION,
        Intent.TRAINING_REQUEST,
        Intent.ADM_REQUEST,
        Intent.POSITIVE_CONFIRMATION,
        Intent.NEGATIVE_CONFIRMATION,
        Intent.GREETING,
    ]

    for intent_key in priority_order:
        pattern = _INTENT_PATTERNS.get(intent_key)
        if pattern and pattern.search(text):
            return intent_key

    return Intent.UNKNOWN


def get_bot_response(
    text: str,
    agent_name: str = "",
    adm_name: str = "",
    language: str = "hi",
) -> dict:
    """Get a bot response for an incoming message.

    Simplified from AARS bot.py for multi-channel use. Returns a dict
    with: text, buttons, escalate_to_adm, intent.

    Args:
        text: Incoming message text.
        agent_name: Agent's name for personalization.
        adm_name: ADM's name for referrals.
        language: Preferred language for response.

    Returns:
        Dict with response details.
    """
    intent = classify_intent(text)

    if intent == Intent.STOP:
        return {
            "intent": intent,
            "text": (
                f"{agent_name} ji, aapki request samajh gayi. "
                "Ab hum aapko message nahi karenge. "
                "Agar future mein wapas aana chahein, toh 'START' type karein."
            ) if language == "hi" else (
                f"{agent_name}, we understand your request. "
                "We will stop sending you messages. "
                "If you want to come back in the future, type 'START'."
            ),
            "buttons": [],
            "escalate_to_adm": False,
            "emit_consent_revoked": True,
        }

    if intent == Intent.TRAINING_REQUEST:
        return {
            "intent": intent,
            "text": (
                f"{agent_name} ji, aapke liye training modules available hain!"
            ) if language == "hi" else (
                f"{agent_name}, training modules are available for you!"
            ),
            "buttons": ["Training shuru karein", "Modules dekhein"],
            "escalate_to_adm": False,
        }

    if intent == Intent.ADM_REQUEST:
        return {
            "intent": intent,
            "text": (
                f"Main {adm_name} ji ko abhi inform karti hoon. Woh jald aapse connect karenge."
            ) if language == "hi" else (
                f"I will inform {adm_name} right away. They will connect with you soon."
            ),
            "buttons": [],
            "escalate_to_adm": True,
            "escalation_reason": f"Agent {agent_name} requested ADM contact",
        }

    if intent == Intent.PRODUCT_QUESTION:
        return {
            "intent": intent,
            "text": (
                f"{agent_name} ji, product ke baare mein accha sawaal hai. "
                "Aapke liye relevant training module suggest karti hoon."
            ) if language == "hi" else (
                f"{agent_name}, good question about the product. "
                "Let me suggest a relevant training module for you."
            ),
            "buttons": ["Training dekhein", "ADM se poochein"],
            "escalate_to_adm": False,
        }

    if intent == Intent.COMMISSION_QUESTION:
        return {
            "intent": intent,
            "text": (
                f"{agent_name} ji, commission se related jaankari ke liye "
                f"{adm_name} ji se baat karna best hoga."
            ) if language == "hi" else (
                f"{agent_name}, for commission-related information, "
                f"it would be best to speak with {adm_name}."
            ),
            "buttons": [],
            "escalate_to_adm": True,
            "escalation_reason": f"Agent {agent_name} has commission questions",
        }

    if intent == Intent.COMPLAINT:
        return {
            "intent": intent,
            "text": (
                f"{agent_name} ji, aapki baat samajh gayi. "
                f"Main {adm_name} ji ko turant bata deti hoon."
            ) if language == "hi" else (
                f"{agent_name}, I understand your concern. "
                f"I will inform {adm_name} immediately."
            ),
            "buttons": [],
            "escalate_to_adm": True,
            "escalation_reason": f"Agent {agent_name} raised a complaint: {text}",
        }

    if intent == Intent.GREETING:
        return {
            "intent": intent,
            "text": (
                f"Namaste {agent_name} ji! Kaise hain aap? Kismein madad kar sakti hoon?"
            ) if language == "hi" else (
                f"Hello {agent_name}! How are you? How can I help?"
            ),
            "buttons": ["Training chahiye", "ADM se baat karein", "Sab theek hai"],
            "escalate_to_adm": False,
        }

    # Unknown / free text
    return {
        "intent": intent,
        "text": (
            f"{agent_name} ji, main insurance se related sawaalon mein madad kar sakti hoon. "
            "Aap kya jaanna chahenge?"
        ) if language == "hi" else (
            f"{agent_name}, I can help with insurance-related questions. "
            "What would you like to know?"
        ),
        "buttons": ["Training chahiye", "ADM se baat karein"],
        "escalate_to_adm": False,
    }
