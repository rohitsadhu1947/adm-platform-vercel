"""
domain/playbook_engine.py — Playbook condition evaluator and default playbook definitions.

Ported from AARS modules/playbook/condition_evaluator.py and seeds/default_playbooks.py.
Simplified for standalone use without Redis/Celery.

The playbook engine provides:
1. A SAFE condition evaluator (NEVER uses eval())
2. Step-by-step execution logic for playbooks
3. Six default playbook definitions covering all major scenarios
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from domain.enums import PlaybookActionType

logger = logging.getLogger(__name__)


# ===========================================================================
# PART 1: Safe Condition Evaluator (no eval()!)
# ===========================================================================

# Supported comparison operators
_OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: _to_num(a) > _to_num(b),
    "<": lambda a, b: _to_num(a) < _to_num(b),
    ">=": lambda a, b: _to_num(a) >= _to_num(b),
    "<=": lambda a, b: _to_num(a) <= _to_num(b),
    "in": lambda a, b: a in b if isinstance(b, (list, tuple, set)) else str(a) in str(b),
    "contains": lambda a, b: b in a if isinstance(a, (list, tuple, set, str)) else False,
}

# Regex to parse condition strings: "field op value" with optional AND joins
_CONDITION_PATTERN = re.compile(
    r"(\w+(?:\.\w+)*)\s*(==|!=|>=|<=|>|<|in|contains)\s*(.+?)(?:\s+AND\s+|$)",
    re.IGNORECASE,
)


def _to_num(val: Any) -> float:
    """Safely convert to number for comparison."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _parse_value(raw: str) -> Any:
    """Parse a value string into a Python value."""
    raw = raw.strip().strip("'\"")
    if raw.lower() == "true":
        return True
    if raw.lower() == "false":
        return False
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    # Check for list: [a, b, c]
    if raw.startswith("[") and raw.endswith("]"):
        items = [s.strip().strip("'\"") for s in raw[1:-1].split(",")]
        return items
    return raw


def _get_nested(context: dict, key: str) -> Any:
    """Get a value from context using dot notation (e.g., 'payload.outcome')."""
    parts = key.split(".")
    current = context
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def evaluate_condition(condition: str | dict, context: dict) -> bool:
    """Evaluate a condition against a context dict.

    Supports two formats:
    1. String: "outcome == answered AND sentiment == positive"
    2. Dict: {"field": "quiz_score", "op": ">=", "value": 60}

    Special string values:
    - "default" -> always True
    - empty string -> always True

    Returns True if ALL parts of the condition match.
    NEVER uses eval(). All parsing is done with regex and explicit operators.
    """
    # Handle dict-format conditions
    if isinstance(condition, dict):
        field_name = condition.get("field", "")
        op = condition.get("op", "==")
        value = condition.get("value")
        actual = _get_nested(context, field_name)
        op_func = _OPS.get(op)
        if op_func is None:
            logger.warning("Unknown operator '%s' in condition dict", op)
            return False
        try:
            return op_func(actual, value)
        except (TypeError, ValueError):
            return False

    # Handle string-format conditions
    condition = str(condition).strip()
    if condition.lower() == "default" or not condition:
        return True

    matches = _CONDITION_PATTERN.findall(condition)
    if not matches:
        logger.warning("Could not parse condition: %s", condition)
        return False

    for field_name, op, raw_value in matches:
        actual = _get_nested(context, field_name)
        expected = _parse_value(raw_value)
        op_func = _OPS.get(op.lower())
        if op_func is None:
            logger.warning("Unknown operator '%s' in condition: %s", op, condition)
            return False
        try:
            if not op_func(actual, expected):
                return False
        except (TypeError, ValueError):
            return False

    return True


