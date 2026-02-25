"""
domain/adm_intelligence.py — ADM support intelligence layer.

Ported from AARS modules/adm/service.py and tasks/adm_briefing.py.
Simplified for standalone use with plain dicts/lists (no SQLAlchemy, no async).

Provides:
1. ADM effectiveness classification (4 tiers)
2. Priority agent ranking algorithm
3. Morning briefing content generation
4. Recommendation engine (action per dormancy reason)
5. Empathy response suggestions for common agent complaints
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional

from domain.enums import AgentLifecycleState, DormancyReasonCategory
from domain.dormancy_taxonomy import get_reason_by_code, _CATEGORY_NAMES_HI

logger = logging.getLogger(__name__)

MAX_PRIORITY_AGENTS = 5


# ===========================================================================
# PART 1: ADM Effectiveness Classification (4 Tiers)
# ===========================================================================

@dataclass
class ADMEffectivenessResult:
    """Result of ADM effectiveness evaluation."""
    classification: str  # HIGH_PERFORMER | AVERAGE | STRUGGLING | UNRESPONSIVE
    reason: str
    activation_rate: float
    nudge_response_rate: float
    portfolio_size: int
    agents_by_state: dict[str, int] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)


def classify_adm_effectiveness(
    activation_rate: float,
    nudge_response_rate: float,
    portfolio_size: int = 0,
    agents_by_state: dict[str, int] | None = None,
) -> ADMEffectivenessResult:
    """Classify ADM performance into one of 4 tiers.

    Thresholds (from AARS spec section 2.9):
    - HIGH_PERFORMER: activation_rate > 10% AND nudge_response_rate > 70%
    - AVERAGE: activation_rate 3-10%
    - STRUGGLING: activation_rate < 3% AND nudge_response_rate > 30%
    - UNRESPONSIVE: nudge_response_rate < 20%

    Args:
        activation_rate: Fraction of agents who reached FIRST_SALE or beyond.
        nudge_response_rate: Fraction of system nudges the ADM acted on.
        portfolio_size: Total agents assigned to this ADM.
        agents_by_state: Dict mapping lifecycle state to agent count.

    Returns:
        ADMEffectivenessResult with classification, reason, and recommendations.
    """
    agents_by_state = agents_by_state or {}
    recommendations = []

    # Classify
    if nudge_response_rate < 0.2:
        classification = "UNRESPONSIVE"
        reason = "Nudge response rate below 20%"
        recommendations = [
            "ADM is not responding to system nudges — consider a direct manager conversation",
            "Check if ADM is receiving notifications properly",
            "Schedule a 1-on-1 to understand blockers",
            "Consider reassigning high-priority agents temporarily",
        ]
    elif activation_rate > 0.10 and nudge_response_rate > 0.7:
        classification = "HIGH_PERFORMER"
        reason = "Strong activation rate with excellent nudge responsiveness"
        recommendations = [
            "Recognize this ADM for excellent performance",
            "Consider them for mentoring struggling ADMs",
            "Share their best practices with the team",
        ]
    elif activation_rate >= 0.03:
        classification = "AVERAGE"
        reason = "Moderate activation rate — room for improvement"
        recommendations = [
            "Focus on converting at-risk agents before they go dormant",
            "Increase frequency of agent check-ins",
            "Review and learn from high-performer strategies",
        ]
    elif nudge_response_rate > 0.3:
        classification = "STRUGGLING"
        reason = "Low activation rate but responsive to nudges — needs support"
        recommendations = [
            "Provide coaching on effective agent conversations",
            "Pair with a high-performing ADM for mentoring",
            "Review approach with dormant agents — may need different strategy",
            "Consider focused training on reactivation techniques",
        ]
    else:
        classification = "AVERAGE"
        reason = "Below-average activation — focus on agent engagement"
        recommendations = [
            "Increase agent touchpoints",
            "Respond to system nudges more promptly",
            "Focus on understanding agent blockers",
        ]

    return ADMEffectivenessResult(
        classification=classification,
        reason=reason,
        activation_rate=round(activation_rate, 4),
        nudge_response_rate=round(nudge_response_rate, 4),
        portfolio_size=portfolio_size,
        agents_by_state=agents_by_state,
        recommendations=recommendations,
    )


def compute_activation_rate(agents: list[dict]) -> float:
    """Compute activation rate from a list of agent dicts.

    Activation = agents who reached FIRST_SALE, ACTIVE, or PRODUCTIVE
    divided by total agents.
    """
    if not agents:
        return 0.0
    activated_states = {
        AgentLifecycleState.FIRST_SALE,
        AgentLifecycleState.ACTIVE,
        AgentLifecycleState.PRODUCTIVE,
    }
    activated = sum(
        1 for a in agents
        if a.get("lifecycle_state") in activated_states
    )
    return activated / len(agents)


# ===========================================================================
# PART 2: Priority Agent Ranking Algorithm
# ===========================================================================

@dataclass
class PriorityAgent:
    """An agent flagged for priority attention by the ADM."""
    agent_id: int
    agent_name: str
    lifecycle_state: str
    priority_score: float
    one_line_context: str
    suggested_action: str
    urgency: str  # CRITICAL | HIGH | MEDIUM
    dormancy_reason: str | None = None


def rank_priority_agents(
    agents: list[dict],
    max_results: int = MAX_PRIORITY_AGENTS,
) -> list[PriorityAgent]:
    """Rank agents by priority for ADM attention.

    Priority scoring algorithm:
    - License expiring soon (< 45 days): +100 points
    - AT_RISK state: +80 points
    - Recently productive but now at risk: +70 points
    - DORMANT state: +60 points
    - High engagement score drop: +50 points
    - ONBOARDED with no contact (> 7 days): +40 points
    - No contact in 30+ days: +30 points

    Args:
        agents: List of agent dicts with keys: id, name, lifecycle_state,
                dormancy_reason, dormancy_duration_days, engagement_score,
                last_contact_date, date_of_joining, etc.
        max_results: Maximum number of priority agents to return.

    Returns:
        Sorted list of PriorityAgent objects (highest priority first).
    """
    scored: list[PriorityAgent] = []
    today = date.today()

    for agent in agents:
        score = 0.0
        context_parts = []
        action = "Check in with the agent"
        urgency = "MEDIUM"
        state = agent.get("lifecycle_state", "")

        # License expiry urgency
        license_expiry = agent.get("license_expiry_date")
        if license_expiry:
            if isinstance(license_expiry, str):
                try:
                    license_expiry = datetime.strptime(license_expiry, "%Y-%m-%d").date()
                except ValueError:
                    license_expiry = None
            if license_expiry:
                days_to_expiry = (license_expiry - today).days
                if 0 < days_to_expiry <= 45:
                    score += 100
                    context_parts.append(f"License expiring in {days_to_expiry} days")
                    action = "Help complete training hours for renewal"
                    urgency = "CRITICAL"
                elif days_to_expiry <= 0:
                    score += 90
                    context_parts.append("License EXPIRED")
                    action = "Urgent: help with license renewal"
                    urgency = "CRITICAL"

        # State-based scoring
        if state == AgentLifecycleState.AT_RISK:
            score += 80
            days_in_state = agent.get("days_in_state", 0)
            context_parts.append(f"At-risk for {days_in_state} days")
            action = "Call to understand what is happening and prevent dormancy"
            urgency = "HIGH"

        elif state == AgentLifecycleState.DORMANT:
            score += 60
            dormancy_days = agent.get("dormancy_duration_days", 0)
            context_parts.append(f"Dormant for {dormancy_days} days")
            reason = agent.get("dormancy_reason", "")
            if reason:
                reason_info = get_reason_by_code(reason)
                if reason_info:
                    action = reason_info.get("suggested_action_en", "Reach out to understand the situation")
                else:
                    action = "Reach out to understand what is happening"
            else:
                action = "Find out why they are inactive"
            urgency = "HIGH"

        elif state == AgentLifecycleState.ONBOARDED:
            doj = agent.get("date_of_joining")
            if doj:
                if isinstance(doj, str):
                    try:
                        doj = datetime.strptime(doj, "%Y-%m-%d").date()
                    except ValueError:
                        doj = None
                if doj:
                    days_since = (today - doj).days
                    if days_since > 7:
                        score += 40
                        context_parts.append(f"Onboarded {days_since} days ago, needs first contact")
                        action = "Make first contact — critical for retention"
                        urgency = "HIGH"

        # No recent contact penalty
        last_contact = agent.get("last_contact_date")
        if last_contact:
            if isinstance(last_contact, str):
                try:
                    last_contact = datetime.strptime(last_contact, "%Y-%m-%d").date()
                except ValueError:
                    last_contact = None
            if last_contact:
                days_since_contact = (today - last_contact).days
                if days_since_contact > 30:
                    score += 30
                    context_parts.append(f"No contact in {days_since_contact} days")

        # Low engagement penalty
        engagement = agent.get("engagement_score", 0.0)
        if engagement < 20 and state not in ("onboarded", "terminated", "lapsed"):
            score += 20
            context_parts.append(f"Very low engagement ({engagement:.0f}%)")

        if score > 0:
            scored.append(PriorityAgent(
                agent_id=agent.get("id", 0),
                agent_name=agent.get("name", "Unknown"),
                lifecycle_state=state,
                priority_score=score,
                one_line_context=" | ".join(context_parts) if context_parts else "Needs attention",
                suggested_action=action,
                urgency=urgency,
                dormancy_reason=agent.get("dormancy_reason"),
            ))

    # Sort by priority score (descending), then by urgency
    urgency_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2}
    scored.sort(key=lambda p: (-p.priority_score, urgency_order.get(p.urgency, 3)))

    return scored[:max_results]


# ===========================================================================
# PART 3: Morning Briefing Content Generation
# ===========================================================================

@dataclass
class MorningBriefing:
    """Content for an ADM's morning briefing."""
    date: date
    greeting: str
    snapshot: dict  # {active_count, at_risk_count, dormant_count, total}
    priority_agents: list[PriorityAgent]
    celebrations: list[dict]  # [{agent_name, achievement}]
    action_items: list[str]
    formatted_text: str  # Ready-to-send text (for Telegram/WhatsApp)
    formatted_text_hi: str  # Hindi version


