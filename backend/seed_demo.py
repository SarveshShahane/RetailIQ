import asyncio
import os
import sys
import uuid
import struct
import zlib
import random
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone, timedelta
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

if url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

# --- Placeholder image generator ---
BASE_DIR = Path(__file__).resolve().parent
AVATARS_DIR = BASE_DIR / "uploads" / "avatars"
LOGOS_DIR = BASE_DIR / "uploads" / "logos"

def _make_png(width: int, height: int, r: int, g: int, b: int) -> bytes:
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
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.png"
    filepath = dest_dir / filename
    filepath.write_bytes(_make_png(size, size, r, g, b))
    relative = filepath.relative_to(BASE_DIR)
    return f"http://127.0.0.1:8000/{relative.as_posix()}"

# --- Data templates ---
PRODUCT_TEMPLATES = {
    "Electronics": [
        ("Wireless Mouse", 800, 1200),
        ("Mechanical Keyboard", 2500, 3999),
        ("USB-C Hub", 1200, 1899),
        ("Bluetooth Headphones", 3000, 4999),
        ("Dual Monitor Stand", 2200, 3499),
        ("FHD Webcam", 1500, 2499),
        ("Portable SSD 1TB", 6500, 8999),
        ("Smart Watch", 3500, 5999)
    ],
    "Apparel": [
        ("Slim Fit Jeans", 900, 1899),
        ("Cotton T-Shirt", 350, 699),
        ("Winter Jacket", 2200, 3999),
        ("Leather Belt", 400, 899),
        ("Running Shoes", 1800, 2999),
        ("Woolen Socks Pack", 200, 499),
        ("Baseball Cap", 250, 599),
        ("Formal Shirt", 800, 1499)
    ],
    "Grocery": [
        ("Basmati Rice 5kg", 450, 650),
        ("Organic Honey 500g", 220, 350),
        ("Green Tea 100 bags", 180, 299),
        ("Extra Virgin Olive Oil 1L", 750, 999),
        ("Whole Wheat Bread", 40, 55),
        ("Fresh Milk 1L", 55, 68),
        ("Mixed Nuts 500g", 400, 599),
        ("Premium Coffee Powder 200g", 280, 399)
    ],
    "Home Decor": [
        ("Ceramic Flower Vase", 350, 799),
        ("Table Desk Lamp", 800, 1499),
        ("Scented Candles Pack", 150, 399),
        ("Wall Clock", 500, 999),
        ("Cotton Cushion Cover Set", 300, 699),
        ("LED Strip Lights 5m", 250, 599),
        ("Indoor Planter Pot", 200, 499),
        ("Throw Blanket", 900, 1799)
    ]
}

CUSTOMER_NAMES = [
    "Rahul Verma", "Priya Nair", "Amit Patel", "Sneha Rao", "Vikram Singh",
    "Anjali Deshmukh", "Siddharth Joshi", "Pooja Hegde", "Rohan Das", "Meera Sen",
    "Arjun Kapoor", "Divya Dutta", "Karan Johar", "Shreya Ghoshal", "Vijay Kumar",
    "Kriti Sanon", "Varun Dhawan", "Aditi Rao", "Manish Malhotra", "Deepika Padukone"
]

CITIES = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Pune", "Chennai", "Kolkata", "Ahmedabad"]
STATES = ["Maharashtra", "Delhi", "Karnataka", "Telangana", "Maharashtra", "Tamil Nadu", "West Bengal", "Gujarat"]

