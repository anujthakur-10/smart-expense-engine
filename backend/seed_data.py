"""
seed_data.py — Sample Data Generator
18 months ka realistic Indian SME invoice data generate karta hai.
Forecasting models ko meaningful data milta hai demo ke liye.

Run: python seed_data.py
"""

import random
from datetime import datetime, timedelta, date
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models.invoice import Invoice, InvoiceItem
from models.vendor import Vendor
import hashlib

# ── Realistic Indian SME Vendors ──────────────────────────────────
VENDORS = [
    {"name": "Sharma Kirana Store", "gstin": "09AAACH7409R1ZZ", "category": "Groceries", "state": "09"},
    {"name": "Gupta Stationery", "gstin": "09AABCU9603R1ZM", "category": "Office Supplies", "state": "09"},
    {"name": "Delhi Electronics Hub", "gstin": "07AAACH7409R1ZZ", "category": "Electronics", "state": "07"},
    {"name": "Rajesh Chai Supplier", "gstin": "09AADCR4229R1ZI", "category": "Beverages", "state": "09"},
    {"name": "Mumbai Packaging Co.", "gstin": "27AABCU9603R1ZM", "category": "Packaging", "state": "27"},
    {"name": "Verma Transport Services", "gstin": "09AABCV1234R1ZK", "category": "Transport", "state": "09"},
    {"name": "Agra Printing Press", "gstin": "09AABCP5678R1ZL", "category": "Printing", "state": "09"},
    {"name": "Noida IT Solutions", "gstin": "09AABCN9012R1ZN", "category": "IT Services", "state": "09"},
    {"name": "Jaipur Textile Traders", "gstin": "08AABCJ3456R1ZP", "category": "Textiles", "state": "08"},
    {"name": "Lucknow Food Supplies", "gstin": "09AABCL7890R1ZQ", "category": "Food", "state": "09"},
]

# Realistic items per vendor category
ITEMS_BY_CATEGORY = {
    "Groceries": [
        ("Aata (Wheat Flour) 10kg", 380, 450),
        ("Rice Basmati 5kg", 350, 500),
        ("Sugar 5kg", 200, 280),
        ("Cooking Oil 5L", 600, 800),
        ("Dal Arhar 2kg", 180, 260),
        ("Namkeen packets", 50, 150),
    ],
    "Office Supplies": [
        ("A4 Paper Ream (500 sheets)", 250, 350),
        ("Pen Set (10 pcs)", 100, 200),
        ("Notebooks (dozen)", 300, 500),
        ("Printer Ink Cartridge", 800, 1500),
        ("Stapler + Pins", 150, 250),
    ],
    "Electronics": [
        ("LED Bulb Pack (10)", 500, 800),
        ("Extension Board", 300, 600),
        ("USB Cable Set", 200, 400),
        ("Calculator", 250, 500),
    ],
    "Beverages": [
        ("Chai Patti 1kg", 300, 500),
        ("Coffee Powder 500g", 250, 400),
        ("Disposable Cups (100)", 80, 150),
        ("Sugar Sachets (box)", 100, 200),
    ],
    "Packaging": [
        ("Carry Bags (100 pcs)", 200, 400),
        ("Bubble Wrap Roll", 300, 600),
        ("Tape Rolls (dozen)", 150, 300),
        ("Corrugated Boxes (25)", 500, 1000),
    ],
    "Transport": [
        ("Local Delivery", 500, 1500),
        ("Inter-city Freight", 2000, 5000),
        ("Courier Charges", 200, 800),
    ],
    "Printing": [
        ("Visiting Cards (500)", 300, 600),
        ("Letterheads (100)", 400, 800),
        ("Invoice Books (5)", 250, 500),
        ("Banner Printing", 500, 1500),
    ],
    "IT Services": [
        ("Internet Monthly", 800, 1500),
        ("Cloud Hosting", 500, 2000),
        ("Software License", 1000, 5000),
        ("Computer Repair", 500, 3000),
    ],
    "Textiles": [
        ("Cloth Material (meter)", 200, 800),
        ("Uniform Set", 500, 1200),
        ("Curtain Fabric", 300, 900),
    ],
    "Food": [
        ("Snacks Wholesale", 500, 1500),
        ("Biscuit Cartons", 300, 800),
        ("Mineral Water (cases)", 200, 600),
        ("Juice Packs (dozen)", 250, 500),
    ],
}

GST_RATES = [5, 12, 18, 28]


