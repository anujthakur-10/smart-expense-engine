"""
invoice_parser.py — OCR Text se Structured Data Extract karta hai
Regex patterns + heuristics use karke invoice fields dhundhta hai:
- Invoice number, Date, Vendor name
- Amounts (subtotal, total, GST)
- GSTIN, Line items
"""

import re
from typing import Dict, List, Optional
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)


class InvoiceParser:
    """
    Raw OCR text ko structured invoice data mein convert karta hai.
    Indian invoice formats ke liye optimized — Hindi + English support.
    """

    # ── Invoice Number Patterns ───────────────────────────────────
    INVOICE_NUM_PATTERNS = [
        r'(?:invoice\s*(?:no|number|#|num)[\s.:]*)\s*([A-Z0-9\-/]+)',
        r'(?:bill\s*(?:no|number|#|num)[\s.:]*)\s*([A-Z0-9\-/]+)',
        r'(?:receipt\s*(?:no|number|#)[\s.:]*)\s*([A-Z0-9\-/]+)',
        r'(?:inv[\s.:/-]*)\s*([A-Z0-9\-/]+)',
        r'(?:बिल\s*(?:नं|संख्या|नंबर)[\s.:]*)\s*([A-Z0-9\-/]+)',   # Hindi: बिल नं
        r'#\s*([A-Z0-9\-/]{3,})',
    ]

    # ── Date Patterns ─────────────────────────────────────────────
    DATE_PATTERNS = [
        # DD/MM/YYYY or DD-MM-YYYY
        (r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})', '%d/%m/%Y'),
        # YYYY-MM-DD (ISO format)
        (r'(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})', '%Y/%m/%d'),
        # DD Mon YYYY (e.g., 15 Jan 2024)
        (r'(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+(\d{4})', None),
    ]

    # ── Amount Patterns ───────────────────────────────────────────
    AMOUNT_PATTERNS = [
        r'(?:total|grand\s*total|net\s*amount|payable)[\s.:₹Rs]*\s*[₹]?\s*([\d,]+\.?\d*)',
        r'(?:कुल|योग|कुल\s*राशि)[\s.:₹]*\s*[₹]?\s*([\d,]+\.?\d*)',     # Hindi amounts
        r'[₹]\s*([\d,]+\.?\d*)',
        r'(?:Rs\.?|INR)\s*([\d,]+\.?\d*)',
    ]

    # ── GST Patterns ──────────────────────────────────────────────
    GST_PATTERNS = {
        'cgst': [
            r'(?:CGST|C\.G\.S\.T)[\s@]*(\d+\.?\d*)%?\s*[₹Rs.:]*\s*([\d,]+\.?\d*)',
        ],
        'sgst': [
            r'(?:SGST|S\.G\.S\.T)[\s@]*(\d+\.?\d*)%?\s*[₹Rs.:]*\s*([\d,]+\.?\d*)',
        ],
        'igst': [
            r'(?:IGST|I\.G\.S\.T)[\s@]*(\d+\.?\d*)%?\s*[₹Rs.:]*\s*([\d,]+\.?\d*)',
        ],
        'gst_rate': [
            r'(?:GST|TAX)[\s@]*(\d+\.?\d*)\s*%',
            r'(\d+\.?\d*)\s*%\s*(?:GST|TAX)',
        ],
    }

    # ── GSTIN Pattern ─────────────────────────────────────────────
    GSTIN_PATTERN = r'[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}'

    def parse(self, raw_text: str) -> Dict:
        """
        Raw OCR text se structured fields extract karta hai.

        Args:
            raw_text: OCR se mila hua text (multi-line)

        Returns:
            dict with extracted fields:
                invoice_number, invoice_date, vendor_name,
                subtotal, total_amount, cgst, sgst, igst,
                gst_rate, vendor_gstin, buyer_gstin, line_items
        """
        text_upper = raw_text.upper()
        text_clean = raw_text.strip()

        result = {
            "invoice_number": self._extract_invoice_number(text_clean),
            "invoice_date": self._extract_date(text_clean),
            "vendor_name": self._extract_vendor_name(text_clean),
            "total_amount": self._extract_total_amount(text_clean),
            "subtotal": self._extract_subtotal(text_clean),
            "gst_details": self._extract_gst(text_clean),
            "vendor_gstin": self._extract_gstin(text_clean, position="first"),
            "buyer_gstin": self._extract_gstin(text_clean, position="second"),
            "line_items": self._extract_line_items(text_clean),
        }

        # GST details unpack karo
        gst = result.pop("gst_details", {})
        result["cgst"] = gst.get("cgst_amount", 0.0)
        result["sgst"] = gst.get("sgst_amount", 0.0)
        result["igst"] = gst.get("igst_amount", 0.0)
        result["gst_rate"] = gst.get("gst_rate", None)

        # Agar subtotal nahi mila toh total se GST minus karo
        if result["subtotal"] == 0.0 and result["total_amount"] > 0:
            total_gst = result["cgst"] + result["sgst"] + result["igst"]
            result["subtotal"] = result["total_amount"] - total_gst

        logger.info(f"📋 Parsed invoice: #{result['invoice_number']} | ₹{result['total_amount']}")
        return result

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Invoice/Bill number extract karta hai"""
        for pattern in self.INVOICE_NUM_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_date(self, text: str) -> Optional[str]:
        """Date extract karta hai — multiple Indian formats support"""
        for pattern, fmt in self.DATE_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    groups = match.groups()
                    if fmt:
                        date_str = "/".join(groups)
                        parsed = datetime.strptime(date_str, fmt)
                        return parsed.strftime("%Y-%m-%d")
                    else:
                        # "15 Jan 2024" format
                        month_map = {
                            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4,
                            'may': 5, 'jun': 6, 'jul': 7, 'aug': 8,
                            'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
                        }
                        day = int(groups[0])
                        month = month_map.get(groups[1][:3].lower(), 1)
                        year = int(groups[2])
                        return f"{year}-{month:02d}-{day:02d}"
                except (ValueError, KeyError):
                    continue
        return None

    def _extract_vendor_name(self, text: str) -> Optional[str]:
        """
        Vendor name extract karta hai — usually invoice ke top pe hota hai.
        Heuristic: First non-empty line jo number/date nahi hai.
        """
        lines = text.strip().split("\n")
        for line in lines[:5]:  # First 5 lines mein dhundho
            line = line.strip()
            if not line or len(line) < 3:
                continue
            # Skip lines that are mostly numbers or dates
            if re.match(r'^[\d\s/\-.:]+$', line):
                continue
            # Skip GST/tax related lines
            if re.search(r'(GST|CGST|SGST|IGST|TAX|INVOICE|BILL|RECEIPT|DATE)', line, re.IGNORECASE):
                continue
            return line
        return None

    def _extract_total_amount(self, text: str) -> float:
        """Total/Grand Total amount extract karta hai"""
        for pattern in self.AMOUNT_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Sabse bada amount lo (usually total hi sabse bada hota hai)
                amounts = []
                for match in matches:
                    try:
                        amount = float(match.replace(",", ""))
                        amounts.append(amount)
                    except ValueError:
                        continue
                if amounts:
                    return max(amounts)
        return 0.0

    def _extract_subtotal(self, text: str) -> float:
        """Subtotal (before tax) amount extract karta hai"""
        patterns = [
            r'(?:sub\s*total|subtotal|taxable\s*(?:value|amount))[\s.:₹Rs]*\s*[₹]?\s*([\d,]+\.?\d*)',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    continue
        return 0.0

    def _extract_gst(self, text: str) -> Dict:
        """CGST, SGST, IGST amounts aur rate extract karta hai"""
        result = {
            "cgst_amount": 0.0,
            "sgst_amount": 0.0,
            "igst_amount": 0.0,
            "gst_rate": None,
        }

        for tax_type, patterns in self.GST_PATTERNS.items():
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    try:
                        if tax_type == "gst_rate":
                            result["gst_rate"] = float(match.group(1))
                        else:
                            rate = float(match.group(1))
                            amount = float(match.group(2).replace(",", ""))
                            result[f"{tax_type}_amount"] = amount
                            if result["gst_rate"] is None:
                                # CGST/SGST rate * 2 = total GST rate
                                if tax_type in ("cgst", "sgst"):
                                    result["gst_rate"] = rate * 2
                                else:
                                    result["gst_rate"] = rate
                    except (ValueError, IndexError):
                        continue

        return result

    def _extract_gstin(self, text: str, position: str = "first") -> Optional[str]:
        """
        GSTIN extract karta hai.
        position="first" → vendor ka GSTIN (usually pehle aata hai)
        position="second" → buyer ka GSTIN
        """
        matches = re.findall(self.GSTIN_PATTERN, text)
        if not matches:
            return None
        if position == "first":
            return matches[0]
        elif position == "second" and len(matches) > 1:
            return matches[1]
        return None

    def _extract_line_items(self, text: str) -> List[Dict]:
        """
        Invoice line items extract karta hai.
        Pattern: Description ... Qty ... Rate ... Amount
        """
        items = []
        # Look for lines with number patterns that could be items
        lines = text.split("\n")

        for line in lines:
            # Pattern: text followed by numbers (qty, rate, amount)
            match = re.search(
                r'(.{3,}?)\s+(\d+\.?\d*)\s+[xX×]?\s*[₹Rs.]*\s*(\d+\.?\d*)\s+[₹Rs.]*\s*([\d,]+\.?\d*)',
                line
            )
            if match:
                items.append({
                    "description": match.group(1).strip(),
                    "quantity": float(match.group(2)),
                    "unit_price": float(match.group(3)),
                    "amount": float(match.group(4).replace(",", "")),
                })

        return items
