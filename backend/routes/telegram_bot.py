"""
Telegram Bot-facing API routes.

These endpoints are designed for the Telegram bot's api_client.py.
They accept telegram_id (the Telegram user ID) instead of the internal DB adm_id,
and return data in the exact format the bot handlers expect.
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func

import hashlib

from database import get_db
from models import ADM, Agent, User, Interaction, Feedback, DiaryEntry, DailyBriefing, TrainingProgress
from services.ai_service import ai_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Telegram Bot"])


# =====================================================================
# POST /telegram/webhook  -  Telegram webhook endpoint (Vercel)
# =====================================================================

@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    """Process incoming Telegram webhook update.

    Telegram sends a JSON Update object to this endpoint whenever
    a user sends a message or interacts with the bot.
    """
    import sys
    import os

    # Ensure bot directory is on path
    bot_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "bot",
    )
    bot_dir = os.path.abspath(bot_dir)
    if bot_dir not in sys.path:
        sys.path.insert(0, bot_dir)

    try:
        json_data = await request.json()

        from database import SessionLocal
        from app_builder import get_application
        from telegram import Update

        application = await get_application(SessionLocal)
        update = Update.de_json(json_data, application.bot)

        await application.process_update(update)

        return {"ok": True}
    except Exception as e:
        logger.error("Webhook processing error: %s", e, exc_info=True)
        # Return 200 even on error to prevent Telegram from retrying
        return {"ok": False, "error": str(e)}


# =====================================================================
# Helper: resolve ADM from telegram_id
# =====================================================================

def _get_adm_by_telegram_id(db: Session, telegram_id: int) -> Optional[ADM]:
    """Find an ADM by their Telegram chat ID."""
    return db.query(ADM).filter(ADM.telegram_chat_id == str(telegram_id)).first()


def _lifecycle_to_bot_status(lifecycle_state: str) -> str:
    """Map backend lifecycle_state to bot-friendly status."""
    mapping = {
        "dormant": "inactive",
        "at_risk": "at_risk",
        "contacted": "active",
        "engaged": "active",
        "trained": "active",
        "active": "active",
    }
    return mapping.get(lifecycle_state, "inactive")


def _agent_to_bot_dict(agent: Agent) -> dict:
    """Convert an Agent model to the dict format the bot expects."""
    # Determine last_active string
    if agent.last_contact_date:
        days_ago = (date.today() - agent.last_contact_date).days
        if days_ago == 0:
            last_active = "Today"
        elif days_ago == 1:
            last_active = "Yesterday"
        else:
            last_active = f"{days_ago} days ago"
    else:
        last_active = f"{agent.dormancy_duration_days} days ago" if agent.dormancy_duration_days else "Never"

    return {
        "id": str(agent.id),
        "agent_code": f"AGT{agent.id:03d}",
        "name": agent.name,
        "phone": agent.phone,
        "status": _lifecycle_to_bot_status(agent.lifecycle_state),
        "lifecycle_state": agent.lifecycle_state,
        "last_active": last_active,
        "location": agent.location,
        "engagement_score": agent.engagement_score,
        "dormancy_reason": agent.dormancy_reason,
    }


# =====================================================================
# POST /adm/register  -  Register ADM from Telegram
# =====================================================================

@router.post("/adm/register")
def register_adm_from_telegram(data: dict, db: Session = Depends(get_db)):
    """Register a new ADM via Telegram bot."""
    telegram_id = data.get("telegram_id")
    name = data.get("name", "")
    employee_id = data.get("employee_id", "")
    region = data.get("region", "")

    if not telegram_id or not name:
        raise HTTPException(status_code=400, detail="telegram_id and name are required")

    # Check if already registered
    existing = db.query(ADM).filter(ADM.telegram_chat_id == str(telegram_id)).first()
    if existing:
        return {
            "id": existing.id,
            "name": existing.name,
            "region": existing.region,
            "telegram_chat_id": existing.telegram_chat_id,
            "message": "Already registered",
        }

    # Create new ADM
    # Use employee_id as a pseudo phone to satisfy the unique constraint
    phone = f"TG-{telegram_id}"

    # Check phone uniqueness
    phone_exists = db.query(ADM).filter(ADM.phone == phone).first()
    if phone_exists:
        # Update existing record with telegram_id
        phone_exists.telegram_chat_id = str(telegram_id)
        phone_exists.name = name
        phone_exists.region = region
        db.commit()
        db.refresh(phone_exists)
        return {
            "id": phone_exists.id,
            "name": phone_exists.name,
            "region": phone_exists.region,
            "telegram_chat_id": phone_exists.telegram_chat_id,
            "message": "Registration updated",
        }

    adm = ADM(
        name=name,
        phone=phone,
        region=region,
        telegram_chat_id=str(telegram_id),
        language="Hindi,English",
        max_capacity=50,
        performance_score=0.0,
    )
    db.add(adm)
    db.flush()  # Get adm.id before creating User

    # Also create a web User login so ADM can access the web dashboard
    # Username = employee_id (lowercase), Password = employee_id (can change later)
    username = employee_id.lower() if employee_id else f"adm{telegram_id}"
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if not existing_user:
        password_hash = hashlib.sha256(employee_id.encode() if employee_id else str(telegram_id).encode()).hexdigest()
        web_user = User(
            username=username,
            password_hash=password_hash,
            role="adm",
            name=name,
            adm_id=adm.id,
        )
        db.add(web_user)
        logger.info(f"Created web login for ADM: username={username}")

    db.commit()
    db.refresh(adm)

    # Auto-assign unassigned agents to this new ADM
    unassigned_agents = db.query(Agent).filter(
        Agent.assigned_adm_id.is_(None)
    ).limit(10).all()

    for agent in unassigned_agents:
        agent.assigned_adm_id = adm.id
    db.commit()

    return {
        "id": adm.id,
        "name": adm.name,
        "region": adm.region,
        "telegram_chat_id": adm.telegram_chat_id,
        "web_username": username,
        "message": "Registration successful. You can also login to the web dashboard.",
    }


# =====================================================================
# GET /adm/profile/{telegram_id}  -  Get ADM profile by Telegram ID
# =====================================================================

@router.get("/adm/profile/{telegram_id}")
def get_adm_profile(telegram_id: int, db: Session = Depends(get_db)):
    """Get ADM profile by Telegram user ID."""
    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    # Count agents
    total_agents = db.query(func.count(Agent.id)).filter(
        Agent.assigned_adm_id == adm.id
    ).scalar() or 0

    return {
        "id": adm.id,
        "name": adm.name,
        "phone": adm.phone,
        "region": adm.region,
        "language": adm.language,
        "telegram_chat_id": adm.telegram_chat_id,
        "total_agents": total_agents,
        "performance_score": adm.performance_score,
        "created_at": adm.created_at.isoformat() if adm.created_at else None,
    }


# =====================================================================
# GET /adm/{telegram_id}/agents  -  Get assigned agents
# =====================================================================

@router.get("/adm/{telegram_id}/agents")
def get_adm_agents_by_telegram(
    telegram_id: int,
    page: int = Query(1, ge=1),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get agents assigned to this ADM (by telegram_id)."""
    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    per_page = 8
    query = db.query(Agent).filter(Agent.assigned_adm_id == adm.id)

    if search:
        query = query.filter(
            (Agent.name.ilike(f"%{search}%")) |
            (Agent.phone.ilike(f"%{search}%"))
        )

    total = query.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    offset = (page - 1) * per_page

    agents = query.order_by(Agent.engagement_score.desc()).offset(offset).limit(per_page).all()

    return {
        "agents": [_agent_to_bot_dict(a) for a in agents],
        "page": page,
        "total_pages": total_pages,
        "total": total,
    }


