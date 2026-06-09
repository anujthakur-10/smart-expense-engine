"""
config.py — Central Configuration File
Saari environment variables aur Supabase settings yahan se manage hongi.
.env file se values load hoti hain via pydantic-settings.
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application Settings — .env file se auto-load hota hai.
    Production mein ye environment variables set karo (Railway/Render dashboard mein).
    """

    # ── App Settings ──────────────────────────────────────────────
    APP_NAME: str = "Smart Expense Engine"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | production

    # ── Supabase Settings ─────────────────────────────────────────
    # Supabase project dashboard se milega: Settings > API
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""          # Public anon key (frontend bhi use karti hai)
    SUPABASE_SERVICE_KEY: str = ""       # Service role key (backend only, RLS bypass)
    SUPABASE_JWT_SECRET: str = ""        # JWT secret for token verification

    # ── Database ──────────────────────────────────────────────────
    # Supabase dashboard se milega: Settings > Database > Connection string
    DATABASE_URL: str = ""

    # ── Supabase Storage ──────────────────────────────────────────
    STORAGE_BUCKET: str = "invoices"     # Supabase storage bucket name

    # ── OCR Settings ──────────────────────────────────────────────
    OCR_LANGUAGES: list = ["hi", "en"]   # Hindi + English
    OCR_CONFIDENCE_THRESHOLD: float = 0.5  # Minimum confidence for OCR results

    # ── Forecasting Settings ──────────────────────────────────────
    FORECAST_MIN_MONTHS: int = 6         # Minimum months of data for Prophet/XGBoost
    FORECAST_DEFAULT_PERIODS: int = 3    # Default months to forecast ahead
    FORECAST_DEFAULT_MODEL: str = "xgboost"  # prophet | xgboost | lightgbm

    # ── Upload Settings ───────────────────────────────────────────
    MAX_UPLOAD_SIZE_MB: int = 10         # Max file size in MB
    ALLOWED_EXTENSIONS: list = [".jpg", ".jpeg", ".png", ".pdf", ".webp"]

    # ── CORS ──────────────────────────────────────────────────────
    # Frontend URLs jo allowed hain (comma separated for multiple)
    CORS_ORIGINS: list = [
        "http://localhost:5173",          # Vite dev server
        "http://localhost:3000",          # Alternative
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    Settings ka singleton instance return karta hai.
    lru_cache ensures ki baar baar .env file parse na ho.
    """
    return Settings()
