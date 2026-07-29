-- ============================================================
-- Inventory Management System - Database Schema
-- Engine : PostgreSQL 14+ (Neon)
-- ============================================================
-- Run this against your Neon database, e.g.:
--   psql "$DATABASE_URL" -f database/schema.sql
-- Neon already provisions a database for you via the connection
-- string, so there's no CREATE DATABASE / USE step here.

CREATE TABLE IF NOT EXISTS suppliers (
    id              SERIAL        PRIMARY KEY,
    name            VARCHAR(150)  NOT NULL,
    contact_person  VARCHAR(100),
    email           VARCHAR(120)  NOT NULL UNIQUE,
    phone           VARCHAR(20),
    address         TEXT,
    city            VARCHAR(80),
    country         VARCHAR(80)   DEFAULT 'India',
    is_active       BOOLEAN       DEFAULT TRUE,
    created_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id          SERIAL        PRIMARY KEY,
    name        VARCHAR(100)  NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    id                SERIAL         PRIMARY KEY,
    name              VARCHAR(200)   NOT NULL,
    sku               VARCHAR(80)    NOT NULL UNIQUE,
    description       TEXT,
    category_id       INT,
    supplier_id       INT,
    unit_price        DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
    selling_price     DECIMAL(10,2)  NOT NULL DEFAULT 0.00,
    quantity_in_stock INT            NOT NULL DEFAULT 0,
    reorder_level     INT            NOT NULL DEFAULT 10,
    reorder_quantity  INT            NOT NULL DEFAULT 50,
    unit              VARCHAR(30)    DEFAULT 'pcs',
    is_active         BOOLEAN        DEFAULT TRUE,
    created_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id)  ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS sales (
    id              SERIAL         PRIMARY KEY,
    invoice_number  VARCHAR(50)    NOT NULL UNIQUE,
    customer_name   VARCHAR(150),
    customer_email  VARCHAR(120),
    total_amount    DECIMAL(12,2)  NOT NULL DEFAULT 0.00,
    discount        DECIMAL(10,2)  DEFAULT 0.00,
    final_amount    DECIMAL(12,2)  NOT NULL DEFAULT 0.00,
    payment_method  VARCHAR(20)    DEFAULT 'cash'
                    CHECK (payment_method IN ('cash', 'card', 'upi', 'bank_transfer')),
    status          VARCHAR(20)    DEFAULT 'completed'
                    CHECK (status IN ('pending', 'completed', 'cancelled', 'refunded')),
    notes           TEXT,
    created_at      TIMESTAMP      DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sale_items (
    id          SERIAL         PRIMARY KEY,
    sale_id     INT            NOT NULL,
    product_id  INT            NOT NULL,
    quantity    INT            NOT NULL,
    unit_price  DECIMAL(10,2)  NOT NULL,
    total_price DECIMAL(10,2)  NOT NULL,
    FOREIGN KEY (sale_id)    REFERENCES sales(id)    ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id              SERIAL      PRIMARY KEY,
    product_id      INT         NOT NULL,
    movement_type   VARCHAR(20) NOT NULL
                    CHECK (movement_type IN ('purchase', 'sale', 'adjustment', 'return', 'damage')),
    quantity_change INT         NOT NULL,
    quantity_after  INT         NOT NULL,
    reference_id    INT,
    notes           TEXT,
    created_by      VARCHAR(80) DEFAULT 'system',
    created_at      TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS restock_alerts (
    id            SERIAL      PRIMARY KEY,
    product_id    INT         NOT NULL,
    current_stock INT         NOT NULL,
    reorder_level INT         NOT NULL,
    is_resolved   BOOLEAN     DEFAULT FALSE,
    resolved_at   TIMESTAMP   NULL DEFAULT NULL,
    created_at    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Postgres has no "ON UPDATE CURRENT_TIMESTAMP" column option (that's
-- MySQL-only), so updated_at is refreshed with a trigger instead.
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_suppliers_updated_at ON suppliers;
CREATE TRIGGER trg_suppliers_updated_at
    BEFORE UPDATE ON suppliers
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

DROP TRIGGER IF EXISTS trg_products_updated_at ON products;
CREATE TRIGGER trg_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Seed data (ON CONFLICT DO NOTHING makes this safe to re-run)
INSERT INTO categories (name, description) VALUES
('Electronics',  'Electronic devices and accessories'),
('Stationery',   'Office and school stationery items'),
('Furniture',    'Office and home furniture'),
('Consumables',  'Day-to-day consumable items'),
('Accessories',  'Various accessories')
ON CONFLICT (name) DO NOTHING;

INSERT INTO suppliers (name, contact_person, email, phone, address, city, country) VALUES
('TechSupply Co.', 'Rahul Sharma', 'rahul@techsupply.in',  '+91-9876543210', '12 MG Road',    'Bengaluru', 'India'),
('OfficeWorld',    'Priya Mehta',  'priya@officeworld.in', '+91-9123456789', '45 Park Street', 'Kolkata',   'India'),
('FurniturePlus',  'Amit Singh',   'amit@furnitureplus.in','+91-9988776655', '78 Link Road',   'Mumbai',    'India')
ON CONFLICT (email) DO NOTHING;

INSERT INTO products (name, sku, description, category_id, supplier_id, unit_price, selling_price, quantity_in_stock, reorder_level, reorder_quantity, unit) VALUES
('Wireless Mouse',      'ELEC-001', 'Ergonomic wireless optical mouse',           1, 1,   350.00,   599.00, 45, 10,  50, 'pcs'),
('Mechanical Keyboard', 'ELEC-002', 'USB mechanical keyboard with backlight',     1, 1,  1200.00,  1999.00, 12,  5,  20, 'pcs'),
('A4 Paper Ream',       'STAT-001', '500 sheets A4 size printing paper',          2, 2,   180.00,   280.00,  8, 15, 100, 'ream'),
('Ball Pen Pack',       'STAT-002', 'Pack of 10 blue ball pens',                  2, 2,    40.00,    75.00,120, 20, 200, 'pack'),
('Office Chair',        'FURN-001', 'Ergonomic office chair with lumbar support', 3, 3,  4500.00,  7500.00,  6,  3,  10, 'pcs'),
('Standing Desk',       'FURN-002', 'Height-adjustable standing desk',            3, 3, 12000.00, 18000.00,  3,  2,   5, 'pcs'),
('Printer Cartridge',   'CONS-001', 'HP compatible black ink cartridge',          4, 1,   450.00,   750.00,  7, 10,  30, 'pcs'),
('Hand Sanitizer',      'CONS-002', '500ml hand sanitizer bottle',                4, 2,    90.00,   150.00, 55, 20, 100, 'bottle'),
('USB-C Cable',         'ACC-001',  '1.5m braided USB-C charging cable',          5, 1,   120.00,   249.00, 80, 15,  60, 'pcs'),
('Laptop Stand',        'ACC-002',  'Aluminium adjustable laptop stand',          5, 1,   800.00,  1499.00, 22,  8,  25, 'pcs')
ON CONFLICT (sku) DO NOTHING;
