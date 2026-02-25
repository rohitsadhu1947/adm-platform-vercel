"""
Assignment service for auto-assigning dormant agents to ADMs.
Considers geography, language, capacity, and current load.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import Agent, ADM, Interaction

logger = logging.getLogger(__name__)

# Mapping of Indian cities to regions for geographic matching
CITY_REGION_MAP = {
    # West
    "mumbai": "West", "pune": "West", "ahmedabad": "West",
    "surat": "West", "nagpur": "West", "nashik": "West",
    "thane": "West", "vadodara": "West", "goa": "West",
    # North
    "delhi": "North", "new delhi": "North", "noida": "North",
    "gurgaon": "North", "gurugram": "North", "lucknow": "North",
    "jaipur": "North", "chandigarh": "North", "amritsar": "North",
    "dehradun": "North", "agra": "North",
    # South
    "bangalore": "South", "bengaluru": "South", "chennai": "South",
    "hyderabad": "South", "kochi": "South", "coimbatore": "South",
    "thiruvananthapuram": "South", "visakhapatnam": "South",
    "mysore": "South", "mysuru": "South",
    # East
    "kolkata": "East", "bhubaneswar": "East", "patna": "East",
    "ranchi": "East", "guwahati": "East", "siliguri": "East",
}

# Common language groupings
LANGUAGE_COMPATIBILITY = {
    "Hindi": ["Hindi", "English"],
    "English": ["English", "Hindi"],
    "Marathi": ["Marathi", "Hindi", "English"],
    "Tamil": ["Tamil", "English"],
    "Telugu": ["Telugu", "English", "Hindi"],
    "Kannada": ["Kannada", "English", "Hindi"],
    "Bengali": ["Bengali", "Hindi", "English"],
    "Gujarati": ["Gujarati", "Hindi", "English"],
    "Malayalam": ["Malayalam", "English"],
    "Punjabi": ["Punjabi", "Hindi", "English"],
}


def _get_region_for_city(city: str) -> str:
    """Determine region for a given city."""
    return CITY_REGION_MAP.get(city.lower().strip(), "Central")


def _languages_match(agent_lang: str, adm_langs: str) -> bool:
    """Check if the agent's language is compatible with ADM's languages."""
    adm_lang_list = [l.strip() for l in adm_langs.split(",")]
    if agent_lang in adm_lang_list:
        return True
    compatible = LANGUAGE_COMPATIBILITY.get(agent_lang, [agent_lang])
    return any(lang in adm_lang_list for lang in compatible)


def _score_adm_for_agent(agent: Agent, adm: ADM, db: Session) -> float:
    """Score an ADM for a given agent assignment (higher is better)."""
    score = 0.0

    # 1. Capacity check (hard filter -- 0 means cannot assign)
    current_count = db.query(func.count(Agent.id)).filter(
        Agent.assigned_adm_id == adm.id
    ).scalar() or 0
    if current_count >= adm.max_capacity:
        return -1.0  # Over capacity

    capacity_utilization = current_count / adm.max_capacity
    score += (1.0 - capacity_utilization) * 30  # Up to 30 points for capacity

    # 2. Geographic match
    agent_region = _get_region_for_city(agent.location)
    adm_region_parts = adm.region.lower()
    if agent_region.lower() in adm_region_parts or agent.location.lower() in adm_region_parts:
        score += 40  # Strong geographic match
    elif agent_region.lower() in adm_region_parts:
        score += 20  # Region match

    # 3. Language compatibility
    if _languages_match(agent.language, adm.language):
        score += 20

    # 4. ADM performance bonus
    score += (adm.performance_score / 100) * 10  # Up to 10 points

    return score


def auto_assign_agents(
    db: Session,
    agent_ids: Optional[List[int]] = None,
    target_adm_id: Optional[int] = None,
    strategy: str = "balanced",
) -> dict:
    """
    Auto-assign agents to ADMs.

    Args:
        db: Database session
        agent_ids: Specific agent IDs to assign (None = all unassigned dormant)
        target_adm_id: Force assignment to a specific ADM (None = auto-select)
        strategy: "balanced" | "geographic" | "language"

    Returns:
        dict with assigned_count, assignments list, and errors list
    """
    assignments = []
    errors = []

    # Get agents to assign
    if agent_ids:
        agents = db.query(Agent).filter(
            Agent.id.in_(agent_ids),
            Agent.assigned_adm_id.is_(None),
        ).all()
        if len(agents) < len(agent_ids):
            found_ids = {a.id for a in agents}
            missing = [aid for aid in agent_ids if aid not in found_ids]
            errors.append(f"Agents not found or already assigned: {missing}")
    else:
        agents = db.query(Agent).filter(
            Agent.assigned_adm_id.is_(None),
            Agent.lifecycle_state.in_(["dormant", "at_risk"]),
        ).all()

    if not agents:
        return {"assigned_count": 0, "assignments": [], "errors": ["No eligible agents found for assignment"]}

    # Get available ADMs
    if target_adm_id:
        adms = db.query(ADM).filter(ADM.id == target_adm_id).all()
        if not adms:
            return {"assigned_count": 0, "assignments": [], "errors": [f"ADM {target_adm_id} not found"]}
    else:
        adms = db.query(ADM).all()

    if not adms:
        return {"assigned_count": 0, "assignments": [], "errors": ["No ADMs available"]}

    # Assign each agent to the best ADM
    for agent in agents:
        best_adm = None
        best_score = -1.0

        for adm in adms:
            score = _score_adm_for_agent(agent, adm, db)
            if score > best_score:
                best_score = score
                best_adm = adm

        if best_adm and best_score > 0:
            agent.assigned_adm_id = best_adm.id
            if agent.lifecycle_state == "dormant":
                agent.lifecycle_state = "dormant"  # Keep dormant until contacted

            reason_parts = []
            agent_region = _get_region_for_city(agent.location)
            if agent_region.lower() in best_adm.region.lower():
                reason_parts.append("geographic match")
            if _languages_match(agent.language, best_adm.language):
                reason_parts.append("language compatible")
            reason_parts.append(f"capacity score: {best_score:.0f}")

            assignments.append({
                "agent_id": agent.id,
                "agent_name": agent.name,
                "adm_id": best_adm.id,
                "adm_name": best_adm.name,
                "score": round(best_score, 1),
                "reason": ", ".join(reason_parts),
            })
        else:
            errors.append(f"No suitable ADM found for agent {agent.id} ({agent.name}) in {agent.location}")

    db.commit()

    return {
        "assigned_count": len(assignments),
        "assignments": assignments,
        "errors": errors,
    }


def rebalance_assignments(db: Session) -> dict:
    """
    Rebalance agent assignments across ADMs to ensure even distribution.
    Moves agents from over-loaded ADMs to under-loaded ones.
    """
    adms = db.query(ADM).all()
    if not adms:
        return {"rebalanced": 0, "moves": [], "errors": ["No ADMs found"]}

    # Calculate current loads
    adm_loads = {}
    for adm in adms:
        count = db.query(func.count(Agent.id)).filter(
            Agent.assigned_adm_id == adm.id
        ).scalar() or 0
        adm_loads[adm.id] = {
            "adm": adm,
            "count": count,
            "capacity": adm.max_capacity,
            "utilization": count / adm.max_capacity if adm.max_capacity > 0 else 1.0,
        }

    avg_utilization = sum(d["utilization"] for d in adm_loads.values()) / len(adm_loads)
    moves = []

    # Find overloaded ADMs (utilization > avg + 20%)
    overloaded = {aid: d for aid, d in adm_loads.items() if d["utilization"] > avg_utilization + 0.2}
    underloaded = {aid: d for aid, d in adm_loads.items() if d["utilization"] < avg_utilization - 0.1}

    for over_id, over_data in overloaded.items():
        excess = over_data["count"] - int(over_data["capacity"] * avg_utilization)
        if excess <= 0:
            continue

        # Get agents that can be moved (dormant, not yet contacted)
        moveable_agents = db.query(Agent).filter(
            Agent.assigned_adm_id == over_id,
            Agent.lifecycle_state.in_(["dormant", "at_risk"]),
        ).limit(excess).all()

        for agent in moveable_agents:
            best_under_id = None
            best_score = -1.0

            for under_id, under_data in underloaded.items():
                score = _score_adm_for_agent(agent, under_data["adm"], db)
                if score > best_score:
                    best_score = score
                    best_under_id = under_id

            if best_under_id and best_score > 0:
                old_adm_name = over_data["adm"].name
                new_adm_name = underloaded[best_under_id]["adm"].name
                agent.assigned_adm_id = best_under_id
                moves.append({
                    "agent_id": agent.id,
                    "agent_name": agent.name,
                    "from_adm_id": over_id,
                    "from_adm_name": old_adm_name,
                    "to_adm_id": best_under_id,
                    "to_adm_name": new_adm_name,
                })

    if moves:
        db.commit()

    return {
        "rebalanced": len(moves),
        "moves": moves,
        "errors": [],
    }
