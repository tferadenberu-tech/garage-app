import io
import re
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
            "km_or_hr": "124500 km",
            "next_service": "129,500 km (+5000)",
            "driver": "Alemayehu T.",
            "technician": "Mekonnen Kebede",
            "type": "PM",
            "work_status": "Completed",
            "start_time": "2026-07-20 08:00",
            "finish_time": "2026-07-20 14:30",
            "effective_hours": 6.5,
            "description": "Engine Oil & Filter Change",
            "replaced_spares": [
                {"part_name": "Oil Filter", "qty": 1, "unit_price": 1200.0, "total_cost": 1200.0},
                {"part_name": "Fuel Filter", "qty": 1, "unit_price": 1800.0, "total_cost": 1800.0}
            ],
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
            "km_or_hr": "8450 hrs",
            "next_service": "8,700 hrs (+250)",
            "driver": "Getachew M.",
            "technician": "Tadesse Hailu",
            "type": "CM",
            "work_status": "In Progress",
            "start_time": "2026-07-22 09:00",
            "finish_time": "2026-07-23 11:00",
            "effective_hours": 26.0,
            "description": "Hydraulic Pump Repair",
            "replaced_spares": [],
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
        return 0.0

# Automatic +5000 km / +250 hrs calculation
def calculate_next_service(km_or_hr_str):
    if not km_or_hr_str:
        return "N/A"
    
    # Extract numbers
    numbers = re.findall(r'\d+', km_or_hr_str.replace(',', ''))
    if not numbers:
        return km_or_hr_str
    
    val = int(numbers[0])
    text_lower = km_or_hr_str.lower()
    
    if "hr" in text_lower or "hour" in text_lower:
        next_val = val + 250
        return f"{next_val:,} hrs (+250)"
    else:
        # Default to KM
        next_val = val + 5000
        return f"{next_val:,} km (+5000)"

# --- Frontend HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY Fleet Dashboard - Maintenance Dashboard</title>
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
                    <h1 class="main-title">SteelY R.M.I Garage Maintenance Dashboard</h1>
                    <div class="main-subtitle">Integrated Work Time, Consumables & Maintenance Tracking</div>
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
                        <div class="cost-line">Spare Parts Cost: {{ "{:,.2f}".format(summary.total_replaced_spares_cost) }} ETB</div>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="summary-card">
                        <h6>MONTHLY SUMMARY (LAST 30 DAYS)</h6>
                        <div class="stat-line">Total Jobs Executed: <strong>{{ summary.total_jobs }}</strong></div>
                        <div class="stat-line text-muted">• PM: <strong>{{ summary.pm_jobs }}</strong> | CM: <strong>{{ summary.cm_jobs }}</strong></div>
                        <div class="stat-line text-muted">• Total Work Hours: <strong>{{ summary.total_work_hours }} hrs</strong></div>
                        <div class="cost-line">Spare Parts Cost: {{ "{:,.2f}".format(summary.total_replaced_spares_cost) }} ETB</div>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="total-hours-card">
                        <div class="text-muted small fw-bold mb-1">⏱️ TOTAL EFFECTIVE WORK TIME</div>
                        <div>
                            <span class="total-hours-num">{{ summary.total_work_hours }}</span>
                            <span class="fw-bold text-primary">Hours</span>
                        </div>
                        <div class="badge-calculated">Calculated across {{ summary.total_jobs }} Work Orders</div>
                    </div>
                </div>
            </div>

            <!-- Form: Create New Work Order -->
            <div class="summary-card mb-4" id="create-wo-section">
                <div class="form-section-title text-primary fw-bold mb-3">
                    📄 Create New Work Order
                </div>
                <form action="/add_work_order" method="POST">
                    <div class="row g-3">
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Serial Number (S/N):</label>
                            <input type="text" name="sn" class="form-control form-control-sm" placeholder="e.g. SN-003" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Work Order No:</label>
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
                            <label class="form-label small fw-bold text-danger">Current Reading (KM / Hr):</label>
                            <input type="text" name="km_or_hr" class="form-control form-control-sm border-danger" placeholder="e.g. 150000 km or 4200 hrs" required>
                            <span class="small text-muted" style="font-size:0.75rem;">💡 Auto +5000km / +250hrs</span>
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
                            <input type="text" name="description" class="form-control form-control-sm" placeholder="e.g. Engine Maintenance and Spare Parts Replacement" required>
                        </div>

                        <!-- Feature 2: Add Replaced Spare Parts Section -->
                        <div class="col-md-12">
                            <div class="p-3 border rounded bg-light border-warning">
                                <h6 class="fw-bold text-dark mb-2">⚙️ +Add Replaced Spare Parts</h6>
                                <div class="row g-2">
                                    <div class="col-md-4">
                                        <label class="form-label small fw-bold">Spare Part Name / Spec:</label>
                                        <input type="text" name="replaced_part_name" class="form-control form-control-sm" placeholder="e.g. Fuel Filter FF5421">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label small fw-bold">Quantity (Pcs):</label>
                                        <input type="number" name="replaced_qty" class="form-control form-control-sm" value="0">
                                    </div>
                                    <div class="col-md-3">
                                        <label class="form-label small fw-bold">Unit Price (ETB):</label>
                                        <input type="number" step="0.01" name="replaced_price" class="form-control form-control-sm" value="0.00">
                                    </div>
                                    <div class="col-md-2 d-flex align-items-end">
                                        <span class="small text-muted">Auto Total Calculation</span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Consumables Inputs -->
                        <div class="col-md-12">
                            <div class="p-3 border rounded bg-light">
                                <h6 class="fw-bold text-dark mb-2">🔋 Consumables Usage (Battery, Lubrication, Tire)</h6>
                                <div class="row g-2">
                                    <div class="col-md-2">
                                        <label class="form-label small">Battery Qty:</label>
                                        <input type="number" name="battery_qty" class="form-control form-control-sm" value="0">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label small">Battery Cost (ETB):</label>
                                        <input type="number" step="0.01" name="battery_cost" class="form-control form-control-sm" value="0.00">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label small">Lubrication Qty (L):</label>
                                        <input type="number" step="0.1" name="lubrication_qty" class="form-control form-control-sm" value="0.0">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label small">Lubrication Cost (ETB):</label>
                                        <input type="number" step="0.01" name="lubrication_cost" class="form-control form-control-sm" value="0.00">
                                    </div>
                                    <div class="col-md-2">
                                        <label class="form-label small">Tire Qty:</label>
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
                                <th>Current Reading</th>
                                <th>🔔 Next Service (+5000km / +250hr)</th>
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
                            {% for log in data.maintenance_logs %}
                            <tr>
                                <td class="fw-bold">{{ log.wo_no }}</td>
                                <td><span class="badge bg-secondary">{{ log.vehicle }}</span></td>
                                <td class="small">{{ log.km_or_hr }}</td>
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
                        <tfoot class="table-light fw-bold">
                            <tr>
                                <td colspan="8" class="text-end">TOTAL EFFECTIVE WORK TIME:</td>
                                <td class="text-center text-primary">{{ summary.total_work_hours }} hrs</td>
                                <td colspan="2"></td>
                            </tr>
                        </tfoot>
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
    
    # Calculate replaced spares cost
    total_spares_cost = 0.0
    for l in garage_data['maintenance_logs']:
        for sp in l.get('replaced_spares', []):
            total_spares_cost += sp.get('total_cost', 0.0)

    summary = {
        "total_jobs": len(garage_data['maintenance_logs']),
        "pm_jobs": sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'PM'),
        "cm_jobs": sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'CM'),
        "total_work_hours": round(total_hours, 2),
        "total_replaced_spares_cost": total_spares_cost
    }
    return render_template_string(HTML_TEMPLATE, data=garage_data, summary=summary)

