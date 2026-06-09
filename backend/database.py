"""
database.py — Database Connection Setup
Supabase PostgreSQL se connect karta hai via SQLAlchemy.
Session management aur Base class yahan define hoti hai.
"""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import get_settings

settings = get_settings()

# ── SQLAlchemy Engine ─────────────────────────────────────────────
# Supabase PostgreSQL connection string use hoti hai
# Format: postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres
#
# NOTE: asyncpg use nahi kar rahe kyunki PaddleOCR synchronous hai,
# toh sync engine hi best rahega yahaan.
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=5,              # Connection pool size
    max_overflow=10,          # Extra connections allowed beyond pool_size
    pool_pre_ping=True,       # Stale connection check (important for cloud DB)
    echo=settings.DEBUG,      # SQL queries print hoga debug mode mein
)

# ── Session Factory ───────────────────────────────────────────────
# Har API request ke liye ek session create hota hai
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ── Base Class ────────────────────────────────────────────────────
# Saare ORM models is Base se inherit karenge
Base = declarative_base()


def get_db():
    """
    FastAPI Dependency — Database session provide karta hai.
    Request complete hone ke baad session automatically close hota hai.

    Usage in router:
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Database tables create karta hai agar exist nahi karte.
    App startup pe call hota hai (main.py mein).
    """
    # Import all models so that Base.metadata knows about them
    import models.vendor    # noqa: F401
    import models.invoice   # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created / verified successfully!")
