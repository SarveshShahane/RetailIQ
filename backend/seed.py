import asyncio
import os
import sys
import uuid
import struct
import zlib
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
from dotenv import load_dotenv

# Add the current directory to sys.path to allow imports from local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import text

# Import Base and recreate function
from db.database import Base, async_engine
from models.user import create_table

# Import Models
from models.user import User, Business
from models.products import Product
from models.invoice import Customer, CustomerAddress, Payment, Invoice, InvoiceItem, InvoiceStatus, PaymentMethod, InvoiceSource
from services.auth import hash_password

load_dotenv()
url = os.getenv('DATABASE_URL')
if not url:
    print("Error: DATABASE_URL not set in environment.")
    sys.exit(1)

# --- Placeholder image generator (minimal valid PNG) ---
BASE_DIR = Path(__file__).resolve().parent
AVATARS_DIR = BASE_DIR / "uploads" / "avatars"
LOGOS_DIR = BASE_DIR / "uploads" / "logos"


def _make_png(width: int, height: int, r: int, g: int, b: int) -> bytes:
    """Generate a minimal valid single-color PNG image in pure Python."""
    def chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = chunk(b"IHDR", ihdr_data)
    raw_row = b"\x00" + bytes([r, g, b]) * width
    raw = raw_row * height
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return header + ihdr + idat + iend


