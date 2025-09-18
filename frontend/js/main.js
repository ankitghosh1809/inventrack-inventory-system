/**
 * main.js — Frontend logic for the Inventory Management System
 *
 * Architecture: Single-page application with manual routing.
 * Each "page" is a <section> shown/hidden based on nav clicks.
 * All data fetching goes through the api() helper which talks to
 * the Flask backend at API_BASE.
 */

const API_BASE = "/api";

// ─────────────────────────────────────────────
// GLOBAL STATE
// ─────────────────────────────────────────────

const state = {
  currentPage: "dashboard",
  products: { page: 1, search: "", category: "" },
  suppliers: { page: 1 },
  sales: { page: 1, search: "" },
  charts: {},       // holds Chart.js instances
  alertCount: 0,
};

// ─────────────────────────────────────────────
// API HELPER
// ─────────────────────────────────────────────

async function api(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const defaults = {
    headers: { "Content-Type": "application/json" },
  };
  try {
    const res = await fetch(url, { ...defaults, ...options });
    const json = await res.json();
    if (!res.ok || !json.success) {
      throw new Error(json.message || "API error");
    }
    return json.data;
  } catch (err) {
    // Re-throw so callers can handle; log here for debugging
    console.error(`API error [${path}]:`, err.message);
    throw err;
  }
}

// ─────────────────────────────────────────────
// TOAST NOTIFICATIONS
// ─────────────────────────────────────────────

