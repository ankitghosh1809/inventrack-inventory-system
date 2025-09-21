# InvenTrack — Inventory Management System

A full-stack inventory management solution built with **Python (Flask)** and **MySQL** on the backend, and a clean **HTML/CSS/JavaScript** dashboard on the frontend.

The system handles everything a small-to-mid-sized business needs: product catalog, supplier management, real-time stock tracking, sales recording, low-stock alerts, and analytics.

---

## Features

- **Product Management** — Add, edit, and deactivate products with SKU, category, pricing, and unit tracking
- **Supplier Management** — Maintain a supplier directory with contact details linked to products
- **Real-Time Stock Tracking** — Every stock change (sale, purchase, adjustment, damage) is logged as a movement record
- **Low-Stock Alerts** — Automatic alerts fire when stock drops to or below the reorder threshold; includes suggested reorder quantity and supplier contact
- **Sales Recording** — Multi-item invoices with customer details, payment method, discounts, and auto-decrement of stock
- **Analytics Dashboard** — Revenue charts, top-selling products, stock value by category
- **Stock Movements Audit Trail** — Full history of who changed what and when

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+, Flask 3.x |
| Database | MySQL 8.x |
| ORM / DB layer | mysql-connector-python (raw SQL, no ORM) |
| Frontend | Vanilla HTML5, CSS3, JavaScript (ES6+) |
| Charts | Chart.js 4 |
| Fonts | IBM Plex Sans, IBM Plex Mono |

---

## Project Structure

```
inventory-management-system/
│
├── backend/
│   ├── app.py              # Flask app — all API routes
│   ├── models.py           # All database queries and business logic
│   ├── database.py         # MySQL connection pool + query helpers
│   ├── config.py           # Config from environment variables
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Environment variable template
│
├── frontend/
│   ├── index.html          # Single-page dashboard UI
│   ├── css/
│   │   └── style.css       # All styles
│   └── js/
│       └── main.js         # All frontend logic and API calls
│
├── database/
│   └── schema.sql          # Full DB schema + seed data
│
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- MySQL 8.x running locally or remotely
- A modern web browser

### 1. Clone the repository

```bash
git clone https://github.com/your-username/inventory-management-system.git
cd inventory-management-system
```

### 2. Set up the database

Log into MySQL and run the schema file:

```bash
mysql -u root -p < database/schema.sql
```

This creates the `inventory_db` database, all tables, and loads some sample data so you can explore the app right away.

### 3. Configure the backend

```bash
cd backend
cp .env.example .env
```

Open `.env` and fill in your MySQL credentials:

```
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password_here
MYSQL_DB=inventory_db
SECRET_KEY=some-long-random-string
FLASK_DEBUG=true
```

### 4. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the backend

```bash
python app.py
```

The API will start at `http://localhost:5000`. You should see output like:

```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### 6. Open the frontend

Just open `frontend/index.html` directly in your browser — no build step needed. The dashboard will connect to the Flask API automatically.

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
| POST | `/api/sales` | Record a new sale |

### Alerts

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/alerts` | Get all unresolved low-stock alerts |
| PATCH | `/api/alerts/:id/resolve` | Mark an alert as resolved |

### Misc

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/categories` | List all categories |
| POST | `/api/categories` | Create a category |
| GET | `/api/stock-movements` | Recent stock movements (all products) |
| GET | `/api/health` | Health check |

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

## Screenshots

> _Add screenshots of your running dashboard here._

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
