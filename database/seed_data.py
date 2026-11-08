"""
Autonomous Data Analyst - Enterprise Seed Data Generator
Simulates realistic Iranian E-Commerce transactions with strict temporal logic,
referential integrity, financial consistency, and RBAC security verification.
"""

import os
import sys
import time
import random
from decimal import Decimal
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values
from faker import Faker
from dotenv import load_dotenv
from tqdm import tqdm

# Load environment variables
load_dotenv()

# =============================================================================
# CONFIGURATION & ENVIRONMENT VARIABLES
# =============================================================================
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres_db")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "ecommerce_analytics")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "StrongAdminPassword_2026!")

DB_READONLY_USER = os.getenv("DB_READONLY_USER", "llm_reader")
DB_READONLY_PASSWORD = os.getenv("DB_READONLY_PASSWORD", "ReadOnlySafePassword_2026!")

SEED_CUSTOMERS_COUNT = int(os.getenv("SEED_CUSTOMERS_COUNT", "1000"))
SEED_PRODUCTS_COUNT = int(os.getenv("SEED_PRODUCTS_COUNT", "500"))
SEED_ORDERS_COUNT = int(os.getenv("SEED_ORDERS_COUNT", "10000"))
FORCE_RESEED = os.getenv("FORCE_RESEED", "false").lower() == "true"
RANDOM_SEED = int(os.getenv("RANDOM_SEED", "42"))

# Set deterministic random seeds for reproducible data generation
random.seed(RANDOM_SEED)
Faker.seed(RANDOM_SEED)
fake = Faker("fa_IR")

# =============================================================================
# CURATED PERSIAN DOMAIN DATA
# =============================================================================

# Weighted Iranian cities reflecting real e-commerce population and traffic distribution
IRANIAN_CITIES = [
    ("تهران", 35),
    ("مشهد", 12),
    ("اصفهان", 10),
    ("شیراز", 8),
    ("تبریز", 7),
    ("کرج", 7),
    ("اهواز", 5),
    ("رشت", 4),
    ("کرمان", 4),
    ("یزد", 4),
    ("قم", 4),
]

CITY_NAMES = [city[0] for city in IRANIAN_CITIES]
CITY_WEIGHTS = [city[1] for city in IRANIAN_CITIES]

IRANIAN_MOBILE_PREFIXES = ["0912", "0919", "0935", "0936", "0913", "0915"]

