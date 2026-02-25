"""
ADM (Agency Development Manager) CRUD routes.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import ADM, Agent, Interaction, Feedback
from schemas import ADMCreate, ADMUpdate, ADMResponse, ADMPerformance, ADMBulkImport, AgentResponse

router = APIRouter(prefix="/adms", tags=["ADMs"])


@router.get("/", response_model=List[ADMResponse])
def list_adms(
    region: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all ADMs."""
    query = db.query(ADM)

    if region:
        query = query.filter(ADM.region.ilike(f"%{region}%"))
    if search:
        query = query.filter(
            (ADM.name.ilike(f"%{search}%")) | (ADM.phone.ilike(f"%{search}%"))
        )

    return query.order_by(ADM.name).offset(skip).limit(limit).all()


@router.post("/bulk-import")
def bulk_import_adms(data: ADMBulkImport, db: Session = Depends(get_db)):
    """Bulk import ADMs."""
    created = []
    errors = []

    for i, adm_data in enumerate(data.adms):
        try:
            existing = db.query(ADM).filter(ADM.phone == adm_data.phone).first()
            if existing:
                errors.append({"index": i, "phone": adm_data.phone, "error": "Duplicate phone"})
                continue

            adm = ADM(**adm_data.model_dump())
            db.add(adm)
            db.flush()
            created.append({"index": i, "id": adm.id, "name": adm.name})
        except Exception as e:
            errors.append({"index": i, "error": str(e)})

    db.commit()

    return {
        "total_submitted": len(data.adms),
        "created": len(created),
        "errors_count": len(errors),
        "created_adms": created,
        "errors": errors,
    }


@router.get("/{adm_id}", response_model=ADMResponse)
def get_adm(adm_id: int, db: Session = Depends(get_db)):
    """Get a single ADM by ID."""
    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")
    return adm


@router.post("/", response_model=ADMResponse, status_code=201)
def create_adm(adm_data: ADMCreate, db: Session = Depends(get_db)):
    """Create a new ADM."""
    existing = db.query(ADM).filter(ADM.phone == adm_data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="ADM with this phone already exists")

    adm = ADM(**adm_data.model_dump())
    db.add(adm)
    db.commit()
    db.refresh(adm)
    return adm


@router.put("/{adm_id}", response_model=ADMResponse)
def update_adm(adm_id: int, adm_data: ADMUpdate, db: Session = Depends(get_db)):
    """Update an ADM."""
    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    update_dict = adm_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(adm, key, value)

    adm.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(adm)
    return adm


@router.delete("/{adm_id}")
def delete_adm(adm_id: int, db: Session = Depends(get_db)):
    """Delete an ADM (unassigns their agents first)."""
    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    # Unassign all agents
    db.query(Agent).filter(Agent.assigned_adm_id == adm_id).update(
        {Agent.assigned_adm_id: None}, synchronize_session="fetch"
    )

    db.delete(adm)
    db.commit()
    return {"detail": "ADM deleted", "id": adm_id}


@router.get("/{adm_id}/performance", response_model=ADMPerformance)
def get_adm_performance(adm_id: int, db: Session = Depends(get_db)):
    """Get detailed performance metrics for an ADM."""
    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    # Agent counts by state
    state_counts = db.query(
        Agent.lifecycle_state,
        func.count(Agent.id),
    ).filter(
        Agent.assigned_adm_id == adm_id,
    ).group_by(Agent.lifecycle_state).all()

    state_map = dict(state_counts)
    total = sum(state_map.values())

    contacted = state_map.get("contacted", 0)
    engaged = state_map.get("engaged", 0)
    trained = state_map.get("trained", 0)
    active = state_map.get("active", 0)

    activation_rate = (active / total * 100) if total > 0 else 0.0

    # Average engagement score
    avg_engagement = db.query(func.avg(Agent.engagement_score)).filter(
        Agent.assigned_adm_id == adm_id,
    ).scalar() or 0.0

    # Interaction count
    total_interactions = db.query(func.count(Interaction.id)).filter(
        Interaction.adm_id == adm_id,
    ).scalar() or 0

    # Follow-up stats
    from datetime import date as date_type
    today = date_type.today()

    pending_followups = db.query(func.count(Interaction.id)).filter(
        Interaction.adm_id == adm_id,
        Interaction.follow_up_status == "pending",
        Interaction.follow_up_date >= today,
    ).scalar() or 0

    overdue_followups = db.query(func.count(Interaction.id)).filter(
        Interaction.adm_id == adm_id,
        Interaction.follow_up_status == "pending",
        Interaction.follow_up_date < today,
    ).scalar() or 0

    return ADMPerformance(
        adm_id=adm_id,
        adm_name=adm.name,
        total_agents=total,
        contacted_agents=contacted,
        engaged_agents=engaged,
        active_agents=active,
        activation_rate=round(activation_rate, 1),
        avg_engagement_score=round(float(avg_engagement), 1),
        total_interactions=total_interactions,
        pending_followups=pending_followups,
        overdue_followups=overdue_followups,
    )


@router.get("/{adm_id}/agents", response_model=List[AgentResponse])
def get_adm_agents(
    adm_id: int,
    lifecycle_state: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get all agents assigned to an ADM."""
    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    query = db.query(Agent).filter(Agent.assigned_adm_id == adm_id)
    if lifecycle_state:
        query = query.filter(Agent.lifecycle_state == lifecycle_state)

    return query.order_by(Agent.engagement_score.desc()).all()