# =====================================================================
# GET /adm/{telegram_id}/agents/priority  -  Priority agents
# =====================================================================

@router.get("/adm/{telegram_id}/agents/priority")
def get_priority_agents(
    telegram_id: int,
    limit: int = Query(5, ge=1, le=10),
    db: Session = Depends(get_db),
):
    """Get priority agents needing attention today."""
    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    today = date.today()
    priority_agents = []

    # 1. Agents with overdue follow-ups
    overdue_interactions = db.query(Interaction).filter(
        Interaction.adm_id == adm.id,
        Interaction.follow_up_date < today,
        Interaction.follow_up_status == "pending",
    ).all()

    seen_ids = set()
    for ix in overdue_interactions:
        if ix.agent_id not in seen_ids:
            agent = db.query(Agent).filter(Agent.id == ix.agent_id).first()
            if agent:
                priority_agents.append({
                    "name": agent.name,
                    "phone": agent.phone,
                    "reason": f"Overdue follow-up (due {ix.follow_up_date})",
                    "agent_code": f"AGT{agent.id:03d}",
                })
                seen_ids.add(ix.agent_id)

    # 2. Dormant agents never contacted
    if len(priority_agents) < limit:
        dormant = db.query(Agent).filter(
            Agent.assigned_adm_id == adm.id,
            Agent.lifecycle_state == "dormant",
            Agent.last_contact_date.is_(None),
        ).limit(limit - len(priority_agents)).all()

        for agent in dormant:
            if agent.id not in seen_ids:
                priority_agents.append({
                    "name": agent.name,
                    "phone": agent.phone,
                    "reason": f"Dormant {agent.dormancy_duration_days} days - never contacted",
                    "agent_code": f"AGT{agent.id:03d}",
                })
                seen_ids.add(agent.id)

    # 3. At-risk agents
    if len(priority_agents) < limit:
        at_risk = db.query(Agent).filter(
            Agent.assigned_adm_id == adm.id,
            Agent.lifecycle_state == "at_risk",
        ).limit(limit - len(priority_agents)).all()

        for agent in at_risk:
            if agent.id not in seen_ids:
                priority_agents.append({
                    "name": agent.name,
                    "phone": agent.phone,
                    "reason": f"At risk - {agent.dormancy_reason or 'needs attention'}",
                    "agent_code": f"AGT{agent.id:03d}",
                })
                seen_ids.add(agent.id)

    return {"agents": priority_agents[:limit]}


