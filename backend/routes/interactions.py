"""
Interaction logging and management routes.
"""

from datetime import datetime, date as date_type
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Interaction, Agent, ADM
from schemas import InteractionCreate, InteractionUpdate, InteractionResponse

router = APIRouter(prefix="/interactions", tags=["Interactions"])


@router.get("/", response_model=List[InteractionResponse])
def list_interactions(
    agent_id: Optional[int] = Query(None),
    adm_id: Optional[int] = Query(None),
    type: Optional[str] = Query(None, description="call|whatsapp|visit|telegram"),
    outcome: Optional[str] = Query(None),
    follow_up_status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List interactions with optional filters."""
    query = db.query(Interaction)

    if agent_id:
        query = query.filter(Interaction.agent_id == agent_id)
    if adm_id:
        query = query.filter(Interaction.adm_id == adm_id)
    if type:
        query = query.filter(Interaction.type == type)
    if outcome:
        query = query.filter(Interaction.outcome == outcome)
    if follow_up_status:
        query = query.filter(Interaction.follow_up_status == follow_up_status)

    return query.order_by(Interaction.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/overdue")
def list_overdue_followups(
    adm_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get all overdue follow-ups."""
    today = date_type.today()
    query = db.query(Interaction).filter(
        Interaction.follow_up_status == "pending",
        Interaction.follow_up_date < today,
    )
    if adm_id:
        query = query.filter(Interaction.adm_id == adm_id)

    interactions = query.order_by(Interaction.follow_up_date).all()

    results = []
    for i in interactions:
        agent = db.query(Agent).filter(Agent.id == i.agent_id).first()
        results.append({
            "interaction_id": i.id,
            "agent_id": i.agent_id,
            "agent_name": agent.name if agent else "Unknown",
            "agent_phone": agent.phone if agent else "N/A",
            "type": i.type,
            "outcome": i.outcome,
            "follow_up_date": i.follow_up_date.isoformat() if i.follow_up_date else None,
            "days_overdue": (today - i.follow_up_date).days if i.follow_up_date else 0,
            "notes": i.notes,
        })

    return results


@router.get("/{interaction_id}", response_model=InteractionResponse)
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    """Get a single interaction."""
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")
    return interaction


@router.post("/", response_model=InteractionResponse, status_code=201)
def create_interaction(data: InteractionCreate, db: Session = Depends(get_db)):
    """Log a new interaction."""
    # Validate agent exists
    agent = db.query(Agent).filter(Agent.id == data.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Validate ADM exists
    adm = db.query(ADM).filter(ADM.id == data.adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    interaction = Interaction(**data.model_dump())

    # Set follow-up status
    if data.follow_up_date:
        interaction.follow_up_status = "pending"

    db.add(interaction)

    # Update agent state if connected
    if data.outcome == "connected":
        if agent.lifecycle_state == "dormant":
            agent.lifecycle_state = "contacted"
        agent.last_contact_date = datetime.utcnow().date()
        # Bump engagement score slightly
        agent.engagement_score = min(100, agent.engagement_score + 5)

    elif data.outcome == "callback_requested":
        agent.last_contact_date = datetime.utcnow().date()
        agent.engagement_score = min(100, agent.engagement_score + 2)

    agent.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(interaction)
    return interaction


@router.put("/{interaction_id}", response_model=InteractionResponse)
def update_interaction(
    interaction_id: int,
    data: InteractionUpdate,
    db: Session = Depends(get_db),
):
    """Update an interaction (notes, follow-up status, etc.)."""
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(interaction, key, value)

    db.commit()
    db.refresh(interaction)
    return interaction


@router.post("/{interaction_id}/complete-followup")
def complete_followup(interaction_id: int, notes: Optional[str] = None, db: Session = Depends(get_db)):
    """Mark a follow-up as completed."""
    interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interaction not found")

    interaction.follow_up_status = "completed"
    if notes:
        existing_notes = interaction.notes or ""
        interaction.notes = f"{existing_notes}\n[Follow-up completed] {notes}".strip()

    db.commit()
    db.refresh(interaction)
    return {"detail": "Follow-up marked as completed", "interaction_id": interaction_id}


@router.get("/stats/summary")
def interaction_stats(
    adm_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get interaction statistics."""
    query = db.query(Interaction)
    if adm_id:
        query = query.filter(Interaction.adm_id == adm_id)

    total = query.count()

    by_type = dict(
        query.with_entities(Interaction.type, func.count(Interaction.id))
        .group_by(Interaction.type).all()
    )

    by_outcome = dict(
        query.with_entities(Interaction.outcome, func.count(Interaction.id))
        .group_by(Interaction.outcome).all()
    )

    today = date_type.today()
    pending = query.filter(
        Interaction.follow_up_status == "pending",
        Interaction.follow_up_date >= today,
    ).count()

    overdue = query.filter(
        Interaction.follow_up_status == "pending",
        Interaction.follow_up_date < today,
    ).count()

    return {
        "total": total,
        "by_type": by_type,
        "by_outcome": by_outcome,
        "pending_followups": pending,
        "overdue_followups": overdue,
    }
