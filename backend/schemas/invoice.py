"""
schemas/invoice.py — Pydantic Schemas for Invoice API
Request/Response validation ke liye use hote hain.
FastAPI automatically JSON schema generate karta hai in se.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime


# ══════════════════════════════════════════════════════════════════
# Invoice Item Schemas
# ══════════════════════════════════════════════════════════════════

class InvoiceItemBase(BaseModel):
    """Invoice line item ki base fields"""
    description: Optional[str] = None
    quantity: float = 1.0
    unit: Optional[str] = None
    unit_price: float = 0.0
    amount: float = 0.0
    hsn_code: Optional[str] = None


class InvoiceItemCreate(InvoiceItemBase):
    """Naya item create karte waqt ye fields chahiye"""
    pass


class InvoiceItemResponse(InvoiceItemBase):
    """API response mein item ka format"""
    id: int
    invoice_id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # ORM mode — SQLAlchemy object se direct convert


# ══════════════════════════════════════════════════════════════════
# Invoice Schemas
# ══════════════════════════════════════════════════════════════════

class InvoiceBase(BaseModel):
    """Invoice ki base fields — create aur update dono mein use"""
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_date: Optional[date] = None
    subtotal: float = 0.0
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    total_amount: float = 0.0
    gst_rate: Optional[float] = None
    is_inter_state: bool = False
    vendor_gstin: Optional[str] = None
    buyer_gstin: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class InvoiceCreate(InvoiceBase):
    """Manual invoice create karte waqt"""
    items: List[InvoiceItemCreate] = []


class InvoiceUpdate(BaseModel):
    """
    Invoice update/edit karte waqt — Review & Edit screen se aata hai.
    Saari fields optional hain kyunki partial update allowed hai.
    """
    invoice_number: Optional[str] = None
    vendor_name: Optional[str] = None
    invoice_date: Optional[date] = None
    subtotal: Optional[float] = None
    cgst: Optional[float] = None
    sgst: Optional[float] = None
    igst: Optional[float] = None
    total_amount: Optional[float] = None
    gst_rate: Optional[float] = None
    is_inter_state: Optional[bool] = None
    vendor_gstin: Optional[str] = None
    buyer_gstin: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None       # pending → reviewed → approved
    items: Optional[List[InvoiceItemCreate]] = None


class InvoiceResponse(InvoiceBase):
    """API response mein invoice ka full format"""
    id: int
    user_id: str
    vendor_id: Optional[int] = None
    upload_date: Optional[datetime] = None
    file_url: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    page_count: int = 1
    raw_ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_language: Optional[str] = None
    is_duplicate: bool = False
    duplicate_of_id: Optional[int] = None
    duplicate_confidence: Optional[float] = None
    status: str = "pending"
    items: List[InvoiceItemResponse] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ══════════════════════════════════════════════════════════════════
# OCR Response Schema — Upload ke baad OCR result
# ══════════════════════════════════════════════════════════════════

class OCRResult(BaseModel):
    """OCR extraction ka result — upload endpoint se return hota hai"""
    raw_text: str = ""
    confidence: float = 0.0
    language: str = "en"
    extracted_fields: dict = {}       # Parsed fields (invoice_number, date, amount, etc.)
    line_items: List[dict] = []       # Detected line items


class UploadResponse(BaseModel):
    """POST /upload ka complete response"""
    invoice: InvoiceResponse
    ocr_result: OCRResult
    fraud_check: dict = {}            # {is_duplicate, confidence, duplicate_id}
    gst_details: dict = {}            # {cgst, sgst, igst, rate, is_inter_state}
    message: str = "Invoice processed successfully"


# ══════════════════════════════════════════════════════════════════
# Dashboard Schemas
# ══════════════════════════════════════════════════════════════════

class DashboardSummary(BaseModel):
    """Dashboard overview stats"""
    total_expenses: float = 0.0
    total_gst_paid: float = 0.0
    total_invoices: int = 0
    total_vendors: int = 0
    pending_reviews: int = 0
    duplicates_flagged: int = 0


class GSTSummaryItem(BaseModel):
    """Monthly GST breakdown"""
    month: str
    cgst: float = 0.0
    sgst: float = 0.0
    igst: float = 0.0
    total_gst: float = 0.0


class MonthlyTrend(BaseModel):
    """Monthly expense trend data point"""
    month: str
    total_amount: float = 0.0
    invoice_count: int = 0


class VendorExpense(BaseModel):
    """Vendor-wise expense breakdown"""
    vendor_name: str
    total_amount: float = 0.0
    invoice_count: int = 0
