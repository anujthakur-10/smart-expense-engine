"""
main.py — FastAPI Application Entry Point
Smart Expense Engine & Predictive Analytics for Indian SMEs

CORS, router mounting, database init — sab yahan hota hai.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import get_settings
from database import init_db
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    App startup aur shutdown events handle karta hai.
    Startup pe database tables create hote hain.
    """
    # ── Startup ────────────────────────────────────────────
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"📌 Environment: {settings.ENVIRONMENT}")

    # Database tables create karo (agar exist nahi karte)
    try:
        init_db()
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        logger.info("⚠️ App will start but DB operations may fail. Check DATABASE_URL.")

    yield

    # ── Shutdown ───────────────────────────────────────────
    logger.info("👋 Shutting down Smart Expense Engine...")


# ── FastAPI App Instance ──────────────────────────────────────────
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "🧾 AI-powered invoice processing for Indian SMEs. "
        "Hindi + English OCR, GST intelligence, expense forecasting."
    ),
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else "/docs",  # Swagger UI
    redoc_url="/redoc",
)


# ── CORS Middleware ───────────────────────────────────────────────
# Frontend (React on Vercel/localhost) ko backend se communicate karne do
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Mount Routers ─────────────────────────────────────────────────
from routers import upload, invoices, dashboard, forecast

app.include_router(upload.router)
app.include_router(invoices.router)
app.include_router(dashboard.router)
app.include_router(forecast.router)


# ── Health Check ──────────────────────────────────────────────────
@app.get("/", tags=["Health"])
async def root():
    """API health check — deployment verify karne ke liye"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running ✅",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "connected" if settings.DATABASE_URL else "not configured",
    }
