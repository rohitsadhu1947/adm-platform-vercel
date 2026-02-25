"""
Daily briefing generation and retrieval routes.
"""

from datetime import date as date_type
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from database import get_db
from models import DailyBriefing, ADM
from schemas import DailyBriefingResponse
from services.briefing_service import generate_daily_briefing

router = APIRouter(prefix="/briefings", tags=["Briefings"])


@router.post("/generate/{adm_id}")
def generate_briefing(
    adm_id: int,
    target_date: Optional[date_type] = Query(None, description="Date for briefing (default: today)"),
    db: Session = Depends(get_db),
):
    """Generate a daily briefing for an ADM."""
    try:
        result = generate_daily_briefing(db, adm_id, target_date)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating briefing: {str(e)}")


@router.get("/{adm_id}")
def get_briefing(
    adm_id: int,
    target_date: Optional[date_type] = Query(None),
    db: Session = Depends(get_db),
):
    """Get a briefing for an ADM. If none exists, generate one."""
    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    today = target_date or date_type.today()

    briefing = db.query(DailyBriefing).filter(
        DailyBriefing.adm_id == adm_id,
        DailyBriefing.date == today,
    ).first()

    if not briefing:
        # Auto-generate
        try:
            return generate_daily_briefing(db, adm_id, today)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    import json
    return {
        "id": briefing.id,
        "adm_id": adm_id,
        "adm_name": adm.name,
        "date": briefing.date.isoformat(),
        "summary_text": briefing.summary_text,
        "priority_agents": json.loads(briefing.priority_agents) if briefing.priority_agents else [],
        "pending_followups": briefing.pending_followups,
        "overdue_followups": briefing.overdue_followups,
        "new_assignments": briefing.new_assignments,
        "action_items": json.loads(briefing.action_items) if briefing.action_items else [],
        "sent_via": briefing.sent_via,
        "created_at": briefing.created_at.isoformat() if briefing.created_at else None,
    }


@router.get("/history/{adm_id}")
def briefing_history(
    adm_id: int,
    limit: int = Query(7, ge=1, le=30),
    db: Session = Depends(get_db),
):
    """Get recent briefing history for an ADM."""
    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    briefings = (
        db.query(DailyBriefing)
        .filter(DailyBriefing.adm_id == adm_id)
        .order_by(DailyBriefing.date.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": b.id,
            "date": b.date.isoformat(),
            "pending_followups": b.pending_followups,
            "new_assignments": b.new_assignments,
            "overdue_followups": b.overdue_followups,
            "sent_via": b.sent_via,
        }
        for b in briefings
    ]
