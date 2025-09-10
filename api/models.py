"""
models.py — All database interactions for the Inventory Management System.

Each section maps to a feature area: products, suppliers, sales, alerts, analytics.
Functions return plain dicts/lists so the Flask routes stay thin.
"""

import random
import string
from datetime import datetime
from database import execute_query, execute_transaction


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def generate_invoice_number():
    """Generate a unique invoice number like INV-20240512-A3X9."""
    today = datetime.now().strftime("%Y%m%d")
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"INV-{today}-{suffix}"


# ─────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────

def get_all_categories():
    return execute_query("SELECT * FROM categories ORDER BY name", fetch=True)


def create_category(name, description=None):
    return execute_query(
        "INSERT INTO categories (name, description) VALUES (%s, %s)",
        (name, description),
    )


# ─────────────────────────────────────────────
# SUPPLIERS
# ─────────────────────────────────────────────

def get_all_suppliers(active_only=True):
    if active_only:
        return execute_query(
            "SELECT * FROM suppliers WHERE is_active = TRUE ORDER BY name", fetch=True
        )
    return execute_query("SELECT * FROM suppliers ORDER BY name", fetch=True)


def get_supplier_by_id(supplier_id):
    rows = execute_query(
        "SELECT * FROM suppliers WHERE id = %s", (supplier_id,), fetch=True
    )
    return rows[0] if rows else None


def create_supplier(data):
    return execute_query(
        """INSERT INTO suppliers (name, contact_person, email, phone, address, city, country)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (
            data["name"],
            data.get("contact_person"),
            data["email"],
            data.get("phone"),
            data.get("address"),
            data.get("city"),
            data.get("country", "India"),
        ),
    )


def update_supplier(supplier_id, data):
    return execute_query(
        """UPDATE suppliers SET name=%s, contact_person=%s, email=%s,
           phone=%s, address=%s, city=%s, country=%s, is_active=%s
           WHERE id=%s""",
        (
            data["name"],
            data.get("contact_person"),
            data["email"],
            data.get("phone"),
            data.get("address"),
            data.get("city"),
            data.get("country", "India"),
            data.get("is_active", True),
            supplier_id,
        ),
    )


def delete_supplier(supplier_id):
    # Soft delete so historical records remain intact
    return execute_query(
        "UPDATE suppliers SET is_active = FALSE WHERE id = %s", (supplier_id,)
    )


# ─────────────────────────────────────────────
# PRODUCTS
# ─────────────────────────────────────────────

def get_all_products(page=1, per_page=10, search=None, category_id=None, low_stock_only=False):
    conditions = ["p.is_active = TRUE"]
    params = []

    if search:
        conditions.append("(p.name LIKE %s OR p.sku LIKE %s)")
        params += [f"%{search}%", f"%{search}%"]

    if category_id:
        conditions.append("p.category_id = %s")
        params.append(category_id)

    if low_stock_only:
        conditions.append("p.quantity_in_stock <= p.reorder_level")

    where = "WHERE " + " AND ".join(conditions)
    offset = (page - 1) * per_page

    query = f"""
        SELECT p.*, c.name AS category_name, s.name AS supplier_name
        FROM products p
        LEFT JOIN categories c ON p.category_id = c.id
        LEFT JOIN suppliers s ON p.supplier_id = s.id
        {where}
        ORDER BY p.name
        LIMIT %s OFFSET %s
    """
    params += [per_page, offset]
    products = execute_query(query, params, fetch=True)

    count_query = f"SELECT COUNT(*) AS total FROM products p {where}"
    total = execute_query(count_query, params[:-2], fetch=True)[0]["total"]

    return {"products": products, "total": total, "page": page, "per_page": per_page}


def get_product_by_id(product_id):
    rows = execute_query(
        """SELECT p.*, c.name AS category_name, s.name AS supplier_name
           FROM products p
           LEFT JOIN categories c ON p.category_id = c.id
           LEFT JOIN suppliers s ON p.supplier_id = s.id
           WHERE p.id = %s""",
        (product_id,),
        fetch=True,
    )
    return rows[0] if rows else None


def create_product(data):
    product_id = execute_query(
        """INSERT INTO products
           (name, sku, description, category_id, supplier_id, unit_price,
            selling_price, quantity_in_stock, reorder_level, reorder_quantity, unit)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            data["name"],
            data["sku"],
            data.get("description"),
            data.get("category_id"),
            data.get("supplier_id"),
            data["unit_price"],
            data["selling_price"],
            data.get("quantity_in_stock", 0),
            data.get("reorder_level", 10),
            data.get("reorder_quantity", 50),
            data.get("unit", "pcs"),
        ),
    )

    # Log initial stock movement if there's opening stock
    if data.get("quantity_in_stock", 0) > 0:
        _log_stock_movement(
            product_id=product_id,
            movement_type="adjustment",
            quantity_change=data["quantity_in_stock"],
            quantity_after=data["quantity_in_stock"],
            notes="Opening stock entry",
        )

    return product_id