@app.route('/add_work_order', methods=['POST'])
def add_work_order():
    start_raw = request.form.get('start_time', '')
    finish_raw = request.form.get('finish_time', '')
    
    start_disp = start_raw.replace('T', ' ') if start_raw else ''
    finish_disp = finish_raw.replace('T', ' ') if finish_raw else ''
    
    eff_hours = calculate_effective_hours(start_raw, finish_raw)
    
    km_input = request.form.get('km_or_hr', '')
    next_serv = calculate_next_service(km_input)
    
    # Process Replaced Spare Part
    rep_name = request.form.get('replaced_part_name', '').strip()
    rep_qty = int(request.form.get('replaced_qty', 0) or 0)
    rep_price = float(request.form.get('replaced_price', 0) or 0)
    
    replaced_list = []
    if rep_name and rep_qty > 0:
        replaced_list.append({
            "part_name": rep_name,
            "qty": rep_qty,
            "unit_price": rep_price,
            "total_cost": rep_qty * rep_price
        })

    new_id = len(garage_data['maintenance_logs']) + 1
    new_log = {
        "id": new_id,
        "sn": request.form.get('sn', f'SN-00{new_id}'),
        "wo_no": request.form.get('wo_no', f'WO-2026-00{new_id}'),
        "vehicle": request.form.get('vehicle', 'N/A'),
        "model": request.form.get('model', 'N/A'),
        "km_or_hr": km_input,
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

# Master Excel Export
@app.route('/export/master_excel')
def export_master_excel():
    output = io.BytesIO()
    
    logs_export = []
    for l in garage_data['maintenance_logs']:
        sp_text = ", ".join([f"{sp['part_name']} ({sp['qty']} pcs)" for sp in l.get('replaced_spares', [])])
        sp_cost = sum([sp['total_cost'] for sp in l.get('replaced_spares', [])])
        
        logs_export.append({
            'Serial Number': l['sn'],
            'Work Order No': l['wo_no'],
            'Vehicle Plate': l['vehicle'],
            'Vehicle Model': l['model'],
            'Current KM / Hours': l['km_or_hr'],
            'Next Service Schedule (+5000/250)': l['next_service'],
            'Work Status': l['work_status'],
            'Technician': l['technician'],
            'Start Time': l['start_time'],
            'End Time': l['finish_time'],
            'Effective Hours': l['effective_hours'],
            'Replaced Spare Parts': sp_text,
            'Spare Parts Total Cost (ETB)': sp_cost,
            'Consumables Total Cost (ETB)': l['battery_cost'] + l['lubrication_cost'] + l['tire_cost']
        })
    logs_df = pd.DataFrame(logs_export)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        logs_df.to_excel(writer, sheet_name='Master Maintenance Log', index=False)
        
    output.seek(0)
    return send_file(output, download_name='SteelY_Master_Garage_Report.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