# =====================================================================
# GET /adm/{telegram_id}/briefing  -  Morning briefing
# =====================================================================

@router.get("/adm/{telegram_id}/briefing")
def get_adm_briefing(telegram_id: int, db: Session = Depends(get_db)):
    """Get morning briefing for an ADM by telegram_id."""
    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    today = date.today()

    # Priority agents
    priority_agents = []
    agents = db.query(Agent).filter(Agent.assigned_adm_id == adm.id).all()

    for agent in agents:
        status = _lifecycle_to_bot_status(agent.lifecycle_state)
        reason = ""
        if agent.lifecycle_state == "dormant":
            days = agent.dormancy_duration_days or 0
            sub_reason = (agent.dormancy_reason or "").split(":")[-1].strip() if agent.dormancy_reason else "No recent activity"
            reason = f"\U0001F534 Dormant {days} days - {sub_reason}"
        elif agent.lifecycle_state == "at_risk":
            sub_reason = (agent.dormancy_reason or "").split(":")[-1].strip() if agent.dormancy_reason else "Needs attention"
            reason = f"\U0001F7E1 At Risk - {sub_reason}"
        elif agent.lifecycle_state in ("contacted", "engaged"):
            reason = f"\U0001F7E2 {agent.lifecycle_state.title()} - Active engagement"
        elif agent.lifecycle_state == "active":
            reason = f"\U0001F7E2 Active - Keep supporting"
        else:
            reason = f"Status: {agent.lifecycle_state}"

        priority_agents.append({
            "name": agent.name,
            "agent_code": f"AGT{agent.id:03d}",
            "reason": reason,
            "status": status,
        })

    # Sort: inactive first, then at_risk, then active
    status_order = {"inactive": 0, "at_risk": 1, "active": 2}
    priority_agents.sort(key=lambda a: status_order.get(a["status"], 3))
    priority_agents = priority_agents[:5]

    # Overdue follow-ups
    overdue_interactions = db.query(Interaction).filter(
        Interaction.adm_id == adm.id,
        Interaction.follow_up_date < today,
        Interaction.follow_up_status == "pending",
    ).all()

    overdue_followups = []
    for ix in overdue_interactions:
        agent = db.query(Agent).filter(Agent.id == ix.agent_id).first()
        overdue_followups.append({
            "agent_name": agent.name if agent else "Unknown",
            "due_date": ix.follow_up_date.strftime("%d %b %Y") if ix.follow_up_date else "N/A",
        })

    # New assignments (dormant agents never contacted)
    new_assignments_q = db.query(Agent).filter(
        Agent.assigned_adm_id == adm.id,
        Agent.lifecycle_state == "dormant",
        Agent.last_contact_date.is_(None),
    ).limit(5).all()

    new_assignments = [
        {"name": a.name, "agent_code": f"AGT{a.id:03d}"}
        for a in new_assignments_q
    ]

    # Yesterday's stats
    yesterday = today - timedelta(days=1)
    yesterday_start = datetime.combine(yesterday, datetime.min.time())
    yesterday_end = datetime.combine(today, datetime.min.time())

    calls_yesterday = db.query(func.count(Interaction.id)).filter(
        Interaction.adm_id == adm.id,
        Interaction.created_at >= yesterday_start,
        Interaction.created_at < yesterday_end,
    ).scalar() or 0

    feedbacks_yesterday = db.query(func.count(Feedback.id)).filter(
        Feedback.adm_id == adm.id,
        Feedback.created_at >= yesterday_start,
        Feedback.created_at < yesterday_end,
    ).scalar() or 0

    # Training tip (rotate daily)
    tips = [
        "\U0001F6E1\uFE0F Smart Term Plan starts at just Rs 595/month for Rs 1 Crore cover - sabse affordable protection!",
        "\U0001F4A1 Customer ko pehle unki need samjhao, phir product pitch karo. Need-based selling works best!",
        "\u2B50 ULIP mein 5 saal ka lock-in hota hai - customer ko yeh clearly batayein upfront.",
        "\U0001F4B0 Commission structure samajhna zaroori hai - renewal commission long-term income deti hai!",
        "\U0001F525 Pension plans ka best selling point: Tax-free income after retirement under Section 10(10A).",
        "\U0001F9E0 Objection handling tip: 'Sochna padega' ka matlab hai customer ko aur information chahiye.",
        "\u2764\uFE0F Child plan pitch karte waqt, bachche ki photo ya naam puchho - emotional connect banao!",
        "\U0001F3AF Dormant agents ko re-activate karna hai? Pehle unki problem suno, phir solution do.",
        "\U0001F680 Digital tools use karo! Online proposal submission se customer experience 10x better hota hai.",
        "\U0001F44F Har din 10 calls ka target rakho - consistency is the key to success!",
    ]
    day_of_year = today.timetuple().tm_yday
    training_tip = tips[day_of_year % len(tips)]

    return {
        "adm_name": adm.name,
        "priority_agents": priority_agents,
        "overdue_followups": overdue_followups,
        "new_assignments": new_assignments,
        "yesterday_stats": {
            "calls": calls_yesterday,
            "feedbacks": feedbacks_yesterday,
            "activations": 0,
        },
        "training_tip": training_tip,
    }