# Persian product catalog definitions by category with price ranges in Iranian Tomans
PRODUCT_CATALOG = {
    "الکترونیک و دیجیتال": {
        "price_min": 800_000,
        "price_max": 85_000_000,
        "base_items": [
            ("گوشی موبایل سامسونگ گلکسی", 18_000_000, 68_000_000),
            ("گوشی موبایل اپل آیفون", 48_000_000, 85_000_000),
            ("گوشی موبایل شیائومی پوکو", 9_500_000, 26_000_000),
            ("لپ‌تاپ مهندسی ایسوس زن‌بوک", 38_000_000, 82_000_000),
            ("لپ‌تاپ اداری لنوو آیدیاپد", 21_000_000, 52_000_000),
            ("هدفون بی‌سیم سونی با حذف نویز فعال", 7_500_000, 24_000_000),
            ("ایرپاد اپل با محفظه شارژ بی‌سیم", 11_000_000, 19_500_000),
            ("ساعت هوشمند سامسونگ گلکسی واچ", 8_500_000, 23_000_000),
            ("تبلت سامسونگ گلکسی تب", 13_000_000, 42_000_000),
            ("مانیتور گیمینگ خمیده ۲۷ اینچ", 11_500_000, 34_000_000),
            ("هارد اکسترنال ضدضربه ۲ ترابایت", 3_600_000, 6_800_000),
            ("پاوربانک فست‌شارژ ۲۰۰۰۰ میلی‌آمپر", 1_200_000, 3_400_000),
            ("مودم روتر فیبر نوری دوبانده", 1_900_000, 5_800_000),
            ("کیبورد مکانیکی گیمینگ RGB", 1_600_000, 7_500_000),
            ("ماوس بی‌سیم ارگونومیک بی‌صدا", 800_000, 3_100_000),
            ("وب‌کم باکیفیت فول اچ‌دی اداری", 1_200_000, 4_200_000),
        ],
    },
    "لوازم خانگی و آشپزخانه": {
        "price_min": 1_500_000,
        "price_max": 35_000_000,
        "base_items": [
            ("اسپرسوساز تمام اتوماتیک دلونگی", 7_500_000, 26_000_000),
            ("سرخ‌کن بدون روغن فیلیپس هواپز", 8_200_000, 17_500_000),
            ("جاروبرقی رباتیک هوشمند نقشه‌بردار", 15_000_000, 35_000_000),
            ("جاروبرقی کیسه‌ای پرقدرت بوش", 8_500_000, 22_000_000),
            ("مایکروویو چندکاره گریل‌دار", 6_800_000, 19_000_000),
            ("مخلوط‌کن و آسیاب پرقدرت شیشه‌ای", 2_200_000, 6_800_000),
            ("چای‌ساز لمسی دیجیتال استیل", 2_600_000, 7_500_000),
            ("اتو بخار سرامیکی ضدچکه", 1_700_000, 5_200_000),
            ("دستگاه تصفیه کننده هوا هوشمند", 8_900_000, 25_000_000),
            ("پنکه ایستاده کنترل‌دار بی‌صدا", 2_700_000, 6_800_000),
            ("سرویس قابلمه گرانیتی ۱۰ پارچه", 4_600_000, 15_500_000),
            ("زودپز تمام استیل کلیپسی دوقلو", 3_400_000, 10_500_000),
            ("آبمیوه‌گیری چهارکاره حرفه‌ای موتور سنگین", 3_900_000, 12_000_000),
        ],
    },
    "پوشاک و مد": {
        "price_min": 350_000,
        "price_max": 8_500_000,
        "base_items": [
            ("کفش ورزشی نایکی پیاده‌روی و رانینگ", 3_200_000, 8_500_000),
            ("کتانی شهری روزمره راحتی چرم", 1_400_000, 4_100_000),
            ("کاپشن مردانه ضدآب کلاه‌دار گرم", 2_800_000, 7_600_000),
            ("هودی سوپر پنبه سه نخ پاییزه", 750_000, 1_950_000),
            ("شلوار جین راسته سرمه‌ای ترک", 850_000, 2_600_000),
            ("پیراهن مردانه آستین بلند رسمی", 550_000, 1_650_000),
            ("مانتو تابستانی خنک الیاف طبیعی", 900_000, 2_800_000),
            ("کیف دوشی مجلسی چرم طبیعی تبریز", 1_900_000, 5_400_000),
            ("کوله‌پشتی لپ‌تاپی ضدآب اداری", 1_100_000, 2_700_000),
            ("عینک آفتابی پلاریزه ضد یووی۴۰۰", 850_000, 3_900_000),
            ("کمربند چرم طبیعی گاوی دو رو", 350_000, 950_000),
            ("ساعت مچی بند چرمی کلاسیک مردانه", 1_950_000, 7_800_000),
        ],
    },
    "آرایشی و بهداشتی": {
        "price_min": 250_000,
        "price_max": 6_000_000,
        "base_items": [
            ("ادکلن گرم و شیرین ماندگار ۱۰۰ میل", 1_850_000, 6_000_000),
            ("کرم ضدآفتاب رنگی فاقد چربی ۵۰ میل", 380_000, 1_150_000),
            ("سرم جوانساز پوست صورت ویتامین سی", 480_000, 1_550_000),
            ("سشوار سالنی موتور سنگین AC", 1_650_000, 4_600_000),
            ("ماشین اصلاح سر و صورت خط‌زن شارژی", 1_050_000, 3_700_000),
            ("مسواک برقی هوشمند اولتراسونیک", 1_300_000, 3_800_000),
            ("شامپو تخصصی تقویت کننده و ضدریزش مو", 250_000, 890_000),
            ("کرم آبرسان عمیق پوست حاوی هیالورونیک", 290_000, 980_000),
            ("پک کامل مراقبت پوستی روز و شب", 1_400_000, 3_900_000),
            ("ریمل حجم‌دهنده مژه بدون ایجاد حساسیت", 310_000, 860_000),
        ],
    },
    "کتاب، فرهنگ و ورزش": {
        "price_min": 150_000,
        "price_max": 4_500_000,
        "base_items": [
            ("کتاب آموزش جامع و عملی پایتون", 290_000, 580_000),
            ("کتاب مبانی یادگیری ماشین و هوش مصنوعی", 340_000, 690_000),
            ("رمان برگزیده ادبیات داستانی معاصر", 160_000, 390_000),
            ("دفتر برنامه‌ریزی هدفمند بولت ژورنال", 190_000, 420_000),
            ("ست خودنویس و روان‌نویس اداری فاخر", 480_000, 1_850_000),
            ("مت یوگا حرفه‌ای ضدلغزش ۸ میلی‌متر", 460_000, 1_250_000),
            ("جفت دمبل متغیر بدنسازی روکش‌دار", 680_000, 2_900_000),
            ("قمقمه ورزشی دوجداره استیل ضدزنگ", 280_000, 780_000),
            ("چادر مسافرتی ضدآب فنری ۴ نفره", 1_750_000, 4_500_000),
            ("بازی فکری رومیزی استراتژیک بردگیم", 380_000, 1_950_000),
        ],
    },
}

