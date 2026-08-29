# InvenTrack — Inventory Management System

A full-stack inventory management solution built with **Python (Flask)** and **PostgreSQL (Neon)** on the backend, deployed on **Vercel**, with a clean **HTML/CSS/JavaScript** dashboard on the frontend.

The system handles everything a small-to-mid-sized business needs: product catalog, supplier management, real-time stock tracking, sales recording, low-stock alerts, and analytics.

---

## Features

- **Product Management** — Add, edit, and deactivate products with SKU, category, pricing, and unit tracking
- **Supplier Management** — Maintain a supplier directory with contact details linked to products
- **Category Management** — Full CRUD, including deactivating categories no longer in use
- **Real-Time Stock Tracking** — Every stock change (sale, purchase, adjustment, damage, return) is logged as a movement record, and every write that touches stock is atomic and row-locked so concurrent sales can't oversell the same product
- **Low-Stock Alerts** — Automatic alerts fire when stock drops to or below the reorder threshold; includes suggested reorder quantity and supplier contact
- **Sales Recording** — Multi-item invoices with customer details, payment method, discounts, and auto-decrement of stock
- **Sale Cancellation / Refunds** — Cancel or refund a sale and its stock is automatically restored
- **Analytics Dashboard** — Revenue charts, top-selling products, stock value by category
- **Stock Movements Audit Trail** — Full history of who changed what and when

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 3.x (Vercel serverless function) |
| Database | PostgreSQL (Neon) |
| DB layer | psycopg2 (raw SQL, no ORM) |
| Frontend | Vanilla HTML5, CSS3, JavaScript (ES6+) |
| Charts | Chart.js 4 |
| Fonts | IBM Plex Sans, IBM Plex Mono |

---

## Project Structure

```
inventory-management-system/
│
├── api/                    # Deployed to Vercel as a serverless function
│   ├── index.py             # Vercel entry point (imports app)
│   ├── app.py                # Flask app — all API routes
│   ├── models.py              # All database queries and business logic
│   ├── database.py            # Postgres (Neon) connection + query helpers
│   ├── config.py               # Config from environment variables
│   └── .env.example            # Copy to .env and fill in real values
│
├── frontend/
│   ├── index.html          # The dashboard — single page, open access
│   ├── css/
│   │   └── style.css       # Dashboard styles
│   └── js/
│       └── main.js         # Dashboard logic and API calls
│
├── database/
│   ├── schema.sql           # Full DB schema + seed data (fresh installs)
│   └── migrations/
│       └── 001_add_auth_and_integrity.sql   # Run once against an existing DB
│
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A PostgreSQL database — [Neon](https://neon.tech) is free and is what this project is deployed against
- A modern web browser

### 1. Clone the repository

```bash
git clone https://github.com/ankitghosh1809/inventrack-inventory-system.git
cd inventrack-inventory-system
```

### 2. Set up the database

Run the schema against your Postgres database:

```bash
psql "$DATABASE_URL" -f database/schema.sql
```

This creates all tables, the `updated_at` triggers, and loads sample data so you can explore the app right away.

**Already have a database from before?** (i.e. you set it up before login/category-deactivation/audit-trail support existed) — run the migration once instead of the full schema:

```bash
psql "$DATABASE_URL" -f database/migrations/001_add_auth_and_integrity.sql
```

It only adds what's missing (new columns, a constraint, some indexes) and is safe to run more than once. Skip this if you just ran `schema.sql` above on a brand-new database — it already includes everything.

### 3. Configure environment variables

Copy `api/.env.example` to `api/.env` and fill in real values:

```
DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require
```

Use the **pooled** connection string from your Neon dashboard (hostname contains `-pooler`) — Vercel's serverless functions open a fresh connection per invocation, and the direct (non-pooled) endpoint runs out of connections much faster under concurrent load.

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the backend locally

```bash
cd api
python app.py
```

When run this way, Flask also serves `frontend/` directly (matching how `vercel.json` routes things in production), so there's nothing extra to configure — just open your browser to:

```
http://localhost:5000
```

No build step needed. It's responsive; the sidebar collapses into a hamburger-triggered drawer below 1024px.

*(Opening `frontend/index.html` directly as a `file://` path won't work — its `fetch("/api/...")` calls need to be same-origin with the Flask server, which is exactly what browsing to `http://localhost:5000` gives you.)*

### Deploying to Vercel

`vercel.json` already routes `/api/*` to `api/index.py` and serves `frontend/` as static files. In the Vercel project's Settings → Environment Variables, add `DATABASE_URL` (the pooled Neon string), then push to trigger a deploy.

---

## API Reference

All endpoints return JSON in this shape:

```json
{
  "success": true,
  "message": "OK",
  "data": { ... }
}
```

All endpoints below are open — no login or session required.

### Dashboard

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard` | Summary stats + chart data |

### Products

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/products` | List products (supports `search`, `page`, `per_page`, `low_stock`) |
| GET | `/api/products/:id` | Get a single product |
| POST | `/api/products` | Create a product |
| PUT | `/api/products/:id` | Update a product |
| PATCH | `/api/products/:id/stock` | Adjust stock level |
| DELETE | `/api/products/:id` | Deactivate a product |
| GET | `/api/products/:id/movements` | Stock movement history for a product |

### Suppliers

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/suppliers` | List active suppliers |
| GET | `/api/suppliers/:id` | Get a single supplier |
| POST | `/api/suppliers` | Create a supplier |
| PUT | `/api/suppliers/:id` | Update a supplier |
| DELETE | `/api/suppliers/:id` | Deactivate a supplier |

### Sales

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/sales` | List sales (supports `search`, pagination) |
| GET | `/api/sales/:id` | Get a sale with its line items |
| POST | `/api/sales` | Record a new sale (atomic — see note below) |
| PATCH | `/api/sales/:id/status` | `{ "status": "cancelled" \| "refunded" }` — restocks the sale's items |

`POST /api/sales` runs as a single database transaction and locks every product involved before checking stock, so two sales for the same product can't both succeed past what's actually available — see the docstring on `models.create_sale` for the details.

### Alerts

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/alerts` | Get all unresolved low-stock alerts |
| PATCH | `/api/alerts/:id/resolve` | Mark an alert as resolved |

### Categories

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/categories` | List categories (`active_only=false` to include deactivated ones) |
| POST | `/api/categories` | Create a category |
| PUT | `/api/categories/:id` | Update a category |
| DELETE | `/api/categories/:id` | Deactivate a category |

### Misc

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/stock-movements` | Recent stock movements (all products) |
| GET | `/api/health` | Health check — actually pings the database, not just "is the process up" |

---

## Database Schema Overview

```
categories ──┐
              ├── products ──── sale_items ──── sales
suppliers  ──┘        │
                       ├── stock_movements
                       └── restock_alerts
```

- Products belong to one category and one supplier
- Each sale has multiple `sale_items` (line items)
- Every stock change writes a row to `stock_movements` (complete audit trail)
- When stock drops ≤ reorder_level, a `restock_alert` is created automatically

---

## Contributing

Pull requests are welcome. For larger changes please open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## License

MIT License — see [LICENSE](LICENSE) for details.

## 🌐 Live Demo
[https://inventrack-inventory-system.vercel.app](https://inventrack-inventory-system.vercel.app)