def generate_morning_briefing(
    adm_name: str,
    agents: list[dict],
    recent_wins: list[dict] | None = None,
    briefing_date: date | None = None,
) -> MorningBriefing:
    """Generate a complete morning briefing for an ADM.

    Args:
        adm_name: The ADM's name for personalization.
        agents: List of agent dicts assigned to this ADM.
        recent_wins: Recent positive events [{agent_name, achievement}].
        briefing_date: Date for the briefing (defaults to today).

    Returns:
        MorningBriefing with all content populated.
    """
    briefing_date = briefing_date or date.today()
    recent_wins = recent_wins or []

    # Compute snapshot
    total = len(agents)
    active = sum(1 for a in agents if a.get("lifecycle_state") in (
        AgentLifecycleState.ACTIVE, AgentLifecycleState.PRODUCTIVE, AgentLifecycleState.FIRST_SALE
    ))
    at_risk = sum(1 for a in agents if a.get("lifecycle_state") == AgentLifecycleState.AT_RISK)
    dormant = sum(1 for a in agents if a.get("lifecycle_state") == AgentLifecycleState.DORMANT)
    onboarded = sum(1 for a in agents if a.get("lifecycle_state") == AgentLifecycleState.ONBOARDED)
    licensed = sum(1 for a in agents if a.get("lifecycle_state") == AgentLifecycleState.LICENSED)

    snapshot = {
        "total": total,
        "active_count": active,
        "at_risk_count": at_risk,
        "dormant_count": dormant,
        "onboarded_count": onboarded,
        "licensed_count": licensed,
    }

    # Priority agents
    priority_agents = rank_priority_agents(agents)

    # Action items
    action_items = []
    if at_risk > 0:
        action_items.append(f"Call {min(at_risk, 3)} at-risk agents today to prevent dormancy")
    if onboarded > 0:
        action_items.append(f"Welcome {onboarded} new agents — first contact is critical")
    if dormant > 0:
        action_items.append(f"Attempt re-engagement with {min(dormant, 2)} dormant agents")
    if not action_items:
        action_items.append("Keep up the regular check-ins with your active agents")

    for pa in priority_agents[:3]:
        action_items.append(f"{pa.agent_name}: {pa.suggested_action}")

    # Format English text
    greeting = f"Good morning, {adm_name}!"

    lines_en = [
        f"Good morning, {adm_name}!",
        f"Date: {briefing_date.strftime('%d %b %Y')}",
        "",
        "--- Your Portfolio ---",
        f"Total agents: {total}",
        f"Active/Productive: {active}",
        f"At-risk: {at_risk}",
        f"Dormant: {dormant}",
        f"New (onboarded): {onboarded}",
        "",
    ]

    if priority_agents:
        lines_en.append("--- Priority Agents Today ---")
        for i, pa in enumerate(priority_agents, 1):
            lines_en.append(f"{i}. {pa.agent_name} ({pa.urgency})")
            lines_en.append(f"   {pa.one_line_context}")
            lines_en.append(f"   Action: {pa.suggested_action}")
        lines_en.append("")

    if recent_wins:
        lines_en.append("--- Celebrations ---")
        for win in recent_wins[:3]:
            lines_en.append(f"  {win.get('agent_name', 'Agent')}: {win.get('achievement', '')}")
        lines_en.append("")

    lines_en.append("--- Today's Action Items ---")
    for item in action_items:
        lines_en.append(f"  - {item}")

    formatted_en = "\n".join(lines_en)

    # Format Hindi text
    lines_hi = [
        f"Suprabhat, {adm_name} ji!",
        f"Tarikh: {briefing_date.strftime('%d %b %Y')}",
        "",
        "--- Aapka Portfolio ---",
        f"Total agents: {total}",
        f"Active/Productive: {active}",
        f"At-risk: {at_risk}",
        f"Dormant: {dormant}",
        f"Naye (onboarded): {onboarded}",
        "",
    ]

    if priority_agents:
        lines_hi.append("--- Aaj ke Priority Agents ---")
        for i, pa in enumerate(priority_agents, 1):
            lines_hi.append(f"{i}. {pa.agent_name} ({pa.urgency})")
            lines_hi.append(f"   {pa.one_line_context}")
            lines_hi.append(f"   Action: {pa.suggested_action}")
        lines_hi.append("")

    if recent_wins:
        lines_hi.append("--- Badhai! ---")
        for win in recent_wins[:3]:
            lines_hi.append(f"  {win.get('agent_name', 'Agent')}: {win.get('achievement', '')}")
        lines_hi.append("")

    lines_hi.append("--- Aaj ke Kaam ---")
    for item in action_items:
        lines_hi.append(f"  - {item}")

    formatted_hi = "\n".join(lines_hi)

    return MorningBriefing(
        date=briefing_date,
        greeting=greeting,
        snapshot=snapshot,
        priority_agents=priority_agents,
        celebrations=recent_wins,
        action_items=action_items,
        formatted_text=formatted_en,
        formatted_text_hi=formatted_hi,
    )


