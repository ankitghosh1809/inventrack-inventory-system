-- ============================================================
-- Migration 001 — auth support, audit trail, data integrity
-- ============================================================
-- Run this ONCE against an EXISTING database that was already
-- set up from an older copy of database/schema.sql (e.g. your
-- live Neon database). It is safe to re-run: every statement is
-- idempotent (IF NOT EXISTS / guarded).
--
--   psql "$DATABASE_URL" -f database/migrations/001_add_auth_and_integrity.sql
--
-- A brand-new database created from the current database/schema.sql
-- already has all of this — you don't need to run this file too.

-- categories: needed so DELETE /api/categories/:id can soft-delete
-- (consistent with how products/suppliers are already deactivated).
ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;

-- sales: records which logged-in user made the sale (paired with the
-- new login system — see api/app.py). Existing rows default to 'system'.
ALTER TABLE sales ADD COLUMN IF NOT EXISTS created_by VARCHAR(80) DEFAULT 'system';

-- products: belt-and-suspenders guard against negative stock at the
-- database level, in addition to the application-level fix in
-- models.create_sale(). Postgres has no ADD CONSTRAINT IF NOT EXISTS,
-- so this is wrapped in a check.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_quantity_non_negative'
    ) THEN
        ALTER TABLE products
            ADD CONSTRAINT chk_quantity_non_negative CHECK (quantity_in_stock >= 0);
    END IF;
END $$;

-- Indexes on foreign-key columns this app filters/joins on often.
-- Postgres does not create these automatically (only PK/UNIQUE do).
CREATE INDEX IF NOT EXISTS idx_products_category_id       ON products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_supplier_id        ON products(supplier_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id           ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_product_id        ON sale_items(product_id);
CREATE INDEX IF NOT EXISTS idx_stock_movements_product_id   ON stock_movements(product_id);
CREATE INDEX IF NOT EXISTS idx_restock_alerts_product_id    ON restock_alerts(product_id);
CREATE INDEX IF NOT EXISTS idx_restock_alerts_unresolved    ON restock_alerts(is_resolved) WHERE is_resolved = FALSE;
CREATE INDEX IF NOT EXISTS idx_sales_created_at             ON sales(created_at);
