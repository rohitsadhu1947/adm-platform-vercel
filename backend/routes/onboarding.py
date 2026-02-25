"""
Agent onboarding workflow routes.
Manages the pipeline: pending -> documents_submitted -> verified -> active
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Agent, ADM
from schemas import OnboardingStart, OnboardingAdvance

router = APIRouter(prefix="/onboarding", tags=["Onboarding"])

ONBOARDING_STAGES = ["pending", "documents_submitted", "verified", "active", "rejected"]


@router.get("/pipeline")
def get_onboarding_pipeline(db: Session = Depends(get_db)):
    """Get agents grouped by onboarding status for the Kanban board."""
    pipeline = {}
    for stage in ONBOARDING_STAGES:
        if stage == "active":
            # For active, show recently onboarded (last 30 days)
            agents = db.query(Agent).filter(
                Agent.onboarding_status == stage,
                Agent.onboarding_completed_at.isnot(None),
            ).order_by(Agent.onboarding_completed_at.desc()).limit(20).all()
        else:
            agents = db.query(Agent).filter(
                Agent.onboarding_status == stage,
            ).order_by(Agent.created_at.desc()).all()

        agent_list = []
        for a in agents:
            adm_name = None
            if a.assigned_adm_id:
                adm = db.query(ADM).filter(ADM.id == a.assigned_adm_id).first()
                adm_name = adm.name if adm else None

            agent_list.append({
                "id": a.id,
                "name": a.name,
                "phone": a.phone,
                "email": a.email,
                "location": a.location,
                "state": a.state,
                "onboarding_status": a.onboarding_status,
                "assigned_adm_id": a.assigned_adm_id,
                "assigned_adm_name": adm_name,
                "onboarding_started_at": a.onboarding_started_at.isoformat() if a.onboarding_started_at else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            })

        pipeline[stage] = {
            "count": len(agent_list),
            "agents": agent_list,
        }

    return pipeline


@router.post("/start")
def start_onboarding(data: OnboardingStart, db: Session = Depends(get_db)):
    """Start onboarding a new agent."""
    # Check for duplicate phone
    existing = db.query(Agent).filter(Agent.phone == data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent with this phone already exists")

    agent = Agent(
        name=data.name,
        phone=data.phone,
        email=data.email,
        location=data.location,
        state=data.state,
        language=data.language,
        lifecycle_state="dormant",
        onboarding_status="pending",
        onboarding_started_at=datetime.utcnow(),
        assigned_adm_id=data.assigned_adm_id,
        engagement_score=0.0,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    return {
        "message": "Onboarding started",
        "agent_id": agent.id,
        "status": "pending",
    }


@router.put("/{agent_id}/advance")
def advance_onboarding(agent_id: int, data: OnboardingAdvance, db: Session = Depends(get_db)):
    """Advance an agent to the next onboarding step."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if data.new_status not in ONBOARDING_STAGES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {ONBOARDING_STAGES}")

    agent.onboarding_status = data.new_status

    if data.new_status == "active":
        agent.onboarding_completed_at = datetime.utcnow()
        agent.lifecycle_state = "contacted"  # Move to contacted lifecycle state

    db.commit()
    db.refresh(agent)

    return {
        "message": f"Agent moved to {data.new_status}",
        "agent_id": agent.id,
        "onboarding_status": agent.onboarding_status,
        "lifecycle_state": agent.lifecycle_state,
    }


@router.post("/{agent_id}/assign-adm")
def assign_adm_during_onboarding(agent_id: int, adm_id: int = Query(...), db: Session = Depends(get_db)):
    """Assign an ADM to an agent during onboarding."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    agent.assigned_adm_id = adm_id
    db.commit()

    return {
        "message": f"Agent assigned to ADM {adm.name}",
        "agent_id": agent.id,
        "adm_id": adm_id,
    }


@router.get("/stats")
def get_onboarding_stats(db: Session = Depends(get_db)):
    """Get onboarding pipeline statistics."""
    stats = dict(
        db.query(Agent.onboarding_status, func.count(Agent.id))
        .group_by(Agent.onboarding_status)
        .all()
    )
    return {
        "total_in_pipeline": sum(v for k, v in stats.items() if k != "active"),
        "by_status": stats,
    }
