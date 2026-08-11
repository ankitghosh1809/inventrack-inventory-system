import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

"""
app.py — Flask REST API for the Inventory Management System

Run:
    python app.py

All routes return JSON. The frontend (../frontend) consumes this API.
When run directly (local dev), this also serves the frontend/ folder
as static files so relative fetch("/api/...") calls in main.js resolve
correctly without a separate static server — see FRONTEND_DIR below.
On Vercel, vercel.json serves frontend/ separately and this app only
ever handles /api/*, so the static config below is simply unused there.
"""

from flask import Flask, jsonify, request, session, send_from_directory
from flask_cors import CORS
import psycopg2

import models
from config import Config
from auth import auth_bp, OPEN_PATHS
from database import get_connection

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")
app.config.from_object(Config)

# Only the origins listed in Config.CORS_ORIGINS (local-dev ports by
# default) can make cross-origin requests, and cookies are allowed
# through so the session survives a cross-origin local-dev setup.
# In production, frontend and API share an origin and this is inert.
CORS(app, supports_credentials=True, origins=Config.CORS_ORIGINS)

app.register_blueprint(auth_bp)


# ─────────────────────────────────────────────
# AUTH GATE
# ─────────────────────────────────────────────
# Fails CLOSED by default: every /api/* route requires a logged-in
# session unless its path is explicitly listed in auth.OPEN_PATHS.
# A new route added later is automatically protected without anyone
# having to remember to decorate it — the previous version of this
# app relied on remembering to add checks to each route individually,
# and predictably some (the PUT routes) never got them.
@app.before_request
def require_login():
    if request.path.startswith("/api/") and request.path not in OPEN_PATHS:
        if not session.get("logged_in"):
            return error("Login required", 401)


# ─────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────