def _save_placeholder(dest_dir: Path, r: int, g: int, b: int, size: int = 128) -> str:
    """Save a colored placeholder PNG and return its URL path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filepath = dest_dir / filename
    filepath.write_bytes(_make_png(size, size, r, g, b))
    relative = filepath.relative_to(BASE_DIR)
    return f"http://127.0.0.1:8000/{relative.as_posix()}"


async def seed_database():
    print("Recreating database tables and RLS policies...")
    await create_table()
    print("Tables recreated successfully.")

    # Create an async session for database insertions
    async_session = async_sessionmaker(bind=async_engine, expire_on_commit=False)

    async with async_session() as session:
        print("\nSeeding Users...")
        # 1. Add Users
        pwd = hash_password("Password123")
        avatar1 = _save_placeholder(AVATARS_DIR, 79, 70, 229)   # indigo
        avatar2 = _save_placeholder(AVATARS_DIR, 236, 72, 153)   # pink
        user1 = User(name="Aarav Sharma", email="aarav@retailiq.com", password=pwd, avatar_url=avatar1)
        user2 = User(name="Neha Gupta", email="neha@retailiq.com", password=pwd, avatar_url=avatar2)
        
        session.add_all([user1, user2])
        await session.commit()
        print(f"Seeded users: {user1.name} (ID: {user1.id}), {user2.name} (ID: {user2.id})")

        print("\nSeeding Businesses...")
        # 2. Add Businesses
        logo_se = _save_placeholder(LOGOS_DIR, 59, 130, 246)   # blue
        b1 = Business(
            user_id=user1.id,
            name="Sharma Electronics",
            gst_number="27AAAAA1111A1Z1",
            phone="9876543210",
            email="info@sharmaelectronics.com",
            address="101, Electronic Market, Lamington Road, Grant Road",
            city="Mumbai",
            state="Maharashtra",
            country="India",
            postal_code="400007",
            logo_url=logo_se,
            invoice_prefix="SE-",
            currency="INR",
            timezone="Asia/Kolkata"
        )
        logo_sp = _save_placeholder(LOGOS_DIR, 34, 197, 94)    # green
        b2 = Business(
            user_id=user1.id,
            name="Sharma Provisions",
            gst_number="27BBBBB2222B2Z2",
            phone="9876543211",
            email="store@sharmaprovisions.com",
            address="Shop No. 4, Juhu Tara Road",
            city="Mumbai",
            state="Maharashtra",
            country="India",
            postal_code="400049",
            logo_url=logo_sp,
            invoice_prefix="SP-",
            currency="INR",
            timezone="Asia/Kolkata"
        )
        logo_gf = _save_placeholder(LOGOS_DIR, 245, 158, 11)   # amber
        b3 = Business(
            user_id=user2.id,
            name="Gupta Furnishings",
            gst_number="07CCCCC3333C3Z3",
            phone="9911223344",
            email="contact@guptafurnishings.com",
            address="Plot 12, Kirti Nagar Industrial Area",
            city="New Delhi",
            state="Delhi",
            country="India",
            postal_code="110015",
            logo_url=logo_gf,
            invoice_prefix="GF-",
            currency="INR",
            timezone="Asia/Kolkata"
        )
        session.add_all([b1, b2, b3])
        await session.commit()
        print(f"Seeded Businesses: {b1.name} (ID: {b1.id}), {b2.name} (ID: {b2.id}), {b3.name} (ID: {b3.id})")

        print("\nSeeding Products...")
        # 3. Add Products
        # Sharma Electronics Products
        p_se_1 = Product(business_id=b1.id, name="Smart LED Bulb", original_price=Decimal("150.00"), selling_price=Decimal("249.00"), stock=80, sku="SKU-LED-001", barcode="890123456001", category="Electronics", description="Smart LED bulb with RGB colors")
        p_se_2 = Product(business_id=b1.id, name="Wireless Mouse", original_price=Decimal("400.00"), selling_price=Decimal("699.00"), stock=50, sku="SKU-WM-002", barcode="890123456002", category="Electronics", description="Ergonomic 2.4GHz wireless mouse")
        p_se_3 = Product(business_id=b1.id, name="Type-C Charging Cable", original_price=Decimal("100.00"), selling_price=Decimal("199.00"), stock=150, sku="SKU-CABLE-003", barcode="890123456003", category="Electronics", description="Braided fast charging Type-C cable")
        p_se_4 = Product(business_id=b1.id, name="Bluetooth Speaker", original_price=Decimal("1200.00"), selling_price=Decimal("1899.00"), stock=20, sku="SKU-SPK-004", barcode="890123456004", category="Electronics", description="Portable waterproof bluetooth speaker")
        p_se_5 = Product(business_id=b1.id, name="Power Bank 10000mAh", original_price=Decimal("800.00"), selling_price=Decimal("1299.00"), stock=35, sku="SKU-PB-005", barcode="890123456005", category="Electronics", description="Fast charging compact power bank")

        # Sharma Provisions Products
        p_sp_1 = Product(business_id=b2.id, name="Basmati Rice 5kg", original_price=Decimal("450.00"), selling_price=Decimal("599.00"), stock=60, sku="SKU-RICE-001", barcode="890123456101", category="Groceries", description="Premium long grain basmati rice")
        p_sp_2 = Product(business_id=b2.id, name="Sunflower Oil 1L", original_price=Decimal("120.00"), selling_price=Decimal("159.00"), stock=100, sku="SKU-OIL-002", barcode="890123456102", category="Groceries", description="Refined sunflower cooking oil")
        p_sp_3 = Product(business_id=b2.id, name="Whole Wheat Atta 10kg", original_price=Decimal("380.00"), selling_price=Decimal("449.00"), stock=40, sku="SKU-ATTA-003", barcode="890123456103", category="Groceries", description="100% whole wheat flour")
        p_sp_4 = Product(business_id=b2.id, name="Organic Honey 500g", original_price=Decimal("200.00"), selling_price=Decimal("299.00"), stock=30, sku="SKU-HONEY-004", barcode="890123456104", category="Groceries", description="Pure organic honey")

        # Gupta Furnishings Products
        p_gf_1 = Product(business_id=b3.id, name="Ergonomic Office Chair", original_price=Decimal("4500.00"), selling_price=Decimal("6999.00"), stock=15, sku="SKU-CHAIR-001", barcode="890123456201", category="Furniture", description="High-back office chair with mesh support")
        p_gf_2 = Product(business_id=b3.id, name="Study Desk", original_price=Decimal("3000.00"), selling_price=Decimal("4499.00"), stock=10, sku="SKU-DESK-002", barcode="890123456202", category="Furniture", description="Wooden study desk with drawers")

        products = [p_se_1, p_se_2, p_se_3, p_se_4, p_se_5, p_sp_1, p_sp_2, p_sp_3, p_sp_4, p_gf_1, p_gf_2]
        session.add_all(products)
        await session.commit()
        print(f"Seeded {len(products)} Products.")

        print("\nSeeding Customers...")
        # 4. Add Customers
        c1 = Customer(business_id=b1.id, name="Rajesh Patel", phone_number_country_code="+91", phone_number="9876543210", email="rajesh@example.com")
        c2 = Customer(business_id=b1.id, name="Priya Nair", phone_number_country_code="+91", phone_number="9823456789", email="priya@example.com")
        c3 = Customer(business_id=b2.id, name="Amit Verma", phone_number_country_code="+91", phone_number="9812345678", email="amit@example.com")
        c4 = Customer(business_id=b3.id, name="Vikram Singh", phone_number_country_code="+91", phone_number="9911223344", email="vikram@example.com")
        
        session.add_all([c1, c2, c3, c4])
        await session.commit()

        # Add Addresses
        addr1 = CustomerAddress(customer_id=c1.id, line1="Flat 502, Orchid Heights", line2="Malad West", city="Mumbai", state="Maharashtra", country="India", postal_code="400064")
        addr2 = CustomerAddress(customer_id=c2.id, line1="A-12, Sector 15", line2="Vashi", city="Navi Mumbai", state="Maharashtra", country="India", postal_code="400703")
        addr3 = CustomerAddress(customer_id=c3.id, line1="23, Sea Breeze Apartments", line2="Bandra West", city="Mumbai", state="Maharashtra", country="India", postal_code="400050")
        addr4 = CustomerAddress(customer_id=c4.id, line1="Flat C-12, Green Meadows", line2="Noida Expressway", city="Noida", state="Uttar Pradesh", country="India", postal_code="201301")

        session.add_all([addr1, addr2, addr3, addr4])
        await session.commit()
        print(f"Seeded {len([c1, c2, c3, c4])} Customers and their Addresses.")

        print("\nSeeding Payments & Invoices...")
        # 5. Add Invoices and Payments

        # --- Invoice 1 (Sharma Electronics, Rajesh Patel, Paid via UPI) ---
        # Items: 2x Smart LED Bulb (249.00 each), 1x Bluetooth Speaker (1899.00)
        # Subtotal: 2 * 249.00 + 1899.00 = 498.00 + 1899.00 = 2397.00
        # Tax (18% GST): 431.46
        # Discount: 100.00
        # Total: 2397.00 + 431.46 - 100.00 = 2728.46
        pay1 = Payment(business_id=b1.id, method=PaymentMethod.UPI, status="COMPLETED", amount=Decimal("2728.46"), paid_at=datetime.now(timezone.utc))
        session.add(pay1)
        await session.commit()

        inv1 = Invoice(
            business_id=b1.id,
            customer_id=c1.id,
            payment_id=pay1.id,
            status=InvoiceStatus.PAID,
            source=InvoiceSource.ONLINE,
            subtotal=Decimal("2397.00"),
            tax=Decimal("431.46"),
            discount=Decimal("100.00"),
            total=Decimal("2728.46"),
            notes="Thank you for shopping at Sharma Electronics!"
        )
        session.add(inv1)
        await session.commit()

        inv1_item1 = InvoiceItem(invoice_id=inv1.id, product_id=p_se_1.id, quantity=2)
        inv1_item2 = InvoiceItem(invoice_id=inv1.id, product_id=p_se_4.id, quantity=1)
        session.add_all([inv1_item1, inv1_item2])

        # --- Invoice 2 (Sharma Electronics, Priya Nair, Paid via CARD) ---
        # Items: 1x Wireless Mouse (699.00), 2x Type-C Charging Cable (199.00 each)
        # Subtotal: 699.00 + 2 * 199.00 = 699.00 + 398.00 = 1097.00
        # Tax (18% GST): 197.46
        # Discount: 0.00
        # Total: 1097.00 + 197.46 - 0.00 = 1294.46
        pay2 = Payment(business_id=b1.id, method=PaymentMethod.CARD, status="COMPLETED", amount=Decimal("1294.46"), paid_at=datetime.now(timezone.utc))
        session.add(pay2)
        await session.commit()

        inv2 = Invoice(
            business_id=b1.id,
            customer_id=c2.id,
            payment_id=pay2.id,
            status=InvoiceStatus.PAID,
            source=InvoiceSource.ONLINE,
            subtotal=Decimal("1097.00"),
            tax=Decimal("197.46"),
            discount=Decimal("0.00"),
            total=Decimal("1294.46"),
            notes="Please visit again!"
        )
        session.add(inv2)
        await session.commit()

        inv2_item1 = InvoiceItem(invoice_id=inv2.id, product_id=p_se_2.id, quantity=1)
        inv2_item2 = InvoiceItem(invoice_id=inv2.id, product_id=p_se_3.id, quantity=2)
        session.add_all([inv2_item1, inv2_item2])

        # --- Invoice 3 (Sharma Electronics, Rajesh Patel, PENDING) ---
        # Items: 1x Power Bank (1299.00)
        # Subtotal: 1299.00
        # Tax (18% GST): 233.82
        # Discount: 50.00
        # Total: 1299.00 + 233.82 - 50.00 = 1482.82
        inv3 = Invoice(
            business_id=b1.id,
            customer_id=c1.id,
            payment_id=None,
            status=InvoiceStatus.PENDING,
            source=InvoiceSource.ONLINE,
            subtotal=Decimal("1299.00"),
            tax=Decimal("233.82"),
            discount=Decimal("50.00"),
            total=Decimal("1482.82"),
            notes="Payment link sent to customer email."
        )
        session.add(inv3)
        await session.commit()

        inv3_item1 = InvoiceItem(invoice_id=inv3.id, product_id=p_se_5.id, quantity=1)
        session.add(inv3_item1)

        # --- Invoice 4 (Sharma Provisions, Amit Verma, Paid via CASH) ---
        # Items: 1x Basmati Rice 5kg (599.00), 2x Sunflower Oil 1L (159.00 each), 1x Organic Honey (299.00)
        # Subtotal: 599.00 + 318.00 + 299.00 = 1216.00
        # Tax (5% GST): 60.80
        # Discount: 20.00
        # Total: 1216.00 + 60.80 - 20.00 = 1256.80
        pay4 = Payment(business_id=b2.id, method=PaymentMethod.CASH, status="COMPLETED", amount=Decimal("1256.80"), paid_at=datetime.now(timezone.utc))
        session.add(pay4)
        await session.commit()

        inv4 = Invoice(
            business_id=b2.id,
            customer_id=c3.id,
            payment_id=pay4.id,
            status=InvoiceStatus.PAID,
            source=InvoiceSource.ONLINE,
            subtotal=Decimal("1216.00"),
            tax=Decimal("60.80"),
            discount=Decimal("20.00"),
            total=Decimal("1256.80"),
            notes="Healthy options for a healthy life!"
        )
        session.add(inv4)
        await session.commit()

        inv4_item1 = InvoiceItem(invoice_id=inv4.id, product_id=p_sp_1.id, quantity=1)
        inv4_item2 = InvoiceItem(invoice_id=inv4.id, product_id=p_sp_2.id, quantity=2)
        inv4_item3 = InvoiceItem(invoice_id=inv4.id, product_id=p_sp_4.id, quantity=1)
        session.add_all([inv4_item1, inv4_item2, inv4_item3])

        # --- Invoice 5 (Gupta Furnishings, Vikram Singh, Paid via UPI) ---
        # Items: 2x Ergonomic Office Chair (6999.00 each)
        # Subtotal: 2 * 6999.00 = 13998.00
        # Tax (18% GST): 2519.64
        # Discount: 500.00
        # Total: 13998.00 + 2519.64 - 500.00 = 16017.64
        pay5 = Payment(business_id=b3.id, method=PaymentMethod.UPI, status="COMPLETED", amount=Decimal("16017.64"), paid_at=datetime.now(timezone.utc))
        session.add(pay5)
        await session.commit()

        inv5 = Invoice(
            business_id=b3.id,
            customer_id=c4.id,
            payment_id=pay5.id,
            status=InvoiceStatus.PAID,
            source=InvoiceSource.ONLINE,
            subtotal=Decimal("13998.00"),
            tax=Decimal("2519.64"),
            discount=Decimal("500.00"),
            total=Decimal("16017.64"),
            notes="Custom furnishing designs by Gupta Furnishings."
        )
        session.add(inv5)
        await session.commit()

        inv5_item1 = InvoiceItem(invoice_id=inv5.id, product_id=p_gf_1.id, quantity=2)
        session.add(inv5_item1)

        await session.commit()
        print(f"Seeded {len([inv1, inv2, inv3, inv4, inv5])} Invoices and Payments.")
        print("\nDatabase seeding completed successfully!")

    await engine.dispose()

if __name__ == '__main__':
    asyncio.run(seed_database())
