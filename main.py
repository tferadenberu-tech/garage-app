import io
import json
from datetime import datetime, timedelta
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, send_file, session

app = Flask(__name__)
app.secret_key = "steely_garage_secret_key"  # Required for session management

# --- In-Memory System Database ---
garage_data = {
    "spare_parts": [
        {"id": 1, "part_name": "Oil Filter", "spec": "LF16015 / Heavy Duty", "qty": 20, "unit_price": 1200.00},
        {"id": 2, "part_name": "Fuel Filter", "spec": "FF5421 / High Efficiency", "qty": 15, "unit_price": 1800.00},
        {"id": 3, "part_name": "Brake Shoe Set", "spec": "Rear Axle / Heavy Duty Standard", "qty": 8, "unit_price": 4500.00}
    ],
    "maintenance_logs": [
        {
            "id": 1,
            "sn": "SN-001",
            "wo_no": "WO-2026-001",
            "vehicle": "AA-3-12345",
            "model": "Sino Truck 371",
            "reading_value": 124500,
            "reading_unit": "KM",
            "next_service": "129,500 KM (+5000)",
            "driver": "Alemayehu T.",
            "technician": "Mekonnen Kebede",
            "type": "PM",
            "work_status": "Completed",
            "start_time": "2026-07-20 08:00",
            "finish_time": "2026-07-20 14:30",
            "effective_hours": 6.5,
            "description": "Engine Oil & Filter Change",
            "replaced_spares": [
                {"part_name": "Oil Filter (LF16015)", "qty": 1, "unit_price": 1200.0, "total_cost": 1200.0},
                {"part_name": "Fuel Filter (FF5421)", "qty": 1, "unit_price": 1800.0, "total_cost": 1800.0}
            ],
            "battery_qty": 0, "battery_cost": 0.0,
            "lubrication_qty": 20.0, "lubrication_cost": 4500.0,
            "tire_qty": 0, "tire_cost": 0.0
        }
    ]
}

def calculate_effective_hours(start_str, finish_str):
    try:
        fmt = "%Y-%m-%dT%H:%M"
        t1 = datetime.strptime(start_str, fmt)
        t2 = datetime.strptime(finish_str, fmt)
        diff = (t2 - t1).total_seconds() / 3600.0
        return round(max(diff, 0.0), 2)
    except:
        return 0.0

def calculate_next_service(val, unit):
    try:
        val_int = int(val)
    except:
        return "N/A"
    
    if unit == "Hour":
        next_val = val_int + 250
        return f"{next_val:,} Hours (+250)"
    else:
        next_val = val_int + 5000
        return f"{next_val:,} KM (+5000)"