function toast(message, type = "info") {
  const icons = { success: "✓", error: "✕", warning: "⚠", info: "ℹ" };
  const container = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.innerHTML = `<span>${icons[type] || icons.info}</span><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ─────────────────────────────────────────────
// NAVIGATION / ROUTING
// ─────────────────────────────────────────────

function navigate(page) {
  document.querySelectorAll(".page-section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));

  const section = document.getElementById(`page-${page}`);
  if (section) section.classList.add("active");

  const navItem = document.querySelector(`[data-page="${page}"]`);
  if (navItem) navItem.classList.add("active");

  document.getElementById("header-title").textContent = pageTitles[page] || "Dashboard";
  state.currentPage = page;

  // Load data for the activated page
  const loaders = {
    dashboard: loadDashboard,
    products: loadProducts,
    suppliers: loadSuppliers,
    sales: loadSales,
    alerts: loadAlerts,
    movements: loadMovements,
  };
  if (loaders[page]) loaders[page]();
}

const pageTitles = {
  dashboard: "Dashboard",
  products: "Products",
  suppliers: "Suppliers",
  sales: "Sales",
  alerts: "Restock Alerts",
  movements: "Stock Movements",
};

// ─────────────────────────────────────────────
// DASHBOARD
// ─────────────────────────────────────────────

async function loadDashboard() {
  try {
    const data = await api("/dashboard");
    renderStats(data);
    renderSalesChart(data.sales_chart);
    renderTopProducts(data.top_products);
    renderCategoryChart(data.category_stock);
  } catch (e) {
    toast("Could not load dashboard data. Is the backend running?", "error");
  }
}

function renderStats(data) {
  const fmt = (n) => "₹" + Number(n).toLocaleString("en-IN", { maximumFractionDigits: 0 });
  document.getElementById("stat-products").textContent = data.total_products;
  document.getElementById("stat-suppliers").textContent = data.total_suppliers;
  document.getElementById("stat-low-stock").textContent = data.low_stock_count;
  document.getElementById("stat-alerts").textContent = data.alert_count;
  document.getElementById("stat-today-rev").textContent = fmt(data.today_revenue);
  document.getElementById("stat-month-rev").textContent = fmt(data.month_revenue);

  // Update sidebar badge
  state.alertCount = data.alert_count;
  const badge = document.getElementById("alert-badge");
  badge.textContent = data.alert_count;
  badge.style.display = data.alert_count > 0 ? "inline-block" : "none";
}

function renderSalesChart(chartData) {
  const canvas = document.getElementById("sales-chart");
  if (!canvas) return;
  if (state.charts.sales) state.charts.sales.destroy();

  const labels = chartData.map(r => {
    const d = new Date(r.date);
    return d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
  });
  const revenues = chartData.map(r => Number(r.revenue));

  state.charts.sales = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Revenue (₹)",
        data: revenues,
        backgroundColor: "rgba(200, 84, 26, 0.15)",
        borderColor: "#c8541a",
        borderWidth: 2,
        borderRadius: 5,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => "₹" + ctx.parsed.y.toLocaleString("en-IN"),
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          grid: { color: "#e2ddd7" },
          ticks: { callback: v => "₹" + (v >= 1000 ? (v/1000).toFixed(0) + "k" : v) },
        },
        x: { grid: { display: false } },
      },
    },
  });
}

function renderTopProducts(products) {
  const tbody = document.getElementById("top-products-body");
  if (!products.length) {
    tbody.innerHTML = `<tr><td colspan="3" class="text-muted" style="padding:20px;text-align:center">No sales data yet</td></tr>`;
    return;
  }
  tbody.innerHTML = products.map((p, i) => `
    <tr>
      <td>${i + 1}. ${escHtml(p.name)}</td>
      <td class="mono text-right">${p.total_sold}</td>
      <td class="mono text-right">₹${Number(p.total_revenue).toLocaleString("en-IN")}</td>
    </tr>
  `).join("");
}

function renderCategoryChart(categories) {
  const canvas = document.getElementById("category-chart");
  if (!canvas || !categories.length) return;
  if (state.charts.category) state.charts.category.destroy();

  const colors = ["#c8541a", "#2d6a4f", "#b5890d", "#2255a4", "#7a5af8", "#6b6560"];
  state.charts.category = new Chart(canvas, {
    type: "doughnut",
    data: {
      labels: categories.map(c => c.category),
      datasets: [{
        data: categories.map(c => Number(c.stock_value)),
        backgroundColor: colors.slice(0, categories.length),
        borderWidth: 0,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "bottom", labels: { boxWidth: 12, padding: 14, font: { size: 11 } } },
        tooltip: {
          callbacks: {
            label: ctx => ` ₹${ctx.parsed.toLocaleString("en-IN")}`,
          },
        },
      },
      cutout: "65%",
    },
  });
}

// ─────────────────────────────────────────────
// PRODUCTS
// ─────────────────────────────────────────────

async function loadProducts() {
  const { page, search, category } = state.products;
  const params = new URLSearchParams({ page, per_page: 10 });
  if (search) params.set("search", search);
  if (category) params.set("category_id", category);

  try {
    const data = await api(`/products?${params}`);
    renderProductsTable(data.products);
    renderPagination("products-pagination", data, (p) => {
      state.products.page = p;
      loadProducts();
    });
  } catch (e) {
    toast("Failed to load products", "error");
  }
}

function renderProductsTable(products) {
  const tbody = document.getElementById("products-tbody");
  if (!products.length) {
    tbody.innerHTML = `<tr><td colspan="8"><div class="empty-state"><p>No products found</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = products.map(p => {
    const stockPct = p.reorder_level > 0
      ? Math.min((p.quantity_in_stock / (p.reorder_level * 3)) * 100, 100)
      : 100;
    const stockClass = p.quantity_in_stock === 0 ? "empty" :
      p.quantity_in_stock <= p.reorder_level ? "low" : "ok";
    const badge = p.quantity_in_stock === 0
      ? `<span class="badge badge-red">Out of Stock</span>`
      : p.quantity_in_stock <= p.reorder_level
      ? `<span class="badge badge-yellow">Low Stock</span>`
      : `<span class="badge badge-green">In Stock</span>`;

    return `<tr>
      <td class="mono">${escHtml(p.sku)}</td>
      <td><strong>${escHtml(p.name)}</strong><br><span class="text-muted" style="font-size:.78rem">${escHtml(p.category_name || "—")}</span></td>
      <td>${escHtml(p.supplier_name || "—")}</td>
      <td class="text-right mono">₹${Number(p.selling_price).toLocaleString("en-IN")}</td>
      <td>
        <div class="stock-bar-wrap">
          <div class="stock-bar"><div class="stock-bar-fill ${stockClass}" style="width:${stockPct}%"></div></div>
          <span class="stock-num">${p.quantity_in_stock} ${escHtml(p.unit)}</span>
        </div>
        ${badge}
      </td>
      <td class="text-right mono text-muted">${p.reorder_level}</td>
      <td>
        <div class="flex gap-2">
          <button class="btn btn-sm btn-secondary" onclick="openStockAdjust(${p.id}, '${escHtml(p.name)}', ${p.quantity_in_stock})">Adjust</button>
          <button class="btn btn-sm btn-secondary" onclick="openEditProduct(${p.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteProduct(${p.id})">Del</button>
        </div>
      </td>
    </tr>`;
  }).join("");
}