def update_product(product_id, data):
    return execute_query(
        """UPDATE products SET name=%s, description=%s, category_id=%s, supplier_id=%s,
           unit_price=%s, selling_price=%s, reorder_level=%s, reorder_quantity=%s,
           unit=%s, is_active=%s WHERE id=%s""",
        (
            data["name"],
            data.get("description"),
            data.get("category_id"),
            data.get("supplier_id"),
            data["unit_price"],
            data["selling_price"],
            data.get("reorder_level", 10),
            data.get("reorder_quantity", 50),
            data.get("unit", "pcs"),
            data.get("is_active", True),
            product_id,
        ),
    )


def adjust_stock(product_id, quantity_change, movement_type="adjustment", notes=None):
    """Manually increase or decrease stock. quantity_change can be negative."""
    product = get_product_by_id(product_id)
    if not product:
        raise ValueError("Product not found")

    new_stock = product["quantity_in_stock"] + quantity_change
    if new_stock < 0:
        raise ValueError("Adjustment would result in negative stock")

    execute_query(
        "UPDATE products SET quantity_in_stock = %s WHERE id = %s",
        (new_stock, product_id),
    )

    _log_stock_movement(
        product_id=product_id,
        movement_type=movement_type,
        quantity_change=quantity_change,
        quantity_after=new_stock,
        notes=notes,
    )

    _check_and_create_alert(product_id, new_stock, product["reorder_level"])
    return new_stock


def delete_product(product_id):
    return execute_query(
        "UPDATE products SET is_active = FALSE WHERE id = %s", (product_id,)
    )


def get_stock_movements(product_id=None, limit=50):
    if product_id:
        return execute_query(
            """SELECT sm.*, p.name AS product_name, p.sku
               FROM stock_movements sm
               JOIN products p ON sm.product_id = p.id
               WHERE sm.product_id = %s
               ORDER BY sm.created_at DESC LIMIT %s""",
            (product_id, limit),
            fetch=True,
        )
    return execute_query(
        """SELECT sm.*, p.name AS product_name, p.sku
           FROM stock_movements sm
           JOIN products p ON sm.product_id = p.id
           ORDER BY sm.created_at DESC LIMIT %s""",
        (limit,),
        fetch=True,
    )


# ─────────────────────────────────────────────
# SALES
# ─────────────────────────────────────────────