# =====================================================================
# GET /adm/{telegram_id}/stats  -  Performance stats
# =====================================================================

@router.get("/adm/{telegram_id}/stats")
def get_adm_stats(telegram_id: int, db: Session = Depends(get_db)):
    """Get performance stats for an ADM by telegram_id."""
    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    today = date.today()

    # Agent portfolio
    agents = db.query(Agent).filter(Agent.assigned_adm_id == adm.id).all()
    total_agents = len(agents)
    active_agents = sum(1 for a in agents if a.lifecycle_state in ("active", "engaged", "trained", "contacted"))
    at_risk_agents = sum(1 for a in agents if a.lifecycle_state == "at_risk")
    inactive_agents = sum(1 for a in agents if a.lifecycle_state == "dormant")

    # Total interactions this month
    month_start = today.replace(day=1)
    total_calls = db.query(func.count(Interaction.id)).filter(
        Interaction.adm_id == adm.id,
        Interaction.created_at >= datetime.combine(month_start, datetime.min.time()),
    ).scalar() or 0

    total_feedbacks = db.query(func.count(Feedback.id)).filter(
        Feedback.adm_id == adm.id,
        Feedback.created_at >= datetime.combine(month_start, datetime.min.time()),
    ).scalar() or 0

    # Activations (agents that became active this month)
    total_activations = sum(
        1 for a in agents
        if a.lifecycle_state == "active" and a.last_policy_sold_date and a.last_policy_sold_date >= month_start
    )

    activation_rate = round((active_agents / total_agents * 100), 1) if total_agents > 0 else 0.0

    # Weekly stats
    week_start = today - timedelta(days=today.weekday())
    w_calls = db.query(func.count(Interaction.id)).filter(
        Interaction.adm_id == adm.id,
        Interaction.created_at >= datetime.combine(week_start, datetime.min.time()),
    ).scalar() or 0

    w_feedbacks = db.query(func.count(Feedback.id)).filter(
        Feedback.adm_id == adm.id,
        Feedback.created_at >= datetime.combine(week_start, datetime.min.time()),
    ).scalar() or 0

    # Pending follow-ups
    pending_fu = db.query(func.count(Interaction.id)).filter(
        Interaction.adm_id == adm.id,
        Interaction.follow_up_status == "pending",
        Interaction.follow_up_date >= today,
    ).scalar() or 0

    overdue_fu = db.query(func.count(Interaction.id)).filter(
        Interaction.adm_id == adm.id,
        Interaction.follow_up_status == "pending",
        Interaction.follow_up_date < today,
    ).scalar() or 0

    # Training
    training_records = db.query(TrainingProgress).filter(
        TrainingProgress.adm_id == adm.id,
    ).all()
    modules_completed = sum(1 for t in training_records if t.completed)
    modules_total = 12  # total modules available
    quiz_avg = round(sum(t.score for t in training_records) / len(training_records), 0) if training_records else 0
    last_training = training_records[-1].module_name if training_records else "N/A"

    return {
        "adm_name": adm.name,
        "period": today.strftime("%B %Y"),
        "total_agents": total_agents,
        "active_agents": active_agents,
        "at_risk_agents": at_risk_agents,
        "inactive_agents": inactive_agents,
        "total_calls": total_calls,
        "total_feedbacks": total_feedbacks,
        "total_activations": total_activations,
        "activation_rate": activation_rate,
        "weekly": {
            "calls": w_calls,
            "calls_target": 50,
            "feedbacks": w_feedbacks,
            "feedbacks_target": 25,
            "follow_ups_completed": 0,
            "follow_ups_total": pending_fu + overdue_fu,
        },
        "training": {
            "modules_completed": modules_completed,
            "modules_total": modules_total,
            "quiz_avg_score": quiz_avg,
            "last_training": last_training,
        },
        "pending_follow_ups": pending_fu,
        "overdue_follow_ups": overdue_fu,
        "daily_streak": 5,
        "best_streak": 12,
    }