# --- Frontend HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I Garage Maintnace dash Bord</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #eef2f5; color: #1f2937; }
        .sidebar { background-color: #111827; min-height: 100vh; color: #9ca3af; padding: 20px 15px; }
        .sidebar .brand-title { color: #3b82f6; font-size: 1.5rem; font-weight: bold; margin-bottom: 5px; }
        .admin-badge { background-color: #ef4444; color: white; font-size: 0.7rem; font-weight: bold; padding: 3px 8px; border-radius: 4px; display: inline-block; margin-bottom: 15px; }
        .btn-export-main { background-color: #10b981; color: white; font-weight: 600; border: none; border-radius: 6px; width: 100%; text-align: left; padding: 10px 12px; margin-bottom: 15px; }
        .btn-export-main:hover { background-color: #059669; color: white; }
        .btn-logout { background-color: #dc2626; color: white; font-weight: 600; border: none; border-radius: 6px; width: 100%; text-align: left; padding: 10px 12px; margin-bottom: 25px; }
        .btn-logout:hover { background-color: #b91c1c; color: white; }
        .nav-link-custom { color: #d1d5db; text-decoration: none; display: block; padding: 10px 0; font-size: 0.95rem; font-weight: 500; }
        .nav-link-custom:hover { color: #ffffff; }
        
        .main-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 25px; }
        .main-title { font-size: 2.1rem; font-weight: 800; color: #111827; margin-bottom: 2px; }
        .main-subtitle { color: #6b7280; font-size: 0.95rem; }
        .user-box { text-align: right; }
        .user-name { font-weight: 700; color: #1f2937; display: block; }
        .user-role { background-color: #ef4444; color: white; font-size: 0.75rem; font-weight: bold; padding: 2px 8px; border-radius: 4px; }
        .btn-header-export { background-color: #10b981; color: white; font-weight: 600; padding: 8px 16px; border-radius: 6px; text-decoration: none; }
        
        .summary-card { background: #ffffff; border-radius: 8px; padding: 18px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .summary-card h6 { color: #2563eb; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.5px; border-bottom: 1px solid #f3f4f6; padding-bottom: 8px; margin-bottom: 12px; }
        .stat-line { font-size: 0.9rem; margin-bottom: 6px; color: #374151; }
        .cost-line { color: #059669; font-weight: 700; font-size: 0.95rem; margin-top: 10px; }
        
        .total-hours-card { background: #ffffff; border-radius: 8px; padding: 18px; border: 1px solid #e5e7eb; height: 100%; display: flex; flex-direction: column; justify-content: center; }
        .total-hours-num { font-size: 2.2rem; font-weight: 800; color: #2563eb; }
        .badge-calculated { background-color: #06b6d4; color: white; font-size: 0.75rem; padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content; margin-top: 8px; }
    </style>
</head>
<body>
<div class="container-fluid p-0">
    <div class="row g-0">
        
        <!-- Left Sidebar Navigation -->
        <div class="col-md-2 sidebar">
            <div class="brand-title">SteelY R.M.I</div>
            <div class="admin-badge">👑 ADMIN CONTROL</div>
            
            <a href="/export/master_excel" class="btn btn-export-main shadow-sm">
                📊 Export Master Excel
            </a>
            <a href="/logout" class="btn btn-logout shadow-sm">
                🚪 Logout System
            </a>

            <nav class="mt-2">
                <a href="#summary-section" class="nav-link-custom">📊 Summaries & Filter</a>
                <a href="#create-wo-section" class="nav-link-custom">➕ Create New Work Order</a>
                <a href="#execution-log-section" class="nav-link-custom">🛠️ Execution & Work Time Log</a>
                <a href="#inventory-section" class="nav-link-custom">⚙️ Spare Parts Inventory</a>
            </nav>
        </div>

        <!-- Right Main Workspace -->
        <div class="col-md-10 p-4">
            
            <!-- Top Header Banner -->
            <div class="main-header">
                <div>
                    <h1 class="main-title">SteelY R.M.I Garage Maintnace dash Bord</h1>
                    <div class="main-subtitle">Integrated Work Time, Consumables & Maintenance Tracking</div>
                </div>
                <div class="d-flex align-items-center gap-4">
                    <div class="user-box">
                        <span class="user-name">{{ user.name }}</span>
                        <span class="user-role">{{ user.role }}</span>
                    </div>
                    <a href="/export/master_excel" class="btn-header-export shadow-sm">
                        📊 Export Master Excel
                    </a>
                </div>
            </div>

            <!-- Top Summary Cards -->
            <div class="row g-3 mb-4" id="summary-section">
                <div class="col-md-4">
                    <div class="summary-card">
                        <h6>WEEKLY SUMMARY (LAST 7 DAYS)</h6>
                        <div class="stat-line">Total Jobs Executed: <strong>{{ weekly.total_jobs }}</strong></div>
                        <div class="stat-line text-muted">• PM: <strong>{{ weekly.pm_jobs }}</strong> | CM: <strong>{{ weekly.cm_jobs }}</strong></div>
                        <div class="stat-line text-muted">• Total Work Hours: <strong>{{ weekly.total_work_hours }} hrs</strong></div>
                        <div class="cost-line">Spare Parts Cost: {{ "{:,.2f}".format(weekly.total_spares_cost) }} ETB</div>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="summary-card">
                        <h6>MONTHLY SUMMARY (LAST 30 DAYS)</h6>
                        <div class="stat-line">Total Jobs Executed: <strong>{{ monthly.total_jobs }}</strong></div>
                        <div class="stat-line text-muted">• PM: <strong>{{ monthly.pm_jobs }}</strong> | CM: <strong>{{ monthly.cm_jobs }}</strong></div>
                        <div class="stat-line text-muted">• Total Work Hours: <strong>{{ monthly.total_work_hours }} hrs</strong></div>
                        <div class="cost-line">Spare Parts Cost: {{ "{:,.2f}".format(monthly.total_spares_cost) }} ETB</div>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="total-hours-card">
                        <div class="text-muted small fw-bold mb-1">⏱️ TOTAL EFFECTIVE WORK TIME</div>
                        <div>
                            <span class="total-hours-num">{{ monthly.total_work_hours }}</span>
                            <span class="fw-bold text-primary">Hours</span>
                        </div>
                        <div class="badge-calculated">Calculated across Monthly Work Orders</div>
                    </div>
                </div>
            </div>

            <!-- Form: Create New Work Order -->
            <div class="summary-card mb-4" id="create-wo-section">
                <div class="form-section-title text-primary fw-bold mb-3">
                    📄 Create New Work Order
                </div>
                <form action="/add_work_order" method="POST" id="wo-form">
                    <div class="row g-3">
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Serial Number (S/N):</label>
                            <input type="text" name="sn" class="form-control form-control-sm" placeholder="e.g. SN-002" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Work Order No:</label>
                            <input type="text" name="wo_no" class="form-control form-control-sm" placeholder="e.g. WO-2026-002" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Vehicle Plate Number:</label>
                            <input type="text" name="vehicle" class="form-control form-control-sm" placeholder="e.g. AA-3-12345" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Vehicle Type / Model:</label>
                            <input type="text" name="model" class="form-control form-control-sm" placeholder="e.g. Sino Truck 371">
                        </div>
                        
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-danger">Current Reading:</label>
                            <input type="number" name="reading_value" class="form-control form-control-sm border-danger" placeholder="e.g. 125000" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-danger">Reading Unit:</label>
                            <select name="reading_unit" class="form-select form-select-sm border-danger" required>
                                <option value="KM">KM (+5000)</option>
                                <option value="Hour">Hour (+250)</option>
                            </select>
                        </div>

                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Job Status:</label>
                            <select name="work_status" class="form-select form-select-sm" required>
                                <option value="Completed">Completed</option>
                                <option value="In Progress">In Progress</option>
                                <option value="Pending">Pending</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Driver Name:</label>
                            <input type="text" name="driver" class="form-control form-control-sm" placeholder="e.g. Abebe K.">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Assigned Technician:</label>
                            <input type="text" name="technician" class="form-control form-control-sm" placeholder="e.g. Mekonnen K." required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-primary">🗓️ Start Date & Time:</label>
                            <input type="datetime-local" name="start_time" class="form-control form-control-sm border-primary" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-primary">🏁 End Date & Time:</label>
                            <input type="datetime-local" name="finish_time" class="form-control form-control-sm border-primary" required>
                        </div>

                        <div class="col-md-12">
                            <label class="form-label small fw-bold">Work Category & Description:</label>
                            <input type="text" name="description" class="form-control form-control-sm" placeholder="e.g. Engine Maintenance and Spare Parts Replacement" required>
                        </div>

                        <!-- Dynamic +Add Replaced Spare Part Section with Auto Calculation -->
                        <div class="col-md-12">
                            <div class="p-3 border rounded bg-light border-warning">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <h6 class="fw-bold text-dark m-0">⚙️ Replaced Spare Parts (Auto Total Calculation)</h6>
                                    <button type="button" class="btn btn-outline-dark btn-sm fw-bold" onclick="addSpareRow()">+ Add Spare Part Row</button>
                                </div>
                                <div id="spare-rows-container">
                                    <div class="row g-2 spare-row mb-2 align-items-center">
                                        <div class="col-md-4">
                                            <input type="text" name="spare_name_spec[]" class="form-control form-control-sm" placeholder="Spare Part Name & Spec" required>
                                        </div>
                                        <div class="col-md-2">
                                            <input type="number" name="spare_qty[]" class="form-control form-control-sm spare-qty" placeholder="Qty" value="1" min="1" required oninput="calculateRowTotal(this)">
                                        </div>
                                        <div class="col-md-3">
                                            <input type="number" step="0.01" name="spare_price[]" class="form-control form-control-sm spare-price" placeholder="Unit Price (ETB)" value="0.00" required oninput="calculateRowTotal(this)">
                                        </div>
                                        <div class="col-md-2">
                                            <span class="small fw-bold text-success row-total-text">0.00 ETB</span>
                                        </div>
                                        <div class="col-md-1">
                                            <button type="button" class="btn btn-danger btn-sm w-100" onclick="removeSpareRow(this)">X</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Consumables Inputs with Auto Calculation -->
                        <div class="col-md-12">
                            <div class="p-3 border rounded bg-light">
                                <h6 class="fw-bold text-dark mb-2">🔋 Consumables Usage (Auto Total Calculation)</h6>
                                <div class="row g-2 align-items-center">
                                    <div class="col-md-2">
                                        <label class="form-label small">Battery Qty / Cost:</label>
                                        <input type="number" name="battery_qty" id="bat_qty" class="form-control form-control-sm mb-1" value="0" placeholder="Qty" oninput="calcConsumables()">
                                        <input type="number" step="0.01" name="battery_cost" id="bat_cost" class="form-control form-control-sm" value="0.00" placeholder="Total Cost" oninput="calcConsumables()">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label small">Lubrication Qty(L) / Cost:</label>
                                        <input type="number" step="0.1" name="lubrication_qty" id="lub_qty" class="form-control form-control-sm mb-1" value="0.0" placeholder="Qty (L)">
                                        <input type="number" step="0.01" name="lubrication_cost" id="lub_cost" class="form-control form-control-sm" value="0.00" placeholder="Total Cost" oninput="calcConsumables()">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label small">Tire Qty / Cost:</label>
                                        <input type="number" name="tire_qty" id="tire_qty" class="form-control form-control-sm mb-1" value="0" placeholder="Qty">
                                        <input type="number" step="0.01" name="tire_cost" id="tire_cost" class="form-control form-control-sm" value="0.00" placeholder="Total Cost" oninput="calcConsumables()">
                                    </div>
                                    <div class="col-md-3 d-flex flex-column justify-content-end">
                                        <span class="small text-muted">Total Consumables Cost:</span>
                                        <span class="fw-bold text-success fs-5" id="total-consumables-display">0.00 ETB</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="col-md-12 text-end mt-3">
                            <button type="submit" class="btn btn-primary btn-sm px-4 fw-bold">💾 Save Work Order</button>
                        </div>
                    </div>
                </form>
            </div>

            <!-- Table 1: Execution & Work Time Log -->
            <div class="summary-card mb-4" id="execution-log-section">
                <h5 class="fw-bold text-dark mb-3">🛠️ Maintenance Execution & Work Time Log</h5>
                <div class="table-responsive">
                    <table class="table table-bordered table-hover align-middle table-sm">
                        <thead class="table-dark">
                            <tr>
                                <th>WO #</th>
                                <th>Plate No</th>
                                <th>Current Reading</th>
                                <th>🔔 Next Service Alert</th>
                                <th>Status</th>
                                <th>Technician</th>
                                <th>Start Time</th>
                                <th>End Time</th>
                                <th>Effective Hours</th>
                                <th>⚙️ Replaced Spare Parts</th>
                                <th>Consumables Cost</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in logs %}
                            <tr>
                                <td class="fw-bold">{{ log.wo_no }}</td>
                                <td><span class="badge bg-secondary">{{ log.vehicle }}</span></td>
                                <td class="small fw-bold">{{ "{:,}".format(log.reading_value) }} {{ log.reading_unit }}</td>
                                <td><span class="badge bg-info text-dark fw-bold">{{ log.next_service }}</span></td>
                                <td>
                                    {% if log.work_status == 'Completed' %}
                                        <span class="badge bg-success">Completed</span>
                                    {% elif log.work_status == 'In Progress' %}
                                        <span class="badge bg-warning text-dark">In Progress</span>
                                    {% else %}
                                        <span class="badge bg-danger">Pending</span>
                                    {% endif %}
                                </td>
                                <td class="small fw-bold">{{ log.technician }}</td>
                                <td class="small text-primary fw-bold">{{ log.start_time }}</td>
                                <td class="small text-primary fw-bold">{{ log.finish_time }}</td>
                                <td class="fw-bold text-center text-success bg-light">{{ log.effective_hours }} hrs</td>
                                <td class="small">
                                    {% if log.replaced_spares %}
                                        {% for sp in log.replaced_spares %}
                                            <div>• <strong>{{ sp.part_name }}</strong> x{{ sp.qty }} ({{ "{:,.2f}".format(sp.total_cost) }} ETB)</div>
                                        {% endfor %}
                                    {% else %}
                                        <span class="text-muted">None</span>
                                    {% endif %}
                                </td>
                                <td class="fw-bold text-end">
                                    {{ "{:,.2f}".format(log.battery_cost + log.lubrication_cost + log.tire_cost) }} ETB
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Table 2: Spare Parts Inventory -->
            <div class="summary-card mb-4" id="inventory-section">
                <h5 class="fw-bold text-dark mb-3">⚙️ Spare Parts Inventory</h5>
                <div class="table-responsive">
                    <table class="table table-hover align-middle table-sm">
                        <thead class="table-dark">
                            <tr>
                                <th>#</th>
                                <th>Spare Part Name</th>
                                <th>Specification</th>
                                <th>Stock Qty</th>
                                <th>Unit Price (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for part in inventory %}
                            <tr>
                                <td>{{ part.id }}</td>
                                <td class="fw-bold">{{ part.part_name }}</td>
                                <td><span class="badge bg-light text-dark border">{{ part.spec }}</span></td>
                                <td>{{ part.qty }}</td>
                                <td>{{ "{:,.2f}".format(part.unit_price) }} ETB</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    </div>
</div>

<script>
    function addSpareRow() {
        const container = document.getElementById('spare-rows-container');
        const newRow = document.createElement('div');
        newRow.className = 'row g-2 spare-row mb-2 align-items-center';
        newRow.innerHTML = `
            <div class="col-md-4">
                <input type="text" name="spare_name_spec[]" class="form-control form-control-sm" placeholder="Spare Part Name & Spec" required>
            </div>
            <div class="col-md-2">
                <input type="number" name="spare_qty[]" class="form-control form-control-sm spare-qty" placeholder="Qty" value="1" min="1" required oninput="calculateRowTotal(this)">
            </div>
            <div class="col-md-3">
                <input type="number" step="0.01" name="spare_price[]" class="form-control form-control-sm spare-price" placeholder="Unit Price (ETB)" value="0.00" required oninput="calculateRowTotal(this)">
            </div>
            <div class="col-md-2">
                <span class="small fw-bold text-success row-total-text">0.00 ETB</span>
            </div>
            <div class="col-md-1">
                <button type="button" class="btn btn-danger btn-sm w-100" onclick="removeSpareRow(this)">X</button>
            </div>
        `;
        container.appendChild(newRow);
    }

    function removeSpareRow(button) {
        const row = button.closest('.spare-row');
        const container = document.getElementById('spare-rows-container');
        if (container.children.length > 1) {
            row.remove();
        } else {
            alert("At least one spare part row is required!");
        }
    }

    function calculateRowTotal(element) {
        const row = element.closest('.spare-row');
        const qty = parseFloat(row.querySelector('.spare-qty').value) || 0;
        const price = parseFloat(row.querySelector('.spare-price').value) || 0;
        const total = qty * price;
        row.querySelector('.row-total-text').innerText = total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " ETB";
    }

    function calcConsumables() {
        const bat = parseFloat(document.getElementById('bat_cost').value) || 0;
        const lub = parseFloat(document.getElementById('lub_cost').value) || 0;
        const tire = parseFloat(document.getElementById('tire_cost').value) || 0;
        const total = bat + lub + tire;
        document.getElementById('total-consumables-display').innerText = total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " ETB";
    }
</script>
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login - SteelY R.M.I Garage</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark d-flex align-items-center justify-content-center vh-100">
    <div class="card p-4 shadow" style="width: 350px;">
        <h3 class="text-center mb-3 text-primary">SteelY R.M.I</h3>
        <p class="text-center text-muted small">Garage Maintenance System Login</p>
        {% if error %}
            <div class="alert alert-danger py-1 small text-center">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label small fw-bold">Username:</label>
                <input type="text" name="username" class="form-control" required placeholder="admin">
            </div>
            <div class="mb-3">
                <label class="form-label small fw-bold">Password:</label>
                <input type="password" name="password" class="form-control" required placeholder="password">
            </div>
            <button type="submit" class="btn btn-primary w-100 fw-bold">Login</button>
        </form>
    </div>
</body>
</html>
"""

# --- Helper Summaries Calculator ---
def get_summaries():
    logs = garage_data['maintenance_logs']
    now = datetime.now()
    
    # Weekly (last 7 days)
    week_ago = now - timedelta(days=7)
    weekly_logs = []
    for l in logs:
        try:
            dt = datetime.strptime(l['start_time'], "%Y-%m-%d %H:%M")
            if dt >= week_ago:
                weekly_logs.append(l)
        except:
            weekly_logs.append(l) # fallback if date format differs
            
    weekly_summary = {
        "total_jobs": len(weekly_logs),
        "pm_jobs": sum(1 for l in weekly_logs if l['type'] == 'PM'),
        "cm_jobs": sum(1 for l in weekly_logs if l['type'] == 'CM'),
        "total_work_hours": round(sum(l['effective_hours'] for l in weekly_logs), 2),
        "total_spares_cost": sum(sum(sp['total_cost'] for sp in l.get('replaced_spares', [])) for l in weekly_logs)
    }

    # Monthly (last 30 days)
    month_ago = now - timedelta(days=30)
    monthly_logs = []
    for l in logs:
        try:
            dt = datetime.strptime(l['start_time'], "%Y-%m-%d %H:%M")
            if dt >= month_ago:
                monthly_logs.append(l)
        except:
            monthly_logs.append(l)

    monthly_summary = {
        "total_jobs": len(monthly_logs),
        "pm_jobs": sum(1 for l in monthly_logs if l['type'] == 'PM'),
        "cm_jobs": sum(1 for l in monthly_logs if l['type'] == 'CM'),
        "total_work_hours": round(sum(l['effective_hours'] for l in monthly_logs), 2),
        "total_spares_cost": sum(sum(sp['total_cost'] for sp in l.get('replaced_spares', [])) for l in monthly_logs)
    }

    return weekly_summary, monthly_summary

# --- App Routes ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['user'] = {"name": "System Admin", "role": "Administrator"}
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid Username or Password (use admin / admin123)"
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    weekly, monthly = get_summaries()
    return render_template_string(
        HTML_TEMPLATE, 
        logs=garage_data['maintenance_logs'], 
        inventory=garage_data['spare_parts'],
        weekly=weekly,
        monthly=monthly,
        user=session.get('user')
    )

@app.route('/add_work_order', methods=['POST'])
def add_work_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    start_raw = request.form.get('start_time', '')
    finish_raw = request.form.get('finish_time', '')
    
    start_disp = start_raw.replace('T', ' ') if start_raw else ''
    finish_disp = finish_raw.replace('T', ' ') if finish_raw else ''
    
    eff_hours = calculate_effective_hours(start_raw, finish_raw)
    
    try:
        r_val = int(request.form.get('reading_value', 0))
    except:
        r_val = 0
        
    r_unit = request.form.get('reading_unit', 'KM')
    next_serv = calculate_next_service(r_val, r_unit)
    
    spare_names = request.form.getlist('spare_name_spec[]')
    spare_qtys = request.form.getlist('spare_qty[]')
    spare_prices = request.form.getlist('spare_price[]')
    
    replaced_list = []
    for i in range(len(spare_names)):
        name = spare_names[i].strip()
        if name:
            try:
                qty = int(spare_qtys[i])
            except:
                qty = 1
            try:
                price = float(spare_prices[i])
            except:
                price = 0.0
                
            replaced_list.append({
                "part_name": name,
                "qty": qty,
                "unit_price": price,
                "total_cost": qty * price
            })

    new_id = len(garage_data['maintenance_logs']) + 1
    new_log = {
        "id": new_id,
        "sn": request.form.get('sn', f'SN-00{new_id}'),
        "wo_no": request.form.get('wo_no', f'WO-2026-00{new_id}'),
        "vehicle": request.form.get('vehicle', 'N/A'),
        "model": request.form.get('model', 'N/A'),
        "reading_value": r_val,
        "reading_unit": r_unit,
        "next_service": next_serv,
        "work_status": request.form.get('work_status', 'Completed'),
        "driver": request.form.get('driver', 'N/A'),
        "technician": request.form.get('technician', 'N/A'),
        "type": "PM",
        "start_time": start_disp,
        "finish_time": finish_disp,
        "effective_hours": eff_hours,
        "description": request.form.get('description', ''),
        "replaced_spares": replaced_list,
        "battery_qty": int(request.form.get('battery_qty', 0) or 0),
        "battery_cost": float(request.form.get('battery_cost', 0) or 0),
        "lubrication_qty": float(request.form.get('lubrication_qty', 0) or 0),
        "lubrication_cost": float(request.form.get('lubrication_cost', 0) or 0),
        "tire_qty": int(request.form.get('tire_qty', 0) or 0),
        "tire_cost": float(request.form.get('tire_cost', 0) or 0)
    }
    garage_data['maintenance_logs'].append(new_log)
    return redirect(url_for('dashboard'))

# Master Excel Export including Weekly and Monthly Summaries
@app.route('/export/master_excel')
def export_master_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    output = io.BytesIO()
    weekly, monthly = get_summaries()
    
    # 1. Logs Dataframe
    logs_export = []
    for l in garage_data['maintenance_logs']:
        sp_text = ", ".join([f"{sp['part_name']} ({sp['qty']} pcs)" for sp in l.get('replaced_spares', [])])
        sp_cost = sum([sp['total_cost'] for sp in l.get('replaced_spares', [])])
        
        logs_export.append({
            'Serial Number': l['sn'],
            'Work Order No': l['wo_no'],
            'Vehicle Plate': l['vehicle'],
            'Vehicle Model': l['model'],
            'Reading Value': l['reading_value'],
            'Reading Unit': l['reading_unit'],
            'Next Service Schedule': l['next_service'],
            'Work Status': l['work_status'],
            'Technician': l['technician'],
            'Start Time': l['start_time'],
            'End Time': l['finish_time'],
            'Effective Hours': l['effective_hours'],
            'Replaced Spare Part (spec)': sp_text,
            'Spare Parts Total Cost (ETB)': sp_cost,
            'Consumables Total Cost (ETB)': l['battery_cost'] + l['lubrication_cost'] + l['tire_cost']
        })
    logs_df = pd.DataFrame(logs_export)

    # 2. Summary Dataframe
    summary_data = [
        {"Report Type": "WEEKLY SUMMARY (Last 7 Days)", "Total Jobs": weekly['total_jobs'], "PM Jobs": weekly['pm_jobs'], "CM Jobs": weekly['cm_jobs'], "Total Work Hours (hrs)": weekly['total_work_hours'], "Spare Parts Total Cost (ETB)": weekly['total_spares_cost']},
        {"Report Type": "MONTHLY SUMMARY (Last 30 Days)", "Total Jobs": monthly['total_jobs'], "PM Jobs": monthly['pm_jobs'], "CM Jobs": monthly['cm_jobs'], "Total Work Hours (hrs)": monthly['total_work_hours'], "Spare Parts Total Cost (ETB)": monthly['total_spares_cost']}
    ]
    summary_df = pd.DataFrame(summary_data)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='Summaries Report', index=False)
        logs_df.to_excel(writer, sheet_name='Master Maintenance Log', index=False)
        
    output.seek(0)
    return send_file(output, download_name='SteelY_Master_Garage_Report.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
