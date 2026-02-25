"""
domain/ — Core domain intelligence for the ADM Platform.

Ported from the AARS (Agent Activation & Retention System) codebase.
Simplified for standalone use with SQLite + demo mode (no Redis, no Celery,
no multi-tenant complexity). All domain logic lives here and powers both
the Telegram bot and the web dashboard.

Modules:
    enums               — All domain enumerations
    lifecycle           — Agent lifecycle finite state machine
    dormancy_taxonomy   — 27 dormancy reasons across 7 categories
    playbook_engine     — Condition evaluator + default playbook definitions
    adm_intelligence    — ADM effectiveness, priority ranking, briefings
    whatsapp_templates  — Bilingual (Hindi + English) message templates
"""

from domain.enums import (
    AgentLifecycleState,
    DormancyReasonCategory,
    DormancyReasonCode,
    ContactOutcome,
    SentimentLabel,
    ChannelType,
    TrainingTopic,
    ProductCategory,
)

__all__ = [
    "AgentLifecycleState",
    "DormancyReasonCategory",
    "DormancyReasonCode",
    "ContactOutcome",
    "SentimentLabel",
    "ChannelType",
    "TrainingTopic",
    "ProductCategory",
]
