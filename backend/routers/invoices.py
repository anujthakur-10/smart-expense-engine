"""
invoices.py — Invoice CRUD Router
List, view, update (review/edit), delete invoices.
"""

import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional

from database import get_db
from auth import get_current_user
from models.invoice import Invoice, InvoiceItem
from schemas.invoice import InvoiceResponse, InvoiceUpdate
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/invoices", tags=["Invoices"])


@router.get("/", response_model=List[InvoiceResponse])
async def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Saare invoices list karo — pagination + search + filter.
    """
    query = db.query(Invoice).filter(Invoice.user_id == user["id"])

    # Status filter
    if status_filter:
        query = query.filter(Invoice.status == status_filter)

    # Search (vendor name ya invoice number mein)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Invoice.vendor_name.ilike(search_term)) |
            (Invoice.invoice_number.ilike(search_term))
        )

    # Pagination
    total = query.count()
    invoices = query.order_by(desc(Invoice.created_at)).offset((page - 1) * limit).limit(limit).all()

    return invoices


@router.get("/export")
async def export_invoices_csv(
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Export all invoices to a CSV file.
    """
    invoices = db.query(Invoice).filter(Invoice.user_id == user["id"]).order_by(desc(Invoice.created_at)).all()

    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header row
    writer.writerow([
        "Invoice ID", "Invoice Number", "Vendor Name", "Date", 
        "Subtotal", "CGST", "SGST", "IGST", "Total Amount", 
        "Status", "Is Duplicate"
    ])
    
    # Data rows
    for inv in invoices:
        writer.writerow([
            inv.id, inv.invoice_number, inv.vendor_name, inv.invoice_date,
            inv.subtotal, inv.cgst, inv.sgst, inv.igst, inv.total_amount,
            inv.status, inv.is_duplicate
        ])
        
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=expenses_export.csv"}
    )

@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Single invoice detail — with items"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == user["id"],
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    update_data: InvoiceUpdate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Invoice update karo — Review & Edit screen se aata hai.
    OCR corrections, status change, manual edits.
    """
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == user["id"],
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Update only provided fields (partial update)
    update_dict = update_data.model_dump(exclude_unset=True, exclude={"items"})
    for field, value in update_dict.items():
        if value is not None:
            setattr(invoice, field, value)

    # Update line items agar provided hain
    if update_data.items is not None:
        # Purane items delete karo
        db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).delete()

        # Naye items add karo
        for item_data in update_data.items:
            item = InvoiceItem(
                invoice_id=invoice_id,
                description=item_data.description,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                amount=item_data.amount,
                hsn_code=item_data.hsn_code,
            )
            db.add(item)

    db.commit()
    db.refresh(invoice)

    logger.info(f"✏️ Invoice #{invoice_id} updated")
    return invoice


@router.delete("/{invoice_id}")
async def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """Invoice delete karo"""
    invoice = db.query(Invoice).filter(
        Invoice.id == invoice_id,
        Invoice.user_id == user["id"],
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    db.delete(invoice)
    db.commit()

    logger.info(f"🗑️ Invoice #{invoice_id} deleted")
    return {"message": f"Invoice #{invoice_id} deleted successfully"}
