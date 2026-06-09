"""
vendor.py — Vendor ORM Model
Vendor (supplier/dukandaar) ki details store karta hai.
Har invoice ek vendor se linked hota hai.
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, func
from database import Base


class Vendor(Base):
    """
    Vendors Table — Dukandaar/Supplier ki information
    GSTIN se state code automatically extract hota hai.
    """
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── User Ownership ────────────────────────────────────────────
    # Supabase user ID — har vendor ek specific user ka hota hai
    user_id = Column(String(255), nullable=False, index=True)

    # ── Vendor Details ────────────────────────────────────────────
    name = Column(String(255), nullable=False)               # Vendor/shop name
    gstin = Column(String(15), nullable=True)                # GSTIN (15-char validated)
    state_code = Column(String(2), nullable=True)            # First 2 digits of GSTIN
    pan = Column(String(10), nullable=True)                  # PAN (extracted from GSTIN)
    address = Column(Text, nullable=True)                    # Full address
    phone = Column(String(15), nullable=True)                # Phone number
    email = Column(String(255), nullable=True)               # Email address
    category = Column(String(100), nullable=True)            # Business category

    # ── Timestamps ────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Vendor(id={self.id}, name='{self.name}', gstin='{self.gstin}')>"
