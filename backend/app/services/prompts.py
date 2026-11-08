"""
Prompt Engineering Core Module
Contains comprehensive domain DDL specifications, few-shot prompt builders,
self-correction prompts, and data-to-Persian synthesis templates.
"""

from typing import Tuple, List, Dict, Any

# =============================================================================
# POSTGRESQL SCHEMA SPECIFICATION & DOMAIN TAXONOMY
# =============================================================================

DATABASE_SCHEMA_DDL = """
-- PostgreSQL 15 Database Schema (UTF-8, Asia/Tehran Timezone)
-- Currency: All monetary amounts (price, unit_price, total_amount, line_total) are strictly in Iranian TOMANS (تومان).

TABLE customers (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL, -- Customer full name in Persian script
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL, -- Iranian mobile format (e.g., '09123456789')
    city VARCHAR(100) NOT NULL, -- Customer residence city
    registration_date TIMESTAMP NOT NULL -- Account creation timestamp
);

TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL, -- Product title in Persian (e.g. 'گوشی موبایل سامسونگ گلکسی مدل پرو کد ۱۰۱')
    category VARCHAR(100) NOT NULL, -- Primary product category
    price NUMERIC(14, 2) NOT NULL CHECK (price >= 0), -- Unit catalog price in Tomans
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0), -- Warehouse inventory
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

TABLE orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    order_date TIMESTAMP NOT NULL, -- Order placement timestamp
    status VARCHAR(50) NOT NULL CHECK (status IN ('completed', 'processing', 'cancelled', 'returned')),
    total_amount NUMERIC(16, 2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0) -- Sum of line items in Tomans
);

TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0), -- Purchased units count
    unit_price NUMERIC(14, 2) NOT NULL CHECK (unit_price >= 0), -- Unit price at purchase in Tomans
    line_total NUMERIC(16, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED -- Total line amount in Tomans
);

-- =============================================================================
-- RELATIONSHIPS & JOIN PATHS
-- =============================================================================
-- 1. customers JOIN orders ON customers.id = orders.customer_id
-- 2. orders JOIN order_items ON orders.id = order_items.order_id
-- 3. products JOIN order_items ON products.id = order_items.product_id

-- =============================================================================
-- DOMAIN VALUE DICTIONARY (CRITICAL FOR ACCURACY)
-- =============================================================================
-- 1. Order Status Values:
--    - 'completed'  : سفارش‌های موفق، قطعی، پرداخت‌شده و تحویل‌شده (استفاده پیش‌فرض برای محاسبه درآمد و فروش)
--    - 'processing' : سفارش‌های در حال پردازش یا آماده‌سازی
--    - 'cancelled'  : سفارش‌های لغوشده یا انصرافی
--    - 'returned'   : سفارش‌های مرجوعی
--
-- 2. Allowed Product Categories (products.category):
--    - 'الکترونیک و دیجیتال' (موبایل، لپ‌تاپ، لوازم جانبی دیجیتال، هدفون، ساعت هوشمند)
--    - 'لوازم خانگی و آشپزخانه' (اسپرسوساز، سرخ‌کن، جاروبرقی، مایکروویو)
--    - 'پوشاک و مد' (کفش ورزشی، هودی، شلوار، کاپشن، ساعت، کیف چرم)
--    - 'آرایشی و بهداشتی' (عطر، کرم، سشوار، مراقبت پوست)
--    - 'کتاب، فرهنگ و ورزش' (کتاب، مت یوگا، قمقمه، دمبل، بازی فکری)
--
-- 3. Iranian Cities (customers.city):
--    - 'تهران', 'مشهد', 'اصفهان', 'شیراز', 'تبریز', 'کرج', 'اهواز', 'رشت', 'کرمان', 'یزد', 'قم'
--
-- 4. Rules for Revenue / Sales Calculations:
--    - When calculating sales, income, or revenue (فروش / درآمد), always filter by `orders.status = 'completed'` unless the question asks explicitly for all or cancelled orders.
--    - For partial product search, always use case-insensitive partial match: `products.name ILIKE '%جستجو%'`.
--    - Use standard PostgreSQL temporal functions:
--      * Today: `order_date >= CURRENT_DATE`
--      * This Week: `order_date >= DATE_TRUNC('week', CURRENT_DATE)`
--      * Last 7 Days: `order_date >= CURRENT_DATE - INTERVAL '7 days'`
--      * Current Month: `order_date >= DATE_TRUNC('month', CURRENT_DATE)`
--      * Last Month: `order_date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month') AND order_date < DATE_TRUNC('month', CURRENT_DATE)`
--      * Current Year: `order_date >= DATE_TRUNC('year', CURRENT_DATE)`
"""


# =============================================================================
# PROMPT BUILDERS
# =============================================================================

