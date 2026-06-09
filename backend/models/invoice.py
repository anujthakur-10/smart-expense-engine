"""
invoice.py — Invoice & InvoiceItem ORM Models
Invoice ki main details + line items store karte hain.
GST breakdown (CGST/SGST/IGST) bhi yahan hai.
Fraud detection ke liye duplicate flags bhi track hote hain.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean,
    DateTime, Date, ForeignKey, func
)
from sqlalchemy.orm import relationship
from database import Base


class Invoice(Base):
    """
    Invoices Table — Har uploaded invoice ka record
    OCR se extracted data + GST calculations + fraud flags
    """
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # ── User Ownership ────────────────────────────────────────────
    user_id = Column(String(255), nullable=False, index=True)

    # ── Invoice Identity ──────────────────────────────────────────
    invoice_number = Column(String(100), nullable=True)      # Extracted invoice/bill number
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    vendor_name = Column(String(255), nullable=True)         # Vendor name (from OCR)
    invoice_date = Column(Date, nullable=True)               # Invoice/bill date
    upload_date = Column(DateTime(timezone=True), server_default=func.now())

    # ── File Storage ──────────────────────────────────────────────
    file_url = Column(String(500), nullable=True)            # Supabase Storage URL
    file_name = Column(String(255), nullable=True)           # Original filename
    file_type = Column(String(10), nullable=True)            # jpg, png, pdf
    page_count = Column(Integer, default=1)                  # PDF pages (1 for images)

    # ── OCR Data ──────────────────────────────────────────────────
    raw_ocr_text = Column(Text, nullable=True)               # Full OCR output (audit trail)
    ocr_confidence = Column(Float, nullable=True)            # Average OCR confidence score
    ocr_language = Column(String(10), nullable=True)         # Detected language (hi/en)

    # ── Financial Data ────────────────────────────────────────────
    subtotal = Column(Float, default=0.0)                    # Amount before tax
    cgst = Column(Float, default=0.0)                        # Central GST
    sgst = Column(Float, default=0.0)                        # State GST
    igst = Column(Float, default=0.0)                        # Integrated GST
    total_amount = Column(Float, default=0.0)                # Final amount (subtotal + tax)
    gst_rate = Column(Float, nullable=True)                  # Detected GST rate (5/12/18/28)
    currency = Column(String(3), default="INR")              # Currency code

    # ── GST Details ───────────────────────────────────────────────
    vendor_gstin = Column(String(15), nullable=True)         # Vendor's GSTIN from invoice
    buyer_gstin = Column(String(15), nullable=True)          # Buyer's GSTIN (if present)
    is_inter_state = Column(Boolean, default=False)          # True = IGST, False = CGST+SGST
    hsn_codes = Column(Text, nullable=True)                  # Comma-separated HSN codes

    # ── Fraud Detection ───────────────────────────────────────────
    is_duplicate = Column(Boolean, default=False)            # Duplicate flag
    duplicate_of_id = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    duplicate_confidence = Column(Float, nullable=True)      # 0.0 to 1.0
    invoice_hash = Column(String(64), nullable=True, index=True)  # SHA256 hash for quick lookup

    # ── Status & Workflow ─────────────────────────────────────────
    status = Column(String(20), default="pending")           # pending | reviewed | approved
    notes = Column(Text, nullable=True)                      # User notes/corrections
    category = Column(String(100), nullable=True)            # Expense category

    # ── Timestamps ────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # ── Relationships ─────────────────────────────────────────────
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Invoice(id={self.id}, number='{self.invoice_number}', total={self.total_amount})>"


class InvoiceItem(Base):
    """
    Invoice Items Table — Invoice ke andar line items
    Har item ka description, quantity, price store hota hai.
    """
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)

    # ── Item Details ──────────────────────────────────────────────
    description = Column(String(500), nullable=True)         # Item name/description
    quantity = Column(Float, default=1.0)                    # Quantity
    unit = Column(String(20), nullable=True)                 # Unit (kg, pcs, litre, etc.)
    unit_price = Column(Float, default=0.0)                  # Price per unit
    amount = Column(Float, default=0.0)                      # Total (quantity × unit_price)
    hsn_code = Column(String(10), nullable=True)             # HSN/SAC code

    # ── Timestamps ────────────────────────────────────────────────
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ── Relationships ─────────────────────────────────────────────
    invoice = relationship("Invoice", back_populates="items")

    def __repr__(self):
        return f"<InvoiceItem(id={self.id}, desc='{self.description}', amount={self.amount})>"