def success(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def error(message="Something went wrong", status=400):
    return jsonify({"success": False, "message": message, "data": None}), status


def safe_int(value, default, min_val=None, max_val=None):
    """int(request.args.get(...)) blows up with an unhandled 500 on
    anything non-numeric. This clamps to [min_val, max_val] and falls
    back to `default` instead of raising."""
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if min_val is not None:
        result = max(result, min_val)
    if max_val is not None:
        result = min(result, max_val)
    return result


def to_number(value, field_name):
    """Coerce a request field to float, raising a ValueError with a
    clean message (caught by the route) instead of letting a bad type
    fall through to a raw Postgres error."""
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{field_name}' must be a number")


def db_error_message(e):
    """Map common Postgres error codes to a message that's safe to
    show the caller, instead of leaking str(e) (which can include raw
    SQL / column names / internal detail)."""
    pgcode = getattr(e, "pgcode", None)
    return {
        "23505": "A record with that value already exists.",
        "23503": "That refers to a category, supplier, or product that doesn't exist.",
        "23514": "One of the submitted values isn't allowed (check payment method, status, or quantity).",
        "23502": "A required field is missing.",
    }.get(pgcode, "Something went wrong processing your request.")


def paginate_args():
    page = safe_int(request.args.get("page"), default=1, min_val=1)
    per_page = safe_int(request.args.get("per_page"), default=Config.DEFAULT_PAGE_SIZE, min_val=1, max_val=100)
    return page, per_page


# ─────────────────────────────────────────────
# STATIC FRONTEND (local dev only — see module docstring)
# ─────────────────────────────────────────────

@app.route("/")
def serve_landing():
    return send_from_directory(FRONTEND_DIR, "index.html")


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    summary = models.get_dashboard_summary()
    chart_days = safe_int(request.args.get("days"), default=7, min_val=1, max_val=90)
    summary["sales_chart"] = models.get_sales_chart_data(chart_days)
    summary["top_products"] = models.get_top_selling_products(5)
    summary["category_stock"] = models.get_category_stock_value()
    return success(summary)


# ─────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────

@app.route("/api/categories", methods=["GET"])
def list_categories():
    active_only = request.args.get("active_only", "true").lower() != "false"
    return success(models.get_all_categories(active_only))


@app.route("/api/categories", methods=["POST"])
def add_category():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return error("Category name is required")
    try:
        cat_id = models.create_category(data["name"], data.get("description"))
        return success({"id": cat_id}, "Category created", 201)
    except Exception as e:
        if getattr(e, "pgcode", None) == "23505":
            return error("A category with this name already exists")
        return error(db_error_message(e))


@app.route("/api/categories/<int:category_id>", methods=["PUT"])
def update_category(category_id):
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return error("Category name is required")
    if not models.get_category_by_id(category_id):
        return error("Category not found", 404)
    try:
        models.update_category(category_id, data["name"], data.get("description"), data.get("is_active", True))
        return success(message="Category updated successfully")
    except Exception as e:
        if getattr(e, "pgcode", None) == "23505":
            return error("A category with this name already exists")
        return error(db_error_message(e))


@app.route("/api/categories/<int:category_id>", methods=["DELETE"])
def remove_category(category_id):
    if not models.get_category_by_id(category_id):
        return error("Category not found", 404)
    models.delete_category(category_id)
    return success(message="Category deactivated")


# ─────────────────────────────────────────────
# SUPPLIERS
# ─────────────────────────────────────────────

@app.route("/api/suppliers", methods=["GET"])
def list_suppliers():
    active_only = request.args.get("active_only", "true").lower() != "false"
    return success(models.get_all_suppliers(active_only))


@app.route("/api/suppliers/<int:supplier_id>", methods=["GET"])
def get_supplier(supplier_id):
    supplier = models.get_supplier_by_id(supplier_id)
    if not supplier:
        return error("Supplier not found", 404)
    return success(supplier)


@app.route("/api/suppliers", methods=["POST"])
def add_supplier():
    data = request.get_json(silent=True) or {}
    if not data:
        return error("Request body is required")
    if not data.get("name"):
        return error("Supplier name is required")
    if not data.get("email"):
        return error("Supplier email is required")
    try:
        supplier_id = models.create_supplier(data)
        return success({"id": supplier_id}, "Supplier added successfully", 201)
    except Exception as e:
        if getattr(e, "pgcode", None) == "23505":  # unique_violation
            return error("A supplier with this email already exists")
        return error(db_error_message(e))


@app.route("/api/suppliers/<int:supplier_id>", methods=["PUT"])
def update_supplier(supplier_id):
    data = request.get_json(silent=True) or {}
    if not data:
        return error("Request body is required")
    if not data.get("name"):
        return error("Supplier name is required")
    if not data.get("email"):
        return error("Supplier email is required")
    if not models.get_supplier_by_id(supplier_id):
        return error("Supplier not found", 404)
    try:
        models.update_supplier(supplier_id, data)
        return success(message="Supplier updated successfully")
    except Exception as e:
        if getattr(e, "pgcode", None) == "23505":
            return error("A supplier with this email already exists")
        return error(db_error_message(e))


@app.route("/api/suppliers/<int:supplier_id>", methods=["DELETE"])
def remove_supplier(supplier_id):
    if not models.get_supplier_by_id(supplier_id):
        return error("Supplier not found", 404)
    models.delete_supplier(supplier_id)
    return success(message="Supplier deactivated")


# ─────────────────────────────────────────────
# PRODUCTS
# ─────────────────────────────────────────────

@app.route("/api/products", methods=["GET"])
def list_products():
    page, per_page = paginate_args()
    search = request.args.get("search")
    category_id = request.args.get("category_id", type=int)
    low_stock = request.args.get("low_stock", "false").lower() == "true"
    result = models.get_all_products(page, per_page, search, category_id, low_stock)
    return success(result)


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = models.get_product_by_id(product_id)
    if not product:
        return error("Product not found", 404)
    return success(product)


@app.route("/api/products", methods=["POST"])
def add_product():
    data = request.get_json(silent=True) or {}
    if not data:
        return error("Request body is required")

    required = ["name", "sku", "unit_price", "selling_price"]
    missing = [f for f in required if not data.get(f) and data.get(f) != 0]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}")

    try:
        data["unit_price"] = to_number(data["unit_price"], "unit_price")
        data["selling_price"] = to_number(data["selling_price"], "selling_price")
    except ValueError as e:
        return error(str(e))

    try:
        product_id = models.create_product(data, created_by=session.get("username", "system"))
        return success({"id": product_id}, "Product created", 201)
    except Exception as e:
        if getattr(e, "pgcode", None) == "23505":  # unique_violation
            return error("A product with this SKU already exists")
        return error(db_error_message(e))


@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    data = request.get_json(silent=True) or {}
    if not data:
        return error("Request body is required")

    required = ["name", "unit_price", "selling_price"]
    missing = [f for f in required if not data.get(f) and data.get(f) != 0]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}")

    if not models.get_product_by_id(product_id):
        return error("Product not found", 404)

    try:
        data["unit_price"] = to_number(data["unit_price"], "unit_price")
        data["selling_price"] = to_number(data["selling_price"], "selling_price")
    except ValueError as e:
        return error(str(e))

    try:
        models.update_product(product_id, data)
        return success(message="Product updated successfully")
    except Exception as e:
        return error(db_error_message(e))