PRODUCT_SUFFIXES = [
    "مدل پرو کد ۱۰۱",
    "نسخه ویژه ۲۰۲۵",
    "سری پلاس ارتقا یافته",
    "مدل اولترا پریمیوم",
    "سری بیزینس ادیشن",
    "کد تجاری ۲۰۰ استاندارد",
    "مدل کامپکت هوشمند",
    "نسخه دلوکس پرستیژ",
    "سری الیت کربن",
    "مدل کلاسیک مدرن",
    "کد ۵۰۲ صادراتی",
    "سری اسمارت نسل جدید",
    "مدل توربو پاور",
    "نسخه طلایی سفارشی",
    "سری اکسپرت حرفه‌ای",
]

# Order statuses and probabilities
ORDER_STATUSES = ["completed", "processing", "cancelled", "returned"]
ORDER_STATUS_WEIGHTS = [75, 10, 10, 5]


# =============================================================================
# DATABASE CONNECTION & HEALTH CHECK
# =============================================================================
def wait_for_db(retries: int = 30, delay: int = 2):
    """
    Attempts to connect to PostgreSQL with backoff until the database is ready.
    """
    print(f"[*] Attempting connection to PostgreSQL at {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}...")
    for attempt in range(1, retries + 1):
        try:
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                dbname=POSTGRES_DB,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                connect_timeout=3,
            )
            conn.autocommit = False
            print(f"[+] Successfully connected to PostgreSQL (Attempt {attempt}/{retries}).")
            return conn
        except psycopg2.OperationalError as e:
            print(f"[!] PostgreSQL not ready yet (Attempt {attempt}/{retries}). Error: {e}")
            if attempt == retries:
                raise RuntimeError("Failed to connect to PostgreSQL after maximum retries.") from e
            time.sleep(delay)


