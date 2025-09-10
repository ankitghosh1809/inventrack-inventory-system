import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

"""
app.py — Flask REST API for the Inventory Management System

Run:
    python app.py

All routes return JSON. The frontend (../frontend) consumes this API.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS

import models
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)  # allow the frontend to talk to this API during local dev


# ─────────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────────

def success(data=None, message="OK", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status


def error(message="Something went wrong", status=400):
    return jsonify({"success": False, "message": message, "data": None}), status


def paginate_args():
    page = max(int(request.args.get("page", 1)), 1)
    per_page = min(int(request.args.get("per_page", 10)), 100)
    return page, per_page


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@app.route("/api/dashboard", methods=["GET"])
def dashboard():
    summary = models.get_dashboard_summary()
    chart_days = int(request.args.get("days", 7))
    summary["sales_chart"] = models.get_sales_chart_data(chart_days)
    summary["top_products"] = models.get_top_selling_products(5)
    summary["category_stock"] = models.get_category_stock_value()
    return success(summary)


# ─────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────

@app.route("/api/categories", methods=["GET"])
def list_categories():
    return success(models.get_all_categories())


@app.route("/api/categories", methods=["POST"])
def add_category():
    data = request.get_json()
    if not data or not data.get("name"):
        return error("Category name is required")
    cat_id = models.create_category(data["name"], data.get("description"))
    return success({"id": cat_id}, "Category created", 201)


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
    data = request.get_json()
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
        if "Duplicate entry" in str(e):
            return error("A supplier with this email already exists")
        return error(str(e))


@app.route("/api/suppliers/<int:supplier_id>", methods=["PUT"])
def update_supplier(supplier_id):
    data = request.get_json()
    if not data:
        return error("Request body is required")
    if not models.get_supplier_by_id(supplier_id):
        return error("Supplier not found", 404)
    models.update_supplier(supplier_id, data)
    return success(message="Supplier updated successfully")


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
    data = request.get_json()
    if not data:
        return error("Request body is required")

    required = ["name", "sku", "unit_price", "selling_price"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return error(f"Missing required fields: {', '.join(missing)}")

    try:
        product_id = models.create_product(data)
        return success({"id": product_id}, "Product created", 201)
    except Exception as e:
        if "Duplicate entry" in str(e):
            return error("A product with this SKU already exists")
        return error(str(e))


@app.route("/api/products/<int:product_id>", methods=["PUT"])
def update_product(product_id):
    data = request.get_json()
    if not data:
        return error("Request body is required")
    if not models.get_product_by_id(product_id):
        return error("Product not found", 404)
    models.update_product(product_id, data)
    return success(message="Product updated successfully")


@app.route("/api/products/<int:product_id>/stock", methods=["PATCH"])
def adjust_stock(product_id):
    """Manually adjust stock (positive to add, negative to remove)."""
    data = request.get_json()
    if not data or "quantity_change" not in data:
        return error("quantity_change is required")

    try:
        new_stock = models.adjust_stock(
            product_id,
            int(data["quantity_change"]),
            data.get("movement_type", "adjustment"),
            data.get("notes"),
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
    limit = int(request.args.get("limit", 20))
    return success(models.get_stock_movements(product_id, limit))


@app.route("/api/stock-movements", methods=["GET"])
def all_movements():
    limit = int(request.args.get("limit", 50))
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
    data = request.get_json()
    if not data:
        return error("Request body is required")
    if not data.get("items") or not isinstance(data["items"], list):
        return error("At least one item is required")
    for item in data["items"]:
        if not item.get("product_id") or not item.get("quantity") or not item.get("unit_price"):
            return error("Each item needs product_id, quantity, and unit_price")
    try:
        result = models.create_sale(data, data["items"])
        return success(result, "Sale recorded successfully", 201)
    except ValueError as e:
        return error(str(e))
    except Exception as e:
        return error(f"Failed to record sale: {str(e)}")


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
    return success({"status": "running"}, "API is healthy")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)