def resolve_next_step(rules: list[dict], context: dict) -> dict | None:
    """Evaluate branching rules and return the first matching rule.

    Each rule dict should have:
        - "condition": str or dict (condition to evaluate)
        - "go_to_step": int (optional, which step to jump to)
        - "action": str (optional, e.g., "route_to_playbook")

    Returns the first matching rule dict, or None if no rules match.
    """
    for rule in rules:
        condition = rule.get("condition", "default")
        if evaluate_condition(condition, context):
            return rule
    return None


# ===========================================================================
# PART 2: Playbook Step Execution
# ===========================================================================

@dataclass
class PlaybookStepResult:
    """Result of executing a single playbook step."""
    step_number: int
    step_name: str
    action_type: str
    success: bool
    message: str = ""
    next_step: int | None = None  # Override next step (from branching)
    route_to_playbook: str | None = None  # Route to different playbook
    context_updates: dict = field(default_factory=dict)


def execute_playbook_step(
    step: dict,
    context: dict,
) -> PlaybookStepResult:
    """Execute a single playbook step and determine the next action.

    This is a simplified executor that generates the action description
    and resolves branching rules. Actual message sending / call scheduling
    is handled by the service layer.

    Args:
        step: The playbook step definition dict.
        context: Current execution context (agent data, previous results).

    Returns:
        PlaybookStepResult with execution details and next-step info.
    """
    step_number = step.get("step_number", 0)
    step_name = step.get("name", f"Step {step_number}")
    action_type = step.get("action_type", "")
    action_config = step.get("action_config", {})
    next_step_rules = step.get("next_step_rules", [])

    # Generate the message from config, substituting variables from context
    message = action_config.get("message", "")
    if message and context:
        for key, value in context.items():
            if isinstance(value, str):
                message = message.replace(f"{{{key}}}", value)

    result = PlaybookStepResult(
        step_number=step_number,
        step_name=step_name,
        action_type=action_type,
        success=True,
        message=message,
    )

    # Resolve branching rules if present
    if next_step_rules:
        matched_rule = resolve_next_step(next_step_rules, context)
        if matched_rule:
            if "go_to_step" in matched_rule:
                result.next_step = matched_rule["go_to_step"]
            if matched_rule.get("action") == "route_to_playbook":
                result.route_to_playbook = matched_rule.get("playbook")

    return result


def get_next_step_number(
    current_step: int,
    steps: list[dict],
    override_next: int | None = None,
) -> int | None:
    """Determine the next step number in a playbook.

    Args:
        current_step: Current step number.
        steps: All playbook step definitions.
        override_next: Override from branching rules.

    Returns:
        Next step number, or None if playbook is complete.
    """
    if override_next is not None:
        # Validate the override step exists
        if any(s.get("step_number") == override_next for s in steps):
            return override_next

    # Default: move to next sequential step
    step_numbers = sorted(s.get("step_number", 0) for s in steps)
    try:
        idx = step_numbers.index(current_step)
        if idx + 1 < len(step_numbers):
            return step_numbers[idx + 1]
    except ValueError:
        pass

    return None  # Playbook complete


# ===========================================================================
# PART 3: Default Playbook Definitions
# ===========================================================================

