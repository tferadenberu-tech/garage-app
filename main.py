import io
from datetime import datetime
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, send_file

app = Flask(__name__)

# --- In-Memory System Database ---
garage_data = {
    "current_user": {
        "name": "System Admin",
        "role": "Administrator"
    },
    "spare_parts": [
        {"id": 1, "part_name": "Oil Filter", "spec": "LF16015 / Heavy Duty", "qty": 20, "unit_price": 1200.00},
        {"id": 2, "part_name": "Fuel Filter", "spec": "FF5421 / High Efficiency", "qty": 15, "unit_price": 1800.00},
        {"id": 3, "part_name": "Brake Shoe Set", "spec": "Rear Axle / Heavy Duty Standard", "qty": 8, "unit_price": 4500.00}
    ],
    "technicians": [
        {"rank": 1, "name": "Mekonnen Kebede", "lead_jobs": 5, "total_hours": 32.5, "score": "98%"},
        {"rank": 2, "name": "Tadesse Hailu", "lead_jobs": 4, "total_hours": 28.0, "score": "92%"},
        {"rank": 3, "name": "Dawit Girma", "lead_jobs": 3, "total_hours": 22.5, "score": "87%"}
    ],
    "maintenance_logs": [
        {
            "id": 1,
            "sn": "SN-001",
            "wo_no": "WO-2026-001",
            "vehicle": "AA-3-12345",
            "model": "Sino Truck 371",
            "km_or_hr": "124,500 km",
            "driver": "Alemayehu T.",
            "technician": "Mekonnen Kebede",
            "type": "PM",
            "work_status": "Completed",
            "start_time": "2026-07-20 08:00",
            "finish_time": "2026-07-20 14:30",
            "effective_hours": 6.5,
            "description": "Engine Oil & Filter Change + System Inspection",
            "spare_cost": 3000.00,
            "battery_qty": 0, "battery_cost": 0.0,
            "lubrication_qty": 20.0, "lubrication_cost": 4500.0,
            "tire_qty": 0, "tire_cost": 0.0
        },
        {
            "id": 2,
            "sn": "SN-002",
            "wo_no": "WO-2026-002",
            "vehicle": "AA-3-11223",
            "model": "CAT Wheel Loader 950H",
            "km_or_hr": "8,450 hrs",
            "driver": "Getachew M.",
            "technician": "Tadesse Hailu",
            "type": "CM",
            "work_status": "In Progress",
            "start_time": "2026-07-22 09:00",
            "finish_time": "2026-07-23 11:00",
            "effective_hours": 26.0,
            "description": "Hydraulic Pump Repair + Battery & Rear Tires Replacement",
            "spare_cost": 0.00,
            "battery_qty": 2, "battery_cost": 18000.0,
            "lubrication_qty": 40.0, "lubrication_cost": 9000.0,
            "tire_qty": 2, "tire_cost": 32000.0
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
        try:
            fmt = "%Y-%m-%d %H:%M"
            t1 = datetime.strptime(start_str, fmt)
            t2 = datetime.strptime(finish_str, fmt)
            diff = (t2 - t1).total_seconds() / 3600.0
            return round(max(diff, 0.0), 2)
        except:
            return 0.0

# --- Frontend HTML Template matching Exact UI Design ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY Garage Fleet Dashboard - SteelY R.M.I Garage Maintenance Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background-color: #eef2f5; color: #1f2937; }
        .sidebar { background-color: #111827; min-height: 100vh; color: #9ca3af; padding: 20px 15px; }
        .sidebar .brand-title { color: #3b82f6; font-size: 1.5rem; font-weight: bold; margin-bottom: 5px; }
        .admin-badge { background-color: #ef4444; color: white; font-size: 0.7rem; font-weight: bold; padding: 3px 8px; border-radius: 4px; display: inline-block; margin-bottom: 15px; }
        .btn-export-main { background-color: #10b981; color: white; font-weight: 600; border: none; border-radius: 6px; width: 100%; text-align: left; padding: 10px 12px; margin-bottom: 25px; }
        .btn-export-main:hover { background-color: #059669; color: white; }
        .nav-link-custom { color: #d1d5db; text-decoration: none; display: block; padding: 10px 0; font-size: 0.95rem; font-weight: 500; }
        .nav-link-custom:hover { color: #ffffff; }
        
        .main-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 25px; }
        .main-title { font-size: 2.1rem; font-weight: 800; color: #111827; margin-bottom: 2px; }
        .main-subtitle { color: #6b7280; font-size: 0.95rem; }
        .user-box { text-align: right; }
        .user-name { font-weight: 700; color: #1f2937; display: block; }
        .user-role { background-color: #ef4444; color: white; font-size: 0.75rem; font-weight: bold; padding: 2px 8px; border-radius: 4px; }
        .btn-header-export { background-color: #10b981; color: white; font-weight: 600; padding: 8px 16px; border-radius: 6px; text-decoration: none; }
        .btn-header-export:hover { background-color: #059669; color: white; }

        .summary-card { background: #ffffff; border-radius: 8px; padding: 18px; border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .summary-card h6 { color: #2563eb; font-weight: 700; font-size: 0.85rem; letter-spacing: 0.5px; border-bottom: 1px solid #f3f4f6; padding-bottom: 8px; margin-bottom: 12px; }
        .stat-line { font-size: 0.9rem; margin-bottom: 6px; color: #374151; }
        .cost-line { color: #059669; font-weight: 700; font-size: 0.95rem; margin-top: 10px; }
        
        .total-hours-card { background: #ffffff; border-radius: 8px; padding: 18px; border: 1px solid #e5e7eb; height: 100%; display: flex; flex-direction: column; justify-content: center; }
        .total-hours-num { font-size: 2.2rem; font-weight: 800; color: #2563eb; }
        .total-hours-unit { font-size: 1rem; color: #2563eb; font-weight: 600; }
        .badge-calculated { background-color: #06b6d4; color: white; font-size: 0.75rem; padding: 4px 8px; border-radius: 4px; display: inline-block; width: fit-content; margin-top: 8px; }

        .filter-card { background: #ffffff; border-radius: 8px; padding: 15px; border: 1px solid #e5e7eb; margin-bottom: 25px; }
        .form-section-title { font-size: 1.1rem; font-weight: 700; color: #2563eb; margin-bottom: 15px; display: flex; align-items: center; gap: 8px; }
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

            <nav class="mt-2">
                <a href="#summary-section" class="nav-link-custom">📊 Summaries & Filter</a>
                <a href="#create-wo-section" class="nav-link-custom">➕ Create New Work Order</a>
                <a href="#execution-log-section" class="nav-link-custom">🛠️ Execution & Work Time Log</a>
                <a href="#consumables-section" class="nav-link-custom">🔋 Consumables Summary</a>
                <a href="#tech-rank-section" class="nav-link-custom">🏆 Tech Performance Rank</a>
                <a href="#inventory-section" class="nav-link-custom">⚙️ Spare Parts Inventory</a>
            </nav>
        </div>

        <!-- Right Main Workspace -->
        <div class="col-md-10 p-4">
            
            <!-- Top Header Banner -->
            <div class="main-header">
                <div>
                    <h1 class="main-title">SteelY R.M.I Garage Maintenance Dashboard</h1>
                    <div class="main-subtitle">Integrated Work Time, Consumables & Fleet Maintenance Tracking</div>
                </div>
                <div class="d-flex align-items-center gap-4">
                    <div class="user-box">
                        <span class="user-name">{{ data.current_user.name }}</span>
                        <span class="user-role">{{ data.current_user.role }}</span>
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
                        <div class="stat-line">Total Jobs Executed: <strong>{{ summary.total_jobs }}</strong></div>
                        <div class="stat-line text-muted">• PM: <strong>{{ summary.pm_jobs }}</strong> | CM: <strong>{{ summary.cm_jobs }}</strong></div>
                        <div class="stat-line text-muted">• Total Work Hours: <strong>{{ summary.total_work_hours }} hrs</strong></div>
                        <div class="cost-line">Spare Parts Cost: {{ "{:,.2f}".format(summary.total_spare_cost) }} ETB</div>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="summary-card">
                        <h6>MONTHLY SUMMARY (LAST 30 DAYS)</h6>
                        <div class="stat-line">Total Jobs Executed: <strong>{{ summary.total_jobs }}</strong></div>
                        <div class="stat-line text-muted">• PM: <strong>{{ summary.pm_jobs }}</strong> | CM: <strong>{{ summary.cm_jobs }}</strong></div>
                        <div class="stat-line text-muted">• Total Work Hours: <strong>{{ summary.total_work_hours }} hrs</strong></div>
                        <div class="cost-line">Spare Parts Cost: {{ "{:,.2f}".format(summary.total_spare_cost) }} ETB</div>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="total-hours-card">
                        <div class="text-muted small fw-bold mb-1">⏱️ TOTAL EFFECTIVE WORK TIME</div>
                        <div>
                            <span class="total-hours-num">{{ summary.total_work_hours }}</span>
                            <span class="total-hours-unit">Hours</span>
                        </div>
                        <div class="badge-calculated">Calculated across {{ summary.total_jobs }} Work Orders</div>
                    </div>
                </div>
            </div>

            <!-- Filter Controls -->
            <div class="filter-card">
                <div class="row align-items-end g-3">
                    <div class="col-md-3">
                        <label class="form-label small fw-bold mb-1">From Date:</label>
                        <input type="date" class="form-control form-control-sm">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small fw-bold mb-1">To Date:</label>
                        <input type="date" class="form-control form-control-sm">
                    </div>
                    <div class="col-md-3">
                        <button class="btn btn-primary btn-sm w-100 fw-bold">Filter Reports</button>
                    </div>
                    <div class="col-md-3">
                        <a href="/export/master_excel" class="btn btn-success btn-sm w-100 fw-bold">📊 Export Filtered Excel Report</a>
                    </div>
                </div>
            </div>

            <!-- Form: Create New Work Order -->
            <div class="summary-card mb-4" id="create-wo-section">
                <div class="form-section-title">
                    📄 Create New Work Order
                </div>
                <form action="/add_work_order" method="POST">
                    <div class="row g-3">
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Serial Number (S/N):</label>
                            <input type="text" name="sn" class="form-control form-control-sm" placeholder="e.g. SN-003" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Work Order No (W.O No):</label>
                            <input type="text" name="wo_no" class="form-control form-control-sm" placeholder="e.g. WO-2026-003" required>
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
                            <label class="form-label small fw-bold">KM / Hour Reading:</label>
                            <input type="text" name="km_or_hr" class="form-control form-control-sm" placeholder="e.g. 150,000 km or 4,200 hrs" required>
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
                            <input type="text" name="driver" class="form-control form-control-sm" placeholder="e.g. Abebe Kebede">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Assigned Technician:</label>
                            <input type="text" name="technician" class="form-control form-control-sm" placeholder="e.g. Mekonnen K." required>
                        </div>

                        <!-- Requested Time Field 1 & 2 -->
                        <div class="col-md-3">
                            <label class="form-label small fw-bold text-primary">🗓️ Work Start Day & Hour:</label>
                            <input type="datetime-local" name="start_time" class="form-control form-control-sm border-primary" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold text-primary">🏁 End Work Day & Hour:</label>
                            <input type="datetime-local" name="finish_time" class="form-control form-control-sm border-primary" required>
                        </div>

                        <div class="col-md-12">
                            <label class="form-label small fw-bold">Work Category & Description:</label>
                            <input type="text" name="description" class="form-control form-control-sm" placeholder="e.g. Engine Overhaul, Oil Filter & Tire Replacement" required>
                        </div>

                        <!-- Requested Feature 4: Consumables Inputs -->
                        <div class="col-md-12">
                            <div class="p-3 border rounded bg-light">
                                <h6 class="fw-bold text-dark mb-2">🔋 Consumables Usage (Battery, Lubrication, Tire)</h6>
                                <div class="row g-2">
                                    <div class="col-md-2">
                                        <label class="form-label small">Battery Qty (Pcs):</label>
                                        <input type="number" name="battery_qty" class="form-control form-control-sm" value="0">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label small">Battery Cost (ETB):</label>
                                        <input type="number" step="0.01" name="battery_cost" class="form-control form-control-sm" value="0.00">
                                    </div>

                                    <div class="col-md-2">
                                        <label class="form-label small">Lubrication Qty (Liters):</label>
                                        <input type="number" step="0.1" name="lubrication_qty" class="form-control form-control-sm" value="0.0">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label small">Lubrication Cost (ETB):</label>
                                        <input type="number" step="0.01" name="lubrication_cost" class="form-control form-control-sm" value="0.00">
                                    </div>

                                    <div class="col-md-2">
                                        <label class="form-label small">Tire Qty (Pcs):</label>
                                        <input type="number" name="tire_qty" class="form-control form-control-sm" value="0">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label small">Tire Cost (ETB):</label>
                                        <input type="number" step="0.01" name="tire_cost" class="form-control form-control-sm" value="0.00">
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
                                <th>KM / Hour</th>
                                <th>Status</th>
                                <th>Technician</th>
                                <th>Start Day & Hour</th>
                                <th>End Day & Hour</th>
                                <th>Effective Hours</th>
                                <th>Consumables (Battery / Lubrication / Tire)</th>
                                <th>Total Consumable Cost</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in data.maintenance_logs %}
                            <tr>
                                <td class="fw-bold">{{ log.wo_no }}</td>
                                <td><span class="badge bg-secondary">{{ log.vehicle }}</span></td>
                                <td class="small">{{ log.km_or_hr }}</td>
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
                                    {% if log.battery_qty > 0 %}<div>• Battery: {{ log.battery_qty }} pcs ({{ "{:,.2f}".format(log.battery_cost) }} ETB)</div>{% endif %}
                                    {% if log.lubrication_qty > 0 %}<div>• Oil/Lube: {{ log.lubrication_qty }} L ({{ "{:,.2f}".format(log.lubrication_cost) }} ETB)</div>{% endif %}
                                    {% if log.tire_qty > 0 %}<div>• Tire: {{ log.tire_qty }} pcs ({{ "{:,.2f}".format(log.tire_cost) }} ETB)</div>{% endif %}
                                    {% if log.battery_qty == 0 and log.lubrication_qty == 0 and log.tire_qty == 0 %}
                                        <span class="text-muted">None</span>
                                    {% endif %}
                                </td>
                                <td class="fw-bold text-end">
                                    {{ "{:,.2f}".format(log.battery_cost + log.lubrication_cost + log.tire_cost) }} ETB
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                        <tfoot class="table-light fw-bold">
                            <tr>
                                <td colspan="7" class="text-end">TOTAL EFFECTIVE WORK TIME & CONSUMABLES COST:</td>
                                <td class="text-center text-primary">{{ summary.total_work_hours }} hrs</td>
                                <td></td>
                                <td class="text-end text-success">
                                    {{ "{:,.2f}".format(summary.total_battery_cost + summary.total_lubrication_cost + summary.total_tire_cost) }} ETB
                                </td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            <!-- Table 2: Consumables Summary -->
            <div class="summary-card mb-4" id="consumables-section">
                <h5 class="fw-bold text-dark mb-3">🔋 Consumables Summary (Tire, Battery & Lubrication)</h5>
                <div class="row g-3">
                    <div class="col-md-4">
                        <div class="p-3 border rounded bg-white border-start border-warning border-4 shadow-sm">
                            <h6 class="text-muted fw-bold">Total Battery Usage</h6>
                            <p class="mb-1"><strong>Total Quantity:</strong> {{ summary.total_battery_qty }} Pcs</p>
                            <p class="mb-0 text-primary fw-bold"><strong>Total Cost:</strong> {{ "{:,.2f}".format(summary.total_battery_cost) }} ETB</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 border rounded bg-white border-start border-info border-4 shadow-sm">
                            <h6 class="text-muted fw-bold">Total Lubrication Usage</h6>
                            <p class="mb-1"><strong>Total Quantity:</strong> {{ summary.total_lubrication_qty }} Liters</p>
                            <p class="mb-0 text-primary fw-bold"><strong>Total Cost:</strong> {{ "{:,.2f}".format(summary.total_lubrication_cost) }} ETB</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 border rounded bg-white border-start border-danger border-4 shadow-sm">
                            <h6 class="text-muted fw-bold">Total Tires Usage</h6>
                            <p class="mb-1"><strong>Total Quantity:</strong> {{ summary.total_tire_qty }} Pcs</p>
                            <p class="mb-0 text-primary fw-bold"><strong>Total Cost:</strong> {{ "{:,.2f}".format(summary.total_tire_cost) }} ETB</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Table 3: Tech Performance Rank -->
            <div class="summary-card mb-4" id="tech-rank-section">
                <h5 class="fw-bold text-dark mb-3">🏆 Technical Work Performance Rank</h5>
                <div class="table-responsive">
                    <table class="table table-hover align-middle table-sm">
                        <thead class="table-dark">
                            <tr>
                                <th>Rank</th>
                                <th>Technician Name</th>
                                <th>Jobs Completed</th>
                                <th>Total Effective Work Hours</th>
                                <th>Performance Rating</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for tech in data.technicians %}
                            <tr>
                                <td class="fw-bold text-center">#{{ tech.rank }}</td>
                                <td class="fw-bold">{{ tech.name }}</td>
                                <td>{{ tech.lead_jobs }} Jobs</td>
                                <td class="fw-bold text-primary">{{ tech.total_hours }} hrs</td>
                                <td><span class="badge bg-success">{{ tech.score }}</span></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Table 4: Spare Parts Inventory -->
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
                            {% for part in data.spare_parts %}
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
</body>
</html>
"""

# --- App Routes ---
@app.route('/')
def dashboard():
    total_hours = sum(l['effective_hours'] for l in garage_data['maintenance_logs'])
    summary = {
        "total_jobs": len(garage_data['maintenance_logs']),
        "pm_jobs": sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'PM'),
        "cm_jobs": sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'CM'),
        "total_work_hours": round(total_hours, 2),
        "total_spare_cost": sum(l['spare_cost'] for l in garage_data['maintenance_logs']),
        "total_battery_qty": sum(l['battery_qty'] for l in garage_data['maintenance_logs']),
        "total_battery_cost": sum(l['battery_cost'] for l in garage_data['maintenance_logs']),
        "total_lubrication_qty": sum(l['lubrication_qty'] for l in garage_data['maintenance_logs']),
        "total_lubrication_cost": sum(l['lubrication_cost'] for l in garage_data['maintenance_logs']),
        "total_tire_qty": sum(l['tire_qty'] for l in garage_data['maintenance_logs']),
        "total_tire_cost": sum(l['tire_cost'] for l in garage_data['maintenance_logs'])
    }
    return render_template_string(HTML_TEMPLATE, data=garage_data, summary=summary)

@app.route('/add_work_order', methods=['POST'])
def add_work_order():
    start_raw = request.form.get('start_time', '')
    finish_raw = request.form.get('finish_time', '')
    
    start_disp = start_raw.replace('T', ' ') if start_raw else ''
    finish_disp = finish_raw.replace('T', ' ') if finish_raw else ''
    
    eff_hours = calculate_effective_hours(start_raw, finish_raw)
    
    new_id = len(garage_data['maintenance_logs']) + 1
    new_log = {
        "id": new_id,
        "sn": request.form.get('sn', f'SN-00{new_id}'),
        "wo_no": request.form.get('wo_no', f'WO-2026-00{new_id}'),
        "vehicle": request.form.get('vehicle', 'N/A'),
        "model": request.form.get('model', 'N/A'),
        "km_or_hr": request.form.get('km_or_hr', 'N/A'),
        "work_status": request.form.get('work_status', 'Completed'),
        "driver": request.form.get('driver', 'N/A'),
        "technician": request.form.get('technician', 'N/A'),
        "type": "PM",
        "start_time": start_disp,
        "finish_time": finish_disp,
        "effective_hours": eff_hours,
        "description": request.form.get('description', ''),
        "spare_cost": 0.0,
        "battery_qty": int(request.form.get('battery_qty', 0) or 0),
        "battery_cost": float(request.form.get('battery_cost', 0) or 0),
        "lubrication_qty": float(request.form.get('lubrication_qty', 0) or 0),
        "lubrication_cost": float(request.form.get('lubrication_cost', 0) or 0),
        "tire_qty": int(request.form.get('tire_qty', 0) or 0),
        "tire_cost": float(request.form.get('tire_cost', 0) or 0)
    }
    garage_data['maintenance_logs'].append(new_log)
    return redirect(url_for('dashboard'))

# Master Excel Export Route
@app.route('/export/master_excel')
def export_master_excel():
    output = io.BytesIO()
    
    logs_export = []
    for l in garage_data['maintenance_logs']:
        logs_export.append({
            'Serial Number (S/N)': l['sn'],
            'Work Order No': l['wo_no'],
            'Vehicle Plate': l['vehicle'],
            'Vehicle Model': l['model'],
            'KM / Hour Reading': l['km_or_hr'],
            'Work Status': l['work_status'],
            'Technician': l['technician'],
            'Driver Name': l['driver'],
            'Work Start Day & Hour': l['start_time'],
            'End Work Day & Hour': l['finish_time'],
            'Effective Work Time (Hours)': l['effective_hours'],
            'Work Description': l['description'],
            'Battery Quantity': l['battery_qty'],
            'Battery Cost (ETB)': l['battery_cost'],
            'Lubrication Quantity (Liters)': l['lubrication_qty'],
            'Lubrication Cost (ETB)': l['lubrication_cost'],
            'Tire Quantity': l['tire_qty'],
            'Tire Cost (ETB)': l['tire_cost'],
            'Total Consumables Cost (ETB)': l['battery_cost'] + l['lubrication_cost'] + l['tire_cost']
        })
    logs_df = pd.DataFrame(logs_export)
    
    total_hours = sum(l['effective_hours'] for l in garage_data['maintenance_logs'])
    summary_data = [
        {
            'Period': 'Weekly Summary (Last 7 Days)',
            'Total Jobs Executed': len(garage_data['maintenance_logs']),
            'Total Effective Work Hours': total_hours,
            'Total Battery Cost (ETB)': sum(l['battery_cost'] for l in garage_data['maintenance_logs']),
            'Total Lubrication Cost (ETB)': sum(l['lubrication_cost'] for l in garage_data['maintenance_logs']),
            'Total Tire Cost (ETB)': sum(l['tire_cost'] for l in garage_data['maintenance_logs'])
        },
        {
            'Period': 'Monthly Summary (Last 30 Days)',
            'Total Jobs Executed': len(garage_data['maintenance_logs']),
            'Total Effective Work Hours': total_hours,
            'Total Battery Cost (ETB)': sum(l['battery_cost'] for l in garage_data['maintenance_logs']),
            'Total Lubrication Cost (ETB)': sum(l['lubrication_cost'] for l in garage_data['maintenance_logs']),
            'Total Tire Cost (ETB)': sum(l['tire_cost'] for l in garage_data['maintenance_logs'])
        }
    ]
    summary_df = pd.DataFrame(summary_data)
    
    tech_df = pd.DataFrame(garage_data['technicians'])
    spares_df = pd.DataFrame(garage_data['spare_parts'])
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        logs_df.to_excel(writer, sheet_name='Maintenance & Hours Log', index=False)
        summary_df.to_excel(writer, sheet_name='Summaries Report', index=False)
        tech_df.to_excel(writer, sheet_name='Technician Ranks', index=False)
        spares_df.to_excel(writer, sheet_name='Spare Parts Inventory', index=False)
        
    output.seek(0)
    
    return send_file(
        output,
        download_name='SteelY_Master_Garage_Maintenance_Report.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