# =============================================================================
# SEEDING FUNCTIONS
# =============================================================================
def seed_customers(conn, count: int) -> list:
    """
    Generates realistic Iranian customers with unique emails and phone numbers.
    Returns list of tuples: [(customer_id, registration_date), ...]
    """
    print(f"\n[*] Generating {count} realistic Iranian customer records...")
    now = datetime.now()
    customer_records = []
    generated_emails = set()

    for i in range(1, count + 1):
        full_name = f"{fake.first_name()} {fake.last_name()}"
        
        # Enforce globally unique email addresses
        while True:
            email_user = f"user_{i}_{random.randint(100, 999)}"
            email_domain = random.choice(["gmail.com", "yahoo.com", "chmail.ir", "iran.ir", "outlook.com"])
            email = f"{email_user}@{email_domain}"
            if email not in generated_emails:
                generated_emails.add(email)
                break

        # Generate realistic Iranian mobile phone numbers
        phone_prefix = random.choice(IRANIAN_MOBILE_PREFIXES)
        phone_body = f"{random.randint(1000000, 9999999)}"
        phone = f"{phone_prefix}{phone_body}"

        # Weighted Persian city distribution
        city = random.choices(CITY_NAMES, weights=CITY_WEIGHTS, k=1)[0]

        # Customer registration date: between 730 days ago (2 years) and 15 days ago
        reg_days_ago = random.uniform(15.0, 730.0)
        registration_date = now - timedelta(days=reg_days_ago)

        customer_records.append((full_name, email, phone, city, registration_date))

    # Bulk insert using psycopg2 execute_values
    query = """
        INSERT INTO customers (full_name, email, phone, city, registration_date)
        VALUES %s
        RETURNING id, registration_date;
    """
    with conn.cursor() as cur:
        returned_rows = execute_values(cur, query, customer_records, fetch=True)
    conn.commit()

    print(f"[+] Successfully seeded {len(returned_rows)} customers.")
    return returned_rows


def seed_products(conn, target_count: int) -> dict:
    """
    Generates distinct Persian catalog products across 5 master categories.
    Returns dictionary mapping: {product_id: unit_price}
    """
    print(f"\n[*] Generating {target_count} Persian product records...")
    now = datetime.now()
    two_years_ago = now - timedelta(days=730)
    products_to_insert = []
    
    categories = list(PRODUCT_CATALOG.keys())
    items_per_category = target_count // len(categories)
    remainder = target_count % len(categories)

    generated_names = set()

    for cat_idx, category in enumerate(categories):
        quota = items_per_category + (1 if cat_idx < remainder else 0)
        cat_info = PRODUCT_CATALOG[category]
        base_items = cat_info["base_items"]
        
        items_generated = 0
        while items_generated < quota:
            for base_item_tuple in base_items:
                if items_generated >= quota:
                    break
                base_name, min_p, max_p = base_item_tuple
                suffix = random.choice(PRODUCT_SUFFIXES)
                prod_name = f"{base_name} {suffix}"
                
                # Ensure unique product names
                if prod_name in generated_names:
                    prod_name = f"{prod_name} #{random.randint(10, 999)}"
                generated_names.add(prod_name)

                # Round price to nearest 10,000 Tomans
                raw_price = random.randint(min_p, max_p)
                price = Decimal(str(int(round(raw_price, -4))))

                stock_quantity = random.randint(0, 300)
                created_at = two_years_ago + timedelta(days=random.uniform(0, 30))

                products_to_insert.append((prod_name, category, price, stock_quantity, created_at))
                items_generated += 1

    query = """
        INSERT INTO products (name, category, price, stock_quantity, created_at)
        VALUES %s
        RETURNING id, price;
    """
    with conn.cursor() as cur:
        returned_rows = execute_values(cur, query, products_to_insert, fetch=True)
    conn.commit()

    product_map = {row[0]: Decimal(str(row[1])) for row in returned_rows}
    print(f"[+] Successfully seeded {len(product_map)} products.")
    return product_map