// ─────────────────────────────────────────────
// SUPPLIERS
// ─────────────────────────────────────────────

async function loadSuppliers() {
  try {
    const data = await api("/suppliers");
    renderSuppliersTable(data);
  } catch (e) {
    toast("Failed to load suppliers", "error");
  }
}

function renderSuppliersTable(suppliers) {
  const tbody = document.getElementById("suppliers-tbody");
  if (!suppliers.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p>No suppliers yet</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = suppliers.map(s => `
    <tr>
      <td><strong>${escHtml(s.name)}</strong></td>
      <td>${escHtml(s.contact_person || "—")}</td>
      <td><a href="mailto:${escHtml(s.email)}">${escHtml(s.email)}</a></td>
      <td>${escHtml(s.phone || "—")}</td>
      <td>${escHtml(s.city || "—")}, ${escHtml(s.country || "")}</td>
      <td>
        <div class="flex gap-2">
          <button class="btn btn-sm btn-secondary" onclick="openEditSupplier(${s.id})">Edit</button>
          <button class="btn btn-sm btn-danger" onclick="deleteSupplier(${s.id})">Remove</button>
        </div>
      </td>
    </tr>
  `).join("");
}

// ─────────────────────────────────────────────
// SALES
// ─────────────────────────────────────────────

async function loadSales() {
  const { page, search } = state.sales;
  const params = new URLSearchParams({ page, per_page: 10 });
  if (search) params.set("search", search);

  try {
    const data = await api(`/sales?${params}`);
    renderSalesTable(data.sales);
    renderPagination("sales-pagination", data, (p) => {
      state.sales.page = p;
      loadSales();
    });
  } catch (e) {
    toast("Failed to load sales", "error");
  }
}

function renderSalesTable(sales) {
  const tbody = document.getElementById("sales-tbody");
  if (!sales.length) {
    tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><p>No sales recorded yet</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = sales.map(s => {
    const statusClass = { completed: "green", pending: "yellow", cancelled: "red", refunded: "blue" }[s.status] || "gray";
    const date = new Date(s.created_at).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
    return `<tr>
      <td class="mono">${escHtml(s.invoice_number)}</td>
      <td>${escHtml(s.customer_name || "Walk-in Customer")}</td>
      <td>${date}</td>
      <td class="mono text-right">₹${Number(s.final_amount).toLocaleString("en-IN")}</td>
      <td>${escHtml(s.payment_method || "—")}</td>
      <td><span class="badge badge-${statusClass}">${s.status}</span></td>
    </tr>`;
  }).join("");
}

// ─────────────────────────────────────────────
// ALERTS
// ─────────────────────────────────────────────

async function loadAlerts() {
  try {
    const data = await api("/alerts");
    renderAlerts(data);
  } catch (e) {
    toast("Failed to load alerts", "error");
  }
}

function renderAlerts(alerts) {
  const container = document.getElementById("alerts-list");
  if (!alerts.length) {
    container.innerHTML = `<div class="empty-state"><p>🎉 No active alerts — all stock levels look good!</p></div>`;
    return;
  }
  container.innerHTML = alerts.map(a => `
    <div class="alert-item">
      <div class="alert-dot"></div>
      <div class="alert-content">
        <div class="alert-product">${escHtml(a.product_name)} <span class="mono text-muted">(${escHtml(a.sku)})</span></div>
        <div class="alert-meta">
          Stock: <strong>${a.current_stock}</strong> units · Reorder at: ${a.reorder_level} ·
          Supplier: ${escHtml(a.supplier_name || "N/A")}
          ${a.supplier_email ? `· <a href="mailto:${a.supplier_email}">${a.supplier_email}</a>` : ""}
        </div>
        <div class="alert-meta">Suggested restock qty: <strong>${a.reorder_quantity || "—"}</strong></div>
      </div>
      <button class="btn btn-sm btn-secondary" onclick="resolveAlert(${a.id}, this)">Mark Resolved</button>
    </div>
  `).join("");
}

async function resolveAlert(alertId, btn) {
  btn.disabled = true;
  try {
    await api(`/alerts/${alertId}/resolve`, { method: "PATCH" });
    toast("Alert resolved", "success");
    loadAlerts();
    state.alertCount = Math.max(0, state.alertCount - 1);
    const badge = document.getElementById("alert-badge");
    badge.textContent = state.alertCount;
    badge.style.display = state.alertCount > 0 ? "inline-block" : "none";
  } catch (e) {
    toast("Failed to resolve alert", "error");
    btn.disabled = false;
  }
}

// ─────────────────────────────────────────────
// STOCK MOVEMENTS
// ─────────────────────────────────────────────

async function loadMovements() {
  try {
    const data = await api("/stock-movements?limit=50");
    renderMovements(data);
  } catch (e) {
    toast("Failed to load movements", "error");
  }
}

function renderMovements(movements) {
  const tbody = document.getElementById("movements-tbody");
  if (!movements.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><p>No stock movements recorded yet</p></div></td></tr>`;
    return;
  }
  tbody.innerHTML = movements.map(m => {
    const typeClass = { sale: "red", purchase: "green", adjustment: "blue", return: "green", damage: "yellow" }[m.movement_type] || "gray";
    const sign = m.quantity_change > 0 ? "+" : "";
    const date = new Date(m.created_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short" });
    return `<tr>
      <td>${date}</td>
      <td><strong>${escHtml(m.product_name)}</strong> <span class="mono text-muted">${escHtml(m.sku)}</span></td>
      <td><span class="badge badge-${typeClass}">${m.movement_type}</span></td>
      <td class="mono ${m.quantity_change > 0 ? "text-right" : "text-right"}" style="color:${m.quantity_change > 0 ? "var(--accent-2)" : "var(--danger)"}">
        ${sign}${m.quantity_change}
      </td>
      <td class="mono">${m.quantity_after}</td>
    </tr>`;
  }).join("");
}

// ─────────────────────────────────────────────
// MODALS — PRODUCT
// ─────────────────────────────────────────────

async function openAddProduct() {
  const categories = await api("/categories");
  const suppliers = await api("/suppliers");
  populateProductForm(null, categories, suppliers);
  document.getElementById("product-modal-title").textContent = "Add Product";
  openModal("product-modal");
}

async function openEditProduct(productId) {
  try {
    const [product, categories, suppliers] = await Promise.all([
      api(`/products/${productId}`),
      api("/categories"),
      api("/suppliers"),
    ]);
    populateProductForm(product, categories, suppliers);
    document.getElementById("product-modal-title").textContent = "Edit Product";
    openModal("product-modal");
  } catch (e) {
    toast("Failed to load product", "error");
  }
}

function populateProductForm(product, categories, suppliers) {
  const form = document.getElementById("product-form");
  form.dataset.id = product ? product.id : "";

  const catSelect = document.getElementById("f-category");
  catSelect.innerHTML = `<option value="">— Select Category —</option>` +
    categories.map(c => `<option value="${c.id}" ${product?.category_id === c.id ? "selected" : ""}>${escHtml(c.name)}</option>`).join("");

  const supSelect = document.getElementById("f-supplier");
  supSelect.innerHTML = `<option value="">— Select Supplier —</option>` +
    suppliers.map(s => `<option value="${s.id}" ${product?.supplier_id === s.id ? "selected" : ""}>${escHtml(s.name)}</option>`).join("");

  const fields = ["name", "sku", "description", "unit_price", "selling_price",
    "quantity_in_stock", "reorder_level", "reorder_quantity", "unit"];
  fields.forEach(f => {
    const el = document.getElementById(`f-${f}`);
    if (el) el.value = product ? (product[f] ?? "") : (f === "unit" ? "pcs" : "");
  });

  if (product) {
    document.getElementById("f-sku").readOnly = true;
  } else {
    document.getElementById("f-sku").readOnly = false;
  }
}

async function submitProductForm() {
  const form = document.getElementById("product-form");
  const id = form.dataset.id;

  const data = {
    name: val("f-name"),
    sku: val("f-sku"),
    description: val("f-description"),
    category_id: val("f-category") || null,
    supplier_id: val("f-supplier") || null,
    unit_price: parseFloat(val("f-unit_price")) || 0,
    selling_price: parseFloat(val("f-selling_price")) || 0,
    quantity_in_stock: parseInt(val("f-quantity_in_stock")) || 0,
    reorder_level: parseInt(val("f-reorder_level")) || 10,
    reorder_quantity: parseInt(val("f-reorder_quantity")) || 50,
    unit: val("f-unit") || "pcs",
  };

  if (!data.name || !data.sku) {
    toast("Name and SKU are required", "warning");
    return;
  }

  try {
    if (id) {
      await api(`/products/${id}`, { method: "PUT", body: JSON.stringify(data) });
      toast("Product updated", "success");
    } else {
      await api("/products", { method: "POST", body: JSON.stringify(data) });
      toast("Product added", "success");
    }
    closeModal("product-modal");
    loadProducts();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function deleteProduct(id) {
  if (!confirm("Deactivate this product? It will be hidden but not permanently deleted.")) return;
  try {
    await api(`/products/${id}`, { method: "DELETE" });
    toast("Product deactivated", "success");
    loadProducts();
  } catch (e) {
    toast(e.message, "error");
  }
}

// ─────────────────────────────────────────────
// STOCK ADJUSTMENT MODAL
// ─────────────────────────────────────────────

function openStockAdjust(productId, productName, currentStock) {
  document.getElementById("adj-product-name").textContent = productName;
  document.getElementById("adj-current-stock").textContent = currentStock;
  document.getElementById("adj-quantity").value = "";
  document.getElementById("adj-type").value = "adjustment";
  document.getElementById("adj-notes").value = "";
  document.getElementById("adj-form").dataset.id = productId;
  openModal("adjust-modal");
}

async function submitStockAdjust() {
  const form = document.getElementById("adj-form");
  const id = form.dataset.id;
  const quantity = parseInt(document.getElementById("adj-quantity").value);
  const type = document.getElementById("adj-type").value;
  const notes = document.getElementById("adj-notes").value;

  if (isNaN(quantity) || quantity === 0) {
    toast("Enter a non-zero quantity", "warning");
    return;
  }

  try {
    const res = await api(`/products/${id}/stock`, {
      method: "PATCH",
      body: JSON.stringify({ quantity_change: quantity, movement_type: type, notes }),
    });
    toast(`Stock updated. New level: ${res.new_stock}`, "success");
    closeModal("adjust-modal");
    loadProducts();
  } catch (e) {
    toast(e.message, "error");
  }
}

// ─────────────────────────────────────────────
// MODALS — SUPPLIER
// ─────────────────────────────────────────────

function openAddSupplier() {
  clearSupplierForm();
  document.getElementById("supplier-modal-title").textContent = "Add Supplier";
  openModal("supplier-modal");
}

async function openEditSupplier(supplierId) {
  try {
    const s = await api(`/suppliers/${supplierId}`);
    document.getElementById("sf-id").value = s.id;
    document.getElementById("sf-name").value = s.name;
    document.getElementById("sf-contact").value = s.contact_person || "";
    document.getElementById("sf-email").value = s.email;
    document.getElementById("sf-phone").value = s.phone || "";
    document.getElementById("sf-address").value = s.address || "";
    document.getElementById("sf-city").value = s.city || "";
    document.getElementById("sf-country").value = s.country || "India";
    document.getElementById("supplier-modal-title").textContent = "Edit Supplier";
    openModal("supplier-modal");
  } catch (e) {
    toast("Failed to load supplier", "error");
  }
}

function clearSupplierForm() {
  ["sf-id", "sf-name", "sf-contact", "sf-email", "sf-phone", "sf-address", "sf-city"].forEach(id => {
    document.getElementById(id).value = "";
  });
  document.getElementById("sf-country").value = "India";
}

async function submitSupplierForm() {
  const id = document.getElementById("sf-id").value;
  const data = {
    name: val("sf-name"),
    contact_person: val("sf-contact"),
    email: val("sf-email"),
    phone: val("sf-phone"),
    address: val("sf-address"),
    city: val("sf-city"),
    country: val("sf-country"),
    is_active: true,
  };

  if (!data.name || !data.email) {
    toast("Name and email are required", "warning");
    return;
  }

  try {
    if (id) {
      await api(`/suppliers/${id}`, { method: "PUT", body: JSON.stringify(data) });
      toast("Supplier updated", "success");
    } else {
      await api("/suppliers", { method: "POST", body: JSON.stringify(data) });
      toast("Supplier added", "success");
    }
    closeModal("supplier-modal");
    loadSuppliers();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function deleteSupplier(id) {
  if (!confirm("Remove this supplier?")) return;
  try {
    await api(`/suppliers/${id}`, { method: "DELETE" });
    toast("Supplier removed", "success");
    loadSuppliers();
  } catch (e) {
    toast(e.message, "error");
  }
}

// ─────────────────────────────────────────────
// SALE MODAL
// ─────────────────────────────────────────────

let saleItems = [];

async function openNewSale() {
  saleItems = [];
  document.getElementById("sale-customer").value = "";
  document.getElementById("sale-email").value = "";
  document.getElementById("sale-payment").value = "cash";
  document.getElementById("sale-discount").value = "0";
  document.getElementById("sale-notes").value = "";

  // Load products for the item selector
  const data = await api("/products?per_page=100");
  const select = document.getElementById("sale-product-select");
  select.innerHTML = `<option value="">— Select Product —</option>` +
    data.products.map(p =>
      `<option value="${p.id}" data-price="${p.selling_price}" data-stock="${p.quantity_in_stock}">
        ${escHtml(p.name)} (${p.quantity_in_stock} ${escHtml(p.unit)}) — ₹${Number(p.selling_price).toLocaleString()}
      </option>`
    ).join("");

  renderSaleItems();
  openModal("sale-modal");
}

function addSaleItem() {
  const select = document.getElementById("sale-product-select");
  const option = select.options[select.selectedIndex];
  if (!option.value) return toast("Please select a product", "warning");

  const qty = parseInt(document.getElementById("sale-qty").value);
  if (!qty || qty < 1) return toast("Enter a valid quantity", "warning");

  const stock = parseInt(option.dataset.stock);
  if (qty > stock) return toast(`Only ${stock} units available`, "warning");

  const existing = saleItems.find(i => i.product_id == option.value);
  if (existing) {
    existing.quantity += qty;
  } else {
    saleItems.push({
      product_id: parseInt(option.value),
      name: option.text.split("(")[0].trim(),
      unit_price: parseFloat(option.dataset.price),
      quantity: qty,
    });
  }

  select.value = "";
  document.getElementById("sale-qty").value = "1";
  renderSaleItems();
}

function removeSaleItem(index) {
  saleItems.splice(index, 1);
  renderSaleItems();
}

function renderSaleItems() {
  const container = document.getElementById("sale-items-list");
  if (!saleItems.length) {
    container.innerHTML = `<p class="text-muted" style="font-size:.85rem;padding:8px 0">No items added yet.</p>`;
    document.getElementById("sale-total-display").textContent = "₹0";
    return;
  }

  let total = 0;
  container.innerHTML = saleItems.map((item, i) => {
    const lineTotal = item.quantity * item.unit_price;
    total += lineTotal;
    return `<div style="display:flex;align-items:center;gap:10px;padding:6px 0;border-bottom:1px solid var(--border)">
      <div style="flex:1">
        <strong>${escHtml(item.name)}</strong><br>
        <span class="text-muted mono" style="font-size:.8rem">₹${item.unit_price.toLocaleString()} × ${item.quantity} = ₹${lineTotal.toLocaleString("en-IN")}</span>
      </div>
      <button class="btn btn-sm btn-danger" onclick="removeSaleItem(${i})">✕</button>
    </div>`;
  }).join("");

  const discount = parseFloat(document.getElementById("sale-discount").value) || 0;
  document.getElementById("sale-total-display").textContent = `₹${(total - discount).toLocaleString("en-IN")}`;
}

async function submitSale() {
  if (!saleItems.length) return toast("Add at least one item", "warning");

  const data = {
    customer_name: val("sale-customer"),
    customer_email: val("sale-email"),
    payment_method: val("sale-payment"),
    discount: parseFloat(val("sale-discount")) || 0,
    notes: val("sale-notes"),
    items: saleItems,
  };

  try {
    const res = await api("/sales", { method: "POST", body: JSON.stringify(data) });
    toast(`Sale recorded! Invoice: ${res.invoice_number}`, "success");
    closeModal("sale-modal");
    saleItems = [];
    loadSales();
    // Reload dashboard and alerts in background
    if (state.currentPage === "dashboard") loadDashboard();
  } catch (e) {
    toast(e.message, "error");
  }
}

// ─────────────────────────────────────────────
// PAGINATION HELPER
// ─────────────────────────────────────────────

function renderPagination(containerId, data, onPage) {
  const container = document.getElementById(containerId);
  if (!container) return;

  const totalPages = Math.ceil(data.total / data.per_page);
  const current = data.page;

  if (totalPages <= 1) { container.innerHTML = ""; return; }

  let html = `<span class="pagination-info">Showing ${((current - 1) * data.per_page) + 1}–${Math.min(current * data.per_page, data.total)} of ${data.total}</span>`;
  html += `<button class="page-btn" onclick="changePage('${containerId}', ${current - 1})" ${current === 1 ? "disabled" : ""}>‹ Prev</button>`;

  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= current - 1 && i <= current + 1)) {
      html += `<button class="page-btn ${i === current ? "active" : ""}" onclick="changePage('${containerId}', ${i})">${i}</button>`;
    } else if (i === current - 2 || i === current + 2) {
      html += `<span style="color:var(--text-muted);padding:0 4px">…</span>`;
    }
  }

  html += `<button class="page-btn" onclick="changePage('${containerId}', ${current + 1})" ${current === totalPages ? "disabled" : ""}>Next ›</button>`;
  container.innerHTML = html;

  // Store onPage callback
  container._onPage = onPage;
}

function changePage(containerId, page) {
  const container = document.getElementById(containerId);
  if (container._onPage) container._onPage(page);
}

// ─────────────────────────────────────────────
// MODAL HELPERS
// ─────────────────────────────────────────────

function openModal(id) {
  document.getElementById(id).classList.add("open");
}
function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}

// Close modal on overlay click
document.addEventListener("click", (e) => {
  if (e.target.classList.contains("modal-overlay")) {
    e.target.classList.remove("open");
  }
});

// ─────────────────────────────────────────────
// UTILITY
// ─────────────────────────────────────────────

function val(id) {
  return document.getElementById(id)?.value?.trim() || "";
}

function escHtml(str) {
  if (str == null) return "";
  return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

// ─────────────────────────────────────────────
// INIT
// ─────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // Nav click handlers
  document.querySelectorAll(".nav-item[data-page]").forEach(item => {
    item.addEventListener("click", () => navigate(item.dataset.page));
  });

  // Product search
  document.getElementById("product-search")?.addEventListener("input", (e) => {
    state.products.search = e.target.value;
    state.products.page = 1;
    loadProducts();
  });

  // Sales search
  document.getElementById("sales-search")?.addEventListener("input", (e) => {
    state.sales.search = e.target.value;
    state.sales.page = 1;
    loadSales();
  });

  // Sale discount live-recalc
  document.getElementById("sale-discount")?.addEventListener("input", renderSaleItems);

  // Boot the dashboard
  navigate("dashboard");
});
