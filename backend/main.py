"""
ADM Platform - FastAPI Application Entry Point (Vercel Serverless)

Axis Max Life Insurance Agent Activation & Re-engagement System.
Provides REST APIs for managing dormant agent activation through
ADMs (Agency Development Managers).

Vercel deployment:
  - No threading (synchronous DB init on cold start)
  - PostgreSQL only (Neon DB)
  - Webhook-based Telegram bot (no polling subprocess)
"""

import logging
import sys
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import init_db, SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("adm_platform")

# Track DB readiness
_db_ready = False


def _run_seed_if_empty():
    """Seed reference data (products, admin user, ADM users) if not already present."""
    from models import Product, User, ReasonTaxonomy

    db = SessionLocal()
    try:
        # Only reset if explicitly requested (never auto-reset on Neon)
        if os.environ.get("RESET_DB", "").lower() in ("true", "1", "yes"):
            logger.warning("RESET_DB=true — dropping and recreating all tables!")
            from database import engine, Base
            db.close()
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
            db = SessionLocal()

        count = db.query(Product).count()
        if count == 0:
            logger.info("No products found. Seeding reference data...")
            from seed_data import seed_database
            seed_database(db)
            logger.info("Reference data seeded successfully.")
        else:
            logger.info(f"Database has {count} products. Skipping full seed.")
            _ensure_key_users(db)

        # Ensure ReasonTaxonomy is populated
        reason_count = db.query(ReasonTaxonomy).count()
        if reason_count == 0:
            logger.info("Seeding feedback reason taxonomy...")
            from seed_data import REASON_TAXONOMY
            for r_data in REASON_TAXONOMY:
                db.add(ReasonTaxonomy(**r_data))
            db.commit()
            logger.info(f"Seeded {len(REASON_TAXONOMY)} reason taxonomy entries.")
    except Exception as e:
        logger.error(f"Seeding error: {e}")
        db.rollback()
    finally:
        db.close()


def _ensure_key_users(db):
    """Ensure admin and key ADM users exist."""
    import hashlib
    from models import User, ADM

    def _hash(pw: str) -> str:
        return hashlib.sha256(pw.encode()).hexdigest()

    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(username="admin", password_hash=_hash("admin123"), role="admin", name="Platform Admin"))
        db.flush()
        logger.info("Created admin user")

    if not db.query(User).filter(User.username == "rohit").first():
        rohit_adm = db.query(ADM).filter(ADM.telegram_chat_id == "8321786545").first()
        if not rohit_adm:
            rohit_adm = ADM(
                name="Rohit Sadhu", phone="7303474258", region="North",
                language="Hindi,English", max_capacity=50, performance_score=0.0,
                telegram_chat_id="8321786545",
            )
            db.add(rohit_adm)
            db.flush()
        db.add(User(username="rohit", password_hash=_hash("rohit123"), role="adm", name="Rohit Sadhu", adm_id=rohit_adm.id))
        db.commit()
        logger.info("Created ADM user: Rohit Sadhu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    global _db_ready

    logger.info("=" * 60)
    logger.info(f"  {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"  Database: PostgreSQL (Neon DB)")
    logger.info(f"  Platform: Vercel Serverless")
    logger.info("=" * 60)

    # Synchronous DB init (no background thread on Vercel)
    try:
        init_db()
        _run_seed_if_empty()
        _db_ready = True
        logger.info("DB init complete.")
    except Exception as e:
        logger.error(f"DB init failed: {e}")
        _db_ready = False

    yield

    logger.info("Shutting down...")


# ---------------------------------------------------------------------------
# Create FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "REST API for the ADM Platform - Axis Max Life Insurance "
        "Agent Activation & Re-engagement System."
    ),
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# CORS Middleware
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Include all route routers under /api/v1
# ---------------------------------------------------------------------------
from routes import (
    agents_router,
    adms_router,
    interactions_router,
    feedback_router,
    diary_router,
    briefings_router,
    analytics_router,
    training_router,
    assignment_router,
    telegram_bot_router,
    auth_router,
    products_router,
    onboarding_router,
    playbooks_router,
    communication_router,
    feedback_tickets_router,
)

API_PREFIX = "/api/v1"

all_routers = [
    telegram_bot_router,
    agents_router,
    adms_router,
    interactions_router,
    feedback_router,
    diary_router,
    briefings_router,
    analytics_router,
    training_router,
    assignment_router,
    auth_router,
    products_router,
    onboarding_router,
    playbooks_router,
    communication_router,
    feedback_tickets_router,
]

# Mount under /api/v1
for r in all_routers:
    app.include_router(r, prefix=API_PREFIX)

# Also mount at root (backward compatibility)
for r in all_routers:
    app.include_router(r)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "platform": "vercel",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check():
    result = {
        "status": "healthy",
        "database": "ready" if _db_ready else "initializing",
        "database_backend": "postgresql",
        "platform": "vercel",
        "version": settings.APP_VERSION,
        "ai_enabled": bool(settings.ANTHROPIC_API_KEY),
        "telegram_webhook": bool(settings.TELEGRAM_WEBHOOK_URL),
    }

    if _db_ready:
        try:
            from models import Agent
            db = SessionLocal()
            result["agent_count"] = db.query(Agent).count()
            db.close()
        except Exception as e:
            result["agent_count"] = 0
            result["database"] = f"error: {str(e)}"

    return result