def seed_orders_and_items(conn, customers_data: list, products_map: dict, total_orders: int):
    """
    Generates orders with strict temporal constraints, weighted recent density,
    and associated line items with financial consistency.
    """
    print(f"\n[*] Generating {total_orders} orders with strict temporal & financial integrity...")
    now = datetime.now()
    today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    product_ids = list(products_map.keys())

    # Pre-generate orders data
    # Temporal distribution weights:
    # 3% today, 12% last 7 days, 25% last 60 to 7 days, 60% historical (reg_date to 60 days ago)
    bracket_choices = ["today", "this_week", "last_month", "historical"]
    bracket_weights = [3, 12, 25, 60]

    orders_prep = []
    items_by_order_idx = []

    for idx in range(total_orders):
        customer_id, reg_date = random.choice(customers_data)
        bracket = random.choices(bracket_choices, weights=bracket_weights, k=1)[0]

        # Calculate order_date strictly respecting customer registration_date
        if bracket == "today":
            seconds_since_midnight = max(60, int((now - today_midnight).total_seconds()))
            order_date = today_midnight + timedelta(seconds=random.randint(0, seconds_since_midnight))
        elif bracket == "this_week":
            start_week = now - timedelta(days=7)
            order_date = start_week + timedelta(seconds=random.randint(0, int(6.5 * 86400)))
        elif bracket == "last_month":
            start_month = now - timedelta(days=60)
            order_date = start_month + timedelta(seconds=random.randint(0, int(53 * 86400)))
        else:  # historical
            max_historical = now - timedelta(days=60)
            if reg_date < max_historical:
                span_sec = int((max_historical - reg_date).total_seconds())
                order_date = reg_date + timedelta(seconds=random.randint(3600, max(3601, span_sec)))
            else:
                span_sec = int((now - reg_date).total_seconds())
                order_date = reg_date + timedelta(seconds=random.randint(3600, max(3601, span_sec)))

        # Enforce hard temporal invariants
        if order_date <= reg_date:
            order_date = reg_date + timedelta(hours=random.randint(1, 24))
        if order_date > now:
            order_date = now - timedelta(minutes=random.randint(1, 45))

        status = random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS, k=1)[0]

        # Select 1 to 5 distinct products for this order
        k_items = random.randint(1, 5)
        selected_prod_ids = random.sample(product_ids, k_items)
        
        order_items_list = []
        calculated_total = Decimal("0.00")

        for pid in selected_prod_ids:
            quantity = random.randint(1, 4)
            unit_price = products_map[pid]
            line_total = Decimal(quantity) * unit_price
            calculated_total += line_total
            order_items_list.append((pid, quantity, unit_price))

        orders_prep.append((customer_id, order_date, status, calculated_total))
        items_by_order_idx.append(order_items_list)

    # Bulk insert orders in batches of 2000 to maintain high throughput and low memory footprint
    batch_size = 2000
    total_batches = (total_orders + batch_size - 1) // batch_size
    total_items_inserted = 0

    print("[*] Inserting orders and order items in batches...")
    for batch_num in tqdm(range(total_batches), desc="Processing Orders Batches"):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_orders)
        
        batch_orders = orders_prep[start_idx:end_idx]
        batch_items_raw = items_by_order_idx[start_idx:end_idx]

        orders_insert_query = """
            INSERT INTO orders (customer_id, order_date, status, total_amount)
            VALUES %s
            RETURNING id;
        """
        with conn.cursor() as cur:
            returned_order_ids = execute_values(cur, orders_insert_query, batch_orders, fetch=True)

        # Build order items linking to newly generated order IDs
        batch_order_items = []
        for (order_row,), raw_items in zip(returned_order_ids, batch_items_raw):
            order_id = order_row
            for pid, quantity, unit_price in raw_items:
                batch_order_items.append((order_id, pid, quantity, unit_price))

        items_insert_query = """
            INSERT INTO order_items (order_id, product_id, quantity, unit_price)
            VALUES %s;
        """
        with conn.cursor() as cur:
            execute_values(cur, items_insert_query, batch_order_items)
            total_items_inserted += len(batch_order_items)

        conn.commit()

    print(f"[+] Successfully seeded {total_orders} orders and {total_items_inserted} order items.")


