"""
upload.py — File Upload + OCR Processing Router
POST /api/upload → Full pipeline:
  Save file → Preprocess → OCR → Parse → GST → Fraud Check → Save to DB
"""

import os
import cv2
import numpy as np
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime

from database import get_db
from auth import get_current_user
from models.invoice import Invoice, InvoiceItem
from models.vendor import Vendor
from schemas.invoice import UploadResponse, InvoiceResponse, OCRResult
from services.image_preprocessor import ImagePreprocessor
from services.pdf_processor import PDFProcessor
from services.ocr_engine import OCREngine
from services.invoice_parser import InvoiceParser
from services.gst_engine import GSTEngine
from services.fraud_detector import FraudDetector
from services.storage import StorageService
from config import get_settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/upload", tags=["Upload"])
settings = get_settings()

# Service instances
preprocessor = ImagePreprocessor()
pdf_processor = PDFProcessor()
ocr_engine = OCREngine(confidence_threshold=settings.OCR_CONFIDENCE_THRESHOLD)
invoice_parser = InvoiceParser()
gst_engine = GSTEngine()
fraud_detector = FraudDetector()
storage_service = StorageService()


@router.post("/", response_model=UploadResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    """
    Invoice file upload karo — OCR + parsing + GST + fraud check sab automatic.

    Accepts: JPEG, PNG, WebP, PDF (multi-page)

    Returns: Extracted invoice data with fraud warnings
    """
    user_id = user["id"]

    # ── Step 1: File validation ───────────────────────────────────
    filename = file.filename or "unknown"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{ext}' not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}",
        )

    # Read file bytes
    file_bytes = await file.read()
    file_size_mb = len(file_bytes) / (1024 * 1024)

    if file_size_mb > settings.MAX_UPLOAD_SIZE_MB:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large ({file_size_mb:.1f}MB). Max: {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    logger.info(f"📤 Upload received: {filename} ({file_size_mb:.1f}MB)")

    # ── Step 2: Upload to Supabase Storage ────────────────────────
    content_type = file.content_type or "application/octet-stream"
    file_url, storage_path = await storage_service.upload_file(
        file_bytes, filename, user_id, content_type
    )

    # ── Step 3: Convert to images ─────────────────────────────────
    if ext == ".pdf":
        # PDF → multiple images
        images = pdf_processor.pdf_bytes_to_images(file_bytes)
        page_count = len(images)
        file_type = "pdf"
    else:
        # Single image
        nparr = np.frombuffer(file_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not decode image file. Please upload a valid image.",
            )
        images = [image]
        page_count = 1
        file_type = ext.replace(".", "")

    # ── Step 4: Preprocess images ─────────────────────────────────
    preprocessed_images = []
    for img in images:
        try:
            processed = preprocessor.preprocess(img)
            # OCR needs color or grayscale — convert back if needed
            if len(processed.shape) == 2:
                processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
            preprocessed_images.append(processed)
        except Exception as e:
            logger.warning(f"⚠️ Preprocessing failed for a page: {e}")
            preprocessed_images.append(img)  # Use original as fallback

    # ── Step 5: OCR Extraction ────────────────────────────────────
    if len(preprocessed_images) == 1:
        ocr_result = ocr_engine.extract_text(preprocessed_images[0])
    else:
        ocr_result = ocr_engine.extract_from_multiple_images(preprocessed_images)

    raw_text = ocr_result.get("raw_text", "")
    avg_confidence = ocr_result.get("avg_confidence", 0.0)
    detected_lang = ocr_result.get("detected_language", "en")

    logger.info(f"📝 OCR complete: {len(raw_text)} chars, confidence={avg_confidence:.2f}")

    # ── Step 6: Parse structured fields ───────────────────────────
    parsed = invoice_parser.parse(raw_text)

    # ── Step 7: GST Calculation ───────────────────────────────────
    gst_details = {}
    vendor_gstin = parsed.get("vendor_gstin")
    buyer_gstin = parsed.get("buyer_gstin")

    if parsed.get("subtotal", 0) > 0 and parsed.get("gst_rate"):
        # State codes extract karo from GSTINs
        seller_state = vendor_gstin[:2] if vendor_gstin and len(vendor_gstin) >= 2 else None
        buyer_state = buyer_gstin[:2] if buyer_gstin and len(buyer_gstin) >= 2 else None

        gst_details = gst_engine.calculate_gst(
            subtotal=parsed["subtotal"],
            gst_rate=parsed["gst_rate"],
            seller_state_code=seller_state,
            buyer_state_code=buyer_state,
        )
        # Update parsed values with calculated GST
        parsed["cgst"] = gst_details.get("cgst", parsed.get("cgst", 0))
        parsed["sgst"] = gst_details.get("sgst", parsed.get("sgst", 0))
        parsed["igst"] = gst_details.get("igst", parsed.get("igst", 0))
    else:
        gst_details = {
            "cgst": parsed.get("cgst", 0),
            "sgst": parsed.get("sgst", 0),
            "igst": parsed.get("igst", 0),
            "gst_rate": parsed.get("gst_rate"),
            "is_inter_state": False,
        }

    # ── Step 8: Fraud/Duplicate Check ─────────────────────────────
    fraud_check = fraud_detector.check_duplicate(
        db=db,
        user_id=user_id,
        invoice_number=parsed.get("invoice_number"),
        vendor_name=parsed.get("vendor_name"),
        total_amount=parsed.get("total_amount", 0),
        invoice_date=parsed.get("invoice_date"),
    )

    # ── Step 9: Find or create vendor ─────────────────────────────
    vendor_id = None
    vendor_name = parsed.get("vendor_name")
    if vendor_name:
        existing_vendor = db.query(Vendor).filter(
            Vendor.user_id == user_id,
            Vendor.name == vendor_name,
        ).first()

        if existing_vendor:
            vendor_id = existing_vendor.id
        else:
            new_vendor = Vendor(
                user_id=user_id,
                name=vendor_name,
                gstin=vendor_gstin,
                state_code=vendor_gstin[:2] if vendor_gstin and len(vendor_gstin) >= 2 else None,
            )
            db.add(new_vendor)
            db.flush()
            vendor_id = new_vendor.id

    # ── Step 10: Save Invoice to Database ─────────────────────────
    invoice_hash = fraud_detector.generate_invoice_hash(
        vendor_name=vendor_name,
        invoice_number=parsed.get("invoice_number"),
        total_amount=parsed.get("total_amount", 0),
    )

    # Parse date string to date object
    invoice_date = None
    if parsed.get("invoice_date"):
        try:
            invoice_date = datetime.strptime(parsed["invoice_date"], "%Y-%m-%d").date()
        except ValueError:
            pass

    invoice = Invoice(
        user_id=user_id,
        invoice_number=parsed.get("invoice_number"),
        vendor_id=vendor_id,
        vendor_name=vendor_name,
        invoice_date=invoice_date,
        file_url=file_url,
        file_name=filename,
        file_type=file_type,
        page_count=page_count,
        raw_ocr_text=raw_text,
        ocr_confidence=avg_confidence,
        ocr_language=detected_lang,
        subtotal=parsed.get("subtotal", 0),
        cgst=parsed.get("cgst", 0),
        sgst=parsed.get("sgst", 0),
        igst=parsed.get("igst", 0),
        total_amount=parsed.get("total_amount", 0),
        gst_rate=parsed.get("gst_rate"),
        vendor_gstin=vendor_gstin,
        buyer_gstin=buyer_gstin,
        is_inter_state=gst_details.get("is_inter_state", False),
        is_duplicate=fraud_check.get("is_duplicate", False),
        duplicate_of_id=fraud_check.get("duplicate_of_id"),
        duplicate_confidence=fraud_check.get("confidence", 0),
        invoice_hash=invoice_hash,
        status="pending",
    )

    db.add(invoice)
    db.flush()

    # Line items save karo
    for item_data in parsed.get("line_items", []):
        item = InvoiceItem(
            invoice_id=invoice.id,
            description=item_data.get("description"),
            quantity=item_data.get("quantity", 1),
            unit_price=item_data.get("unit_price", 0),
            amount=item_data.get("amount", 0),
            hsn_code=item_data.get("hsn_code"),
        )
        db.add(item)

    db.commit()
    db.refresh(invoice)

    logger.info(f"✅ Invoice #{invoice.id} saved successfully!")

    # ── Build Response ────────────────────────────────────────────
    return UploadResponse(
        invoice=InvoiceResponse.model_validate(invoice),
        ocr_result=OCRResult(
            raw_text=raw_text,
            confidence=avg_confidence,
            language=detected_lang,
            extracted_fields=parsed,
            line_items=parsed.get("line_items", []),
        ),
        fraud_check=fraud_check,
        gst_details=gst_details,
        message="Invoice processed successfully!" if not fraud_check["is_duplicate"]
                else f"⚠️ {fraud_check['message']}",
    )
