"""
fraud_detector.py — Invoice Fraud & Duplicate Detection
Same invoice baar baar upload ho toh catch karta hai.

Detection Methods:
1. Exact Match — Same invoice_number + vendor → definite duplicate
2. Fuzzy Match — Same vendor + amount + date within ±3 days → probable duplicate
3. Hash-based — SHA256 hash for O(1) lookup speed
"""

import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from models.invoice import Invoice
import logging

logger = logging.getLogger(__name__)


class FraudDetector:
    """
    Invoice duplicate/fraud detection engine.
    Upload hote waqt check karta hai ki ye invoice pehle toh nahi aaya.
    """

    def check_duplicate(
        self,
        db: Session,
        user_id: str,
        invoice_number: str = None,
        vendor_name: str = None,
        total_amount: float = None,
        invoice_date: str = None,
    ) -> Dict:
        """
        Naye invoice ko existing invoices se compare karta hai.

        Args:
            db: Database session
            user_id: Current user ID
            invoice_number: Extracted invoice number
            vendor_name: Extracted vendor name
            total_amount: Total invoice amount
            invoice_date: Invoice date (YYYY-MM-DD string)

        Returns:
            dict: {
                is_duplicate: bool,
                confidence: float (0.0-1.0),
                duplicate_of_id: int or None,
                match_type: "exact" | "fuzzy" | "hash" | None,
                message: str
            }
        """
        result = {
            "is_duplicate": False,
            "confidence": 0.0,
            "duplicate_of_id": None,
            "match_type": None,
            "message": "No duplicate found",
        }

        # ── Method 1: Hash-based check (fastest) ─────────────────
        invoice_hash = self._generate_hash(vendor_name, invoice_number, total_amount)
        hash_match = db.query(Invoice).filter(
            and_(
                Invoice.user_id == user_id,
                Invoice.invoice_hash == invoice_hash,
            )
        ).first()

        if hash_match:
            result.update({
                "is_duplicate": True,
                "confidence": 1.0,
                "duplicate_of_id": hash_match.id,
                "match_type": "hash",
                "message": f"⚠️ Exact duplicate found! Matches Invoice #{hash_match.id}",
            })
            logger.warning(f"🚨 Hash match found: Invoice #{hash_match.id}")
            return result

        # ── Method 2: Exact match on invoice number + vendor ──────
        if invoice_number and vendor_name:
            exact_match = db.query(Invoice).filter(
                and_(
                    Invoice.user_id == user_id,
                    func.lower(Invoice.invoice_number) == invoice_number.lower(),
                    func.lower(Invoice.vendor_name) == vendor_name.lower(),
                )
            ).first()

            if exact_match:
                result.update({
                    "is_duplicate": True,
                    "confidence": 0.95,
                    "duplicate_of_id": exact_match.id,
                    "match_type": "exact",
                    "message": f"⚠️ Duplicate detected! Same invoice number & vendor as Invoice #{exact_match.id}",
                })
                logger.warning(f"🚨 Exact match: Invoice #{exact_match.id}")
                return result

        # ── Method 3: Fuzzy match — same vendor + amount + nearby date ──
        if vendor_name and total_amount and total_amount > 0:
            fuzzy_query = db.query(Invoice).filter(
                and_(
                    Invoice.user_id == user_id,
                    func.lower(Invoice.vendor_name) == vendor_name.lower(),
                    Invoice.total_amount == total_amount,
                )
            )

            # Date range check — ±3 days ke andar
            if invoice_date:
                try:
                    inv_date = datetime.strptime(invoice_date, "%Y-%m-%d").date()
                    date_start = inv_date - timedelta(days=3)
                    date_end = inv_date + timedelta(days=3)
                    fuzzy_query = fuzzy_query.filter(
                        Invoice.invoice_date.between(date_start, date_end)
                    )
                except ValueError:
                    pass

            fuzzy_match = fuzzy_query.first()

            if fuzzy_match:
                result.update({
                    "is_duplicate": True,
                    "confidence": 0.75,
                    "duplicate_of_id": fuzzy_match.id,
                    "match_type": "fuzzy",
                    "message": (
                        f"⚠️ Probable duplicate! Same vendor ({vendor_name}), "
                        f"same amount (₹{total_amount}), similar date — "
                        f"matches Invoice #{fuzzy_match.id}"
                    ),
                })
                logger.warning(f"🚨 Fuzzy match: Invoice #{fuzzy_match.id}")
                return result

        return result

    def _generate_hash(
        self,
        vendor_name: str = None,
        invoice_number: str = None,
        total_amount: float = None,
    ) -> str:
        """
        Invoice ka unique SHA256 hash generate karta hai.
        Combination: vendor_name + invoice_number + total_amount
        Fast O(1) duplicate lookup ke liye.
        """
        parts = [
            (vendor_name or "").lower().strip(),
            (invoice_number or "").lower().strip(),
            str(total_amount or 0),
        ]
        combined = "|".join(parts)
        return hashlib.sha256(combined.encode()).hexdigest()

    def generate_invoice_hash(
        self,
        vendor_name: str = None,
        invoice_number: str = None,
        total_amount: float = None,
    ) -> str:
        """Public method — invoice save karte waqt hash generate karo"""
        return self._generate_hash(vendor_name, invoice_number, total_amount)
