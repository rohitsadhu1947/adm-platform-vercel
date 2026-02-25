"""
Feedback submission and analytics routes.
"""

from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
from models import Feedback, Agent, ADM
from schemas import FeedbackCreate, FeedbackUpdate, FeedbackResponse, FeedbackAnalytics
from services.ai_service import ai_service

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.get("/", response_model=List[FeedbackResponse])
def list_feedbacks(
    agent_id: Optional[int] = Query(None),
    adm_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    sentiment: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List feedbacks with optional filters."""
    query = db.query(Feedback)

    if agent_id:
        query = query.filter(Feedback.agent_id == agent_id)
    if adm_id:
        query = query.filter(Feedback.adm_id == adm_id)
    if category:
        query = query.filter(Feedback.category == category)
    if priority:
        query = query.filter(Feedback.priority == priority)
    if status:
        query = query.filter(Feedback.status == status)
    if sentiment:
        query = query.filter(Feedback.sentiment == sentiment)

    return query.order_by(Feedback.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/analytics", response_model=FeedbackAnalytics)
def feedback_analytics(
    adm_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """Get feedback analytics and trends."""
    base_query = db.query(Feedback)
    if adm_id:
        base_query = base_query.filter(Feedback.adm_id == adm_id)

    total = base_query.count()

    by_category = dict(
        base_query.with_entities(Feedback.category, func.count(Feedback.id))
        .group_by(Feedback.category).all()
    )

    by_priority = dict(
        base_query.with_entities(Feedback.priority, func.count(Feedback.id))
        .group_by(Feedback.priority).all()
    )

    by_status = dict(
        base_query.with_entities(Feedback.status, func.count(Feedback.id))
        .group_by(Feedback.status).all()
    )

    by_sentiment = dict(
        base_query.with_entities(Feedback.sentiment, func.count(Feedback.id))
        .group_by(Feedback.sentiment).all()
    )

    # Top subcategories
    top_subs = (
        base_query.with_entities(Feedback.subcategory, func.count(Feedback.id).label("cnt"))
        .filter(Feedback.subcategory.isnot(None))
        .group_by(Feedback.subcategory)
        .order_by(func.count(Feedback.id).desc())
        .limit(10)
        .all()
    )
    top_subcategories = [{"subcategory": sub, "count": cnt} for sub, cnt in top_subs]

    # Average resolution time for resolved feedbacks
    resolved = base_query.filter(
        Feedback.status == "resolved",
        Feedback.resolved_at.isnot(None),
    ).all()

    avg_resolution = None
    if resolved:
        total_hours = sum(
            (fb.resolved_at - fb.created_at).total_seconds() / 3600
            for fb in resolved
            if fb.resolved_at and fb.created_at
        )
        avg_resolution = round(total_hours / len(resolved), 1) if resolved else None

    return FeedbackAnalytics(
        total_feedbacks=total,
        by_category=by_category,
        by_priority=by_priority,
        by_status=by_status,
        by_sentiment=by_sentiment,
        top_subcategories=top_subcategories,
        avg_resolution_time_hours=avg_resolution,
    )


@router.get("/top-reasons")
def top_feedback_reasons(
    region: Optional[str] = None,
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get top feedback reasons, optionally by region."""
    query = db.query(
        Feedback.category,
        Feedback.subcategory,
        func.count(Feedback.id).label("count"),
    )

    if region:
        # Join with Agent to filter by location
        query = query.join(Agent, Feedback.agent_id == Agent.id).filter(
            Agent.location.ilike(f"%{region}%")
        )

    results = (
        query.group_by(Feedback.category, Feedback.subcategory)
        .order_by(func.count(Feedback.id).desc())
        .limit(limit)
        .all()
    )

    return [
        {"category": cat, "subcategory": sub, "count": cnt}
        for cat, sub, cnt in results
    ]


@router.get("/by-region")
def feedback_by_region(db: Session = Depends(get_db)):
    """Get feedback counts grouped by agent location."""
    results = (
        db.query(Agent.location, func.count(Feedback.id))
        .join(Agent, Feedback.agent_id == Agent.id)
        .group_by(Agent.location)
        .order_by(func.count(Feedback.id).desc())
        .all()
    )
    return [{"location": loc, "count": cnt} for loc, cnt in results]


@router.get("/{feedback_id}", response_model=FeedbackResponse)
def get_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Get a single feedback."""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    return feedback


@router.post("/", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(data: FeedbackCreate, db: Session = Depends(get_db)):
    """Submit new feedback. AI will automatically analyze if raw_text is provided."""
    # Validate references
    agent = db.query(Agent).filter(Agent.id == data.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    adm = db.query(ADM).filter(ADM.id == data.adm_id).first()
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    feedback = Feedback(**data.model_dump())

    # AI analysis if raw text is provided
    if data.raw_text:
        try:
            agent_context = f"Agent: {agent.name}, Location: {agent.location}, State: {agent.lifecycle_state}"
            analysis = await ai_service.analyze_feedback(data.raw_text, agent_context)

            if not data.category or data.category == "support_issues":
                feedback.category = analysis.get("category", data.category)
            feedback.subcategory = analysis.get("subcategory", data.subcategory)
            feedback.ai_summary = analysis.get("summary", "")
            if not data.sentiment:
                feedback.sentiment = analysis.get("sentiment", "neutral")
            feedback.priority = analysis.get("priority", data.priority)
        except Exception as e:
            # If AI fails, continue with user-provided data
            pass

    # Compute sentiment score if not provided
    if data.raw_text and not feedback.sentiment:
        score = await ai_service.compute_sentiment_score(data.raw_text)
        if score > 0.2:
            feedback.sentiment = "positive"
        elif score < -0.2:
            feedback.sentiment = "negative"
        else:
            feedback.sentiment = "neutral"

    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.put("/{feedback_id}", response_model=FeedbackResponse)
def update_feedback(
    feedback_id: int,
    data: FeedbackUpdate,
    db: Session = Depends(get_db),
):
    """Update feedback status or action taken."""
    feedback = db.query(Feedback).filter(Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(feedback, key, value)

    if data.status == "resolved":
        feedback.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(feedback)
    return feedback