def generate_hash(vendor_name, invoice_number, total_amount):
    parts = [vendor_name.lower(), str(invoice_number).lower(), str(total_amount)]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def seed_database(user_id: str = "seed-demo-user-001"):
    """
    18 months ka sample data generate karta hai.

    Args:
        user_id: User ID jiske liye data create hona hai.
                 Supabase Auth se register karne ke baad actual user_id daal do.
    """
    db = SessionLocal()

    try:
        # Check if data already exists
        existing = db.query(Invoice).filter(Invoice.user_id == user_id).count()
        if existing > 0:
            print(f"⚠️  Data already exists ({existing} invoices). Skipping seed.")
            return

        print("🌱 Seeding database with 18 months of sample data...")

        # Create vendors
        vendor_ids = {}
        for v_data in VENDORS:
            vendor = Vendor(
                user_id=user_id,
                name=v_data["name"],
                gstin=v_data["gstin"],
                state_code=v_data["state"],
                category=v_data["category"],
            )
            db.add(vendor)
            db.flush()
            vendor_ids[v_data["name"]] = vendor.id

        # Generate invoices for 18 months
        start_date = datetime.now() - timedelta(days=18 * 30)
        invoice_count = 0

        for month_offset in range(18):
            # Month ka first day
            month_date = start_date + timedelta(days=month_offset * 30)

            # Har month mein 8-15 invoices
            num_invoices = random.randint(8, 15)

            # Festive season (Oct-Nov) mein zyada spending
            if month_date.month in [10, 11]:
                num_invoices = random.randint(12, 20)

            for _ in range(num_invoices):
                # Random vendor choose karo
                vendor_data = random.choice(VENDORS)
                vendor_name = vendor_data["name"]
                category = vendor_data["category"]
                vendor_state = vendor_data["state"]

                # Random date within the month
                day = random.randint(1, 28)
                try:
                    inv_date = date(month_date.year, month_date.month, day)
                except ValueError:
                    inv_date = date(month_date.year, month_date.month, 28)

                # Generate line items
                available_items = ITEMS_BY_CATEGORY.get(category, [("Generic Item", 100, 500)])
                num_items = random.randint(1, min(4, len(available_items)))
                selected_items = random.sample(available_items, num_items)

                subtotal = 0
                invoice_items = []

                for item_name, price_min, price_max in selected_items:
                    qty = random.randint(1, 10)
                    unit_price = round(random.uniform(price_min, price_max), 2)
                    amount = round(qty * unit_price, 2)
                    subtotal += amount

                    invoice_items.append({
                        "description": item_name,
                        "quantity": qty,
                        "unit_price": unit_price,
                        "amount": amount,
                    })

                # GST calculate karo
                gst_rate = random.choice(GST_RATES)
                buyer_state = "09"  # Default: UP (buyer ka state)

                is_inter_state = vendor_state != buyer_state
                if is_inter_state:
                    igst = round(subtotal * gst_rate / 100, 2)
                    cgst = 0.0
                    sgst = 0.0
                else:
                    half_rate = gst_rate / 2
                    cgst = round(subtotal * half_rate / 100, 2)
                    sgst = round(subtotal * half_rate / 100, 2)
                    igst = 0.0

                total_amount = round(subtotal + cgst + sgst + igst, 2)

                # Invoice number generate karo
                invoice_number = f"INV-{inv_date.strftime('%Y%m')}-{random.randint(1000, 9999)}"

                invoice_hash = generate_hash(vendor_name, invoice_number, total_amount)

                # Invoice create karo
                invoice = Invoice(
                    user_id=user_id,
                    invoice_number=invoice_number,
                    vendor_id=vendor_ids.get(vendor_name),
                    vendor_name=vendor_name,
                    invoice_date=inv_date,
                    subtotal=subtotal,
                    cgst=cgst,
                    sgst=sgst,
                    igst=igst,
                    total_amount=total_amount,
                    gst_rate=gst_rate,
                    vendor_gstin=vendor_data["gstin"],
                    is_inter_state=is_inter_state,
                    invoice_hash=invoice_hash,
                    status=random.choice(["pending", "reviewed", "approved", "approved", "approved"]),
                    category=category,
                    ocr_confidence=round(random.uniform(0.7, 0.98), 3),
                    ocr_language=random.choice(["hi", "en", "en"]),
                )
                db.add(invoice)
                db.flush()

                # Line items add karo
                for item_data in invoice_items:
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        description=item_data["description"],
                        quantity=item_data["quantity"],
                        unit_price=item_data["unit_price"],
                        amount=item_data["amount"],
                    )
                    db.add(item)

                invoice_count += 1

        db.commit()
        print(f"✅ Seed complete! Created {len(VENDORS)} vendors and {invoice_count} invoices.")

    except Exception as e:
        db.rollback()
        print(f"❌ Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
    seed_database()