# ===========================================================================
# PART 4: Recommendation Engine
# ===========================================================================

def get_recommendation_for_agent(
    lifecycle_state: str,
    dormancy_reason: str | None = None,
    days_in_state: int = 0,
    engagement_score: float = 0.0,
    last_contact_days_ago: int | None = None,
) -> dict:
    """Generate a recommendation for what action to take with an agent.

    Returns a dict with: action, reasoning, urgency, channel, talking_points.

    Args:
        lifecycle_state: Agent's current state.
        dormancy_reason: Specific dormancy reason code (optional).
        days_in_state: Number of days in the current state.
        engagement_score: Current engagement score (0-100).
        last_contact_days_ago: Days since last contact (None if never contacted).
    """
    result = {
        "action": "check_in",
        "reasoning": "",
        "urgency": "MEDIUM",
        "channel": "whatsapp",
        "talking_points": [],
        "talking_points_hi": [],
    }

    # DORMANT agents
    if lifecycle_state == AgentLifecycleState.DORMANT:
        if dormancy_reason:
            reason_info = get_reason_by_code(dormancy_reason)
            if reason_info:
                result["action"] = "personalized_outreach"
                result["reasoning"] = reason_info.get("description_en", "")
                result["urgency"] = "HIGH"
                result["channel"] = "call"
                result["talking_points"] = reason_info.get("adm_talking_points", [])
                result["suggested_action"] = reason_info.get("suggested_action_en", "")
                result["suggested_action_hi"] = reason_info.get("suggested_action_hi", "")
                return result

        # Unknown dormancy reason
        if last_contact_days_ago is None or last_contact_days_ago > 30:
            result["action"] = "discovery_call"
            result["reasoning"] = "Dormant with unknown reason — need to understand the situation"
            result["urgency"] = "HIGH"
            result["channel"] = "call"
            result["talking_points"] = [
                "Start with a warm, non-judgmental check-in",
                "Ask open-ended questions: 'How are things going?'",
                "Listen for clues about the real reason for inactivity",
                "Do not push for sales — focus on understanding",
            ]
            result["talking_points_hi"] = [
                "Warm check-in se shuru karein, judge nahi karein",
                "Open-ended sawaal poochein: 'Sab kaisa chal raha hai?'",
                "Real reason sunne ki koshish karein",
                "Sales ke liye push na karein — pehle samjhein",
            ]
        else:
            result["action"] = "follow_up"
            result["reasoning"] = "Recently contacted dormant agent — follow up on previous conversation"
            result["urgency"] = "MEDIUM"
            result["talking_points"] = [
                "Reference the previous conversation",
                "Ask if they had a chance to think about what was discussed",
                "Offer specific help based on what they shared last time",
            ]

    # AT_RISK agents
    elif lifecycle_state == AgentLifecycleState.AT_RISK:
        if days_in_state > 30:
            result["action"] = "in_person_visit"
            result["reasoning"] = f"At-risk for {days_in_state} days — digital outreach may not be enough"
            result["urgency"] = "HIGH"
            result["channel"] = "visit"
            result["talking_points"] = [
                "Consider an in-person visit — shows you care",
                "Bring something useful (product material, success stories)",
                "Ask about their challenges face-to-face",
                "Create a concrete plan together",
            ]
        else:
            result["action"] = "timely_call"
            result["reasoning"] = "Recently at-risk — a timely call can prevent dormancy"
            result["urgency"] = "HIGH"
            result["channel"] = "call"
            result["talking_points"] = [
                "Call quickly — timing matters",
                "Ask if everything is okay without being accusatory",
                "Offer specific help (training, joint visit, process support)",
                "Set up a follow-up within the week",
            ]

    # ONBOARDED agents
    elif lifecycle_state == AgentLifecycleState.ONBOARDED:
        if days_in_state > 14:
            result["action"] = "urgent_first_steps"
            result["reasoning"] = "Onboarded but no progress in 14+ days — needs help getting started"
            result["urgency"] = "HIGH"
            result["channel"] = "call"
            result["talking_points"] = [
                "Understand what is blocking their progress",
                "Help with exam preparation if not licensed yet",
                "Walk through the first steps of getting started",
                "Set specific milestones for the next 2 weeks",
            ]
        else:
            result["action"] = "welcome_and_orient"
            result["reasoning"] = "New agent — help them get licensed and started"
            result["urgency"] = "MEDIUM"
            result["channel"] = "call"
            result["talking_points"] = [
                "Welcome them warmly to the team",
                "Explain what their first 30 days should look like",
                "Help them understand the exam and licensing process",
                "Schedule regular weekly check-ins",
            ]

    # LICENSED agents
    elif lifecycle_state == AgentLifecycleState.LICENSED:
        result["action"] = "first_sale_coaching"
        result["reasoning"] = "Licensed but no sale yet — focus on getting the first sale"
        result["urgency"] = "MEDIUM"
        result["channel"] = "call"
        result["talking_points"] = [
            "Discuss their warm market (family, friends, neighbors)",
            "Role-play a sales conversation",
            "Offer to join them for their first customer meeting",
            "Share simple product comparison sheets they can use",
        ]

    # FIRST_SALE agents
    elif lifecycle_state == AgentLifecycleState.FIRST_SALE:
        result["action"] = "build_momentum"
        result["reasoning"] = "First sale done — celebrate and build on this momentum"
        result["urgency"] = "MEDIUM"
        result["channel"] = "whatsapp"
        result["talking_points"] = [
            "Congratulate them genuinely",
            "Ask how the sale went — what worked?",
            "Help them identify the next 3-5 prospects",
            "Discuss cross-selling opportunities",
        ]

    # ACTIVE/PRODUCTIVE agents
    elif lifecycle_state in (AgentLifecycleState.ACTIVE, AgentLifecycleState.PRODUCTIVE):
        result["action"] = "maintain_engagement"
        result["reasoning"] = "Performing well — keep regular engagement"
        result["urgency"] = "LOW"
        result["channel"] = "whatsapp"
        result["talking_points"] = [
            "Regular check-in — keep the relationship warm",
            "Share any new product updates or promotions",
            "Recognize their achievements",
            "Discuss their goals for the month",
        ]

    else:
        result["action"] = "monitor"
        result["reasoning"] = "Keep in touch and monitor progress"
        result["urgency"] = "LOW"

    return result