# =============================================================================
# VERIFICATION SUITE & RBAC SECURITY PROOF
# =============================================================================
def verify_database_integrity(conn):
    """
    Runs comprehensive aggregation checks on seeded data and proves
    that the llm_reader role is strictly read-only and blocked from DDL/DML.
    """
    print("\n" + "=" * 75)
    print("           DATABASE VERIFICATION & RBAC SECURITY SUITE")
    print("=" * 75)

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM customers;")
        cust_cnt = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM products;")
        prod_cnt = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM orders;")
        ord_cnt = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM order_items;")
        items_cnt = cur.fetchone()[0]

        cur.execute("SELECT COALESCE(SUM(total_amount), 0) FROM orders WHERE status = 'completed';")
        completed_revenue = cur.fetchone()[0]

        cur.execute("""
            SELECT status, COUNT(*), SUM(total_amount)
            FROM orders
            GROUP BY status
            ORDER BY count(*) DESC;
        """)
        status_breakdown = cur.fetchall()

    print(f"[✓] Customers Record Count     : {cust_cnt:,}")
    print(f"[✓] Products Catalog Count      : {prod_cnt:,}")
    print(f"[✓] Orders Total Transactions   : {ord_cnt:,}")
    print(f"[✓] Order Items Line Details    : {items_cnt:,}")
    print(f"[✓] Total Completed Revenue     : {Decimal(completed_revenue):,f} Tomans")
    print("-" * 75)
    print("Order Status Distribution:")
    for status, count, amount in status_breakdown:
        print(f"  • {status:<12}: {count:,} orders | Total: {Decimal(amount or 0):,f} Tomans")
    print("-" * 75)

    # Security Verification: Connect as llm_reader and test RBAC guardrails
    print(f"[*] Testing Security Sandbox for role '{DB_READONLY_USER}'...")
    try:
        reader_conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            dbname=POSTGRES_DB,
            user=DB_READONLY_USER,
            password=DB_READONLY_PASSWORD,
            connect_timeout=3,
        )
        with reader_conn.cursor() as cur:
            # 1. Test Read Privilege
            cur.execute("SELECT COUNT(*) FROM orders;")
            read_count = cur.fetchone()[0]
            print(f"[✓] READ PERMISSION VERIFIED: '{DB_READONLY_USER}' successfully read {read_count:,} orders.")

            # 2. Test Mutating Privileges (Must be rejected)
            destructive_query_blocked = False
            try:
                cur.execute("DELETE FROM orders WHERE id = 1;")
                reader_conn.commit()
            except Exception as sec_exc:
                reader_conn.rollback()
                destructive_query_blocked = True
                print(f"[SECURITY PASS] '{DB_READONLY_USER}' blocked from destructive DELETE query!")
                print(f"  Engine Response: {sec_exc.__class__.__name__} - {str(sec_exc).strip()}")

            if not destructive_query_blocked:
                raise RuntimeError(f"SECURITY CRITICAL FAILURE: '{DB_READONLY_USER}' was able to delete records!")

        reader_conn.close()
        print("[+] All RBAC security policies verified successfully.")
    except Exception as e:
        print(f"[!] Security Verification Exception: {e}")
        raise e

    print("=" * 75)
    print("           PHASE 1 DATABASE FOUNDATION FULLY READY")
    print("=" * 75)


# =============================================================================
# MAIN ORCHESTRATION PIPELINE
# =============================================================================
def main():
    print("=" * 75)
    print("      Autonomous Data Analyst - Database Provisioning & Seeder")
    print("=" * 75)

    conn = wait_for_db()

    # Check idempotency
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM customers;")
        existing_customers = cur.fetchone()[0]

    if existing_customers > 0 and not FORCE_RESEED:
        print(f"[!] Database already seeded with {existing_customers:,} customers.")
        print("[!] FORCE_RESEED is set to false. Skipping generation and running verification...")
        verify_database_integrity(conn)
        conn.close()
        sys.exit(0)

    if FORCE_RESEED and existing_customers > 0:
        print("[!] FORCE_RESEED=true detected. Truncating existing tables...")
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE order_items, orders, products, customers RESTART IDENTITY CASCADE;")
        conn.commit()
        print("[+] Tables truncated successfully.")

    start_time = time.time()

    # Step A: Seed Customers
    customers_data = seed_customers(conn, SEED_CUSTOMERS_COUNT)

    # Step B: Seed Products
    products_map = seed_products(conn, SEED_PRODUCTS_COUNT)

    # Step C: Seed Orders and Order Items
    seed_orders_and_items(conn, customers_data, products_map, SEED_ORDERS_COUNT)

    elapsed = time.time() - start_time
    print(f"\n[+] Seeding pipeline completed in {elapsed:.2f} seconds.")

    # Run verification suite
    verify_database_integrity(conn)

    conn.close()


if __name__ == "__main__":
    main()