# =====================================================================
# GET /adm/{telegram_id}/diary  -  Diary entries
# =====================================================================

@router.get("/adm/{telegram_id}/diary")
def get_adm_diary(
    telegram_id: int,
    date_param: Optional[str] = Query(None, alias="date"),
    db: Session = Depends(get_db),
):
    """Get diary entries for an ADM by telegram_id."""
    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    today = date.today()
    target_date = today

    if date_param:
        try:
            target_date = date.fromisoformat(date_param)
        except ValueError:
            pass

    # Get entries for the target date, plus overdue from past
    entries_query = db.query(DiaryEntry).filter(
        DiaryEntry.adm_id == adm.id,
    )

    # Get overdue (past dates, not completed)
    overdue_entries = entries_query.filter(
        DiaryEntry.scheduled_date < target_date,
        DiaryEntry.status.in_(["scheduled", "missed", "rescheduled"]),
    ).order_by(DiaryEntry.scheduled_date).all()

    # Today's entries (all statuses except completed shown)
    today_entries = entries_query.filter(
        DiaryEntry.scheduled_date == target_date,
    ).order_by(DiaryEntry.scheduled_time).all()

    # Upcoming (next 7 days) — include both scheduled and rescheduled
    upcoming_entries = entries_query.filter(
        DiaryEntry.scheduled_date > target_date,
        DiaryEntry.scheduled_date <= target_date + timedelta(days=7),
        DiaryEntry.status.in_(["scheduled", "rescheduled"]),
    ).order_by(DiaryEntry.scheduled_date, DiaryEntry.scheduled_time).all()

    result_entries = []

    for entry in overdue_entries:
        agent_name = ""
        if entry.agent_id:
            agent = db.query(Agent).filter(Agent.id == entry.agent_id).first()
            agent_name = agent.name if agent else ""

        result_entries.append({
            "id": str(entry.id),
            "title": entry.notes or f"{entry.entry_type.replace('_', ' ').title()}",
            "time": entry.scheduled_time or "",
            "priority": "overdue",
            "completed": entry.status == "completed",
            "agent_name": agent_name,
            "date": entry.scheduled_date.isoformat(),
        })

    for entry in today_entries:
        agent_name = ""
        if entry.agent_id:
            agent = db.query(Agent).filter(Agent.id == entry.agent_id).first()
            agent_name = agent.name if agent else ""

        result_entries.append({
            "id": str(entry.id),
            "title": entry.notes or f"{entry.entry_type.replace('_', ' ').title()}",
            "time": entry.scheduled_time or "",
            "priority": "today",
            "completed": entry.status == "completed",
            "agent_name": agent_name,
            "date": entry.scheduled_date.isoformat(),
        })

    for entry in upcoming_entries:
        agent_name = ""
        if entry.agent_id:
            agent = db.query(Agent).filter(Agent.id == entry.agent_id).first()
            agent_name = agent.name if agent else ""

        result_entries.append({
            "id": str(entry.id),
            "title": entry.notes or f"{entry.entry_type.replace('_', ' ').title()}",
            "time": entry.scheduled_time or "",
            "priority": "upcoming",
            "completed": entry.status == "completed",
            "agent_name": agent_name,
            "date": entry.scheduled_date.isoformat(),
        })

    return {"entries": result_entries}


