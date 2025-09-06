-- ============================================================
-- Inventory Management System - Database Schema
-- Author: Your Name
-- Created: 2024
-- ============================================================

CREATE DATABASE IF NOT EXISTS inventory_db;
USE inventory_db;

-- Suppliers table
CREATE TABLE IF NOT EXISTS suppliers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    contact_person VARCHAR(100),
    email VARCHAR(120) UNIQUE NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    city VARCHAR(80),
    country VARCHAR(80) DEFAULT 'India',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Categories table
CREATE TABLE IF NOT EXISTS categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    sku VARCHAR(80) UNIQUE NOT NULL,
    description TEXT,
    category_id INT,
    supplier_id INT,
    unit_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    selling_price DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    quantity_in_stock INT NOT NULL DEFAULT 0,
    reorder_level INT NOT NULL DEFAULT 10,       -- triggers low-stock alert below this
    reorder_quantity INT NOT NULL DEFAULT 50,    -- how much to order when restocking
    unit VARCHAR(30) DEFAULT 'pcs',             -- pcs, kg, litre, box, etc.
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(id) ON DELETE SET NULL
);

-- Sales table
CREATE TABLE IF NOT EXISTS sales (
    id INT AUTO_INCREMENT PRIMARY KEY,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    customer_name VARCHAR(150),
    customer_email VARCHAR(120),
    total_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    discount DECIMAL(10, 2) DEFAULT 0.00,
    final_amount DECIMAL(12, 2) NOT NULL DEFAULT 0.00,
    payment_method ENUM('cash', 'card', 'upi', 'bank_transfer') DEFAULT 'cash',
    status ENUM('pending', 'completed', 'cancelled', 'refunded') DEFAULT 'completed',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sale items table (line items per sale)
CREATE TABLE IF NOT EXISTS sale_items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sale_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_price DECIMAL(10, 2) NOT NULL,
    FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
);

-- Stock movements (audit trail for every stock change)
CREATE TABLE IF NOT EXISTS stock_movements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    movement_type ENUM('purchase', 'sale', 'adjustment', 'return', 'damage') NOT NULL,
    quantity_change INT NOT NULL,           -- positive = stock added, negative = stock removed
    quantity_after INT NOT NULL,            -- stock level after this movement
    reference_id INT,                       -- sale_id or purchase_id if applicable
    notes TEXT,
    created_by VARCHAR(80) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- Restock alerts log
CREATE TABLE IF NOT EXISTS restock_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    current_stock INT NOT NULL,
    reorder_level INT NOT NULL,
    is_resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- ============================================================
-- Seed Data
-- ============================================================

INSERT INTO categories (name, description) VALUES
('Electronics', 'Electronic devices and accessories'),
('Stationery', 'Office and school stationery items'),
('Furniture', 'Office and home furniture'),
('Consumables', 'Day-to-day consumable items'),
('Accessories', 'Various accessories');

INSERT INTO suppliers (name, contact_person, email, phone, address, city, country) VALUES
('TechSupply Co.', 'Rahul Sharma', 'rahul@techsupply.in', '+91-9876543210', '12 MG Road', 'Bengaluru', 'India'),
('OfficeWorld', 'Priya Mehta', 'priya@officeworld.in', '+91-9123456789', '45 Park Street', 'Kolkata', 'India'),
('FurniturePlus', 'Amit Singh', 'amit@furnitureplus.in', '+91-9988776655', '78 Link Road', 'Mumbai', 'India');

INSERT INTO products (name, sku, description, category_id, supplier_id, unit_price, selling_price, quantity_in_stock, reorder_level, reorder_quantity, unit) VALUES
('Wireless Mouse', 'ELEC-001', 'Ergonomic wireless optical mouse', 1, 1, 350.00, 599.00, 45, 10, 50, 'pcs'),
('Mechanical Keyboard', 'ELEC-002', 'USB mechanical keyboard with backlight', 1, 1, 1200.00, 1999.00, 12, 5, 20, 'pcs'),
('A4 Paper Ream', 'STAT-001', '500 sheets A4 size printing paper', 2, 2, 180.00, 280.00, 8, 15, 100, 'ream'),
('Ball Pen Pack', 'STAT-002', 'Pack of 10 blue ball pens', 2, 2, 40.00, 75.00, 120, 20, 200, 'pack'),
('Office Chair', 'FURN-001', 'Ergonomic office chair with lumbar support', 3, 3, 4500.00, 7500.00, 6, 3, 10, 'pcs'),
('Standing Desk', 'FURN-002', 'Height-adjustable standing desk', 3, 3, 12000.00, 18000.00, 3, 2, 5, 'pcs'),
('Printer Cartridge', 'CONS-001', 'HP compatible black ink cartridge', 4, 1, 450.00, 750.00, 7, 10, 30, 'pcs'),
('Hand Sanitizer', 'CONS-002', '500ml hand sanitizer bottle', 4, 2, 90.00, 150.00, 55, 20, 100, 'bottle'),
('USB-C Cable', 'ACC-001', '1.5m braided USB-C charging cable', 5, 1, 120.00, 249.00, 80, 15, 60, 'pcs'),
('Laptop Stand', 'ACC-002', 'Aluminium adjustable laptop stand', 5, 1, 800.00, 1499.00, 22, 8, 25, 'pcs');
