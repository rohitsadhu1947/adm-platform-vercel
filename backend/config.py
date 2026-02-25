"""
Configuration settings for the ADM Platform backend.
Uses pydantic-settings for environment variable management.

DATABASE_URL priority:
  1. DATABASE_URL env var (set in Railway → points to Neon PostgreSQL)
  2. Fallback: SQLite for local development
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "ADM Platform - Axis Max Life Insurance"
    APP_VERSION: str = "3.0.0-vercel"
    DEBUG: bool = False

    # Database — Neon PostgreSQL (REQUIRED, no SQLite fallback on Vercel)
    DATABASE_URL: str = ""

    @property
    def is_postgres(self) -> bool:
        """True when using PostgreSQL (always True on Vercel)."""
        return self.DATABASE_URL.startswith("postgresql")

    # Anthropic Claude API
    ANTHROPIC_API_KEY: str = ""

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_URL: str = ""

    # WhatsApp Business API (placeholder)
    WHATSAPP_API_URL: str = ""
    WHATSAPP_API_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173,http://localhost:8080,https://adm-agent.vercel.app"

    # Security
    SECRET_KEY: str = "adm-platform-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Feature Flags
    ENABLE_AI_FEATURES: bool = True
    ENABLE_TELEGRAM_BOT: bool = False
    ENABLE_WHATSAPP: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
    }


settings = Settings()