# =====================================================================
# POST /diary  -  Add diary entry (telegram-friendly)
# =====================================================================

@router.post("/diary/telegram")
def add_diary_entry_telegram(data: dict, db: Session = Depends(get_db)):
    """Add a diary entry from Telegram bot."""
    telegram_id = data.get("adm_telegram_id")
    title = data.get("title", "")
    date_str = data.get("date")
    time_str = data.get("time")  # HH:MM format (e.g., "09:00", "15:00")
    priority = data.get("priority", "today")

    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    sched_date = date.today()
    if date_str:
        try:
            sched_date = date.fromisoformat(date_str)
        except ValueError:
            pass

    entry = DiaryEntry(
        adm_id=adm.id,
        scheduled_date=sched_date,
        scheduled_time=time_str,  # Now properly saved (HH:MM or None)
        entry_type="follow_up",
        notes=title,
        status="scheduled",
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)

    return {
        "id": entry.id,
        "title": title,
        "date": sched_date.isoformat(),
        "time": time_str,
        "status": "scheduled",
    }


# =====================================================================
# PUT /diary/{entry_id}  -  Update diary entry (telegram-friendly)
# =====================================================================

@router.put("/diary/{entry_id}/telegram")
def update_diary_entry_telegram(entry_id: str, data: dict, db: Session = Depends(get_db)):
    """Update a diary entry from Telegram bot."""
    try:
        eid = int(entry_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid entry ID")

    entry = db.query(DiaryEntry).filter(DiaryEntry.id == eid).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Diary entry not found")

    if data.get("completed"):
        entry.status = "completed"

    if data.get("date"):
        try:
            entry.scheduled_date = date.fromisoformat(data["date"])
            # Keep status as "scheduled" so it shows up in diary queries
            # "rescheduled" status gets excluded from upcoming entries
            entry.status = "scheduled"
        except ValueError:
            pass

    db.commit()
    db.refresh(entry)
    return {"id": entry.id, "status": entry.status}


# =====================================================================
# POST /feedback  -  Submit feedback (telegram-friendly)
# =====================================================================

@router.post("/feedback/telegram")
def submit_feedback_telegram(data: dict, db: Session = Depends(get_db)):
    """Submit feedback from Telegram bot."""
    telegram_id = data.get("adm_telegram_id")
    agent_id_str = data.get("agent_id", "")
    contact_type = data.get("contact_type", "call")
    outcome = data.get("outcome", "connected")
    category = data.get("category", "support_issues")
    subcategory = data.get("subcategory", "")
    notes = data.get("notes", "")
    followup_date_str = data.get("followup_date")

    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    # Resolve agent_id
    try:
        agent_id = int(agent_id_str)
    except (ValueError, TypeError):
        agent_id = None

    if not agent_id:
        # Try to find by agent code
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Create interaction
    type_map = {"Call": "call", "WhatsApp": "whatsapp", "Visit": "visit"}
    outcome_map = {"Connected": "connected", "Not Answered": "not_answered", "Busy": "busy", "Callback Requested": "callback_requested"}

    interaction = Interaction(
        agent_id=agent_id,
        adm_id=adm.id,
        type=type_map.get(contact_type, "call"),
        outcome=outcome_map.get(outcome, "connected"),
        notes=notes,
        feedback_category=category,
        feedback_subcategory=subcategory,
    )

    # Handle follow-up
    if followup_date_str and followup_date_str != "Not set":
        try:
            fu_date = datetime.strptime(followup_date_str, "%d %b %Y").date()
            interaction.follow_up_date = fu_date
            interaction.follow_up_status = "pending"
        except ValueError:
            pass

    db.add(interaction)

    # Also create feedback record if connected with category
    if outcome == "Connected" and category != "N/A":
        feedback = Feedback(
            agent_id=agent_id,
            adm_id=adm.id,
            interaction_id=None,
            category=category,
            subcategory=subcategory,
            raw_text=notes,
            sentiment="neutral",
            priority="medium",
            status="new",
        )
        db.add(feedback)

    # Update agent contact date
    agent.last_contact_date = date.today()
    if agent.lifecycle_state == "dormant":
        agent.lifecycle_state = "contacted"
    agent.engagement_score = min(100, agent.engagement_score + 5)

    db.commit()

    return {
        "id": interaction.id if hasattr(interaction, 'id') else 0,
        "message": "Feedback saved successfully",
    }


# =====================================================================
# POST /interactions  -  Log interaction (telegram-friendly)
# =====================================================================

@router.post("/interactions/telegram")
def log_interaction_telegram(data: dict, db: Session = Depends(get_db)):
    """Log an interaction from Telegram bot."""
    telegram_id = data.get("adm_telegram_id")
    agent_id_str = data.get("agent_id", "")
    topic = data.get("topic", "Other")
    outcome = data.get("outcome", "Neutral")
    notes = data.get("notes", "")
    followup_date_str = data.get("followup_date")

    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    try:
        agent_id = int(agent_id_str)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid agent ID")

    outcome_map = {"Positive": "connected", "Neutral": "callback_requested", "Negative": "declined"}

    interaction = Interaction(
        agent_id=agent_id,
        adm_id=adm.id,
        type="call",
        outcome=outcome_map.get(outcome, "connected"),
        notes=f"[{topic}] {notes}",
    )

    if followup_date_str and followup_date_str != "Not set":
        try:
            fu_date = datetime.strptime(followup_date_str, "%d %b %Y").date()
            interaction.follow_up_date = fu_date
            interaction.follow_up_status = "pending"
        except ValueError:
            pass

    db.add(interaction)

    # Update agent
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if agent:
        agent.last_contact_date = date.today()
        agent.engagement_score = min(100, agent.engagement_score + 3)

    db.commit()

    return {
        "id": interaction.id if hasattr(interaction, 'id') else 0,
        "message": "Interaction logged successfully",
    }


# =====================================================================
# GET /adm/{telegram_id}/feedback/pending  -  Pending feedbacks
# =====================================================================

@router.get("/adm/{telegram_id}/feedback/pending")
def get_pending_feedbacks(telegram_id: int, db: Session = Depends(get_db)):
    """Get pending follow-ups for an ADM."""
    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    today = date.today()
    pending = db.query(Interaction).filter(
        Interaction.adm_id == adm.id,
        Interaction.follow_up_status == "pending",
    ).all()

    results = []
    for ix in pending:
        agent = db.query(Agent).filter(Agent.id == ix.agent_id).first()
        results.append({
            "agent_name": agent.name if agent else "Unknown",
            "due_date": ix.follow_up_date.isoformat() if ix.follow_up_date else None,
            "overdue": ix.follow_up_date < today if ix.follow_up_date else False,
            "notes": ix.notes,
        })

    return {"pending": results, "total": len(results)}


# =====================================================================
# GET /adm/{telegram_id}/interactions  -  Interactions list
# =====================================================================

@router.get("/adm/{telegram_id}/interactions")
def get_adm_interactions(
    telegram_id: int,
    agent_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get interactions for an ADM."""
    adm = _get_adm_by_telegram_id(db, telegram_id)
    if not adm:
        raise HTTPException(status_code=404, detail="ADM not found")

    query = db.query(Interaction).filter(Interaction.adm_id == adm.id)

    if agent_id:
        try:
            query = query.filter(Interaction.agent_id == int(agent_id))
        except ValueError:
            pass

    interactions = query.order_by(Interaction.created_at.desc()).limit(20).all()

    results = []
    for ix in interactions:
        agent = db.query(Agent).filter(Agent.id == ix.agent_id).first()
        results.append({
            "id": ix.id,
            "agent_name": agent.name if agent else "Unknown",
            "type": ix.type,
            "outcome": ix.outcome,
            "notes": ix.notes,
            "date": ix.created_at.isoformat() if ix.created_at else None,
        })

    return {"interactions": results}


# =====================================================================
# Training endpoints for bot
# =====================================================================

@router.get("/training/categories")
def get_training_categories(db: Session = Depends(get_db)):
    """Get training categories from DB products."""
    from models import Product

    category_labels = {
        "term": "Term Insurance",
        "savings": "Savings Plans",
        "ulip": "ULIPs",
        "pension": "Pension Plans",
        "child": "Child Plans",
        "group": "Group Insurance",
        "health": "Health Insurance",
    }

    # Get distinct categories from actual products in DB
    categories_in_db = db.query(Product.category).filter(
        Product.active == True
    ).distinct().all()

    categories = []
    for (cat,) in categories_in_db:
        categories.append({
            "id": cat,
            "name": category_labels.get(cat, cat.title()),
        })

    return {"categories": categories}


@router.get("/training/categories/{category}/products")
def get_training_products(category: str, db: Session = Depends(get_db)):
    """Get products in a training category from DB."""
    from models import Product

    category_labels = {
        "term": "Term Insurance",
        "savings": "Savings Plans",
        "ulip": "ULIPs",
        "pension": "Pension Plans",
        "child": "Child Plans",
        "group": "Group Insurance",
        "health": "Health Insurance",
    }

    products = db.query(Product).filter(
        Product.category == category,
        Product.active == True,
    ).all()

    return {
        "products": [
            {
                "id": str(p.id),
                "name": p.name,
                "category": category_labels.get(p.category, p.category.title()),
            }
            for p in products
        ]
    }


@router.get("/training/products/{product_id}/summary")
def get_product_summary(product_id: str, db: Session = Depends(get_db)):
    """Get product summary from DB for the bot."""
    from models import Product

    try:
        pid = int(product_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Product not found")

    product = db.query(Product).filter(Product.id == pid).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Parse key_features JSON
    key_features = []
    if product.key_features:
        try:
            key_features = json.loads(product.key_features)
        except (json.JSONDecodeError, TypeError):
            key_features = [product.key_features]

    # Build selling tips as USPs
    usps = []
    if product.selling_tips:
        usps = [tip.strip() for tip in product.selling_tips.split(".") if tip.strip()]

    return {
        "name": product.name,
        "category": product.category.title(),
        "description": product.description or "",
        "key_features": key_features,
        "target_audience": product.target_audience or "",
        "usps": usps,
        "premium_range": product.premium_range or "",
        "commission_rate": product.commission_rate or "",
        "common_objections": [],
    }


@router.get("/training/products/{product_id}/quiz")
def get_product_quiz(product_id: str, db: Session = Depends(get_db)):
    """Get quiz for a product. Generates basic quiz from product data."""
    from models import Product

    try:
        pid = int(product_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Product not found")

    product = db.query(Product).filter(Product.id == pid).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Generate basic quiz questions from product data
    questions = [
        {
            "question": f"{product.name} kis category mein aata hai?",
            "options": ["Term Insurance", "Savings Plans", "ULIPs", "Pension Plans"],
            "correct": ["term", "savings", "ulip", "pension", "child", "group", "health"].index(product.category) if product.category in ["term", "savings", "ulip", "pension"] else 0,
        },
        {
            "question": f"{product.name} ka target audience kaun hai?",
            "options": [
                product.target_audience or "Working professionals",
                "Only senior citizens",
                "Only NRIs",
                "Only corporate employees",
            ],
            "correct": 0,
        },
        {
            "question": "Life insurance ka primary purpose kya hai?",
            "options": ["Wealth creation", "Family protection", "Tax saving", "Investment returns"],
            "correct": 1,
        },
    ]

    return {"questions": questions}


@router.post("/training/quiz/submit")
def submit_quiz_telegram(data: dict, db: Session = Depends(get_db)):
    """Submit quiz result from Telegram bot."""
    telegram_id = data.get("adm_telegram_id")
    product_id = data.get("product_id", "")
    score = data.get("score", 0)
    total = data.get("total", 0)

    if telegram_id:
        adm = _get_adm_by_telegram_id(db, telegram_id)
        if adm:
            # Save training progress
            progress = TrainingProgress(
                adm_id=adm.id,
                module_name=product_id,
                module_category="product_knowledge",
                score=round((score / total * 100), 1) if total > 0 else 0,
                completed=score >= (total * 0.7),
                completed_at=datetime.utcnow() if score >= (total * 0.7) else None,
            )
            db.add(progress)
            db.commit()

    return {"message": "Quiz result saved", "score": score, "total": total}


# =====================================================================
# POST /ai/ask  -  AI Product Q&A
# =====================================================================

@router.post("/ai/ask")
async def ask_product_question(data: dict, db: Session = Depends(get_db)):
    """AI-powered product question answering for the bot."""
    question = data.get("question", "")
    telegram_id = data.get("telegram_id")

    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    result = await ai_service.answer_product_question(question)

    return {
        "answer": result.get("answer", ""),
        "related_products": result.get("suggested_products", []),
        "confidence": result.get("confidence", 0.5),
    }