def build_sql_generation_prompt(user_query: str) -> Tuple[str, str]:
    """
    Constructs system and user prompts instructing LLM to generate raw PostgreSQL SELECT query.
    """
    system_prompt = (
        "You are an Elite Principal Data Analyst and PostgreSQL Database Architect.\n"
        "Your task is to translate natural language analytical business questions (in Persian or English) "
        "into a single, highly optimized, syntactically correct PostgreSQL 15 SQL query.\n\n"
        "DATABASE SCHEMA & DOMAIN RULES:\n"
        f"{DATABASE_SCHEMA_DDL}\n\n"
        "STRICT EXECUTION GUIDELINES:\n"
        "1. Output ONLY the raw executable SQL query starting with SELECT or WITH. Do NOT enclose it in Markdown code blocks (```sql), do NOT include any preamble, comments, or explanations.\n"
        "2. Only generate SELECT queries. Any mutating queries (INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE) are strictly forbidden.\n"
        "3. Always provide clear, descriptive English aliases for computed columns (e.g., AS total_revenue, AS order_count, AS customer_name).\n"
        "4. Always qualify column names with table aliases (e.g., o.total_amount, c.city, p.category) to avoid ambiguity.\n"
        "5. For sales/revenue calculations, always filter by o.status = 'completed' unless explicitly specified otherwise.\n"
        "6. If the query returns unaggregated itemized records, include a reasonable LIMIT (e.g., LIMIT 50) to prevent oversized payloads.\n"
        "7. For Persian strings, use the exact values documented in the Domain Value Dictionary (e.g. products.category = 'الکترونیک و دیجیتال')."
    )

    user_prompt = (
        f"Business Question: {user_query}\n\n"
        "Generate the single executable PostgreSQL SELECT query now:"
    )

    return system_prompt, user_prompt


def build_sql_correction_prompt(
    user_query: str,
    failed_sql: str,
    db_error: str,
    attempt: int,
) -> Tuple[str, str]:
    """
    Constructs self-healing prompt feeding the database error and failed SQL back to LLM.
    """
    system_prompt = (
        "You are an Elite PostgreSQL Troubleshooting Architect.\n"
        "An analytical SQL query you previously generated failed to execute on PostgreSQL 15.\n"
        "Carefully analyze the schema, the failed SQL, and the exact database engine error message, "
        "diagnose the root cause, and produce the corrected PostgreSQL query.\n\n"
        "DATABASE SCHEMA:\n"
        f"{DATABASE_SCHEMA_DDL}\n\n"
        "STRICT OUTPUT RULES:\n"
        "1. Output ONLY the corrected raw executable SQL query starting with SELECT or WITH.\n"
        "2. Do NOT wrap in Markdown code blocks (```sql), do NOT include apologies, comments, or explanations.\n"
        "3. Ensure all group by columns, table aliases, column names, and data types match PostgreSQL specifications."
    )

    user_prompt = (
        f"User Business Question: {user_query}\n\n"
        f"Failed SQL Query (Attempt {attempt}):\n{failed_sql}\n\n"
        f"PostgreSQL Engine Error:\n{db_error}\n\n"
        "Correct the query and output ONLY the executable PostgreSQL SELECT statement:"
    )

    return system_prompt, user_prompt


def build_data_to_text_prompt(
    user_query: str,
    executed_sql: str,
    rows: List[Dict[str, Any]],
    row_count: int,
) -> Tuple[str, str]:
    """
    Constructs prompt instructing LLM to synthesize raw SQL result rows into fluent, executive Persian text.
    """
    system_prompt = (
        "شما «دستیار هوشمند تحلیل داده‌های سازمانی» (Autonomous Data Analyst) هستید؛ "
        "یک متخصص ارشد هوش تجاری (BI) که خروجی کوئری‌های پایگاه داده را برای مدیرعامل و مدیران ارشد به زبانی "
        "بسیار روان، دقیق، محترمانه و حرفه‌ای به فارسی بازگو می‌کند.\n\n"
        "قوانین پاسخ‌دهی به فارسی:\n"
        "۱. تمام مبالغ مالی در پایگاه داده به «تومان» ذخیره شده‌اند. اعداد را با جداکننده ارقام (مانند ۴۵,۵۰۰,۰۰۰ تومان) بنویسید و در مبالغ بالا، معادل خوانای حروفی (مانند ۴۵ میلیون و ۵۰۰ هزار تومان) را نیز قید کنید.\n"
        "۲. پاسخ باید موجز، متمرکز، بدون حاشیه و مناسب برای ارسال در پیام‌رسان تلگرام باشد (از بولت‌پوینت‌های مرتب استفاده کنید).\n"
        "۳. به هیچ وجه اسامی فنی ستون‌های دیتابیس یا کدهای SQL را در متن پیام ذکر نکنید؛ پاسخ باید کاملاً طبیعی و در سطح زبان مدیران باشد.\n"
        "۴. اگر تعداد سطرها صفر بود (row_count == 0) یا نتیجه خالی بود، با احترام اعلام کنید که برای بازه یا شروط مدنظر رکوردی یافت نشد.\n"
        "۵. در صورت ارائه رتبه‌بندی، مقادیر اول تا سوم را با ذکر آمار مشخص نمایید."
    )

    preview_rows = rows[:15]

    user_prompt = (
        f"پرسش مدیر: {user_query}\n\n"
        f"کوئری اجرا شده در پایگاه داده:\n{executed_sql}\n\n"
        f"تعداد سطرهای حاصل: {row_count}\n"
        f"داده‌های مستخرج از دیتابیس (حداکثر ۱۵ سطر اول):\n{preview_rows}\n\n"
        "پاسخ نهایی تحلیلی و مدیریتی به زبان فارسی:"
    )

    return system_prompt, user_prompt