def get_default_playbooks() -> list[dict]:
    """Return the six default playbook definitions.

    These cover the major intervention scenarios:
    1. New agent onboarding
    2. Dormant agent reactivation (generic)
    3. At-risk intervention
    4. Commission concern resolution
    5. System/process issue resolution
    6. Training engagement

    Each playbook has: name, description, trigger_conditions, success_criteria,
    max_duration_days, and steps (list of step dicts with branching rules).
    """
    return [
        # -- 1. New Agent Onboarding --
        {
            "name": "New Agent Onboarding",
            "name_hi": "Naye Agent ki Onboarding",
            "description": (
                "For newly onboarded agents. Welcomes them, introduces ADM, "
                "sends initial training, and ensures first contact within 3 days."
            ),
            "trigger_conditions": {
                "lifecycle_state": "onboarded",
            },
            "success_criteria": {
                "target_state": "licensed",
            },
            "max_duration_days": 14,
            "steps": [
                {
                    "step_number": 1,
                    "name": "Welcome message",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "welcome_new_agent",
                        "message": (
                            "Welcome {agent_name}! You are now part of our team. "
                            "Your ADM {adm_name} will connect with you soon."
                        ),
                    },
                    "delay_days": 0,
                    "next_step_rules": [],
                },
                {
                    "step_number": 2,
                    "name": "ADM nudge — first contact needed",
                    "action_type": PlaybookActionType.ADM_NUDGE,
                    "action_config": {
                        "nudge_type": "FIRST_CONTACT_NEEDED",
                        "urgency": "HIGH",
                        "message": (
                            "{agent_name} was just onboarded. Please make first contact "
                            "within 24 hours — first impression is critical for retention."
                        ),
                    },
                    "delay_days": 0,
                    "next_step_rules": [],
                },
                {
                    "step_number": 3,
                    "name": "Training intro module",
                    "action_type": PlaybookActionType.WHATSAPP_TRAINING,
                    "action_config": {
                        "training_topic": "product_term_life",
                        "content_type": "video",
                        "message": (
                            "Here is your first training module. Watch this 2-minute video "
                            "about Term Life insurance — our most popular product."
                        ),
                    },
                    "delay_days": 1,
                    "next_step_rules": [],
                },
                {
                    "step_number": 4,
                    "name": "Check-in if no response",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "gentle_checkin",
                        "message": (
                            "Hi {agent_name}, how are you settling in? "
                            "Do you have any questions about getting started?"
                        ),
                    },
                    "delay_days": 3,
                    "next_step_rules": [
                        {
                            "condition": {"field": "agent_replied", "op": "==", "value": True},
                            "go_to_step": 5,
                        },
                    ],
                },
                {
                    "step_number": 5,
                    "name": "ADM follow-up nudge if no ADM contact",
                    "action_type": PlaybookActionType.ADM_NUDGE,
                    "action_config": {
                        "nudge_type": "FOLLOW_UP_NEEDED",
                        "message": (
                            "{agent_name} has been onboarded for {days_in_state} days. "
                            "Please ensure they have been contacted."
                        ),
                    },
                    "delay_days": 4,
                    "next_step_rules": [],
                },
            ],
        },

        # -- 2. Dormant Agent Reactivation (Generic) --
        {
            "name": "Dormant Re-engagement",
            "name_hi": "Dormant Agent ko Wapas Laana",
            "description": (
                "Generic re-engagement playbook for dormant agents. Uses a gentle "
                "check-in, waits for response, then routes to specific playbook "
                "based on the identified dormancy reason."
            ),
            "trigger_conditions": {
                "lifecycle_state": "dormant",
            },
            "success_criteria": {
                "dormancy_reason_identified": True,
                "or": {"signal_type": "policy_sold"},
            },
            "max_duration_days": 21,
            "steps": [
                {
                    "step_number": 1,
                    "name": "WhatsApp gentle check-in",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "gentle_checkin",
                        "message": (
                            "Hi {agent_name}, it has been a while! "
                            "We would love to help you get back on track. "
                            "Is there anything we can help with?"
                        ),
                    },
                    "delay_days": 0,
                    "next_step_rules": [],
                },
                {
                    "step_number": 2,
                    "name": "Wait for response",
                    "action_type": PlaybookActionType.WAIT,
                    "action_config": {"wait_days": 3},
                    "delay_days": 3,
                    "next_step_rules": [
                        {
                            "condition": {"field": "agent_replied", "op": "==", "value": True},
                            "go_to_step": 4,
                        },
                    ],
                },
                {
                    "step_number": 3,
                    "name": "Follow-up message",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "reengagement_followup",
                        "message": (
                            "{agent_name}, just checking in again. We have new training "
                            "material and support available. Reply anytime — we are here to help."
                        ),
                    },
                    "delay_days": 0,
                    "next_step_rules": [],
                },
                {
                    "step_number": 4,
                    "name": "ADM nudge with context",
                    "action_type": PlaybookActionType.ADM_NUDGE,
                    "action_config": {
                        "nudge_type": "DORMANCY_REENGAGEMENT",
                        "message": (
                            "{agent_name} is dormant for {dormancy_duration_days} days. "
                            "Reason: {dormancy_reason}. Please reach out personally."
                        ),
                    },
                    "delay_days": 1,
                    "next_step_rules": [
                        {
                            "condition": {
                                "field": "dormancy_reason_category",
                                "op": "==",
                                "value": "training_gap",
                            },
                            "action": "route_to_playbook",
                            "playbook": "Training Engagement",
                        },
                        {
                            "condition": {
                                "field": "dormancy_reason_category",
                                "op": "==",
                                "value": "economic",
                            },
                            "action": "route_to_playbook",
                            "playbook": "Commission Concern Resolution",
                        },
                    ],
                },
            ],
        },

        # -- 3. At-Risk Intervention --
        {
            "name": "At-Risk Intervention",
            "name_hi": "At-Risk Agent ki Madad",
            "description": (
                "For agents showing signs of disengagement (AT_RISK state). "
                "Quick intervention before they become dormant."
            ),
            "trigger_conditions": {
                "lifecycle_state": "at_risk",
            },
            "success_criteria": {
                "target_state": "active",
            },
            "max_duration_days": 14,
            "steps": [
                {
                    "step_number": 1,
                    "name": "ADM urgent nudge",
                    "action_type": PlaybookActionType.ADM_NUDGE,
                    "action_config": {
                        "nudge_type": "AT_RISK_INTERVENTION",
                        "urgency": "HIGH",
                        "message": (
                            "{agent_name} is showing signs of disengagement. "
                            "They have been at-risk for {days_in_state} days. "
                            "A timely call can prevent them from going dormant."
                        ),
                    },
                    "delay_days": 0,
                    "next_step_rules": [],
                },
                {
                    "step_number": 2,
                    "name": "Friendly check-in message",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "gentle_checkin",
                        "message": (
                            "Hi {agent_name}, how are things going? "
                            "We noticed it has been a while since your last activity. "
                            "Is there anything holding you back?"
                        ),
                    },
                    "delay_days": 1,
                    "next_step_rules": [],
                },
                {
                    "step_number": 3,
                    "name": "Training nudge",
                    "action_type": PlaybookActionType.WHATSAPP_TRAINING,
                    "action_config": {
                        "training_topic": "sales_objection_handling",
                        "message": (
                            "Here is a quick refresher on handling customer objections. "
                            "This is one of the most useful skills for making sales."
                        ),
                    },
                    "delay_days": 2,
                    "next_step_rules": [],
                },
                {
                    "step_number": 4,
                    "name": "Escalate if no improvement",
                    "action_type": PlaybookActionType.ESCALATE,
                    "action_config": {
                        "escalate_to": "regional_manager",
                        "urgency": "MEDIUM",
                        "message": (
                            "{agent_name} has been at-risk for {days_in_state} days "
                            "with no response to outreach. May need in-person visit."
                        ),
                    },
                    "delay_days": 7,
                    "next_step_rules": [],
                },
            ],
        },

        # -- 4. Commission Concern Resolution --
        {
            "name": "Commission Concern Resolution",
            "name_hi": "Commission ki Chinta ka Samadhan",
            "description": (
                "For agents whose dormancy is driven by economic concerns "
                "(commission too low, competitor offers, payment issues)."
            ),
            "trigger_conditions": {
                "lifecycle_state": "dormant",
                "dormancy_reason_category": "economic",
            },
            "success_criteria": {
                "signal_type": "policy_sold",
            },
            "max_duration_days": 21,
            "steps": [
                {
                    "step_number": 1,
                    "name": "Commission structure explainer",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "commission_explainer",
                        "message": (
                            "We understand commission matters. Here is a clear breakdown "
                            "of our commission structure and how top agents earn 2-3x more. "
                            "Check out these earning scenarios."
                        ),
                    },
                    "delay_days": 0,
                    "next_step_rules": [],
                },
                {
                    "step_number": 2,
                    "name": "ADM nudge with specific concern",
                    "action_type": PlaybookActionType.ADM_NUDGE,
                    "action_config": {
                        "nudge_type": "COMMISSION_CONCERN",
                        "message": (
                            "{agent_name} has commission concerns: {dormancy_reason}. "
                            "Please discuss earning potential and address their specific issues."
                        ),
                    },
                    "delay_days": 1,
                    "next_step_rules": [],
                },
                {
                    "step_number": 3,
                    "name": "Success stories and earning tips",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "success_stories",
                        "message": (
                            "Meet Rajesh — he started just like you and now earns Rs 50,000+ "
                            "per month. Here are 3 strategies that work for our top earners."
                        ),
                    },
                    "delay_days": 3,
                    "next_step_rules": [],
                },
            ],
        },

        # -- 5. System/Process Issue Resolution --
        {
            "name": "System Issue Resolution",
            "name_hi": "System/Process Problem ka Samadhan",
            "description": (
                "For agents stuck due to operational issues "
                "(complex process, tech barriers, slow issuance, KYC issues)."
            ),
            "trigger_conditions": {
                "lifecycle_state": "dormant",
                "dormancy_reason_category": "operational",
            },
            "success_criteria": {
                "target_state": "licensed",
            },
            "max_duration_days": 14,
            "steps": [
                {
                    "step_number": 1,
                    "name": "Acknowledge the issue",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "issue_acknowledgment",
                        "message": (
                            "Hi {agent_name}, we understand you have been facing difficulties "
                            "with {dormancy_reason}. We are here to help resolve this."
                        ),
                    },
                    "delay_days": 0,
                    "next_step_rules": [],
                },
                {
                    "step_number": 2,
                    "name": "Process training module",
                    "action_type": PlaybookActionType.WHATSAPP_TRAINING,
                    "action_config": {
                        "training_topic": "process_digital_tools",
                        "message": (
                            "Here is a step-by-step guide that walks you through the process. "
                            "It covers everything from start to finish."
                        ),
                    },
                    "delay_days": 1,
                    "next_step_rules": [],
                },
                {
                    "step_number": 3,
                    "name": "ADM hands-on help",
                    "action_type": PlaybookActionType.ADM_NUDGE,
                    "action_config": {
                        "nudge_type": "HANDS_ON_HELP_NEEDED",
                        "message": (
                            "{agent_name} needs hands-on help with {dormancy_reason}. "
                            "Please schedule a call to walk them through the process."
                        ),
                    },
                    "delay_days": 2,
                    "next_step_rules": [],
                },
            ],
        },

        # -- 6. Training Engagement --
        {
            "name": "Training Engagement",
            "name_hi": "Training ke Zariye Engagement",
            "description": (
                "For agents with training-gap dormancy reasons. Sends product training, "
                "quiz, and routes to ADM for guided first sale."
            ),
            "trigger_conditions": {
                "lifecycle_state": "dormant",
                "dormancy_reason_category": "training_gap",
            },
            "success_criteria": {
                "target_state": "licensed",
                "or": {"signal_type": "policy_sold"},
            },
            "max_duration_days": 30,
            "steps": [
                {
                    "step_number": 1,
                    "name": "Ask product interest",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "product_interest_query",
                        "message": (
                            "Namaste {agent_name}! We want to help you learn about our products. "
                            "Which product interests you most? "
                            "Reply: 1) Term Life 2) Endowment 3) ULIP 4) Health"
                        ),
                    },
                    "delay_days": 0,
                    "next_step_rules": [],
                },
                {
                    "step_number": 2,
                    "name": "Send product micro-training",
                    "action_type": PlaybookActionType.WHATSAPP_TRAINING,
                    "action_config": {
                        "training_topic": "based_on_reply",
                        "fallback_topic": "product_term_life",
                        "content_type": "video",
                        "message": "Here is a short training video. Watch it and then take the quiz!",
                    },
                    "delay_days": 1,
                    "next_step_rules": [],
                },
                {
                    "step_number": 3,
                    "name": "Quiz (3-5 questions)",
                    "action_type": PlaybookActionType.WHATSAPP_TRAINING,
                    "action_config": {
                        "content_type": "quiz",
                        "quiz_questions": 5,
                        "pass_score": 60,
                    },
                    "delay_days": 1,
                    "next_step_rules": [
                        {
                            "condition": {"field": "quiz_score", "op": ">=", "value": 60},
                            "go_to_step": 4,
                        },
                        {
                            "condition": {"field": "quiz_score", "op": "<", "value": 60},
                            "go_to_step": 2,
                        },
                    ],
                },
                {
                    "step_number": 4,
                    "name": "ADM nudge — agent ready for guided sale",
                    "action_type": PlaybookActionType.ADM_NUDGE,
                    "action_config": {
                        "nudge_type": "GUIDED_SALE_READY",
                        "message": (
                            "{agent_name} completed product training with score {quiz_score}%. "
                            "They are ready for a guided first sale. Please schedule a joint call."
                        ),
                    },
                    "delay_days": 0,
                    "next_step_rules": [],
                },
                {
                    "step_number": 5,
                    "name": "Follow-up if ADM does not act",
                    "action_type": PlaybookActionType.WHATSAPP_MESSAGE,
                    "action_config": {
                        "template": "training_followup",
                        "message": (
                            "Great job on the training, {agent_name}! "
                            "Your ADM {adm_name} will help you with your first customer visit. "
                            "In the meantime, here are some tips for approaching customers."
                        ),
                    },
                    "delay_days": 3,
                    "next_step_rules": [],
                },
            ],
        },
    ]


