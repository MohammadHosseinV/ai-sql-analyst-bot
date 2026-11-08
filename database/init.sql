-- =============================================================================
-- Autonomous Data Analyst - Database Initialization Script
-- Architecture: PostgreSQL 15+ (UTF-8 Native Encoding, Asia/Tehran Timezone)
-- Security: Hardened Role-Based Access Control (RBAC) for AI SQL Agent
-- =============================================================================

SET client_encoding = 'UTF8';
SET TIME ZONE 'Asia/Tehran';

-- =============================================================================
-- 1. TABLE DEFINITIONS (DDL)
-- =============================================================================

-- Table: customers
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    phone VARCHAR(20) NOT NULL,
    city VARCHAR(100) NOT NULL,
    registration_date TIMESTAMP NOT NULL
);

COMMENT ON TABLE customers IS 'Stores customer personal records, contact information, geographic location, and registration timestamps.';
COMMENT ON COLUMN customers.id IS 'Unique surrogate primary key for each registered customer.';
COMMENT ON COLUMN customers.full_name IS 'Customer full name in Persian script.';
COMMENT ON COLUMN customers.email IS 'Unique email address used for login and customer identification.';
COMMENT ON COLUMN customers.phone IS 'Iranian mobile phone number (e.g., 0912xxxxxxx).';
COMMENT ON COLUMN customers.city IS 'Iranian province capital or major city where customer resides.';
COMMENT ON COLUMN customers.registration_date IS 'Exact timestamp when customer created their account.';

-- Table: products
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    price NUMERIC(14, 2) NOT NULL CHECK (price >= 0),
    stock_quantity INTEGER NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE products IS 'Master catalog storing product details, category taxonomies, unit prices in Tomans, and inventory counts.';
COMMENT ON COLUMN products.id IS 'Unique primary key for each catalog item.';
COMMENT ON COLUMN products.name IS 'Persian title and specification description of the product.';
COMMENT ON COLUMN products.category IS 'High-level Iranian retail market department or product category.';
COMMENT ON COLUMN products.price IS 'Official retail unit price stored in Iranian Tomans.';
COMMENT ON COLUMN products.stock_quantity IS 'Available units remaining in fulfillment centers.';
COMMENT ON COLUMN products.created_at IS 'Timestamp when the product was introduced into the catalog.';

-- Table: orders
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id) ON DELETE RESTRICT,
    order_date TIMESTAMP NOT NULL,
    status VARCHAR(50) NOT NULL CHECK (status IN ('completed', 'processing', 'cancelled', 'returned')),
    total_amount NUMERIC(16, 2) NOT NULL DEFAULT 0 CHECK (total_amount >= 0)
);

COMMENT ON TABLE orders IS 'Header records for customer purchase transactions including timestamp, status lifecycle, and total value.';
COMMENT ON COLUMN orders.id IS 'Unique identifier for each placed transaction.';
COMMENT ON COLUMN orders.customer_id IS 'Foreign key referencing customers(id) who executed the order.';
COMMENT ON COLUMN orders.order_date IS 'Timestamp when order transaction occurred (must succeed customer registration_date).';
COMMENT ON COLUMN orders.status IS 'Lifecycle fulfillment stage: completed, processing, cancelled, or returned.';
COMMENT ON COLUMN orders.total_amount IS 'Calculated sum of all related order item line totals in Tomans.';

-- Table: order_items
CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(14, 2) NOT NULL CHECK (unit_price >= 0),
    line_total NUMERIC(16, 2) GENERATED ALWAYS AS (quantity * unit_price) STORED
);

COMMENT ON TABLE order_items IS 'Detailed line items associated with each order, establishing relation between orders and products.';
COMMENT ON COLUMN order_items.id IS 'Surrogate primary key for each order line item entry.';
COMMENT ON COLUMN order_items.order_id IS 'Foreign key referencing orders(id) cascading on deletion.';
COMMENT ON COLUMN order_items.product_id IS 'Foreign key referencing products(id) restricting catalog item removal.';
COMMENT ON COLUMN order_items.quantity IS 'Quantity of the specific product item purchased.';
COMMENT ON COLUMN order_items.unit_price IS 'Actual unit price in Tomans at the time of purchase.';
COMMENT ON COLUMN order_items.line_total IS 'Deterministic stored generated column computing (quantity * unit_price).';

-- =============================================================================
-- 2. ANALYTICAL & PERFORMANCE INDEXES (B-TREE)
-- =============================================================================

-- Customer lookup and cohort analysis
CREATE INDEX IF NOT EXISTS idx_customers_city ON customers(city);
CREATE INDEX IF NOT EXISTS idx_customers_reg_date ON customers(registration_date);

-- Catalog filtering, grouping and pricing aggregations
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price);

-- Order filtering, lifecycle status, temporal trends and executive reporting
CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_order_date ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_date_status ON orders(order_date, status);

-- Line item join optimization and product sales velocity
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items(product_id);

-- =============================================================================
-- 3. HARDENED SECURITY SETUP: READ-ONLY AI AGENT ROLE (llm_reader)
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'llm_reader') THEN
        CREATE ROLE llm_reader WITH LOGIN PASSWORD 'ReadOnlySafePassword_2026!';
    ELSE
        ALTER ROLE llm_reader WITH LOGIN PASSWORD 'ReadOnlySafePassword_2026!';
    END IF;
END
$$;

-- Revoke all existing public schema privileges
REVOKE ALL ON SCHEMA public FROM llm_reader;

-- Grant selective connectivity and read privileges
GRANT CONNECT ON DATABASE ecommerce_analytics TO llm_reader;
GRANT USAGE ON SCHEMA public TO llm_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO llm_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO llm_reader;

-- Engine-level Guardrails against Runaway Queries and Destructive LLM Hallucinations
ALTER ROLE llm_reader SET statement_timeout = '10s';
ALTER ROLE llm_reader SET default_transaction_read_only = on;
