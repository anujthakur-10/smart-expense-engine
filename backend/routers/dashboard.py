"""
dashboard.py — Analytics Dashboard Router
Summary stats, GST breakdown, monthly trends, vendor-wise expenses.
"""

from fastapi import APIRouter, Depends, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List

from database import get_db
from auth import get_current_user
from models.invoice import Invoice
from models.vendor import Vendor
from schemas.invoice import DashboardSummary, GSTSummaryItem, MonthlyTrend, VendorExpense
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Dashboard ke top-level stats — total expenses, GST, invoice count, etc."""
    user_id = user["id"]

    # Total expenses
    total_expenses = db.query(func.sum(Invoice.total_amount)).filter(
        Invoice.user_id == user_id
    ).scalar() or 0

    # Total GST paid
    total_gst = db.query(
        func.sum(Invoice.cgst + Invoice.sgst + Invoice.igst)
    ).filter(Invoice.user_id == user_id).scalar() or 0

    # Counts
    total_invoices = db.query(func.count(Invoice.id)).filter(
        Invoice.user_id == user_id
    ).scalar() or 0

    total_vendors = db.query(func.count(Vendor.id)).filter(
        Vendor.user_id == user_id
    ).scalar() or 0

    pending_reviews = db.query(func.count(Invoice.id)).filter(
        Invoice.user_id == user_id,
        Invoice.status == "pending",
    ).scalar() or 0

    duplicates = db.query(func.count(Invoice.id)).filter(
        Invoice.user_id == user_id,
        Invoice.is_duplicate == True,
    ).scalar() or 0

    return DashboardSummary(
        total_expenses=round(float(total_expenses), 2),
        total_gst_paid=round(float(total_gst), 2),
        total_invoices=total_invoices,
        total_vendors=total_vendors,
        pending_reviews=pending_reviews,
        duplicates_flagged=duplicates,
    )


@router.get("/gst-summary", response_model=List[GSTSummaryItem])
async def get_gst_summary(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Monthly GST breakdown — CGST, SGST, IGST alag alag"""
    results = db.query(
        func.to_char(func.date_trunc('month', Invoice.invoice_date), 'YYYY-MM').label('month'),
        func.sum(Invoice.cgst).label('cgst'),
        func.sum(Invoice.sgst).label('sgst'),
        func.sum(Invoice.igst).label('igst'),
    ).filter(
        Invoice.user_id == user["id"],
        Invoice.invoice_date.isnot(None),
    ).group_by(
        func.date_trunc('month', Invoice.invoice_date)
    ).order_by(func.date_trunc('month', Invoice.invoice_date)).all()

    return [
        GSTSummaryItem(
            month=row.month,
            cgst=round(float(row.cgst or 0), 2),
            sgst=round(float(row.sgst or 0), 2),
            igst=round(float(row.igst or 0), 2),
            total_gst=round(float((row.cgst or 0) + (row.sgst or 0) + (row.igst or 0)), 2),
        )
        for row in results
    ]


@router.get("/monthly-trend", response_model=List[MonthlyTrend])
async def get_monthly_trend(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Month-over-month expense trend"""
    results = db.query(
        func.to_char(func.date_trunc('month', Invoice.invoice_date), 'YYYY-MM').label('month'),
        func.sum(Invoice.total_amount).label('total'),
        func.count(Invoice.id).label('count'),
    ).filter(
        Invoice.user_id == user["id"],
        Invoice.invoice_date.isnot(None),
    ).group_by(
        func.date_trunc('month', Invoice.invoice_date)
    ).order_by(func.date_trunc('month', Invoice.invoice_date)).all()

    return [
        MonthlyTrend(
            month=row.month,
            total_amount=round(float(row.total or 0), 2),
            invoice_count=row.count,
        )
        for row in results
    ]


@router.get("/vendor-expenses", response_model=List[VendorExpense])
async def get_vendor_expenses(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Top vendors by expense — pie chart ke liye"""
    results = db.query(
        Invoice.vendor_name,
        func.sum(Invoice.total_amount).label('total'),
        func.count(Invoice.id).label('count'),
    ).filter(
        Invoice.user_id == user["id"],
        Invoice.vendor_name.isnot(None),
    ).group_by(
        Invoice.vendor_name
    ).order_by(func.sum(Invoice.total_amount).desc()).limit(limit).all()

    return [
        VendorExpense(
            vendor_name=row.vendor_name or "Unknown",
            total_amount=round(float(row.total or 0), 2),
            invoice_count=row.count,
        )
        for row in results
    ]

# ── Simulated Email Alert Task ──────────────────────────────────────
def send_summary_email_task(email: str, total_expenses: float):
    """Background task jo simulate karega ki email send ho raha hai"""
    import time
    logger.info(f"📧 Preparing to send monthly summary to {email}...")
    time.sleep(2)  # Simulate network delay
    logger.info(f"✅ Success! Sent email to {email}: 'Your total expenses this month are ₹{total_expenses}'")

@router.post("/trigger-summary-email")
async def trigger_email(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Trigger background email sending task"""
    # Calculate current month's expenses just for the email
    user_id = user["id"]
    total = db.query(func.sum(Invoice.total_amount)).filter(
        Invoice.user_id == user_id
    ).scalar() or 0
    
    # Schedule the task in the background
    background_tasks.add_task(send_summary_email_task, user.get("email", "user@example.com"), round(float(total), 2))
    
    return {"message": "Email alert triggered in background!"}