@app.route("/api/products/<int:product_id>/stock", methods=["PATCH"])
def adjust_stock(product_id):
    """Manually adjust stock (positive to add, negative to remove)."""
    data = request.get_json(silent=True) or {}
    if "quantity_change" not in data:
        return error("quantity_change is required")

    try:
        quantity_change = int(data["quantity_change"])
    except (TypeError, ValueError):
        return error("quantity_change must be a whole number")

    try:
        new_stock = models.adjust_stock(
            product_id,
            quantity_change,
            data.get("movement_type", "adjustment"),
            data.get("notes"),
            created_by=session.get("username", "system"),
        )
        return success({"new_stock": new_stock}, "Stock adjusted")
    except ValueError as e:
        return error(str(e))


@app.route("/api/products/<int:product_id>", methods=["DELETE"])
def remove_product(product_id):
    if not models.get_product_by_id(product_id):
        return error("Product not found", 404)
    models.delete_product(product_id)
    return success(message="Product deactivated")


@app.route("/api/products/<int:product_id>/movements", methods=["GET"])
def product_movements(product_id):
    if not models.get_product_by_id(product_id):
        return error("Product not found", 404)
    limit = safe_int(request.args.get("limit"), default=20, min_val=1, max_val=200)
    return success(models.get_stock_movements(product_id, limit))


@app.route("/api/stock-movements", methods=["GET"])
def all_movements():
    limit = safe_int(request.args.get("limit"), default=50, min_val=1, max_val=200)
    return success(models.get_stock_movements(limit=limit))


# ─────────────────────────────────────────────
# SALES
# ─────────────────────────────────────────────

@app.route("/api/sales", methods=["GET"])
def list_sales():
    page, per_page = paginate_args()
    search = request.args.get("search")
    return success(models.get_all_sales(page, per_page, search))


@app.route("/api/sales/<int:sale_id>", methods=["GET"])
def get_sale(sale_id):
    sale = models.get_sale_by_id(sale_id)
    if not sale:
        return error("Sale not found", 404)
    return success(sale)


@app.route("/api/sales", methods=["POST"])
def create_sale():
    data = request.get_json(silent=True) or {}
    if not data:
        return error("Request body is required")
    if not data.get("items") or not isinstance(data["items"], list):
        return error("At least one item is required")

    for item in data["items"]:
        if not item.get("product_id") or not item.get("quantity") or item.get("unit_price") is None:
            return error("Each item needs product_id, quantity, and unit_price")
        try:
            item["quantity"] = int(item["quantity"])
            item["unit_price"] = float(item["unit_price"])
        except (TypeError, ValueError):
            return error("Item quantity and unit_price must be numbers")
        if item["quantity"] <= 0:
            return error("Item quantity must be greater than zero")

    try:
        result = models.create_sale(data, data["items"], created_by=session.get("username", "system"))
        return success(result, "Sale recorded successfully", 201)
    except ValueError as e:
        return error(str(e))
    except Exception as e:
        return error(f"Failed to record sale: {db_error_message(e)}")


@app.route("/api/sales/<int:sale_id>/status", methods=["PATCH"])
def update_sale_status(sale_id):
    """Cancel or refund a sale. Restocks the items and logs the
    reversal as a stock movement — the schema already supported these
    statuses (see database/schema.sql) but nothing ever wrote them."""
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in ("cancelled", "refunded"):
        return error("status must be 'cancelled' or 'refunded'")

    sale = models.get_sale_by_id(sale_id)
    if not sale:
        return error("Sale not found", 404)
    if sale["status"] in ("cancelled", "refunded"):
        return error(f"Sale is already {sale['status']}")

    try:
        models.cancel_or_refund_sale(sale_id, new_status, created_by=session.get("username", "system"))
        return success(message=f"Sale marked as {new_status} and stock restored")
    except ValueError as e:
        return error(str(e))


# ─────────────────────────────────────────────
# ALERTS
# ─────────────────────────────────────────────

@app.route("/api/alerts", methods=["GET"])
def list_alerts():
    return success(models.get_active_alerts())


@app.route("/api/alerts/<int:alert_id>/resolve", methods=["PATCH"])
def resolve_alert(alert_id):
    models.resolve_alert(alert_id)
    return success(message="Alert resolved")


# ─────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Actually checks the database, not just that the process is up —
    the previous version returned "healthy" even with DATABASE_URL
    missing or the DB unreachable, which defeats the point of a health
    check."""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()
        return success({"status": "running", "database": "connected"}, "API is healthy")
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "API is running but the database is unreachable",
            "data": {"status": "running", "database": "disconnected", "detail": str(e)},
        }), 503


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
