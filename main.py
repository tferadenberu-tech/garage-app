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
    "technicians": [
        {"name": "Mekonnen Kebede", "lead_jobs": 5, "total_hours": 32.5, "rank": 1, "score": "98%"},
        {"name": "Tadesse Hailu", "lead_jobs": 4, "total_hours": 28.0, "rank": 2, "score": "92%"},
        {"name": "Dawit Girma", "lead_jobs": 3, "total_hours": 22.5, "rank": 3, "score": "87%"}
    ],
    "maintenance_logs": [
        {
            "id": 1,
            "wo_no": "WO-2026-001",
            "vehicle": "AA-3-12345",
            "model": "Sino Truck 371",
            "driver": "Alemayehu T.",
            "technician": "Mekonnen Kebede",
            "type": "PM",
            "work_status": "Completed",
            "km_or_hr": "124,500 km",
            "start_time": "2026-07-20 08:00",
            "finish_time": "2026-07-20 14:30",
            "effective_hours": 6.5,
            "description": "Engine Oil & Filter Change + Maintenance Check",
            "replaced_spares": [
                {"name": "Oil Filter", "spec": "LF16015", "qty": 1, "cost": 1200.0},
                {"name": "Fuel Filter", "spec": "FF5421", "qty": 1, "cost": 1800.0}
            ],
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
            "technician": "Tadesse Hailu",
            "type": "CM",
            "work_status": "In Progress",
            "km_or_hr": "8,450 hrs",
            "start_time": "2026-07-22 09:00",
            "finish_time": "2026-07-23 11:00",
            "effective_hours": 26.0,
            "description": "Hydraulic Pump Repair + Battery & Rear Tires Replacement",
            "replaced_spares": [
                {"name": "Hydraulic Oil", "spec": "ISO VG 68", "qty": 1, "cost": 15000.0}
            ],
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
                    📊 Export Master Excel (All Data)
                </a>
            </div>

            <ul class="nav nav-pills flex-column">
                <li class="nav-item mb-2"><a href="#dashboard-summary" class="nav-link text-white">📊 Summaries & Filter</a></li>
                <li class="nav-item mb-2"><a href="#new-work-order" class="nav-link text-white fw-bold">➕ Create New Work Order</a></li>
                <li class="nav-item mb-2"><a href="#maintenance-logs" class="nav-link text-white">🛠️ Execution & Work Time Log</a></li>
                <li class="nav-item mb-2"><a href="#tech-rank" class="nav-link text-white">🏆 Tech Performance Rank</a></li>
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
                    <span class="text-muted small">Integrated Maintenance, Work Hours, Consumables & Technician Ranking System</span>
                </div>
                <div>
                    <a href="/export/master_excel" class="btn btn-excel btn-lg shadow-sm">
                        📥 Export Complete Excel Report
                    </a>
                </div>
            </div>

            <!-- 1. SUMMARIES & FILTERS SECTION -->
            <div class="row g-3 mb-4" id="dashboard-summary">
                <div class="col-md-4">
                    <div class="card card-summary p-3 h-100">
                        <h6 class="fw-bold text-primary border-bottom pb-2">WEEKLY SUMMARY (LAST 7 DAYS)</h6>
                        <p class="mb-1">Total Jobs Executed: <strong>{{ summary.total_jobs }}</strong></p>
                        <p class="mb-1 text-muted small">• PM: <strong>{{ summary.pm_jobs }}</strong> | CM: <strong>{{ summary.cm_jobs }}</strong></p>
                        <p class="mb-1 text-muted small">• Total Work Hours: <strong>{{ summary.total_work_hours }} hrs</strong></p>
                        <h6 class="fw-bold text-success mt-2">Spare Cost: {{ "{:,.2f}".format(summary.total_spare_cost) }} ETB</h6>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="card card-summary p-3 h-100">
                        <h6 class="fw-bold text-primary border-bottom pb-2">MONTHLY SUMMARY (LAST 30 DAYS)</h6>
                        <p class="mb-1">Total Jobs Executed: <strong>{{ summary.total_jobs }}</strong></p>
                        <p class="mb-1 text-muted small">• PM: <strong>{{ summary.pm_jobs }}</strong> | CM: <strong>{{ summary.cm_jobs }}</strong></p>
                        <p class="mb-1 text-muted small">• Total Work Hours: <strong>{{ summary.total_work_hours }} hrs</strong></p>
                        <h6 class="fw-bold text-success mt-2">Spare Cost: {{ "{:,.2f}".format(summary.total_spare_cost) }} ETB</h6>
                    </div>
                </div>

                <div class="col-md-4">
                    <div class="card card-summary p-3 h-100 bg-light">
                        <h6 class="fw-bold text-dark border-bottom pb-2">⏱️ TOTAL EFFECTIVE WORK TIME</h6>
                        <h2 class="fw-bold text-primary my-2">{{ summary.total_work_hours }} <small class="fs-6">Hours</small></h2>
                        <span class="badge bg-info text-dark">Across {{ summary.total_jobs }} Work Orders</span>
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
                        <a href="/export/master_excel" class="btn btn-excel btn-sm w-100 shadow-sm">📊 Export Weekly/Monthly Excel</a>
                    </div>
                </div>
            </div>

            <!-- 2. CREATE NEW WORK ORDER FORM -->
            <div class="card card-summary p-4 mb-4 form-card" id="new-work-order">
                <h5 class="fw-bold text-primary mb-3">📝 Create New Work Order</h5>
                <form action="/add_work_order" method="POST">
                    <div class="row g-3">
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Work Order No (W.O No):</label>
                            <input type="text" name="wo_no" class="form-control form-control-sm" placeholder="e.g. WO-2026-003" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Vehicle Plate No:</label>
                            <input type="text" name="vehicle" class="form-control form-control-sm" placeholder="e.g. AA-3-12345" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Vehicle Model:</label>
                            <input type="text" name="model" class="form-control form-control-sm" placeholder="e.g. Sino Truck">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">KM / Hour Reading:</label>
                            <input type="text" name="km_or_hr" class="form-control form-control-sm" placeholder="e.g. 150,000 km or 4,200 hrs" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Work Status:</label>
                            <select name="work_status" class="form-select form-select-sm" required>
                                <option value="Completed">Completed</option>
                                <option value="In Progress">In Progress</option>
                                <option value="Pending">Pending</option>
                            </select>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Maintenance Type:</label>
                            <select name="type" class="form-select form-select-sm" required>
                                <option value="PM">PM (Preventive)</option>
                                <option value="CM">CM (Corrective)</option>
                            </select>
                        </div>

                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Driver Name:</label>
                            <input type="text" name="driver" class="form-control form-control-sm" placeholder="e.g. Kebede M.">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Assigned Technician:</label>
                            <input type="text" name="technician" class="form-control form-control-sm" placeholder="e.g. Mekonnen K." required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Starting Day & Hour:</label>
                            <input type="datetime-local" name="start_time" class="form-control form-control-sm" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Finished Day & Hour:</label>
                            <input type="datetime-local" name="finish_time" class="form-control form-control-sm" required>
                        </div>

                        <div class="col-md-12">
                            <label class="form-label small fw-bold">Work Description:</label>
                            <input type="text" name="description" class="form-control form-control-sm" placeholder="e.g. Engine Overhaul, Oil Filter Replacement" required>
                        </div>

                        <!-- 🛠️ Dynamic Replaced Spare Parts Section -->
                        <div class="col-md-12">
                            <div class="p-3 border rounded bg-light">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <label class="form-label small fw-bold text-dark mb-0">🔧 Replaced Spare Parts List:</label>
                                    <button type="button" class="btn btn-sm btn-outline-success fw-bold" onclick="addSpareRow()">+ Add Replaced Spare Part</button>
                                </div>
                                <div id="spare-parts-container">
                                    <div class="row g-2 mb-2 spare-row">
                                        <div class="col-md-4">
                                            <input type="text" name="spare_name[]" class="form-control form-control-sm" placeholder="Spare Part Name (e.g. Oil Filter)">
                                        </div>
                                        <div class="col-md-4">
                                            <input type="text" name="spare_spec[]" class="form-control form-control-sm" placeholder="Specification (Spec)">
                                        </div>
                                        <div class="col-md-2">
                                            <input type="number" name="spare_qty[]" class="form-control form-control-sm" placeholder="Qty" value="1">
                                        </div>
                                        <div class="col-md-2">
                                            <input type="number" step="0.01" name="spare_cost[]" class="form-control form-control-sm" placeholder="Total Cost (ETB)" value="0.00">
                                        </div>
                                    </div>
                                </div>
                            </div>
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
                            <button type="submit" class="btn btn-primary btn-sm px-4 fw-bold">💾 Save Work Order & Update Performance</button>
                        </div>
                    </div>
                </form>
            </div>

            <!-- 3. WORK TIME & MAINTENANCE EXECUTION LOG TABLE -->
            <div class="card card-summary p-4 mb-4" id="maintenance-logs">
                <h5 class="fw-bold text-dark mb-3">🛠️ Maintenance Execution & Work Time Log</h5>
                <div class="table-responsive">
                    <table class="table table-bordered align-middle table-sm">
                        <thead class="table-dark">
                            <tr>
                                <th>WO #</th>
                                <th>Plate No</th>
                                <th>KM / Hour Reading</th>
                                <th>Status</th>
                                <th>Type</th>
                                <th>Technician</th>
                                <th>Start / Finish Time</th>
                                <th>Total Effective Work Time</th>
                                <th>Replaced Spare Parts & Spec</th>
                                <th>Consumables (Battery/Oil/Tire)</th>
                                <th>Spare Cost (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in data.maintenance_logs %}
                            <tr>
                                <td class="fw-bold">{{ log.wo_no }}</td>
                                <td><span class="badge bg-secondary">{{ log.vehicle }}</span></td>
                                <td class="fw-bold text-primary small">{{ log.km_or_hr }}</td>
                                <td>
                                    {% if log.work_status == 'Completed' %}
                                        <span class="badge bg-success">Completed</span>
                                    {% elif log.work_status == 'In Progress' %}
                                        <span class="badge bg-warning text-dark">In Progress</span>
                                    {% else %}
                                        <span class="badge bg-danger">Pending</span>
                                    {% endif %}
                                </td>
                                <td><span class="badge bg-{{ 'success' if log.type == 'PM' else 'danger' }}">{{ log.type }}</span></td>
                                <td class="small fw-bold">{{ log.technician }}</td>
                                <td class="small">{{ log.start_time }}<br><span class="text-muted">{{ log.finish_time }}</span></td>
                                <td class="fw-bold text-center text-primary bg-light">{{ log.effective_hours }} hrs</td>
                                <td class="small">
                                    {% for sp in log.replaced_spares %}
                                        <div>• <strong>{{ sp.name }}</strong> ({{ sp.spec }}) x{{ sp.qty }}</div>
                                    {% endfor %}
                                </td>
                                <td class="small">
                                    {% if log.battery_qty > 0 %}<div>• Battery: {{ log.battery_qty }} pcs</div>{% endif %}
                                    {% if log.lubrication_qty > 0 %}<div>• Oil: {{ log.lubrication_qty }} L</div>{% endif %}
                                    {% if log.tire_qty > 0 %}<div>• Tire: {{ log.tire_qty }} pcs</div>{% endif %}
                                </td>
                                <td class="fw-bold text-end">{{ "{:,.2f}".format(log.spare_cost) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                        <tfoot class="table-light fw-bold">
                            <tr>
                                <td colspan="7" class="text-end">TOTAL EFFECTIVE WORK TIME & SPARES COST:</td>
                                <td class="text-center text-primary">{{ summary.total_work_hours }} hrs</td>
                                <td colspan="2"></td>
                                <td class="text-end text-success">{{ "{:,.2f}".format(summary.total_spare_cost) }} ETB</td>
                            </tr>
                        </tfoot>
                    </table>
                </div>
            </div>

            <!-- 🏆 4. TECHNICAL WORK PERFORMANCE RANK TABLE -->
            <div class="card card-summary p-4 mb-4" id="tech-rank">
                <h5 class="fw-bold text-dark mb-3">🏆 Technical Work Performance Rank</h5>
                <div class="table-responsive">
                    <table class="table table-hover align-middle table-sm">
                        <thead class="table-dark">
                            <tr>
                                <th>Rank</th>
                                <th>Technician / Mechanic Name</th>
                                <th>Jobs Completed</th>
                                <th>Total Effective Hours Worked</th>
                                <th>Performance Rating</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for tech in data.technicians %}
                            <tr>
                                <td class="fw-bold text-center">
                                    {% if tech.rank == 1 %}
                                        🥇 1st
                                    {% elif tech.rank == 2 %}
                                        🥈 2nd
                                    {% elif tech.rank == 3 %}
                                        🥉 3rd
                                    {% else %}
                                        #{{ tech.rank }}
                                    {% endif %}
                                </td>
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

            <!-- 5. CONSUMABLES SUMMARY -->
            <div class="card card-summary p-4 mb-4" id="consumables-summary">
                <h5 class="fw-bold text-dark mb-3">🔋 Consumables Summary</h5>
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

            <!-- 6. SPARE PARTS INVENTORY WITH SPEC -->
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

<script>
function addSpareRow() {
    const container = document.getElementById('spare-parts-container');
    const newRow = document.createElement('div');
    newRow.className = 'row g-2 mb-2 spare-row';
    newRow.innerHTML = `
        <div class="col-md-4">
            <input type="text" name="spare_name[]" class="form-control form-control-sm" placeholder="Spare Part Name">
        </div>
        <div class="col-md-4">
            <input type="text" name="spare_spec[]" class="form-control form-control-sm" placeholder="Specification (Spec)">
        </div>
        <div class="col-md-2">
            <input type="number" name="spare_qty[]" class="form-control form-control-sm" placeholder="Qty" value="1">
        </div>
        <div class="col-md-2">
            <input type="number" step="0.01" name="spare_cost[]" class="form-control form-control-sm" placeholder="Total Cost (ETB)" value="0.00">
        </div>
    `;
    container.appendChild(newRow);
}
</script>
</body>
</html>
"""

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
    start_raw = request.form.get('start_time')
    finish_raw = request.form.get('finish_time')
    
    start_disp = start_raw.replace('T', ' ') if start_raw else ''
    finish_disp = finish_raw.replace('T', ' ') if finish_raw else ''
    
    eff_hours = calculate_effective_hours(start_raw, finish_raw)
    
    # Process dynamic replaced spare parts
    spare_names = request.form.getlist('spare_name[]')
    spare_specs = request.form.getlist('spare_spec[]')
    spare_qtys = request.form.getlist('spare_qty[]')
    spare_costs = request.form.getlist('spare_cost[]')
    
    replaced_list = []
    total_spare_cost_calc = 0.0
    for name, spec, qty, cost in zip(spare_names, spare_specs, spare_qtys, spare_costs):
        if name.strip():
            c_val = float(cost or 0)
            q_val = int(qty or 1)
            replaced_list.append({
                "name": name,
                "spec": spec,
                "qty": q_val,
                "cost": c_val
            })
            total_spare_cost_calc += c_val
    
    new_id = len(garage_data['maintenance_logs']) + 1
    new_log = {
        "id": new_id,
        "wo_no": request.form.get('wo_no', f'WO-2026-00{new_id}'),
        "vehicle": request.form.get('vehicle', 'N/A'),
        "model": request.form.get('model', 'N/A'),
        "km_or_hr": request.form.get('km_or_hr', 'N/A'),
        "work_status": request.form.get('work_status', 'Completed'),
        "driver": request.form.get('driver', 'N/A'),
        "technician": request.form.get('technician', 'N/A'),
        "type": request.form.get('type', 'PM'),
        "start_time": start_disp,
        "finish_time": finish_disp,
        "effective_hours": eff_hours,
        "description": request.form.get('description', ''),
        "replaced_spares": replaced_list,
        "spare_cost": total_spare_cost_calc,
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
    
    # 1. Maintenance & Work Hours Sheet
    logs_export = []
    for l in garage_data['maintenance_logs']:
        sp_summary = ", ".join([f"{sp['name']} ({sp['spec']}) x{sp['qty']}" for sp in l['replaced_spares']])
        logs_export.append({
            'Work Order No': l['wo_no'],
            'Vehicle Plate': l['vehicle'],
            'Vehicle Model': l['model'],
            'KM / Hour Reading': l['km_or_hr'],
            'Work Status': l['work_status'],
            'Type (PM/CM)': l['type'],
            'Technician': l['technician'],
            'Driver Name': l['driver'],
            'Starting Day & Hour': l['start_time'],
            'Finished Day & Hour': l['finish_time'],
            'Total Effective Work Time (Hours)': l['effective_hours'],
            'Work Description': l['description'],
            'Replaced Spare Parts & Spec': sp_summary,
            'Spare Parts Cost (ETB)': l['spare_cost'],
            'Battery Qty': l['battery_qty'],
            'Battery Cost (ETB)': l['battery_cost'],
            'Lubrication Qty (L)': l['lubrication_qty'],
            'Lubrication Cost (ETB)': l['lubrication_cost'],
            'Tire Qty': l['tire_qty'],
            'Tire Cost (ETB)': l['tire_cost']
        })
    logs_df = pd.DataFrame(logs_export)
    
    # 2. Weekly & Monthly Summary Cards Sheet
    total_hours = sum(l['effective_hours'] for l in garage_data['maintenance_logs'])
    total_spares = sum(l['spare_cost'] for l in garage_data['maintenance_logs'])
    summary_data = [
        {'Summary Period': 'Weekly Summary (Last 7 Days)', 'Total Jobs Executed': len(garage_data['maintenance_logs']), 'PM Jobs': sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'PM'), 'CM Jobs': sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'CM'), 'Total Effective Work Time (Hrs)': total_hours, 'Total Spare Cost (ETB)': total_spares},
        {'Summary Period': 'Monthly Summary (Last 30 Days)', 'Total Jobs Executed': len(garage_data['maintenance_logs']), 'PM Jobs': sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'PM'), 'CM Jobs': sum(1 for l in garage_data['maintenance_logs'] if l['type'] == 'CM'), 'Total Effective Work Time (Hrs)': total_hours, 'Total Spare Cost (ETB)': total_spares}
    ]
    summary_df = pd.DataFrame(summary_data)
    
    # 3. Technician Performance Rank Sheet
    tech_df = pd.DataFrame(garage_data['technicians'])
    
    # 4. Consumables Summary Sheet
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
    
    # 5. Spare Parts Inventory Sheet
    spares_df = pd.DataFrame(garage_data['spare_parts'])
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        logs_df.to_excel(writer, sheet_name='Maintenance & Work Hours', index=False)
        summary_df.to_excel(writer, sheet_name='Weekly & Monthly Summaries', index=False)
        tech_df.to_excel(writer, sheet_name='Tech Performance Rank', index=False)
        consumables_df.to_excel(writer, sheet_name='Consumables Summary', index=False)
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