# ===========================================================================
# PART 5: Empathy Response Suggestions
# ===========================================================================

EMPATHY_RESPONSES: dict[str, dict] = {
    # Keyed by dormancy reason category or common complaint theme
    "commission_low": {
        "en": [
            "I understand your concern about commission. Let me show you how our top agents are earning well.",
            "Commission is important, and I want to help you maximize your earnings. Can we look at your product mix?",
            "Many agents felt the same way initially but found success with the right approach. Let me share some strategies.",
        ],
        "hi": [
            "Main samajhta hoon commission ki chinta. Chaliye dekhte hain hamare top agents kaise accha kamate hain.",
            "Commission zaroori hai, aur main chahta hoon aap zyada earn karein. Kya hum aapka product mix dekh sakte hain?",
            "Bahut agents ko pehle aisa laga, lekin sahi approach se unhone success payi. Kuch strategies share karta hoon.",
        ],
    },
    "no_support": {
        "en": [
            "I hear you, and I am sorry you have felt unsupported. That is going to change starting today.",
            "You are right to expect support from us. Let us create a plan so you feel backed up.",
            "I want to be available for you. Let us set up a regular time to connect every week.",
        ],
        "hi": [
            "Main sun raha hoon, aur mujhe sorry hai ki aapko support nahi mila. Aaj se badlav hoga.",
            "Aap sahi keh rahe hain ki support milna chahiye. Chaliye ek plan banate hain.",
            "Main aapke liye available hoon. Haftein mein ek fixed time set karte hain connect karne ke liye.",
        ],
    },
    "process_difficulty": {
        "en": [
            "The process can feel overwhelming at first. Let me walk you through it step by step.",
            "Many agents face this challenge initially. I will help you with your next proposal personally.",
            "We have simpler digital tools now. Let me show you how they work.",
        ],
        "hi": [
            "Process pehle mushkil lagta hai. Chaliye step by step dekhte hain.",
            "Bahut agents ko shuru mein yeh dikkat hoti hai. Main aapka agla proposal personally karwa doonga.",
            "Ab hamare paas simple digital tools hain. Main dikhata hoon kaise kaam karte hain.",
        ],
    },
    "health_issues": {
        "en": [
            "Your health comes first. Please take care of yourself and come back when you are ready.",
            "I hope you feel better soon. There is no pressure at all — we will be here when you are ready.",
            "Wishing you a speedy recovery. Let me know if there is anything I can do to help.",
        ],
        "hi": [
            "Aapki sehat sabse pehle hai. Dhyan rakhein aur jab taiyaar hon tab aayein.",
            "Jaldi theek hone ki dua hai. Koi pressure nahi hai — jab chahein tab wapas aayein.",
            "Jaldi recovery ki kaamna hai. Kuch bhi madad chahiye toh batayein.",
        ],
    },
    "lost_interest": {
        "en": [
            "I understand it can feel that way sometimes. What originally attracted you to insurance?",
            "Let me share some stories of agents who felt the same way but found new motivation.",
            "Maybe we can find a different approach that works better for you. What would make this exciting again?",
        ],
        "hi": [
            "Main samajhta hoon kabhi kabhi aisa lagta hai. Pehle insurance mein kya accha laga tha?",
            "Kuch agents ki kahani sunayein jo aisa feel karte the par phir naya motivation mila.",
            "Shayad koi alag approach better kaam kare. Kya cheez isko dobara exciting bana sakti hai?",
        ],
    },
    "competitor_concern": {
        "en": [
            "It is natural to compare. Let me show you the full picture of what we offer beyond just commission.",
            "Many companies offer higher rates but less support. Let us talk about total value.",
            "Our agents who stay long-term earn more because of renewals and persistency bonuses. Let me explain.",
        ],
        "hi": [
            "Compare karna natural hai. Commission ke alaawa hum aur kya offer karte hain woh dikhata hoon.",
            "Bahut companies zyada rate deti hain par support kam. Total value ki baat karte hain.",
            "Hamare long-term agents renewals aur persistency bonuses se zyada kamate hain. Samjhata hoon.",
        ],
    },
    "general_frustration": {
        "en": [
            "I hear your frustration, and it is valid. Let us work through this together.",
            "Thank you for sharing this with me. I want to help resolve this.",
            "You are not alone in this. Let me see what I can do to help.",
        ],
        "hi": [
            "Main aapki frustration samajh raha hoon, aur yeh valid hai. Saath mein solve karte hain.",
            "Share karne ke liye shukriya. Main isko resolve karne mein madad karna chahta hoon.",
            "Aap akele nahi hain. Dekhte hain main kya kar sakta hoon.",
        ],
    },
}


