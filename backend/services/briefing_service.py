"""
Briefing service to generate daily morning briefings for each ADM.
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from models import Agent, ADM, Interaction, DiaryEntry, DailyBriefing, Feedback

logger = logging.getLogger(__name__)


def generate_daily_briefing(db: Session, adm_id: int, target_date: Optional[date] = None) -> dict:
    """
    Generate a daily briefing for an ADM.

    Includes:
    - Priority agents requiring attention
    - Pending and overdue follow-ups
    - New assignments
    - Today's diary schedule
    - Summary of recent feedback trends
    """
    today = target_date or date.today()
    yesterday = today - timedelta(days=1)

    # Validate ADM exists
    adm = db.query(ADM).filter(ADM.id == adm_id).first()
    if not adm:
        raise ValueError(f"ADM with id {adm_id} not found")

    # ---- Priority Agents ----
    # Agents with overdue follow-ups or high engagement drop
    priority_agents = []

    # Overdue follow-up agents
    overdue_interactions = db.query(Interaction).filter(
        Interaction.adm_id == adm_id,
        Interaction.follow_up_date < today,
        Interaction.follow_up_status == "pending",
    ).all()

    overdue_agent_ids = set()
    for interaction in overdue_interactions:
        if interaction.agent_id not in overdue_agent_ids:
            agent = db.query(Agent).filter(Agent.id == interaction.agent_id).first()
            if agent:
                priority_agents.append({
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "reason": "Overdue follow-up",
                    "details": f"Follow-up was due on {interaction.follow_up_date}",
                    "priority": "high",
                })
                overdue_agent_ids.add(agent.id)

    # Dormant agents assigned but never contacted
    uncontacted = db.query(Agent).filter(
        Agent.assigned_adm_id == adm_id,
        Agent.lifecycle_state == "dormant",
        Agent.last_contact_date.is_(None),
    ).limit(5).all()

    for agent in uncontacted:
        if agent.id not in overdue_agent_ids:
            priority_agents.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "reason": "Never contacted",
                "details": f"Dormant for {agent.dormancy_duration_days} days, assigned but not yet contacted",
                "priority": "medium",
            })

    # Critical feedback agents
    critical_feedbacks = db.query(Feedback).filter(
        Feedback.adm_id == adm_id,
        Feedback.priority.in_(["high", "critical"]),
        Feedback.status.in_(["new", "in_review"]),
    ).all()

    for fb in critical_feedbacks:
        agent = db.query(Agent).filter(Agent.id == fb.agent_id).first()
        if agent and agent.id not in overdue_agent_ids:
            priority_agents.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "reason": f"Critical feedback: {fb.category}",
                "details": fb.raw_text[:100] if fb.raw_text else "No details",
                "priority": fb.priority,
            })

    # ---- Pending & Overdue Follow-ups ----
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

    # ---- New Assignments (agents assigned since yesterday) ----
    new_assignments = db.query(func.count(Agent.id)).filter(
        Agent.assigned_adm_id == adm_id,
        Agent.lifecycle_state == "dormant",
        Agent.last_contact_date.is_(None),
    ).scalar() or 0

    # ---- Today's Schedule ----
    todays_diary = db.query(DiaryEntry).filter(
        DiaryEntry.adm_id == adm_id,
        DiaryEntry.scheduled_date == today,
        DiaryEntry.status == "scheduled",
    ).all()

    schedule_items = []
    for entry in todays_diary:
        agent_name = "N/A"
        if entry.agent_id:
            agent = db.query(Agent).filter(Agent.id == entry.agent_id).first()
            agent_name = agent.name if agent else "Unknown"

        schedule_items.append({
            "time": entry.scheduled_time or "Anytime",
            "type": entry.entry_type,
            "agent_name": agent_name,
            "notes": entry.notes or "",
        })

    # ---- Portfolio Summary ----
    agent_states = db.query(
        Agent.lifecycle_state,
        func.count(Agent.id),
    ).filter(
        Agent.assigned_adm_id == adm_id,
    ).group_by(Agent.lifecycle_state).all()

    portfolio = {state: count for state, count in agent_states}
    total_agents = sum(portfolio.values())

    # ---- Summary Text ----
    summary_parts = [f"Good morning, {adm.name}! Here's your daily briefing for {today.strftime('%B %d, %Y')}."]
    summary_parts.append(f"\nYou are managing {total_agents} agents across your portfolio.")

    if overdue_followups > 0:
        summary_parts.append(f"\n** ATTENTION: You have {overdue_followups} OVERDUE follow-ups that need immediate action.")

    if pending_followups > 0:
        summary_parts.append(f"\nYou have {pending_followups} pending follow-ups scheduled.")

    if new_assignments > 0:
        summary_parts.append(f"\n{new_assignments} new dormant agents have been assigned to you and need first contact.")

    if len(schedule_items) > 0:
        summary_parts.append(f"\nYou have {len(schedule_items)} scheduled activities for today.")

    if priority_agents:
        summary_parts.append(f"\n{len(priority_agents)} agents require priority attention today.")

    # Agent state breakdown
    if portfolio:
        summary_parts.append("\nPortfolio breakdown:")
        for state in ["dormant", "at_risk", "contacted", "engaged", "trained", "active"]:
            count = portfolio.get(state, 0)
            if count > 0:
                summary_parts.append(f"  - {state.replace('_', ' ').title()}: {count}")

    summary_text = "\n".join(summary_parts)

    # ---- Action Items ----
    action_items = []
    if overdue_followups > 0:
        action_items.append(f"Clear {overdue_followups} overdue follow-ups")
    if new_assignments > 0:
        action_items.append(f"Make first contact with {min(new_assignments, 5)} new dormant agents")
    if len(priority_agents) > 0:
        action_items.append(f"Address {len(priority_agents)} priority agent cases")
    for item in schedule_items[:3]:
        action_items.append(f"{item['type'].replace('_', ' ').title()}: {item['agent_name']} at {item['time']}")

    # ---- Save Briefing ----
    # Check if briefing already exists for this date
    existing = db.query(DailyBriefing).filter(
        DailyBriefing.adm_id == adm_id,
        DailyBriefing.date == today,
    ).first()

    if existing:
        existing.priority_agents = json.dumps(priority_agents)
        existing.pending_followups = pending_followups
        existing.new_assignments = new_assignments
        existing.overdue_followups = overdue_followups
        existing.summary_text = summary_text
        existing.action_items = json.dumps(action_items)
        briefing = existing
    else:
        briefing = DailyBriefing(
            adm_id=adm_id,
            date=today,
            priority_agents=json.dumps(priority_agents),
            pending_followups=pending_followups,
            new_assignments=new_assignments,
            overdue_followups=overdue_followups,
            summary_text=summary_text,
            action_items=json.dumps(action_items),
            sent_via="in_app",
        )
        db.add(briefing)

    db.commit()
    db.refresh(briefing)

    return {
        "id": briefing.id,
        "adm_id": adm_id,
        "adm_name": adm.name,
        "date": today.isoformat(),
        "summary_text": summary_text,
        "priority_agents": priority_agents,
        "pending_followups": pending_followups,
        "overdue_followups": overdue_followups,
        "new_assignments": new_assignments,
        "action_items": action_items,
        "schedule": schedule_items,
        "portfolio": portfolio,
    }
