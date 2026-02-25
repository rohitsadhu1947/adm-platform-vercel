"""
Agent assignment routes.
Provides auto-assignment, rebalancing, and assignment statistics.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Agent, ADM
from schemas import AssignmentRequest, AssignmentResult
from services.assignment_service import auto_assign_agents, rebalance_assignments

router = APIRouter(prefix="/assignment", tags=["Assignment"])


@router.post("/auto-assign", response_model=AssignmentResult)
def trigger_auto_assignment(
    request: AssignmentRequest,
    db: Session = Depends(get_db),
):
    """
    Trigger automatic assignment of agents to ADMs.

    Strategies:
    - balanced: distribute evenly considering capacity, geography, and language
    - geographic: prioritize geographic proximity
    - language: prioritize language compatibility

    If agent_ids is not provided, assigns all unassigned dormant/at-risk agents.
    If adm_id is not provided, auto-selects the best ADM for each agent.
    """
    result = auto_assign_agents(
        db=db,
        agent_ids=request.agent_ids,
        target_adm_id=request.adm_id,
        strategy=request.strategy,
    )

    return AssignmentResult(
        assigned_count=result["assigned_count"],
        assignments=result["assignments"],
        errors=result["errors"],
    )


@router.post("/rebalance")
def trigger_rebalance(db: Session = Depends(get_db)):
    """
    Rebalance agent assignments across ADMs.

    Moves dormant/at-risk agents from overloaded ADMs to underloaded ones,
    considering geographic and language compatibility.

    Only agents in dormant or at_risk state (not yet actively engaged) are moved.
    """
    result = rebalance_assignments(db)

    return {
        "rebalanced_count": result["rebalanced"],
        "moves": result["moves"],
        "errors": result["errors"],
    }


@router.get("/stats")
def get_assignment_stats(db: Session = Depends(get_db)):
    """
    Get comprehensive assignment statistics.

    Returns:
    - Total agents, assigned vs unassigned counts
    - Per-ADM load breakdown
    - Capacity utilization
    - Geographic distribution of assignments
    """
    total_agents = db.query(func.count(Agent.id)).scalar() or 0
    assigned = db.query(func.count(Agent.id)).filter(
        Agent.assigned_adm_id.isnot(None),
    ).scalar() or 0
    unassigned = total_agents - assigned

    # Per-ADM load
    adms = db.query(ADM).all()
    adm_stats = []

    for adm in adms:
        agent_count = db.query(func.count(Agent.id)).filter(
            Agent.assigned_adm_id == adm.id,
        ).scalar() or 0

        # Agent state breakdown for this ADM
        state_counts = dict(
            db.query(Agent.lifecycle_state, func.count(Agent.id))
            .filter(Agent.assigned_adm_id == adm.id)
            .group_by(Agent.lifecycle_state)
            .all()
        )

        utilization = round((agent_count / adm.max_capacity * 100), 1) if adm.max_capacity > 0 else 0

        adm_stats.append({
            "adm_id": adm.id,
            "adm_name": adm.name,
            "region": adm.region,
            "assigned_agents": agent_count,
            "max_capacity": adm.max_capacity,
            "utilization_pct": utilization,
            "state_breakdown": state_counts,
        })

    # Geographic distribution of unassigned agents
    unassigned_by_location = dict(
        db.query(Agent.location, func.count(Agent.id))
        .filter(Agent.assigned_adm_id.is_(None))
        .group_by(Agent.location)
        .order_by(func.count(Agent.id).desc())
        .all()
    )

    # Language distribution of unassigned agents
    unassigned_by_language = dict(
        db.query(Agent.language, func.count(Agent.id))
        .filter(Agent.assigned_adm_id.is_(None))
        .group_by(Agent.language)
        .order_by(func.count(Agent.id).desc())
        .all()
    )

    # Average capacity utilization
    avg_utilization = 0
    if adm_stats:
        avg_utilization = round(
            sum(s["utilization_pct"] for s in adm_stats) / len(adm_stats), 1
        )

    return {
        "total_agents": total_agents,
        "assigned_agents": assigned,
        "unassigned_agents": unassigned,
        "assignment_rate_pct": round((assigned / total_agents * 100), 1) if total_agents > 0 else 0,
        "total_adms": len(adms),
        "avg_capacity_utilization_pct": avg_utilization,
        "adm_breakdown": adm_stats,
        "unassigned_by_location": unassigned_by_location,
        "unassigned_by_language": unassigned_by_language,
    }