def create_sale(sale_data, items):
    """
    Create a sale with multiple line items.
    Decrements stock for each product and logs movements.
    items: list of {product_id, quantity, unit_price}
    """
    # Validate stock availability first
    for item in items:
        product = get_product_by_id(item["product_id"])
        if not product:
            raise ValueError(f"Product {item['product_id']} not found")
        if product["quantity_in_stock"] < item["quantity"]:
            raise ValueError(
                f"Insufficient stock for '{product['name']}'. "
                f"Available: {product['quantity_in_stock']}, Requested: {item['quantity']}"
            )

    invoice = generate_invoice_number()
    total_amount = sum(i["quantity"] * i["unit_price"] for i in items)
    discount = sale_data.get("discount", 0)
    final_amount = total_amount - discount

    # Insert sale header
    sale_id = execute_query(
        """INSERT INTO sales
           (invoice_number, customer_name, customer_email, total_amount,
            discount, final_amount, payment_method, status, notes)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            invoice,
            sale_data.get("customer_name"),
            sale_data.get("customer_email"),
            total_amount,
            discount,
            final_amount,
            sale_data.get("payment_method", "cash"),
            "completed",
            sale_data.get("notes"),
        ),
    )

    # Insert line items and update stock
    for item in items:
        item_total = item["quantity"] * item["unit_price"]
        execute_query(
            """INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, total_price)
               VALUES (%s, %s, %s, %s, %s)""",
            (sale_id, item["product_id"], item["quantity"], item["unit_price"], item_total),
        )

        # Decrement stock
        product = get_product_by_id(item["product_id"])
        new_stock = product["quantity_in_stock"] - item["quantity"]
        execute_query(
            "UPDATE products SET quantity_in_stock = %s WHERE id = %s",
            (new_stock, item["product_id"]),
        )
        _log_stock_movement(
            product_id=item["product_id"],
            movement_type="sale",
            quantity_change=-item["quantity"],
            quantity_after=new_stock,
            reference_id=sale_id,
        )
        _check_and_create_alert(item["product_id"], new_stock, product["reorder_level"])

    return {"sale_id": sale_id, "invoice_number": invoice, "final_amount": final_amount}


def get_all_sales(page=1, per_page=10, search=None):
    conditions = []
    params = []

    if search:
        conditions.append("(s.invoice_number LIKE %s OR s.customer_name LIKE %s)")
        params += [f"%{search}%", f"%{search}%"]

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    offset = (page - 1) * per_page

    sales = execute_query(
        f"""SELECT * FROM sales {where}
            ORDER BY created_at DESC LIMIT %s OFFSET %s""",
        params + [per_page, offset],
        fetch=True,
    )
    total = execute_query(
        f"SELECT COUNT(*) AS total FROM sales {where}", params, fetch=True
    )[0]["total"]

    return {"sales": sales, "total": total, "page": page, "per_page": per_page}


def get_sale_by_id(sale_id):
    sale = execute_query(
        "SELECT * FROM sales WHERE id = %s", (sale_id,), fetch=True
    )
    if not sale:
        return None
    sale = sale[0]
    sale["items"] = execute_query(
        """SELECT si.*, p.name AS product_name, p.sku
           FROM sale_items si
           JOIN products p ON si.product_id = p.id
           WHERE si.sale_id = %s""",
        (sale_id,),
        fetch=True,
    )
    return sale


# ─────────────────────────────────────────────
# ALERTS
# ─────────────────────────────────────────────

def get_active_alerts():
    return execute_query(
        """SELECT ra.*, p.name AS product_name, p.sku, p.reorder_quantity,
                  s.name AS supplier_name, s.email AS supplier_email
           FROM restock_alerts ra
           JOIN products p ON ra.product_id = p.id
           LEFT JOIN suppliers s ON p.supplier_id = s.id
           WHERE ra.is_resolved = FALSE
           ORDER BY ra.created_at DESC""",
        fetch=True,
    )


def resolve_alert(alert_id):
    return execute_query(
        "UPDATE restock_alerts SET is_resolved = TRUE, resolved_at = NOW() WHERE id = %s",
        (alert_id,),
    )


# ─────────────────────────────────────────────
# ANALYTICS / DASHBOARD
# ─────────────────────────────────────────────

def get_dashboard_summary():
    total_products = execute_query(
        "SELECT COUNT(*) AS cnt FROM products WHERE is_active = TRUE", fetch=True
    )[0]["cnt"]

    low_stock_count = execute_query(
        "SELECT COUNT(*) AS cnt FROM products WHERE is_active = TRUE AND quantity_in_stock <= reorder_level",
        fetch=True,
    )[0]["cnt"]

    out_of_stock = execute_query(
        "SELECT COUNT(*) AS cnt FROM products WHERE is_active = TRUE AND quantity_in_stock = 0",
        fetch=True,
    )[0]["cnt"]

    total_suppliers = execute_query(
        "SELECT COUNT(*) AS cnt FROM suppliers WHERE is_active = TRUE", fetch=True
    )[0]["cnt"]

    # Revenue today
    today_revenue = execute_query(
        """SELECT COALESCE(SUM(final_amount), 0) AS revenue
           FROM sales WHERE DATE(created_at) = CURDATE() AND status = 'completed'""",
        fetch=True,
    )[0]["revenue"]

    # Revenue this month
    month_revenue = execute_query(
        """SELECT COALESCE(SUM(final_amount), 0) AS revenue
           FROM sales
           WHERE MONTH(created_at) = MONTH(NOW())
             AND YEAR(created_at) = YEAR(NOW())
             AND status = 'completed'""",
        fetch=True,
    )[0]["revenue"]

    # Active alerts count
    alert_count = execute_query(
        "SELECT COUNT(*) AS cnt FROM restock_alerts WHERE is_resolved = FALSE", fetch=True
    )[0]["cnt"]

    return {
        "total_products": total_products,
        "low_stock_count": low_stock_count,
        "out_of_stock": out_of_stock,
        "total_suppliers": total_suppliers,
        "today_revenue": float(today_revenue),
        "month_revenue": float(month_revenue),
        "alert_count": alert_count,
    }


def get_sales_chart_data(days=7):
    """Daily revenue for the last N days."""
    return execute_query(
        """SELECT DATE(created_at) AS date,
                  COUNT(*) AS orders,
                  COALESCE(SUM(final_amount), 0) AS revenue
           FROM sales
           WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
             AND status = 'completed'
           GROUP BY DATE(created_at)
           ORDER BY date""",
        (days,),
        fetch=True,
    )


def get_top_selling_products(limit=5):
    return execute_query(
        """SELECT p.name, p.sku, SUM(si.quantity) AS total_sold,
                  SUM(si.total_price) AS total_revenue
           FROM sale_items si
           JOIN products p ON si.product_id = p.id
           GROUP BY si.product_id
           ORDER BY total_sold DESC
           LIMIT %s""",
        (limit,),
        fetch=True,
    )


def get_category_stock_value():
    """Total stock value (cost) per category."""
    return execute_query(
        """SELECT c.name AS category,
                  SUM(p.quantity_in_stock * p.unit_price) AS stock_value,
                  SUM(p.quantity_in_stock) AS total_units
           FROM products p
           JOIN categories c ON p.category_id = c.id
           WHERE p.is_active = TRUE
           GROUP BY p.category_id
           ORDER BY stock_value DESC""",
        fetch=True,
    )


# ─────────────────────────────────────────────
# INTERNAL HELPERS
# ─────────────────────────────────────────────

def _log_stock_movement(product_id, movement_type, quantity_change, quantity_after, reference_id=None, notes=None):
    execute_query(
        """INSERT INTO stock_movements
           (product_id, movement_type, quantity_change, quantity_after, reference_id, notes)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (product_id, movement_type, quantity_change, quantity_after, reference_id, notes),
    )


def _check_and_create_alert(product_id, current_stock, reorder_level):
    """Create a restock alert if stock has dropped to or below the reorder level."""
    if current_stock <= reorder_level:
        # Avoid duplicate unresolved alerts
        existing = execute_query(
            "SELECT id FROM restock_alerts WHERE product_id = %s AND is_resolved = FALSE",
            (product_id,),
            fetch=True,
        )
        if not existing:
            execute_query(
                """INSERT INTO restock_alerts (product_id, current_stock, reorder_level)
                   VALUES (%s, %s, %s)""",
                (product_id, current_stock, reorder_level),
            )
