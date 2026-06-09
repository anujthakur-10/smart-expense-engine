"""
gst_engine.py — Indian GST Calculation Engine
CGST/SGST/IGST split, GSTIN validation, state code mapping.
Indian tax rules ke according sab handle karta hai.

Rules:
- Intra-state (same state) → CGST + SGST (rate/2 each)
- Inter-state (different states) → IGST (full rate)
- Valid GST rates: 0%, 5%, 12%, 18%, 28%
"""

import re
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class GSTEngine:
    """
    Indian GST Calculator + Validator.
    CGST/SGST/IGST automatically split karta hai.
    """

    # Standard GST slabs in India
    VALID_RATES = [0, 5, 12, 18, 28]

    # ── Indian State Codes (Census 2011) ──────────────────────────
    # GSTIN ke pehle 2 digits state code hote hain
    STATE_CODES = {
        "01": "Jammu & Kashmir", "02": "Himachal Pradesh",
        "03": "Punjab", "04": "Chandigarh",
        "05": "Uttarakhand", "06": "Haryana",
        "07": "Delhi", "08": "Rajasthan",
        "09": "Uttar Pradesh", "10": "Bihar",
        "11": "Sikkim", "12": "Arunachal Pradesh",
        "13": "Nagaland", "14": "Manipur",
        "15": "Mizoram", "16": "Tripura",
        "17": "Meghalaya", "18": "Assam",
        "19": "West Bengal", "20": "Jharkhand",
        "21": "Odisha", "22": "Chhattisgarh",
        "23": "Madhya Pradesh", "24": "Gujarat",
        "25": "Daman & Diu", "26": "Dadra & Nagar Haveli",
        "27": "Maharashtra", "28": "Andhra Pradesh",
        "29": "Karnataka", "30": "Goa",
        "31": "Lakshadweep", "32": "Kerala",
        "33": "Tamil Nadu", "34": "Puducherry",
        "35": "Andaman & Nicobar", "36": "Telangana",
        "37": "Andhra Pradesh (New)", "38": "Ladakh",
    }

    # GSTIN format: 2 digits + 5 alpha + 4 digits + 1 alpha + 1 alphanum + Z + 1 alphanum
    GSTIN_REGEX = re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$')

    def calculate_gst(
        self,
        subtotal: float,
        gst_rate: float,
        seller_state_code: str = None,
        buyer_state_code: str = None,
    ) -> Dict:
        """
        GST calculate karta hai — CGST/SGST ya IGST.

        Args:
            subtotal: Amount before tax (taxable value)
            gst_rate: GST rate percentage (5, 12, 18, or 28)
            seller_state_code: Seller ka state code (GSTIN ke first 2 digits)
            buyer_state_code: Buyer ka state code

        Returns:
            dict: {cgst, sgst, igst, total_gst, total_amount, is_inter_state, gst_rate}
        """
        # Rate validate karo — nearest valid rate pe round karo
        gst_rate = self._nearest_valid_rate(gst_rate)

        # Inter-state ya intra-state decide karo
        is_inter_state = self._is_inter_state(seller_state_code, buyer_state_code)

        if is_inter_state:
            # Inter-state: Sirf IGST lagega (full rate)
            igst = round(subtotal * gst_rate / 100, 2)
            result = {
                "cgst": 0.0,
                "sgst": 0.0,
                "igst": igst,
                "total_gst": igst,
                "total_amount": round(subtotal + igst, 2),
                "is_inter_state": True,
                "gst_rate": gst_rate,
            }
        else:
            # Intra-state: CGST + SGST (rate equally split)
            half_rate = gst_rate / 2
            cgst = round(subtotal * half_rate / 100, 2)
            sgst = round(subtotal * half_rate / 100, 2)
            total_gst = cgst + sgst
            result = {
                "cgst": cgst,
                "sgst": sgst,
                "igst": 0.0,
                "total_gst": total_gst,
                "total_amount": round(subtotal + total_gst, 2),
                "is_inter_state": False,
                "gst_rate": gst_rate,
            }

        logger.info(
            f"🧮 GST calculated: ₹{subtotal} @ {gst_rate}% → "
            f"CGST=₹{result['cgst']}, SGST=₹{result['sgst']}, IGST=₹{result['igst']}"
        )
        return result

    def validate_gstin(self, gstin: str) -> Dict:
        """
        GSTIN format validate karta hai aur details extract karta hai.

        Args:
            gstin: 15 character GSTIN string

        Returns:
            dict: {is_valid, state_code, state_name, pan, entity_code, errors}
        """
        result = {
            "is_valid": False,
            "gstin": gstin,
            "state_code": None,
            "state_name": None,
            "pan": None,
            "entity_code": None,
            "errors": [],
        }

        if not gstin:
            result["errors"].append("GSTIN is empty")
            return result

        gstin = gstin.upper().strip()

        # Length check
        if len(gstin) != 15:
            result["errors"].append(f"GSTIN must be 15 characters, got {len(gstin)}")
            return result

        # Regex format check
        if not self.GSTIN_REGEX.match(gstin):
            result["errors"].append("GSTIN format is invalid")
            return result

        # State code validate karo
        state_code = gstin[:2]
        if state_code not in self.STATE_CODES:
            result["errors"].append(f"Invalid state code: {state_code}")
            return result

        # Sab theek hai — details extract karo
        result["is_valid"] = True
        result["state_code"] = state_code
        result["state_name"] = self.STATE_CODES[state_code]
        result["pan"] = gstin[2:12]         # Characters 3-12 = PAN
        result["entity_code"] = gstin[12]   # Character 13 = Entity code

        return result

    def detect_transaction_type(
        self,
        vendor_gstin: str = None,
        buyer_gstin: str = None,
    ) -> Dict:
        """
        GSTIN se transaction type detect karta hai (intra/inter state).

        Returns:
            dict: {is_inter_state, seller_state, buyer_state, transaction_type}
        """
        seller_state = None
        buyer_state = None

        if vendor_gstin:
            validation = self.validate_gstin(vendor_gstin)
            if validation["is_valid"]:
                seller_state = validation["state_code"]

        if buyer_gstin:
            validation = self.validate_gstin(buyer_gstin)
            if validation["is_valid"]:
                buyer_state = validation["state_code"]

        is_inter = self._is_inter_state(seller_state, buyer_state)

        return {
            "is_inter_state": is_inter,
            "seller_state": seller_state,
            "seller_state_name": self.STATE_CODES.get(seller_state, "Unknown"),
            "buyer_state": buyer_state,
            "buyer_state_name": self.STATE_CODES.get(buyer_state, "Unknown"),
            "transaction_type": "Inter-State (IGST)" if is_inter else "Intra-State (CGST+SGST)",
        }

    def _is_inter_state(self, seller_state: str = None, buyer_state: str = None) -> bool:
        """
        Inter-state transaction check.
        Agar dono states available hain aur different hain → inter-state.
        Agar koi ek missing hai → default intra-state (safe assumption).
        """
        if seller_state and buyer_state:
            return seller_state != buyer_state
        return False  # Default: intra-state

    def _nearest_valid_rate(self, rate: float) -> float:
        """
        Given rate ko nearest valid GST slab pe round karta hai.
        E.g., 17.5 → 18, 6 → 5, 15 → 18
        """
        if rate is None or rate <= 0:
            return 0
        return min(self.VALID_RATES, key=lambda x: abs(x - rate))

    def get_state_name(self, state_code: str) -> str:
        """State code se state name return karta hai"""
        return self.STATE_CODES.get(state_code, "Unknown")