# ===========================================================================
# PART 4: Playbook Selection
# ===========================================================================

def select_playbook_for_agent(
    lifecycle_state: str,
    dormancy_reason: str | None = None,
    dormancy_reason_category: str | None = None,
) -> dict | None:
    """Select the best matching playbook for an agent based on their state and reason.

    Priority order:
    1. Exact dormancy_reason_category match
    2. Lifecycle state match
    3. Generic re-engagement fallback

    Args:
        lifecycle_state: Agent's current lifecycle state.
        dormancy_reason: Specific dormancy reason code (optional).
        dormancy_reason_category: Category of dormancy reason (optional).

    Returns:
        The best matching playbook dict, or None if no match.
    """
    playbooks = get_default_playbooks()

    # Infer category from reason code if not provided
    if dormancy_reason and not dormancy_reason_category:
        if "." in dormancy_reason:
            dormancy_reason_category = dormancy_reason.split(".")[0]

    # First pass: match on dormancy_reason_category
    if dormancy_reason_category:
        for pb in playbooks:
            trigger = pb.get("trigger_conditions", {})
            if (
                trigger.get("dormancy_reason_category") == dormancy_reason_category
                and trigger.get("lifecycle_state", lifecycle_state) == lifecycle_state
            ):
                return pb

    # Second pass: match on lifecycle_state alone
    for pb in playbooks:
        trigger = pb.get("trigger_conditions", {})
        if (
            trigger.get("lifecycle_state") == lifecycle_state
            and "dormancy_reason_category" not in trigger
        ):
            return pb

    # Fallback: Dormant Re-engagement
    if lifecycle_state in ("dormant", "at_risk"):
        for pb in playbooks:
            if "Re-engagement" in pb["name"] or "At-Risk" in pb["name"]:
                return pb

    return None
