"""
Playbook routes — expose default playbook definitions and playbook recommendation.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import Agent
from domain.enums import PlaybookActionType
from domain.playbook_engine import get_default_playbooks, select_playbook_for_agent

router = APIRouter(prefix="/playbooks", tags=["Playbooks"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _serialize_action_type(action_type) -> str:
    """Convert a PlaybookActionType enum (or string) to a plain string."""
    if isinstance(action_type, PlaybookActionType):
        return action_type.value
    return str(action_type)


def _serialize_step(step: dict) -> dict:
    """Serialize a single playbook step to a JSON-safe dict."""
    return {
        "step_number": step.get("step_number"),
        "name": step.get("name", ""),
        "action_type": _serialize_action_type(step.get("action_type", "")),
        "action_config": step.get("action_config", {}),
        "delay_days": step.get("delay_days", 0),
        "next_step_rules": step.get("next_step_rules", []),
    }


def _serialize_playbook(pb: dict) -> dict:
    """Serialize a full playbook definition to a JSON-safe dict."""
    trigger = pb.get("trigger_conditions", {})
    return {
        "name": pb.get("name", ""),
        "name_hi": pb.get("name_hi", ""),
        "description": pb.get("description", ""),
        "target_lifecycle_state": trigger.get("lifecycle_state", ""),
        "target_dormancy_category": trigger.get("dormancy_reason_category", ""),
        "max_duration_days": pb.get("max_duration_days"),
        "success_criteria": pb.get("success_criteria", {}),
        "steps": [_serialize_step(s) for s in pb.get("steps", [])],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/")
def list_playbooks():
    """Return all default playbook definitions."""
    playbooks = get_default_playbooks()
    return [_serialize_playbook(pb) for pb in playbooks]


@router.get("/recommend/{agent_id}")
def recommend_playbook(
    agent_id: int,
    db: Session = Depends(get_db),
):
    """Recommend the best playbook for a given agent based on their current state.

    Uses the agent's lifecycle_state and dormancy_reason to select the most
    appropriate playbook from the default set.
    """
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")

    # Extract dormancy_reason_category from the dotted reason code if present
    dormancy_reason = agent.dormancy_reason
    dormancy_reason_category = None
    if dormancy_reason and "." in dormancy_reason:
        dormancy_reason_category = dormancy_reason.split(".")[0]

    playbook = select_playbook_for_agent(
        lifecycle_state=agent.lifecycle_state or "dormant",
        dormancy_reason=dormancy_reason,
        dormancy_reason_category=dormancy_reason_category,
    )

    if not playbook:
        return {
            "agent_id": agent_id,
            "agent_name": agent.name,
            "lifecycle_state": agent.lifecycle_state,
            "dormancy_reason": dormancy_reason,
            "recommended_playbook": None,
            "message": "No matching playbook found for this agent's current state.",
        }

    return {
        "agent_id": agent_id,
        "agent_name": agent.name,
        "lifecycle_state": agent.lifecycle_state,
        "dormancy_reason": dormancy_reason,
        "recommended_playbook": _serialize_playbook(playbook),
    }


@router.get("/{name}")
def get_playbook(name: str):
    """Return a single playbook by name (case-insensitive match)."""
    playbooks = get_default_playbooks()
    for pb in playbooks:
        if pb["name"].lower() == name.lower():
            return _serialize_playbook(pb)

    raise HTTPException(status_code=404, detail=f"Playbook '{name}' not found")
