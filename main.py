import io
from datetime import datetime
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, send_file

app = Flask(__name__)

# --- Core Data Structure ---
garage_data = {
    "vehicles": [
        {"id": 1, "plate": "AA-3-12345", "model": "Sino Truck 371", "driver": "Alemayehu T.", "status": "In Service"},
        {"id": 2, "plate": "AA-3-67890", "model": "Toyota Hilux 2022", "driver": "Kassahun B.", "status": "Ready"},
        {"id": 3, "plate": "AA-3-11223", "model": "CAT Wheel Loader 950H", "driver": "Getachew M.", "status": "Under Repair"}
    ],
    "spare_parts": [
        {"id": 1, "part_name": "Oil Filter", "spec": "LF16015 / Fleetguard Heavy Duty", "qty": 18, "unit_price": 1200.00},
        {"id": 2, "part_name": "Fuel Filter", "spec": "FF5421 / High Efficiency", "qty": 12, "unit_price": 1800.00},
        {"id": 3, "part_name": "Brake Shoe Set", "spec": "Rear Axle / Sino Heavy Duty Standard", "qty": 6, "unit_price": 4500.00},
        {"id": 4, "part_name": "Hydraulic Oil", "spec": "ISO VG 68 - 20L Drum", "qty": 8, "unit_price": 15000.00}
    ],
    "maintenance_logs": [
        {
            "id": 1,
            "wo_no": "WO-2026-001",
            "vehicle": "AA-3-12345",
            "model": "Sino Truck 371",
            "driver": "Alemayehu T.",
            "type": "PM",
            "start_time": "2026-07-20 08:00",
            "finish_time": "2026-07-20 14:30",
            "effective_hours": 6.5,
            "description": "Engine Oil & Filter Change + Maintenance Check",
            "spares_used": "Oil Filter, Fuel Filter",
            "spare_cost": 3000.00,
            "battery_qty": 0, "battery_cost": 0.0,
            "lubrication_qty": 20, "lubrication_cost": 4500.0,
            "tire_qty": 0, "tire_cost": 0.0
        },
        {
            "id": 2,
            "wo_no": "WO-2026-002",
            "vehicle": "AA-3-11223",
            "model": "CAT Wheel Loader 950H",
            "driver": "Getachew M.",
            "type": "CM",
            "start_time": "2026-07-22 09:00",
            "finish_time": "2026-07-23 11:00",
            "effective_hours": 26.0,
            "description": "Hydraulic Pump Repair + Battery & Rear Tires Replacement",
            "spares_used": "Hydraulic Oil, Seal Kit",
            "spare_cost": 15000.00,
            "battery_qty": 2, "battery_cost": 18000.0,
            "lubrication_qty": 40, "lubrication_cost": 9000.0,
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

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I Garage Maintenance Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; color: #1e293b; }
        .sidebar { min-height: 100vh; background-color: #0f172a; color: white; }
        .header-banner { background: #ffffff; border-bottom: 2px solid #e2e8f0; padding: 20px; border-radius: 10px; }
        .card-summary { background: #ffffff; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 2px 6px rgba(0,0,0,0.02); }
        .btn-excel { background-color: #10b981; color: white; font-weight: bold; border: none; }
        .btn-excel:hover { background-color: #059669; color: white; }
        .form-card { background: #ffffff; border-top: 4px solid #2563eb; border-radius: 10px; }
    </style>
</head>
<body>
<div class="container-fluid">
    <div class="row">
        <!-- Sidebar Navigation -->
        <div class="col-md-2 sidebar p-3">
            <h4 class="text-primary fw-bold">SteelY R.M.I</h4>
            <p class="text-secondary small">Garage Maintenance System</p>
            <hr class="border-secondary">
            
            <div class="d-grid gap-2 mb-4">
                <a href="/export/master_excel" class="btn btn-excel shadow-sm btn-sm">
                    📊 Export Master Excel (All in One)
                </a>
            </div>

            <ul class="nav nav-pills flex-column">
                <li class="nav-item mb-2"><a href="#dashboard-summary" class="nav-link text-white">📊 Weekly & Monthly Summaries</a></li>
                <li class="nav-item mb-2"><a href="#new-work-order" class="nav-link text-white fw-bold">➕ Create New Work Order</a></li>
                <li class="nav-item mb-2"><a href="#maintenance-logs" class="nav-link text-white">🛠️ Execution & Work Time Log</a></li>
                <li class="nav-item mb-2"><a href="#consumables-summary" class="nav-link text-white">🔋 Consumables Summary</a></li>
                <li class="nav-item mb-2"><a href="#spare-parts" class="nav-link text-white">⚙️ Spare Parts Inventory</a></li>
            </ul>
        </div>

        <!-- Main Content Area -->
        <div class="col-md-10 p-4">
            
            <!-- Header Bar -->
            <div class="header-banner mb-4 d-flex justify-content-between align-items-center shadow-sm">
                <div>
                    <h2 class="fw-bold mb-1" style="color:#0f172a;">SteelY R.M.I Garage Maintenance Dashboard</h2>
                    <span class="text-muted small">Integrated Maintenance, Consumables & Work Time Tracking System</span>
                </div>
                <div>
                    <a href="/export/master_excel" class="btn btn-excel btn-lg shadow-sm">
                        📥 Export Filtered Excel Report
                    </a>
                </div>
            </div>

            <!-- 1. WEEKLY & MONTHLY SUMMARIES + FILTER SECTION -->
            <div class="row g-3 mb-4" id="dashboard-summary">
                <!-- Weekly Summary -->
                <div class="col-md-6">
                    <div class="card card-summary p-3 h-100">
                        <h6 class="fw-bold text-primary border-bottom pb-2">WEEKLY SUMMARY (LAST 7 DAYS)</h6>
                        <div class="row mt-2">
                            <div class="col-6">
                                <p class="mb-1">Total Jobs Executed: <strong>{{ summary.total_jobs }}</strong></p>
                                <p class="mb-1 text-muted small">• Preventive Maintenance (PM): <strong>{{ summary.pm_jobs }}</strong></p>
                                <p class="mb-1 text-muted small">• Corrective Maintenance (CM): <strong>{{ summary.cm_jobs }}</strong></p>
                                <p class="mb-0 text-muted small">• Inspection & Checkup: <strong>0</strong></p>
                            </div>
                            <div class="col-6 text-end">
                                <h5 class="fw-bold text-dark mt-2">Spare Parts Cost:</h5>
                                <h4 class="fw-bold text-success">{{ "{:,.2f}".format(summary.total_spare_cost) }} ETB</h4>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Monthly Summary -->
                <div class="col-md-6">
                    <div class="card card-summary p-3 h-100">
                        <h6 class="fw-bold text-primary border-bottom pb-2">MONTHLY SUMMARY (LAST 30 DAYS)</h6>
                        <div class="row mt-2">
                            <div class="col-6">
                                <p class="mb-1">Total Jobs Executed: <strong>{{ summary.total_jobs }}</strong></p>
                                <p class="mb-1 text-muted small">• Preventive Maintenance (PM): <strong>{{ summary.pm_jobs }}</strong></p>
                                <p class="mb-1 text-muted small">• Corrective Maintenance (CM): <strong>{{ summary.cm_jobs }}</strong></p>
                                <p class="mb-0 text-muted small">• Inspection & Checkup: <strong>0</strong></p>
                            </div>
                            <div class="col-6 text-end">
                                <h5 class="fw-bold text-dark mt-2">Spare Parts Cost:</h5>
                                <h4 class="fw-bold text-success">{{ "{:,.2f}".format(summary.total_spare_cost) }} ETB</h4>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Filter Controls -->
            <div class="card card-summary p-3 mb-4">
                <div class="row align-items-end g-3">
                    <div class="col-md-3">
                        <label class="form-label small fw-bold">From Date:</label>
                        <input type="date" class="form-control form-control-sm">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small fw-bold">To Date:</label>
                        <input type="date" class="form-control form-control-sm">
                    </div>
                    <div class="col-md-3">
                        <button class="btn btn-primary btn-sm w-100 fw-bold">Filter Reports</button>
                    </div>
                    <div class="col-md-3">
                        <a href="/export/master_excel" class="btn btn-excel btn-sm w-100 shadow-sm">📊 Export Filtered Excel Report</a>
                    </div>
                </div>
            </div>

            <!-- 2. CREATE NEW WORK ORDER FORM -->
            <div class="card card-summary p-4 mb-4 form-card" id="new-work-order">
                <h5 class="fw-bold text-primary mb-3">📝 Create New Work Order</h5>
                <form action="/add_work_order" method="POST">
                    <div class="row g-3">
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Serial Number (S/N):</label>
                            <input type="text" name="sn" class="form-control form-control-sm" placeholder="e.g. SN-001">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Work Order No (W.O No):</label>
                            <input type="text" name="wo_no" class="form-control form-control-sm" placeholder="e.g. WO-2026-003" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Vehicle Plate Number:</label>
                            <input type="text" name="vehicle" class="form-control form-control-sm" placeholder="e.g. AA-3-12345" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Vehicle Type / Model:</label>
                            <input type="text" name="model" class="form-control form-control-sm" placeholder="e.g. Sino Truck / Hilux">
                        </div>

                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Driver Name:</label>
                            <input type="text" name="driver" class="form-control form-control-sm" placeholder="e.g. Kebede M.">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Maintenance Type:</label>
                            <select name="type" class="form-select form-select-sm" required>
                                <option value="PM">PM (Preventive Maintenance)</option>
                                <option value="CM">CM (Corrective Maintenance)</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Starting Day & Hour:</label>
                            <input type="datetime-local" name="start_time" class="form-control form-control-sm" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Finished Day & Hour:</label>
                            <input type="datetime-local" name="finish_time" class="form-control form-control-sm" required>
                        </div>

                        <div class="col-md-6">
                            <label class="form-label small fw-bold">Work Description:</label>
                            <input type="text" name="description" class="form-control form-control-sm" placeholder="e.g. Engine Overhaul, Oil Filter Replacement" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Spare Part Name Used:</label>
                            <input type="text" name="spares_used" class="form-control form-control-sm" placeholder="e.g. Oil Filter, Air Filter">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Spare Parts Cost (ETB):</label>
                            <input type="number" step="0.01" name="spare_cost" class="form-control form-control-sm" value="0.00">
                        </div>

                        <!-- Consumables Inputs -->
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-warning">Battery Qty (Pcs):</label>
                            <input type="number" name="battery_qty" class="form-control form-control-sm" value="0">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-warning">Battery Cost (ETB):</label>
                            <input type="number" step="0.01" name="battery_cost" class="form-control form-control-sm" value="0.00">
                        </div>

                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-info">Lubrication Qty (Liters):</label>
                            <input type="number" step="0.1" name="lubrication_qty" class="form-control form-control-sm" value="0.0">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-info">Lubrication Cost (ETB):</label>
                            <input type="number" step="0.01" name="lubrication_cost" class="form-control form-control-sm" value="0.00">
                        </div>

                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-danger">Tire Qty (Pcs):</label>
                            <input type="number" name="tire_qty" class="form-control form-control-sm" value="0">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-danger">Tire Cost (ETB):</label>
                            <input type="number" step="0.01" name="tire_cost" class="form-control form-control-sm" value="0.00">
                        </div>

                        <div class="col-md-12 text-end mt-3">
                            <button type="submit" class="btn btn-primary btn-sm px-4 fw-bold">💾 Save Work Order & Calculate Time</button>
                        </div>
                    </div>
                </form>
            </div>

            <!-- 3. CONSUMABLES SUMMARY -->
            <div class="card card-summary p-4 mb-4" id="consumables-summary">
                <h5 class="fw-bold text-dark mb-3">🔋 Weekly & Monthly Consumables Summary</h5>
                <div class="row g-3">
                    <div class="col-md-4">
                        <div class="p-3 border rounded bg-white border-start border-warning border-4 shadow-sm">
                            <h6 class="text-muted fw-bold">Total Battery</h6>
                            <p class="mb-1"><strong>Qty:</strong> {{ summary.total_battery_qty }} Pcs</p>
                            <p class="mb-0 text-primary fw-bold"><strong>Cost:</strong> {{ "{:,.2f}".format(summary.total_battery_cost) }} ETB</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 border rounded bg-white border-start border-info border-4 shadow-sm">
                            <h6 class="text-muted fw-bold">Total Lubrication</h6>
                            <p class="mb-1"><strong>Qty:</strong> {{ summary.total_lubrication_qty }} Liters</p>
                            <p class="mb-0 text-primary fw-bold"><strong>Cost:</strong> {{ "{:,.2f}".format(summary.total_lubrication_cost) }} ETB</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 border rounded bg-white border-start border-danger border-4 shadow-sm">
                            <h6 class="text-muted fw-bold">Total Tires</h6>
                            <p class="mb-1"><strong>Qty:</strong> {{ summary.total_tire_qty }} Pcs</p>
                            <p class="mb-0 text-primary fw-bold"><strong>Cost:</strong> {{ "{:,.2f}".format(summary.total_tire_cost) }} ETB</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- 4. WORK TIME & MAINTENANCE LOG TABLE -->
            <div class="card card-summary p-4 mb-4" id="maintenance-logs">
                <h5 class="fw-bold text-dark mb-3">🛠️ Work Time & Maintenance Execution Log</h5>
                <div class="table-responsive">
                    <table class="table table-bordered align-middle table-sm">
                        <thead class="table-dark">
                            <tr>
                                <th>WO #</th>
                                <th>Plate No</th>
                                <th>Type</th>
                                <th>Start Date & Hour</th>
                                <th>Finished Date & Hour</th>
                                <th>Total Effective Work Time</th>
                                <th>Work Description</th>
                                <th>Battery (Qty/Cost)</th>
                                <th>Lubrication (Qty/Cost)</th>
                                <th>Tire (Qty/Cost)</th>
                                <th>Spare Cost (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in data.maintenance_logs %}
                            <tr>
                                <td class="fw-bold">{{ log.wo_no }}</td>
                                <td><span class="badge bg-secondary">{{ log.vehicle }}</span></td>
                                <td><span class="badge bg-{{ 'success' if log.type == 'PM' else 'danger' }}">{{ log.type }}</span></td>
                                <td class="small">{{ log.start_time }}</td>
                                <td class="small">{{ log.finish_time }}</td>
                                <td class="fw-bold text-center text-primary bg-light">{{ log.effective_hours }} hrs</td>
                                <td class="small">{{ log.description }}</td>
                                <td class="small">{{ log.battery_qty }} pcs / {{ "{:,.0f}".format(log.battery_cost) }} ETB</td>
                                <td class="small">{{ log.lubrication_qty }} L / {{ "{:,.0f}".format(log.lubrication_cost) }} ETB</td>
                                <td class="small">{{ log.tire_qty }} pcs / {{ "{:,.0f}".format(log.tire_cost) }} ETB</td>
                                <td class="fw-bold text-end">{{ "{:,.2f}".format(log.spare_cost) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- 5. SPARE PARTS INVENTORY WITH SPEC -->
            <div class="card card-summary p-4 mb-4" id="spare-parts">
                <h5 class="fw-bold text-dark mb-3">⚙️ Spare Parts Inventory & Specifications</h5>
                <div class="table-responsive">
                    <table class="table table-hover align-middle table-sm">
                        <thead class="table-dark">
                            <tr>
                                <th>#</th>
                                <th>Spare Part Name</th>
                                <th>Specification (Spec)</th>
                                <th>Stock Qty</th>
                                <th>Unit Price (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for part in data.spare_parts %}
                            <tr>
                                <td>{{ part.id }}</td>
                                <td class="fw-bold text-dark">{{ part.part_name }}</td>
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

@app.route('/')
def dashboard():
    summary = {
        "total_jobs": len(garage_data['maintenance_logs']),
        "pm_jobs": sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'PM'),
        "cm_jobs": sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'CM'),
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
    start_raw = request.form.get('start_time')
    finish_raw = request.form.get('finish_time')
    
    start_disp = start_raw.replace('T', ' ') if start_raw else ''
    finish_disp = finish_raw.replace('T', ' ') if finish_raw else ''
    
    eff_hours = calculate_effective_hours(start_raw, finish_raw)
    
    new_id = len(garage_data['maintenance_logs']) + 1
    new_log = {
        "id": new_id,
        "wo_no": request.form.get('wo_no', f'WO-2026-00{new_id}'),
        "vehicle": request.form.get('vehicle', 'N/A'),
        "model": request.form.get('model', 'N/A'),
        "driver": request.form.get('driver', 'N/A'),
        "type": request.form.get('type', 'PM'),
        "start_time": start_disp,
        "finish_time": finish_disp,
        "effective_hours": eff_hours,
        "description": request.form.get('description', ''),
        "spares_used": request.form.get('spares_used', ''),
        "spare_cost": float(request.form.get('spare_cost', 0) or 0),
        "battery_qty": int(request.form.get('battery_qty', 0) or 0),
        "battery_cost": float(request.form.get('battery_cost', 0) or 0),
        "lubrication_qty": float(request.form.get('lubrication_qty', 0) or 0),
        "lubrication_cost": float(request.form.get('lubrication_cost', 0) or 0),
        "tire_qty": int(request.form.get('tire_qty', 0) or 0),
        "tire_cost": float(request.form.get('tire_cost', 0) or 0)
    }
    garage_data['maintenance_logs'].append(new_log)
    return redirect(url_for('dashboard'))

@app.route('/export/master_excel')
def export_master_excel():
    output = io.BytesIO()
    
    logs_df = pd.DataFrame(garage_data['maintenance_logs'])
    logs_df.rename(columns={
        'id': 'ID',
        'wo_no': 'Work Order No',
        'vehicle': 'Vehicle Plate',
        'model': 'Vehicle Model',
        'driver': 'Driver Name',
        'type': 'Type (PM/CM)',
        'start_time': 'Starting Day & Hour',
        'finish_time': 'Finished Day & Hour',
        'effective_hours': 'Total Effective Work Time (Hours)',
        'description': 'Work Description',
        'spares_used': 'Spare Part Name Used',
        'spare_cost': 'Spare Parts Cost (ETB)',
        'battery_qty': 'Battery Qty (Pcs)',
        'battery_cost': 'Battery Cost (ETB)',
        'lubrication_qty': 'Lubrication Qty (Liters)',
        'lubrication_cost': 'Lubrication Cost (ETB)',
        'tire_qty': 'Tire Qty (Pcs)',
        'tire_cost': 'Tire Cost (ETB)'
    }, inplace=True)
    
    consumables_summary = [{
        'Consumable Category': 'Battery',
        'Total Quantity (Pcs)': sum(l['battery_qty'] for l in garage_data['maintenance_logs']),
        'Total Cost (ETB)': sum(l['battery_cost'] for l in garage_data['maintenance_logs'])
    }, {
        'Consumable Category': 'Lubrication',
        'Total Quantity (Liters)': sum(l['lubrication_qty'] for l in garage_data['maintenance_logs']),
        'Total Cost (ETB)': sum(l['lubrication_cost'] for l in garage_data['maintenance_logs'])
    }, {
        'Consumable Category': 'Tire',
        'Total Quantity (Pcs)': sum(l['tire_qty'] for l in garage_data['maintenance_logs']),
        'Total Cost (ETB)': sum(l['tire_cost'] for l in garage_data['maintenance_logs'])
    }]
    consumables_df = pd.DataFrame(consumables_summary)
    
    spares_df = pd.DataFrame(garage_data['spare_parts'])
    spares_df.rename(columns={
        'id': 'Part ID',
        'part_name': 'Spare Part Name',
        'spec': 'Specification (Spec)',
        'qty': 'Stock Quantity',
        'unit_price': 'Unit Price (ETB)'
    }, inplace=True)
    
    vehicles_df = pd.DataFrame(garage_data['vehicles'])
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        logs_df.to_excel(writer, sheet_name='Maintenance & Work Hours', index=False)
        consumables_df.to_excel(writer, sheet_name='Consumables Summary', index=False)
        spares_df.to_excel(writer, sheet_name='Spare Parts Inventory', index=False)
        vehicles_df.to_excel(writer, sheet_name='Vehicle Fleet', index=False)
        
    output.seek(0)
    
    return send_file(
        output,
        download_name='SteelY_Master_Garage_Maintenance_Report.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