def get_empathy_response(
    complaint_theme: str,
    language: str = "hi",
    index: int = 0,
) -> str | None:
    """Get an empathy response suggestion for a complaint theme.

    Args:
        complaint_theme: Key from EMPATHY_RESPONSES (e.g., 'commission_low').
        language: 'hi' or 'en'.
        index: Which response variant to return (0, 1, or 2).

    Returns:
        An empathy response string, or None if theme not found.
    """
    theme_data = EMPATHY_RESPONSES.get(complaint_theme)
    if not theme_data:
        # Try general frustration as fallback
        theme_data = EMPATHY_RESPONSES.get("general_frustration")
    if not theme_data:
        return None

    responses = theme_data.get(language, theme_data.get("hi", []))
    if not responses:
        return None

    return responses[index % len(responses)]


def suggest_empathy_theme(dormancy_reason_code: str | None) -> str:
    """Map a dormancy reason code to an empathy response theme.

    Args:
        dormancy_reason_code: The DormancyReasonCode string value.

    Returns:
        The matching empathy theme key.
    """
    if not dormancy_reason_code:
        return "general_frustration"

    category = dormancy_reason_code.split(".")[0] if "." in dormancy_reason_code else ""

    mapping = {
        "economic.commission_too_low": "commission_low",
        "economic.competitor_better_commission": "competitor_concern",
        "economic.irregular_payments": "commission_low",
        "economic.insufficient_income": "commission_low",
        "engagement_gap.adm_never_contacted": "no_support",
        "engagement_gap.adm_no_followthrough": "no_support",
        "engagement_gap.feels_unsupported": "no_support",
        "engagement_gap.no_recognition": "no_support",
        "operational.proposal_process_complex": "process_difficulty",
        "operational.technology_barriers": "process_difficulty",
        "operational.claim_experience_bad": "general_frustration",
        "operational.slow_issuance": "general_frustration",
        "operational.kyc_issues": "process_difficulty",
        "personal.health_issues": "health_issues",
        "personal.lost_interest": "lost_interest",
        "personal.other_employment": "lost_interest",
    }

    return mapping.get(dormancy_reason_code, "general_frustration")


