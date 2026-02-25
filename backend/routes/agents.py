"""
Agent CRUD routes.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Agent, ADM
from schemas import AgentCreate, AgentUpdate, AgentResponse, AgentBulkImport

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/", response_model=List[AgentResponse])
def list_agents(
    lifecycle_state: Optional[str] = Query(None, description="Filter by lifecycle state"),
    location: Optional[str] = Query(None, description="Filter by location (city)"),
    assigned_adm_id: Optional[int] = Query(None, description="Filter by assigned ADM"),
    unassigned: Optional[bool] = Query(None, description="Show only unassigned agents"),
    search: Optional[str] = Query(None, description="Search by name or phone"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List agents with optional filters."""
    query = db.query(Agent)

    if lifecycle_state:
        query = query.filter(Agent.lifecycle_state == lifecycle_state)
    if location:
        query = query.filter(Agent.location.ilike(f"%{location}%"))
    if assigned_adm_id:
        query = query.filter(Agent.assigned_adm_id == assigned_adm_id)
    if unassigned:
        query = query.filter(Agent.assigned_adm_id.is_(None))
    if search:
        query = query.filter(
            (Agent.name.ilike(f"%{search}%")) | (Agent.phone.ilike(f"%{search}%"))
        )

    total = query.count()
    agents = query.order_by(Agent.dormancy_duration_days.desc()).offset(skip).limit(limit).all()

    return agents


@router.get("/count")
def count_agents(
    lifecycle_state: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Get count of agents, optionally by state."""
    query = db.query(func.count(Agent.id))
    if lifecycle_state:
        query = query.filter(Agent.lifecycle_state == lifecycle_state)
    return {"count": query.scalar()}


@router.get("/states-summary")
def states_summary(db: Session = Depends(get_db)):
    """Get count of agents by lifecycle state."""
    results = db.query(
        Agent.lifecycle_state,
        func.count(Agent.id),
    ).group_by(Agent.lifecycle_state).all()

    return {state: count for state, count in results}


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: int, db: Session = Depends(get_db)):
    """Get a single agent by ID."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/", response_model=AgentResponse, status_code=201)
def create_agent(agent_data: AgentCreate, db: Session = Depends(get_db)):
    """Create a new agent."""
    # Check for duplicate phone
    existing = db.query(Agent).filter(Agent.phone == agent_data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Agent with this phone number already exists")

    # Validate ADM if specified
    if agent_data.assigned_adm_id:
        adm = db.query(ADM).filter(ADM.id == agent_data.assigned_adm_id).first()
        if not adm:
            raise HTTPException(status_code=400, detail="Assigned ADM not found")

    agent = Agent(**agent_data.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: int, agent_data: AgentUpdate, db: Session = Depends(get_db)):
    """Update an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_dict = agent_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(agent, key, value)

    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


@router.delete("/{agent_id}")
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    """Delete an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.delete(agent)
    db.commit()
    return {"detail": "Agent deleted", "id": agent_id}


@router.post("/{agent_id}/assign/{adm_id}", response_model=AgentResponse)
def assign_agent_to_adm(agent_id: int, adm_id: int, db: Session = Depends(get_db)):
    """Assign an agent to an ADM."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    # Check capacity
    current_count = db.query(func.count(Agent.id)).filter(
        Agent.assigned_adm_id == adm_id
    ).scalar() or 0
    if current_count >= adm.max_capacity:
        raise HTTPException(status_code=400, detail=f"ADM {adm.name} is at full capacity ({adm.max_capacity})")

    agent.assigned_adm_id = adm_id
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


@router.post("/{agent_id}/unassign", response_model=AgentResponse)
def unassign_agent(agent_id: int, db: Session = Depends(get_db)):
    """Remove ADM assignment from an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.assigned_adm_id = None
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)
    return agent


@router.post("/{agent_id}/transition")
def transition_state(
    agent_id: int,
    new_state: str = Query(..., description="New lifecycle state"),
    db: Session = Depends(get_db),
):
    """Transition agent to a new lifecycle state."""
    valid_states = ["dormant", "at_risk", "contacted", "engaged", "trained", "active"]
    if new_state not in valid_states:
        raise HTTPException(status_code=400, detail=f"Invalid state. Must be one of: {valid_states}")

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    old_state = agent.lifecycle_state
    agent.lifecycle_state = new_state
    agent.updated_at = datetime.utcnow()

    if new_state == "contacted":
        agent.last_contact_date = datetime.utcnow().date()

    db.commit()
    db.refresh(agent)

    return {
        "agent_id": agent_id,
        "old_state": old_state,
        "new_state": new_state,
        "name": agent.name,
    }


@router.post("/bulk-import")
def bulk_import_agents(data: AgentBulkImport, db: Session = Depends(get_db)):
    """Bulk import agents."""
    created = []
    errors = []

    for i, agent_data in enumerate(data.agents):
        try:
            existing = db.query(Agent).filter(Agent.phone == agent_data.phone).first()
            if existing:
                errors.append({"index": i, "phone": agent_data.phone, "error": "Duplicate phone"})
                continue

            agent = Agent(**agent_data.model_dump())
            db.add(agent)
            db.flush()
            created.append({"index": i, "id": agent.id, "name": agent.name})
        except Exception as e:
            errors.append({"index": i, "error": str(e)})

    db.commit()

    return {
        "total_submitted": len(data.agents),
        "created": len(created),
        "errors_count": len(errors),
        "created_agents": created,
        "errors": errors,
    }
