"""
domain/lifecycle.py — Agent lifecycle finite state machine.

Ported from AARS modules/agent/lifecycle.py. Simplified for standalone use.

The lifecycle FSM determines how agents transition between states based on
signals (events). It is the heart of the reactivation logic.

State Diagram:
    ONBOARDED --> LICENSED (license activated)
    LICENSED --> FIRST_SALE (first policy sold)
    FIRST_SALE --> ACTIVE (2+ policies)
    ACTIVE --> PRODUCTIVE (sustained high performance)
    ACTIVE/PRODUCTIVE --> AT_RISK (engagement drop)
    AT_RISK --> DORMANT (no activity for extended period)
    AT_RISK --> ACTIVE (positive re-engagement)
    DORMANT --> LICENSED (re-engagement without sale)
    DORMANT --> ACTIVE (policy sold while dormant)
    ANY --> LAPSED (license expired)
    LAPSED --> LICENSED (license renewed)
    TERMINATED --> (no transitions out — terminal)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from domain.enums import AgentLifecycleState, SignalType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Positive Signal Classification
# ---------------------------------------------------------------------------

ALWAYS_POSITIVE_SIGNALS: set[str] = {
    SignalType.POLICY_SOLD,
    SignalType.WHATSAPP_AGENT_REPLIED,
    SignalType.TRAINING_COMPLETED,
    SignalType.ADM_AGENT_VISIT_LOGGED,
}


def is_positive_signal(signal_type: str, payload: dict | None = None) -> bool:
    """Evaluate whether a specific signal instance is a positive engagement signal.

    Some signals are always positive (e.g., policy sold). Others depend on
    their payload (e.g., a voice call is positive only if answered).

    Args:
        signal_type: The type of signal received.
        payload: Optional dict with signal-specific data.

    Returns:
        True if this signal indicates positive agent engagement.
    """
    if signal_type in ALWAYS_POSITIVE_SIGNALS:
        return True

    payload = payload or {}

    if signal_type == SignalType.VOICE_CALL_OUTCOME:
        return payload.get("outcome") in ("answered", "completed")

    if signal_type == SignalType.WHATSAPP_TRAINING_INTERACTION:
        completion = payload.get("completion_percentage", 0) or 0
        return (
            completion > 50
            or payload.get("interaction_type") == "QUIZ_COMPLETED"
        )

    if signal_type == SignalType.ADM_AGENT_CALL_LOGGED:
        return payload.get("outcome") in ("CONNECTED", "DETAILED_DISCUSSION")

    return False


# ---------------------------------------------------------------------------
# Agent Context (lightweight — works without ORM dependency)
# ---------------------------------------------------------------------------

@dataclass
class AgentContext:
    """Minimal agent data needed for lifecycle transitions.

    This decouples the FSM from the ORM model, so it can be used from
    both the web service layer and the Telegram bot.
    """
    lifecycle_state: str = AgentLifecycleState.ONBOARDED
    total_policies_sold: int = 0
    engagement_score: float = 0.0
    last_positive_signal_at: Optional[datetime] = None
    days_in_state: int = 0


# ---------------------------------------------------------------------------
# State-Specific Transition Handlers
# ---------------------------------------------------------------------------

def _check_onboarded(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """Transitions from ONBOARDED."""
    if signal_type == SignalType.LICENSE_STATUS_CHANGED:
        if payload.get("new_status") == "ACTIVE":
            return AgentLifecycleState.LICENSED
    # Also allow direct progression if they sell a policy
    if signal_type == SignalType.POLICY_SOLD:
        return AgentLifecycleState.FIRST_SALE
    return None


def _check_licensed(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """Transitions from LICENSED."""
    if signal_type == SignalType.POLICY_SOLD:
        return AgentLifecycleState.FIRST_SALE
    return None


def _check_first_sale(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """Transitions from FIRST_SALE."""
    if signal_type == SignalType.POLICY_SOLD:
        # 2+ total policies (including the one being signaled) -> ACTIVE
        if (agent.total_policies_sold or 0) + 1 >= 2:
            return AgentLifecycleState.ACTIVE
    return None


def _check_active(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """Transitions from ACTIVE.

    ACTIVE -> PRODUCTIVE requires sustained performance, typically evaluated
    by a periodic batch process rather than a single signal.
    ACTIVE -> AT_RISK is also evaluated periodically based on engagement score.
    """
    return None


def _check_productive(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """Transitions from PRODUCTIVE.

    PRODUCTIVE -> AT_RISK is evaluated by periodic batch process.
    """
    return None


def _check_at_risk(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """Transitions from AT_RISK."""
    # A sale brings them back to ACTIVE immediately
    if signal_type == SignalType.POLICY_SOLD:
        return AgentLifecycleState.ACTIVE

    # Strong positive re-engagement with decent engagement score
    if is_positive_signal(signal_type, payload):
        if (agent.engagement_score or 0) > 60:
            return AgentLifecycleState.ACTIVE
    return None


def _check_dormant(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """Transitions from DORMANT."""
    # A sale brings them back to ACTIVE
    if signal_type == SignalType.POLICY_SOLD:
        return AgentLifecycleState.ACTIVE

    # Positive signal without sale -> back to LICENSED (re-engagement started)
    if is_positive_signal(signal_type, payload):
        return AgentLifecycleState.LICENSED
    return None


def _check_lapsed(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """Transitions from LAPSED (license expired)."""
    if signal_type == SignalType.LICENSE_STATUS_CHANGED:
        if payload.get("new_status") == "ACTIVE":
            return AgentLifecycleState.LICENSED
    return None


def _check_terminated(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """TERMINATED is a final state. No automatic transitions out."""
    return None


def _check_global(signal_type: str, payload: dict, agent: AgentContext) -> str | None:
    """Global transitions that apply from ANY state (checked first)."""
    if signal_type == SignalType.LICENSE_STATUS_CHANGED:
        if payload.get("new_status") == "EXPIRED":
            return AgentLifecycleState.LAPSED
    return None


# Handler dispatch table
_STATE_HANDLERS: dict[str, callable] = {
    AgentLifecycleState.ONBOARDED: _check_onboarded,
    AgentLifecycleState.LICENSED: _check_licensed,
    AgentLifecycleState.FIRST_SALE: _check_first_sale,
    AgentLifecycleState.ACTIVE: _check_active,
    AgentLifecycleState.PRODUCTIVE: _check_productive,
    AgentLifecycleState.AT_RISK: _check_at_risk,
    AgentLifecycleState.DORMANT: _check_dormant,
    AgentLifecycleState.LAPSED: _check_lapsed,
    AgentLifecycleState.TERMINATED: _check_terminated,
}


# ---------------------------------------------------------------------------
# Main FSM Function
# ---------------------------------------------------------------------------

def compute_transition(
    current_state: str,
    signal_type: str,
    payload: dict | None = None,
    agent: AgentContext | None = None,
) -> str | None:
    """Determine if a signal triggers a lifecycle state transition.

    This is the primary entry point for the lifecycle FSM. Given an agent's
    current state and a signal (event), it returns the new state the agent
    should transition to, or None if no transition should occur.

    Args:
        current_state: The agent's current lifecycle state.
        signal_type: The type of signal/event received.
        payload: Signal-specific data dict.
        agent: Agent context for data-dependent transitions.

    Returns:
        The new lifecycle state string, or None if no transition.
    """
    payload = payload or {}
    agent = agent or AgentContext()

    # Check global transitions first (license expiry overrides everything)
    new_state = _check_global(signal_type, payload, agent)
    if new_state and new_state != current_state:
        return new_state

    # Check state-specific handler
    handler = _STATE_HANDLERS.get(current_state)
    if handler:
        new_state = handler(signal_type, payload, agent)
        if new_state and new_state != current_state:
            return new_state

    return None


# ---------------------------------------------------------------------------
# Periodic Evaluation Helpers
# ---------------------------------------------------------------------------

def evaluate_risk_status(
    current_state: str,
    days_since_last_activity: int,
    engagement_score: float,
    at_risk_threshold_days: int = 30,
    dormant_threshold_days: int = 90,
    engagement_at_risk_threshold: float = 40.0,
) -> str | None:
    """Evaluate whether an agent should be moved to AT_RISK or DORMANT.

    Called by periodic batch processes (not by individual signals).
    Returns new state or None if no change needed.

    Args:
        current_state: Agent's current lifecycle state.
        days_since_last_activity: Days since last positive signal.
        engagement_score: Current engagement score (0-100).
        at_risk_threshold_days: Days of inactivity before AT_RISK.
        dormant_threshold_days: Days of inactivity before DORMANT.
        engagement_at_risk_threshold: Score below which agent is AT_RISK.

    Returns:
        New lifecycle state or None.
    """
    # Only evaluate active/productive/at_risk agents
    active_states = {
        AgentLifecycleState.ACTIVE,
        AgentLifecycleState.PRODUCTIVE,
        AgentLifecycleState.FIRST_SALE,
        AgentLifecycleState.LICENSED,
    }

    if current_state in active_states:
        if days_since_last_activity >= dormant_threshold_days:
            return AgentLifecycleState.DORMANT
        if (
            days_since_last_activity >= at_risk_threshold_days
            or engagement_score < engagement_at_risk_threshold
        ):
            return AgentLifecycleState.AT_RISK

    if current_state == AgentLifecycleState.AT_RISK:
        if days_since_last_activity >= dormant_threshold_days:
            return AgentLifecycleState.DORMANT

    return None


def get_lifecycle_display_info(state: str) -> dict:
    """Return display metadata for a lifecycle state.

    Useful for dashboards and Telegram bot formatting.
    """
    display_map = {
        AgentLifecycleState.ONBOARDED: {
            "label": "Onboarded",
            "label_hi": "Naya Agent",
            "color": "#3498db",
            "emoji": "\U0001f195",
            "description": "Recently joined, not yet licensed",
        },
        AgentLifecycleState.LICENSED: {
            "label": "Licensed",
            "label_hi": "License Mila",
            "color": "#2ecc71",
            "emoji": "\U0001f4cb",
            "description": "Licensed but no sale yet",
        },
        AgentLifecycleState.FIRST_SALE: {
            "label": "First Sale",
            "label_hi": "Pehli Sale",
            "color": "#27ae60",
            "emoji": "\U0001f389",
            "description": "Made their first policy sale",
        },
        AgentLifecycleState.ACTIVE: {
            "label": "Active",
            "label_hi": "Active",
            "color": "#2ecc71",
            "emoji": "\u2705",
            "description": "Regularly selling policies",
        },
        AgentLifecycleState.PRODUCTIVE: {
            "label": "Productive",
            "label_hi": "Top Performer",
            "color": "#f39c12",
            "emoji": "\u2b50",
            "description": "Consistently high performance",
        },
        AgentLifecycleState.AT_RISK: {
            "label": "At Risk",
            "label_hi": "Risk Mein",
            "color": "#e67e22",
            "emoji": "\u26a0\ufe0f",
            "description": "Showing signs of disengagement",
        },
        AgentLifecycleState.DORMANT: {
            "label": "Dormant",
            "label_hi": "Dormant",
            "color": "#e74c3c",
            "emoji": "\U0001f534",
            "description": "No activity for extended period",
        },
        AgentLifecycleState.LAPSED: {
            "label": "Lapsed",
            "label_hi": "License Expired",
            "color": "#95a5a6",
            "emoji": "\u23f0",
            "description": "License expired",
        },
        AgentLifecycleState.TERMINATED: {
            "label": "Terminated",
            "label_hi": "Terminated",
            "color": "#7f8c8d",
            "emoji": "\u274c",
            "description": "No longer active — terminal state",
        },
    }
    return display_map.get(state, {
        "label": state.replace("_", " ").title(),
        "label_hi": state,
        "color": "#bdc3c7",
        "emoji": "\u2753",
        "description": "Unknown state",
    })
