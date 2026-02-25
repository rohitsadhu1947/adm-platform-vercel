"""
Analytics dashboard endpoints.
Provides KPIs, funnel data, dormancy analysis, regional stats, and performance metrics.
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from database import get_db
from models import Agent, ADM, Interaction, Feedback, DiaryEntry
from schemas import DashboardKPIs, ActivationFunnel, DormancyBreakdown

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardKPIs)
def get_dashboard_kpis(db: Session = Depends(get_db)):
    """
    Get key performance indicators for the analytics dashboard.
    Returns total agents, state counts, activation rate, ADM count,
    interaction stats, and average engagement score.
    """
    from datetime import date as date_type

    # Agent counts by lifecycle state
    state_counts = dict(
        db.query(Agent.lifecycle_state, func.count(Agent.id))
        .group_by(Agent.lifecycle_state)
        .all()
    )

    total_agents = sum(state_counts.values())
    dormant = state_counts.get("dormant", 0)
    at_risk = state_counts.get("at_risk", 0)
    contacted = state_counts.get("contacted", 0)
    engaged = state_counts.get("engaged", 0)
    trained = state_counts.get("trained", 0)
    active = state_counts.get("active", 0)

    activation_rate = round((active / total_agents * 100), 1) if total_agents > 0 else 0.0

    # ADM count
    total_adms = db.query(func.count(ADM.id)).scalar() or 0

    # Interaction stats
    total_interactions = db.query(func.count(Interaction.id)).scalar() or 0

    today = date_type.today()
    pending_followups = db.query(func.count(Interaction.id)).filter(
        Interaction.follow_up_status == "pending",
        Interaction.follow_up_date >= today,
    ).scalar() or 0

    overdue_followups = db.query(func.count(Interaction.id)).filter(
        Interaction.follow_up_status == "pending",
        Interaction.follow_up_date < today,
    ).scalar() or 0

    # Average engagement score
    avg_engagement = db.query(func.avg(Agent.engagement_score)).scalar() or 0.0

    return DashboardKPIs(
        total_agents=total_agents,
        dormant_agents=dormant,
        at_risk_agents=at_risk,
        contacted_agents=contacted,
        engaged_agents=engaged,
        trained_agents=trained,
        active_agents=active,
        activation_rate=activation_rate,
        total_adms=total_adms,
        total_interactions=total_interactions,
        pending_followups=pending_followups,
        overdue_followups=overdue_followups,
        avg_engagement_score=round(float(avg_engagement), 1),
    )


@router.get("/funnel", response_model=ActivationFunnel)
def get_activation_funnel(db: Session = Depends(get_db)):
    """
    Get the activation funnel showing agent counts at each lifecycle stage
    and conversion rates between stages.
    """
    state_counts = dict(
        db.query(Agent.lifecycle_state, func.count(Agent.id))
        .group_by(Agent.lifecycle_state)
        .all()
    )

    dormant = state_counts.get("dormant", 0)
    at_risk = state_counts.get("at_risk", 0)
    contacted = state_counts.get("contacted", 0)
    engaged = state_counts.get("engaged", 0)
    trained = state_counts.get("trained", 0)
    active = state_counts.get("active", 0)

    total = dormant + at_risk + contacted + engaged + trained + active

    # Conversion rates (cumulative from dormant)
    conversion_rates = {}
    if total > 0:
        passed_dormant = contacted + engaged + trained + active
        conversion_rates["dormant_to_contacted"] = round((passed_dormant / (dormant + at_risk + passed_dormant)) * 100, 1) if (dormant + at_risk + passed_dormant) > 0 else 0
        conversion_rates["contacted_to_engaged"] = round(((engaged + trained + active) / passed_dormant) * 100, 1) if passed_dormant > 0 else 0
        conversion_rates["engaged_to_trained"] = round(((trained + active) / (engaged + trained + active)) * 100, 1) if (engaged + trained + active) > 0 else 0
        conversion_rates["trained_to_active"] = round((active / (trained + active)) * 100, 1) if (trained + active) > 0 else 0
        conversion_rates["overall_activation"] = round((active / total) * 100, 1)
    else:
        conversion_rates = {
            "dormant_to_contacted": 0,
            "contacted_to_engaged": 0,
            "engaged_to_trained": 0,
            "trained_to_active": 0,
            "overall_activation": 0,
        }

    return ActivationFunnel(
        dormant=dormant,
        at_risk=at_risk,
        contacted=contacted,
        engaged=engaged,
        trained=trained,
        active=active,
        conversion_rates=conversion_rates,
    )


@router.get("/dormancy-reasons", response_model=DormancyBreakdown)
def get_dormancy_reasons(db: Session = Depends(get_db)):
    """
    Get a breakdown of dormancy reasons with counts,
    grouped by reason category, duration bucket, location, and state.
    """
    # By reason (parse category from "category: subcategory" format)
    dormant_agents = db.query(Agent).filter(
        Agent.lifecycle_state.in_(["dormant", "at_risk"]),
        Agent.dormancy_reason.isnot(None),
    ).all()

    by_reason = {}
    for agent in dormant_agents:
        reason = agent.dormancy_reason
        # Extract category part (before colon)
        category = reason.split(":")[0].strip() if ":" in reason else reason
        by_reason[category] = by_reason.get(category, 0) + 1

    # By duration bucket
    by_duration = {
        "30-90 days": 0,
        "91-180 days": 0,
        "181-365 days": 0,
        "365+ days": 0,
    }
    all_dormant = db.query(Agent).filter(
        Agent.lifecycle_state.in_(["dormant", "at_risk"]),
    ).all()

    for agent in all_dormant:
        d = agent.dormancy_duration_days
        if d <= 90:
            by_duration["30-90 days"] += 1
        elif d <= 180:
            by_duration["91-180 days"] += 1
        elif d <= 365:
            by_duration["181-365 days"] += 1
        else:
            by_duration["365+ days"] += 1

    # By location
    by_location = dict(
        db.query(Agent.location, func.count(Agent.id))
        .filter(Agent.lifecycle_state.in_(["dormant", "at_risk"]))
        .group_by(Agent.location)
        .order_by(func.count(Agent.id).desc())
        .all()
    )

    # By state
    by_state = dict(
        db.query(Agent.state, func.count(Agent.id))
        .filter(
            Agent.lifecycle_state.in_(["dormant", "at_risk"]),
            Agent.state.isnot(None),
        )
        .group_by(Agent.state)
        .order_by(func.count(Agent.id).desc())
        .all()
    )

    return DormancyBreakdown(
        by_reason=by_reason,
        by_duration=by_duration,
        by_location=by_location,
        by_state=by_state,
    )


@router.get("/regional")
def get_regional_analytics(db: Session = Depends(get_db)):
    """
    Get activation metrics grouped by region/city.
    Shows agent distribution, activation rates, and engagement scores per city.
    """
    # Agents by city with state breakdown
    city_data = (
        db.query(
            Agent.location,
            Agent.lifecycle_state,
            func.count(Agent.id).label("count"),
            func.avg(Agent.engagement_score).label("avg_engagement"),
        )
        .group_by(Agent.location, Agent.lifecycle_state)
        .all()
    )

    # Organize by city
    cities = {}
    for location, state, count, avg_eng in city_data:
        if location not in cities:
            cities[location] = {
                "city": location,
                "total": 0,
                "dormant": 0,
                "at_risk": 0,
                "contacted": 0,
                "engaged": 0,
                "trained": 0,
                "active": 0,
                "activation_rate": 0,
                "avg_engagement": 0,
            }
        cities[location][state] = count
        cities[location]["total"] += count

    # Calculate activation rates and aggregate engagement
    for city, data in cities.items():
        total = data["total"]
        active = data.get("active", 0)
        data["activation_rate"] = round((active / total * 100), 1) if total > 0 else 0

        # Get aggregate engagement for this city
        avg = db.query(func.avg(Agent.engagement_score)).filter(
            Agent.location == city
        ).scalar() or 0.0
        data["avg_engagement"] = round(float(avg), 1)

    # Sort by total agents descending
    result = sorted(cities.values(), key=lambda x: x["total"], reverse=True)
    return result


@router.get("/adm-performance")
def get_adm_performance(db: Session = Depends(get_db)):
    """
    ADM leaderboard with performance metrics.
    Ranks ADMs by activation rate, total agents managed, interactions logged,
    and engagement score.
    """
    from datetime import date as date_type
    today = date_type.today()

    adms = db.query(ADM).all()
    leaderboard = []

    for adm in adms:
        # Agent counts
        agent_states = dict(
            db.query(Agent.lifecycle_state, func.count(Agent.id))
            .filter(Agent.assigned_adm_id == adm.id)
            .group_by(Agent.lifecycle_state)
            .all()
        )
        total_agents = sum(agent_states.values())
        active_agents = agent_states.get("active", 0)
        contacted_agents = agent_states.get("contacted", 0)
        engaged_agents = agent_states.get("engaged", 0)

        activation_rate = round((active_agents / total_agents * 100), 1) if total_agents > 0 else 0

        # Interaction counts
        total_interactions = db.query(func.count(Interaction.id)).filter(
            Interaction.adm_id == adm.id,
        ).scalar() or 0

        # Avg engagement score
        avg_engagement = db.query(func.avg(Agent.engagement_score)).filter(
            Agent.assigned_adm_id == adm.id,
        ).scalar() or 0.0

        # Overdue follow-ups
        overdue = db.query(func.count(Interaction.id)).filter(
            Interaction.adm_id == adm.id,
            Interaction.follow_up_status == "pending",
            Interaction.follow_up_date < today,
        ).scalar() or 0

        # Feedback resolution rate
        total_feedback = db.query(func.count(Feedback.id)).filter(
            Feedback.adm_id == adm.id,
        ).scalar() or 0
        resolved_feedback = db.query(func.count(Feedback.id)).filter(
            Feedback.adm_id == adm.id,
            Feedback.status == "resolved",
        ).scalar() or 0
        resolution_rate = round((resolved_feedback / total_feedback * 100), 1) if total_feedback > 0 else 0

        leaderboard.append({
            "adm_id": adm.id,
            "adm_name": adm.name,
            "region": adm.region,
            "performance_score": adm.performance_score,
            "total_agents": total_agents,
            "active_agents": active_agents,
            "contacted_agents": contacted_agents,
            "engaged_agents": engaged_agents,
            "activation_rate": activation_rate,
            "total_interactions": total_interactions,
            "avg_engagement_score": round(float(avg_engagement), 1),
            "overdue_followups": overdue,
            "feedback_resolution_rate": resolution_rate,
        })

    # Sort by performance score descending
    leaderboard.sort(key=lambda x: x["performance_score"], reverse=True)
    return leaderboard


@router.get("/feedback-trends")
def get_feedback_trends(
    period: str = Query("weekly", description="daily|weekly|monthly"),
    db: Session = Depends(get_db),
):
    """
    Get feedback trends over time, grouped by category.
    Shows how feedback volumes change across time periods.
    """
    from datetime import timedelta, date as date_type

    today = date_type.today()

    if period == "daily":
        days_back = 30
        date_format = "%Y-%m-%d"
    elif period == "weekly":
        days_back = 90
        date_format = "%Y-W%W"
    else:  # monthly
        days_back = 365
        date_format = "%Y-%m"

    start_date = today - timedelta(days=days_back)

    # Get all feedback in the date range
    feedbacks = db.query(Feedback).filter(
        Feedback.created_at >= start_date,
    ).all()

    # Group by period and category
    trends = {}
    for fb in feedbacks:
        if fb.created_at is None:
            continue
        if period == "daily":
            period_key = fb.created_at.strftime("%Y-%m-%d")
        elif period == "weekly":
            # ISO week
            iso = fb.created_at.isocalendar()
            period_key = f"{iso[0]}-W{iso[1]:02d}"
        else:
            period_key = fb.created_at.strftime("%Y-%m")

        key = (period_key, fb.category)
        trends[key] = trends.get(key, 0) + 1

    # Format the response
    result = []
    for (p, cat), count in sorted(trends.items()):
        result.append({
            "period": p,
            "category": cat,
            "count": count,
        })

    # Also provide a summary by category
    category_totals = {}
    for fb in feedbacks:
        category_totals[fb.category] = category_totals.get(fb.category, 0) + 1

    return {
        "period_type": period,
        "start_date": start_date.isoformat(),
        "end_date": today.isoformat(),
        "total_feedbacks": len(feedbacks),
        "by_category_total": category_totals,
        "trends": result,
    }


@router.get("/activity-feed")
def get_activity_feed(
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Get recent activity for the live dashboard feed."""
    from datetime import datetime as dt

    recent_interactions = db.query(Interaction).order_by(
        Interaction.created_at.desc()
    ).limit(limit).all()

    feed = []
    for ix in recent_interactions:
        agent = db.query(Agent).filter(Agent.id == ix.agent_id).first()
        adm = db.query(ADM).filter(ADM.id == ix.adm_id).first()

        # Format time as relative string
        time_str = "recently"
        if ix.created_at:
            delta = dt.utcnow() - ix.created_at
            secs = delta.total_seconds()
            if secs < 60:
                time_str = "just now"
            elif secs < 3600:
                time_str = f"{int(secs/60)} min ago"
            elif secs < 86400:
                hrs = int(secs/3600)
                time_str = f"{hrs} hr{'s' if hrs > 1 else ''} ago"
            else:
                days = delta.days
                time_str = f"{days} day{'s' if days > 1 else ''} ago"

        # Determine type and icon
        type_map = {"call": "call", "whatsapp": "call", "visit": "engagement", "telegram": "feedback"}
        icon_map = {"call": "phone", "whatsapp": "message-square", "visit": "user-check", "telegram": "message-square"}
        feed_type = type_map.get(ix.type, "call")
        icon = icon_map.get(ix.type, "phone")

        # Build descriptive text
        agent_name = agent.name if agent else "Unknown Agent"
        agent_loc = agent.location if agent else ""

        if ix.outcome == "connected":
            text = f"Productive {ix.type} with {agent_name} ({agent_loc})"
        elif ix.outcome == "follow_up_scheduled":
            text = f"Follow-up scheduled with {agent_name} ({agent_loc})"
        elif ix.outcome == "not_answered":
            text = f"Attempted {ix.type} to {agent_name} ({agent_loc}) - no answer"
        elif ix.outcome == "callback_requested":
            text = f"Callback requested by {agent_name} ({agent_loc})"
        else:
            text = f"{ix.type.title()} with {agent_name} ({agent_loc}) - {ix.outcome}"

        if ix.notes and len(ix.notes) > 0:
            text += f" - {ix.notes[:60]}..."

        feed.append({
            "id": ix.id,
            "type": feed_type,
            "text": text,
            "adm": adm.name if adm else "Unknown",
            "time": time_str,
            "icon": icon,
        })

    return feed