async def seed_demo_database():
    print("Erasing database (recreating tables and RLS policies)...")
    await create_table()
    print("Tables recreated successfully.")

    async_session = async_sessionmaker(bind=async_engine, expire_on_commit=False)

    async with async_session() as session:
        print("\nSeeding Users...")
        pwd = hash_password("")
        avatar1 = _save_placeholder(AVATARS_DIR, 79, 70, 229)   # indigo
        avatar2 = _save_placeholder(AVATARS_DIR, 236, 72, 153)   # pink
        
        user1 = User(name="Demo User One", email="user1@retailiq.com", password=pwd, avatar_url=avatar1, is_verified=True)
        user2 = User(name="Demo User Two", email="user2@retailiq.com", password=pwd, avatar_url=avatar2, is_verified=True)
        
        session.add_all([user1, user2])
        await session.commit()
        print(f"Seeded Users: {user1.name} (user1@retailiq.com), {user2.name} (user2@retailiq.com)")

        businesses_to_seed = [
            # User 1 Businesses
            (user1, "Apex Retail", "27AAAAA1111A1Z1", "Electronics", "SE-"),
            (user1, "Blue Sky Mart", "27BBBBB2222B2Z2", "Grocery", "BS-"),
            (user1, "Zenith Outlets", "27CCCCC3333C3Z3", "Apparel", "ZO-"),
            (user1, "Summit Goods", "27DDDDD4444D4Z4", "Home Decor", "SG-"),
            (user1, "Velocity Store", "27EEEEE5555E5Z5", "Electronics", "VS-"),
            # User 2 Businesses
            (user2, "Pinnacle Tech", "27FFFFF6666F6Z6", "Electronics", "PT-"),
            (user2, "Horizon Groceries", "27GGGGG7777G7Z7", "Grocery", "HG-"),
            (user2, "Vista Apparel", "27HHHHH8888H8Z8", "Apparel", "VA-"),
            (user2, "Nova Furnitures", "27IIIII9999I9Z9", "Home Decor", "NF-"),
            (user2, "Eco Shoppe", "27JJJJJ0000J0Z0", "Grocery", "ES-")
        ]

        for owner, b_name, gst, b_type, prefix in businesses_to_seed:
            print(f"\nSeeding Business: {b_name} for {owner.name}...")
            logo_color = (random.randint(50, 200), random.randint(50, 200), random.randint(50, 200))
            logo_url = _save_placeholder(LOGOS_DIR, *logo_color)
            
            business = Business(
                user_id=owner.id,
                name=b_name,
                gst_number=gst,
                phone=f"9876{random.randint(100000, 999999)}",
                email=f"info@{b_name.lower().replace(' ', '')}.com",
                address=f"{random.randint(10, 500)}, Main St, Sector {random.randint(1, 15)}",
                city=CITIES[businesses_to_seed.index((owner, b_name, gst, b_type, prefix)) % len(CITIES)],
                state=STATES[businesses_to_seed.index((owner, b_name, gst, b_type, prefix)) % len(STATES)],
                country="India",
                postal_code=str(random.randint(400001, 400099)),
                logo_url=logo_url,
                invoice_prefix=prefix,
                currency="INR",
                timezone="Asia/Kolkata"
            )
            session.add(business)
            await session.commit()

            # Seed Products
            print(f"  Adding Products...")
            products = []
            category_templates = PRODUCT_TEMPLATES.get(b_type, PRODUCT_TEMPLATES["Grocery"])
            for p_name, orig, sell in category_templates:
                product = Product(
                    name=p_name,
                    business_id=business.id,
                    original_price=Decimal(orig),
                    selling_price=Decimal(sell),
                    stock=random.randint(5, 100),
                    sku=f"{prefix[:2]}{random.randint(100, 999)}",
                    barcode=f"890123{random.randint(1000000, 9999999)}",
                    category=b_type,
                    description=f"High quality {p_name.lower()} perfect for business and personal use."
                )
                products.append(product)
            session.add_all(products)
            await session.commit()

            # Seed Customers
            print(f"  Adding Customers...")
            customers = []
            for name in CUSTOMER_NAMES:
                cust_phone = f"+9198{random.randint(10000000, 99999999)}"
                customer = Customer(
                    business_id=business.id,
                    name=name,
                    phone_number_country_code="+91",
                    phone_number=cust_phone[3:],
                    email=f"{name.lower().replace(' ', '')}@example.com"
                )
                session.add(customer)
                await session.commit()

                # Add customer address
                addr = CustomerAddress(
                    customer_id=customer.id,
                    line1=f"Flat {random.randint(101, 1205)}, Building {random.choice(['A','B','C'])}",
                    line2=f"Near Landmark {random.randint(1, 10)}",
                    city=business.city,
                    state=business.state,
                    country=business.country,
                    postal_code=business.postal_code
                )
                session.add(addr)
                customers.append(customer)
            await session.commit()

            # Seed Invoices (Sales distribution over the last 30 days)
            invoice_count = random.randint(120, 180)
            print(f"  Seeding {invoice_count} Invoices...")
            
            invoices = []
            base_date = datetime.now(timezone.utc) - timedelta(days=30)
            
            for i in range(invoice_count):
                day_offset = random.randint(0, 30)
                inv_date = base_date + timedelta(
                    days=day_offset,
                    hours=random.randint(9, 21),
                    minutes=random.randint(0, 59)
                )
                
                is_weekend = inv_date.weekday() in [4, 5, 6]
                item_count = random.randint(1, 3)
                if is_weekend:
                    item_count = random.randint(2, 4)
                
                customer = random.choice(customers)
                
                rand_status = random.random()
                if rand_status < 0.85:
                    status = InvoiceStatus.PAID
                elif rand_status < 0.95:
                    status = InvoiceStatus.PENDING
                else:
                    status = InvoiceStatus.DRAFT
                
                invoice = Invoice(
                    business_id=business.id,
                    customer_id=customer.id,
                    status=status,
                    source=InvoiceSource.ONLINE,
                    subtotal=Decimal('0.00'),
                    tax=Decimal('0.00'),
                    discount=Decimal('0.00'),
                    total=Decimal('0.00'),
                    notes="Thank you for shopping with us!",
                    created_at=inv_date,
                    updated_at=inv_date
                )
                session.add(invoice)
                await session.commit()
                
                subtotal = Decimal('0.00')
                chosen_products = random.sample(products, min(item_count, len(products)))
                
                for prod in chosen_products:
                    qty = random.randint(1, 3)
                    if is_weekend:
                        qty = random.randint(1, 5)
                        
                    item = InvoiceItem(
                        invoice_id=invoice.id,
                        product_id=prod.id,
                        quantity=qty
                    )
                    session.add(item)
                    subtotal += prod.selling_price * qty
                
                tax = subtotal * Decimal('0.18')
                total = subtotal + tax
                
                invoice.subtotal = subtotal
                invoice.tax = tax
                invoice.total = total
                
                if status == InvoiceStatus.PAID:
                    payment = Payment(
                        business_id=business.id,
                        method=random.choice(list(PaymentMethod)),
                        status="COMPLETED",
                        amount=total,
                        paid_at=inv_date,
                        created_at=inv_date
                    )
                    session.add(payment)
                    await session.commit()
                    invoice.payment_id = payment.id
                
                await session.commit()

        print("\nAll businesses, products, customers, and invoices successfully seeded!")
        await engine.dispose()

if __name__ == '__main__':
    asyncio.run(seed_demo_database())