# ===========================================================================
# PART 6: System Recommendation (for Agent Detail view)
# ===========================================================================

def compute_system_recommendation(
    lifecycle_state: str,
    days_in_state: int = 0,
    last_positive_signal_days_ago: int | None = None,
    dormancy_reason: str | None = None,
) -> str:
    """Generate a one-line system recommendation for an agent.

    Used in the ADM agent detail view to give a quick recommendation.

    Returns:
        A concise recommendation string.
    """
    if lifecycle_state == AgentLifecycleState.DORMANT:
        if last_positive_signal_days_ago is not None and last_positive_signal_days_ago <= 7:
            return "Re-engagement window open — call now while interest is fresh"
        if dormancy_reason:
            reason_info = get_reason_by_code(dormancy_reason)
            if reason_info:
                return reason_info.get("suggested_action_en", "Try a personal call to understand what is happening")
        return "Dormant agent — try a personal call to understand what is happening"

    if lifecycle_state == AgentLifecycleState.AT_RISK:
        if days_in_state > 30:
            return "At-risk for over a month — consider an in-person visit"
        return "Recently at-risk — a timely call can prevent dormancy"

    if lifecycle_state == AgentLifecycleState.ONBOARDED:
        if days_in_state > 14:
            return "Onboarded but no progress — help with first steps"
        return "New agent — help them get licensed and started"

    if lifecycle_state == AgentLifecycleState.LICENSED:
        return "Licensed but no sale yet — focus on first-sale coaching"

    if lifecycle_state == AgentLifecycleState.FIRST_SALE:
        return "First sale done — celebrate and build momentum"

    if lifecycle_state in (AgentLifecycleState.ACTIVE, AgentLifecycleState.PRODUCTIVE):
        return "Performing well — continue regular engagement"

    return "Keep in touch and monitor progress"
