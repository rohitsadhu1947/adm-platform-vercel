"""
Database setup using SQLAlchemy — PostgreSQL only (Neon DB).

This is the Vercel serverless version. No SQLite support.
Connection pooling is tuned for short-lived serverless functions.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Build engine — PostgreSQL / Neon only
# ---------------------------------------------------------------------------

if not settings.DATABASE_URL or settings.DATABASE_URL.startswith("sqlite"):
    raise RuntimeError(
        "DATABASE_URL must be a PostgreSQL connection string (Neon DB). "
        "Set it in Vercel environment variables."
    )

logger.info("Using PostgreSQL backend (Neon DB)")

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,       # Auto-reconnect stale connections
    pool_size=3,              # Lower for serverless (short-lived functions)
    max_overflow=5,
    pool_timeout=10,
    pool_recycle=120,         # Shorter recycle for serverless
    echo=settings.DEBUG,
)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables if they don't exist."""
    from models import (
        Agent, ADM, Interaction, Feedback,
        TrainingProgress, DiaryEntry, DailyBriefing,
        User, Product,
        ReasonTaxonomy, FeedbackTicket, DepartmentQueue, AggregationAlert,
        TicketMessage, BotState,
    )
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created / verified.")
