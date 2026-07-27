from datetime import datetime
import io
import pandas as pd
from flask import Flask, redirect, render_template_string, request, send_file, session, url_for

app = Flask(__name__)
app.secret_key = "steely_garage_secret_key"

# In-memory mock database store for workshop maintenance and inventory
garage_data = {
    "spare_parts": [
        {"id": 1, "part_name": "Fuel Filter", "spec": "FF-5782 / P550388", "for_vehicle": "Genlyon Truck", "qty": 14, "unit_price": 850.00},
        {"id": 2, "part_name": "Oil Filter", "spec": "LF-16015 / P550388", "for_vehicle": "Howo Dump Truck", "qty": 20, "unit_price": 950.00},
        {"id": 3, "part_name": "Brake Lining Set", "spec": "Heavy Duty Standard", "for_vehicle": "Sany Truck", "qty": 8, "unit_price": 4200.00},
        {"id": 4, "part_name": "Alternator Belt", "spec": "PK-10-1450", "for_vehicle": "Toyota Hilux", "qty": 12, "unit_price": 600.00}
    ],
    "maintenance_logs": [
        {
            "id": 1,
            "sn": "001",
            "wo_no": "WO-2026-001",
            "vehicle": "Genlyon Truck",
            "model": "380HP",
            "reading_value": 45200,
            "reading_unit": "KM",
            "next_service": 50200,
            "driver": "Abebe Kebede",
            "technicians": "Tesfaye & Mulugeta",
            "maintenance_type": "PM",
            "work_status": "Completed",
            "start_time": "2026-07-20 08:30",
            "finish_time": "2026-07-20 14:00",
            "effective_hours": 5.5,
            "description": "Routine preventive maintenance. Replaced oil and fuel filters.",
            "replaced_spares": [
                {"part_name": "Fuel Filter", "spec": "FF-5782", "qty": 1, "unit_price": 850.00, "total_cost": 850.00},
                {"part_name": "Oil Filter", "spec": "LF-16015", "qty": 1, "unit_price": 950.00, "total_cost": 950.00}
            ],
            "battery_qty": 0,
            "battery_cost": 0.0,
            "lubrication_qty": 25.0,
            "lubrication_cost": 3750.00,
            "tire_qty": 0,
            "tire_cost": 0.0
        }
    ]
}

def calculate_next_service(current_reading, unit):
    if unit == "KM":
        return current_reading + 5000
    elif unit == "HRS":
        return current_reading + 250
    return current_reading + 1000

def calculate_effective_hours(start_str, finish_str):
    try:
        fmt = "%Y-%m-%dT%H:%M"
        start = datetime.strptime(start_str, fmt)
        finish = datetime.strptime(finish_str, fmt)
        diff = (finish - start).total_seconds() / 3600.0
        return round(max(diff, 0.0), 2)
    except Exception:
        return 0.0

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I - Garage & Workshop Maintenance Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        .table-water-blue { background-color: #e3f2fd !important; }
        .card-header-dark { background-color: #1e293b; color: white; }
    </style>
</head>
<body class="bg-light">

<nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4 shadow-sm">
    <div class="container-fluid">
        <a class="navbar-brand fw-bold" href="#">⚙️ SteelY R.M.I Workshop Garage</a>
        <div class="d-flex align-items-center text-white">
            <span class="me-3 small">👤 {{ user.name }} ({{ user.role }})</span>
            <button class="btn btn-outline-light btn-sm me-2" data-bs-toggle="modal" data-bs-target="#inventoryModal">📦 Spare Inventory</button>
            <a href="/export/master_excel" class="btn btn-success btn-sm me-2">📥 Export Excel</a>
            <a href="/reset_all_logs" class="btn btn-outline-danger btn-sm" onclick="return confirm('Are you sure you want to clear all logs?');">🗑️ Reset Logs</a>
        </div>
    </div>
</nav>

<div class="container-fluid px-4">

    <!-- KPI Summary Row -->
    <div class="row g-3 mb-4">
        <div class="col-md-6">
            <div class="card shadow-sm border-primary">
                <div class="card-header bg-primary text-white fw-bold">📊 Weekly Operational Performance Summary</div>
                <div class="card-body bg-white">
                    <div class="row text-center">
                        <div class="col-4 border-end">
                            <span class="text-muted small d-block">Total Jobs</span>
                            <h4 class="fw-bold text-primary mb-0">{{ weekly.total_jobs }}</h4>
                        </div>
                        <div class="col-4 border-end">
                            <span class="text-muted small d-block">Effective Hours</span>
                            <h4 class="fw-bold text-success mb-0">{{ weekly.total_work_hours }} hrs</h4>
                        </div>
                        <div class="col-4">
                            <span class="text-muted small d-block">Total Expenditure</span>
                            <h4 class="fw-bold text-danger mb-0">{{ "{:,.2f}".format(weekly.total_expenditure) }} ETB</h4>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <div class="col-md-6">
            <div class="card shadow-sm border-dark">
                <div class="card-header card-header-dark fw-bold">📈 Monthly Operational Performance Summary</div>
                <div class="card-body bg-white">
                    <div class="row text-center">
                        <div class="col-4 border-end">
                            <span class="text-muted small d-block">Total Jobs</span>
                            <h4 class="fw-bold text-dark mb-0">{{ monthly.total_jobs }}</h4>
                        </div>
                        <div class="col-4 border-end">
                            <span class="text-muted small d-block">Effective Hours</span>
                            <h4 class="fw-bold text-success mb-0">{{ monthly.total_work_hours }} hrs</h4>
                        </div>
                        <div class="col-4">
                            <span class="text-muted small d-block">Total Expenditure</span>
                            <h4 class="fw-bold text-danger mb-0">{{ "{:,.2f}".format(monthly.total_expenditure) }} ETB</h4>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Main Content Layout -->
    <div class="row g-4">
        <!-- Left Column: Add Work Order Form -->
        <div class="col-xl-4">
            <div class="card shadow-sm">
                <div class="card-header bg-dark text-white fw-bold">📝 Log New Maintenance Work Order</div>
                <div class="card-body bg-white">
                    <form action="/add_work_order" method="POST">
                        <div class="row g-2 mb-2">
                            <div class="col-6">
                                <label class="form-label small fw-bold">S/N</label>
                                <input type="text" name="sn" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold">Work Order No</label>
                                <input type="text" name="wo_no" class="form-control form-control-sm" placeholder="WO-2026-XXX" required>
                            </div>
                        </div>

                        <div class="row g-2 mb-2">
                            <div class="col-6">
                                <label class="form-label small fw-bold">Vehicle / Asset</label>
                                <input type="text" name="vehicle" class="form-control form-control-sm" placeholder="e.g. Genlyon Truck" required>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold">Model</label>
                                <input type="text" name="model" class="form-control form-control-sm" placeholder="e.g. 380HP" required>
                            </div>
                        </div>

                        <div class="row g-2 mb-2">
                            <div class="col-6">
                                <label class="form-label small fw-bold">Reading Value</label>
                                <input type="number" name="reading_value" class="form-control form-control-sm" placeholder="45000" required>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold">Reading Unit</label>
                                <select name="reading_unit" class="form-select form-select-sm">
                                    <option value="KM">KM</option>
                                    <option value="HRS">HRS</option>
                                    <option value="Miles">Miles</option>
                                </select>
                            </div>
                        </div>

                        <div class="row g-2 mb-2">
                            <div class="col-6">
                                <label class="form-label small fw-bold">Driver Name</label>
                                <input type="text" name="driver" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold">Assigned Technicians</label>
                                <input type="text" name="technicians" class="form-control form-control-sm" required>
                            </div>
                        </div>

                        <div class="row g-2 mb-2">
                            <div class="col-6">
                                <label class="form-label small fw-bold">Maintenance Type</label>
                                <select name="maintenance_type" class="form-select form-select-sm">
                                    <option value="PM">PM (Preventive)</option>
                                    <option value="CM">CM (Corrective)</option>
                                    <option value="Inspection">Inspection</option>
                                </select>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold">Work Status</label>
                                <select name="work_status" class="form-select form-select-sm">
                                    <option value="Completed">Completed</option>
                                    <option value="In Progress">In Progress</option>
                                    <option value="Pending Spares">Pending Spares</option>
                                </select>
                            </div>
                        </div>

                        <div class="row g-2 mb-2">
                            <div class="col-6">
                                <label class="form-label small fw-bold">Start Time</label>
                                <input type="datetime-local" name="start_time" class="form-control form-control-sm" required>
                            </div>
                            <div class="col-6">
                                <label class="form-label small fw-bold">Finish Time</label>
                                <input type="datetime-local" name="finish_time" class="form-control form-control-sm" required>
                            </div>
                        </div>

                        <div class="mb-2">
                            <label class="form-label small fw-bold">Work Description & Actions Taken</label>
                            <textarea name="description" class="form-control form-control-sm" rows="2" required></textarea>
                        </div>

                        <hr class="my-2">
                        <label class="form-label small fw-bold text-primary">⚙️ Replaced Spare Parts</label>
                        <div id="spare-rows-container">
                            <div class="row g-2 spare-row mb-2 align-items-center">
                                <div class="col-md-3">
                                    <input type="text" name="spare_name[]" class="form-control form-control-sm" placeholder="Part Name">
                                </div>
                                <div class="col-md-3">
                                    <input type="text" name="spare_spec[]" class="form-control form-control-sm" placeholder="Specification">
                                </div>
                                <div class="col-md-1">
                                    <input type="number" name="spare_qty[]" class="form-control form-control-sm spare-qty" placeholder="Qty" value="1" min="1" oninput="calculateRowTotal(this)">
                                </div>
                                <div class="col-md-2">
                                    <input type="number" step="0.01" name="spare_price[]" class="form-control form-control-sm spare-price" placeholder="Price" value="0.00" oninput="calculateRowTotal(this)">
                                </div>
                                <div class="col-md-2">
                                    <span class="small fw-bold text-success row-total-text">0.00 ETB</span>
                                </div>
                                <div class="col-md-1">
                                    <button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeSpareRow(this)">✕</button>
                                </div>
                            </div>
                        </div>
                        <button type="button" class="btn btn-outline-secondary btn-sm mb-3 w-100" onclick="addSpareRow()">+ Add Another Spare Part</button>

                        <div class="row g-2 mb-3">
                            <div class="col-4">
                                <label class="form-label small text-muted">Battery Cost (ETB)</label>
                                <input type="number" step="0.01" name="battery_cost" class="form-control form-control-sm" value="0.00">
                            </div>
                            <div class="col-4">
                                <label class="form-label small text-muted">Lubrication Cost (ETB)</label>
                                <input type="number" step="0.01" name="lubrication_cost" class="form-control form-control-sm" value="0.00">
                            </div>
                            <div class="col-4">
                                <label class="form-label small text-muted">Tire Cost (ETB)</label>
                                <input type="number" step="0.01" name="tire_cost" class="form-control form-control-sm" value="0.00">
                            </div>
                        </div>

                        <button type="submit" class="btn btn-primary btn-sm w-100 fw-bold">Save Work Order Record</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- Right Column: Logs Table -->
        <div class="col-xl-8">
            <div class="card shadow-sm mb-4">
                <div class="card-header bg-secondary text-white d-flex justify-content-between align-items-center">
                    <span class="fw-bold">📋 Workshop Maintenance Activity Records</span>
                    <form method="GET" class="d-flex gap-2 align-items-center mb-0">
                        <input type="date" name="start_date" class="form-control form-control-sm" value="{{ request.args.get('start_date', '') }}">
                        <span class="text-white small">to</span>
                        <input type="date" name="end_date" class="form-control form-control-sm" value="{{ request.args.get('end_date', '') }}">
                        <button type="submit" class="btn btn-light btn-sm">Filter</button>
                        <a href="/" class="btn btn-outline-light btn-sm">Reset</a>
                    </form>
                </div>
                <div class="card-body bg-white p-0 table-responsive">
                    <table class="table table-bordered table-striped table-hover mb-0 align-middle" style="font-size: 0.85rem;">
                        <thead class="table-water-blue text-center">
                            <tr>
                                <th>S/N</th>
                                <th>WO No</th>
                                <th>Vehicle / Model</th>
                                <th>Reading</th>
                                <th>Next Serv.</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Eff. Hrs</th>
                                <th>Spares Cost</th>
                                <th>Battery</th>
                                <th>Lubricant</th>
                                <th>Tires</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in logs %}
                            <tr>
                                <td class="text-center fw-bold">{{ log.sn }}</td>
                                <td class="fw-bold text-primary">{{ log.wo_no }}</td>
                                <td>{{ log.vehicle }} <br><span class="text-muted small">({{ log.model }})</span></td>
                                <td class="text-center">{{ log.reading_value }} {{ log.reading_unit }}</td>
                                <td class="text-center text-danger fw-bold">{{ log.next_service }}</td>
                                <td class="text-center"><span class="badge bg-info text-dark">{{ log.maintenance_type }}</span></td>
                                <td class="text-center">
                                    <span class="badge {% if log.work_status == 'Completed' %}bg-success{% elif log.work_status == 'In Progress' %}bg-warning text-dark{% else %}bg-secondary{% endif %}">
                                        {{ log.work_status }}
                                    </span>
                                </td>
                                <td class="text-center fw-bold">{{ log.effective_hours }}h</td>
                                <td class="small">{{ "{:,.2f}".format(log.replaced_spares | sum(attribute='total_cost')) }} ETB</td>
                                <td class="small">{{ "{:,.2f}".format(log.battery_cost) }} ETB</td>
                                <td class="small">{{ "{:,.2f}".format(log.lubrication_cost) }} ETB</td>
                                <td class="small">{{ "{:,.2f}".format(log.tire_cost) }} ETB</td>
                                <td class="text-center">
                                    <a href="/delete_log/{{ log.id }}" class="btn btn-outline-danger btn-sm px-2 py-0 fw-bold" onclick="return confirm('Delete this work log entry?');">✕</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    </div>
</div>

<!-- Modal: Spare Inventory & Stock Management -->
<div class="modal fade" id="inventoryModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header bg-primary text-white">
                <h5 class="modal-title fw-bold">⚙️ SteelY R.M.I Spare Inventory & Stock Management</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <span class="text-muted small">Manage current workshop spare parts storage levels and unit pricing.</span>
                    <button type="button" class="btn btn-success btn-sm fw-bold" data-bs-toggle="modal" data-bs-target="#addSpareModal">+ Add New Spare Part</button>
                </div>
                <div class="table-responsive">
                    <table class="table table-bordered table-sm align-middle">
                        <thead class="table-water-blue">
                            <tr>
                                <th>ID</th>
                                <th>Part Name</th>
                                <th>Specification</th>
                                <th>For Vehicle</th>
                                <th>Qty in Stock</th>
                                <th>Unit Price (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for part in inventory %}
                            <tr>
                                <td class="fw-bold">{{ part.id }}</td>
                                <td class="fw-bold text-primary">{{ part.part_name }}</td>
                                <td class="small">{{ part.spec }}</td>
                                <td><span class="badge bg-secondary">{{ part.for_vehicle }}</span></td>
                                <td class="fw-bold">{{ part.qty }}</td>
                                <td class="fw-bold text-success">{{ "{:,.2f}".format(part.unit_price) }} ETB</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>

<!-- Modal: Add New Spare Part Form -->
<div class="modal fade" id="addSpareModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <form action="/add_spare_part" method="POST">
                <div class="modal-header bg-success text-white">
                    <h5 class="modal-title fw-bold">➕ Add Spare Part to Store Inventory</h5>
                    <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <div class="mb-2">
                        <label class="form-label small fw-bold">Part Name</label>
                        <input type="text" name="part_name" class="form-control form-control-sm" placeholder="e.g. Brake Pad" required>
                    </div>
                    <div class="mb-2">
                        <label class="form-label small fw-bold">Specification / Part Number</label>
                        <input type="text" name="spec" class="form-control form-control-sm" placeholder="e.g. BP-4420" required>
                    </div>
                    <div class="mb-2">
                        <label class="form-label small fw-bold">For Vehicle / Application</label>
                        <input type="text" name="for_vehicle" class="form-control form-control-sm" placeholder="e.g. Howo Dump Truck" required>
                    </div>
                    <div class="row g-2 mb-2">
                        <div class="col-6">
                            <label class="form-label small fw-bold">Initial Quantity in Stock</label>
                            <input type="number" name="qty" class="form-control form-control-sm" value="1" min="0" required>
                        </div>
                        <div class="col-6">
                            <label class="form-label small fw-bold">Unit Price (ETB)</label>
                            <input type="number" step="0.01" name="unit_price" class="form-control form-control-sm" value="0.00" min="0" required>
                        </div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
                    <button type="submit" class="btn btn-success btn-sm fw-bold">Save Spare Part</button>
                </div>
            </form>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
function addSpareRow() {
    const container = document.getElementById("spare-rows-container");
    const newRow = document.createElement("div");
    newRow.className = "row g-2 spare-row mb-2 align-items-center";
    newRow.innerHTML = `
        <div class="col-md-3">
            <input type="text" name="spare_name[]" class="form-control form-control-sm" placeholder="Part Name" required>
        </div>
        <div class="col-md-3">
            <input type="text" name="spare_spec[]" class="form-control form-control-sm" placeholder="Specification" required>
        </div>
        <div class="col-md-1">
            <input type="number" name="spare_qty[]" class="form-control form-control-sm spare-qty" placeholder="Qty" value="1" min="1" required oninput="calculateRowTotal(this)">
        </div>
        <div class="col-md-2">
            <input type="number" step="0.01" name="spare_price[]" class="form-control form-control-sm spare-price" placeholder="Unit Price (ETB)" value="0.00" required oninput="calculateRowTotal(this)">
        </div>
        <div class="col-md-2">
            <span class="small fw-bold text-success row-total-text">0.00 ETB</span>
        </div>
        <div class="col-md-1">
            <button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeSpareRow(this)">✕</button>
        </div>
    `;
    container.appendChild(newRow);
}

function removeSpareRow(btn) {
    const row = btn.closest(".spare-row");
    if (document.querySelectorAll(".spare-row").length > 1) {
        row.remove();
    } else {
        alert("At least one spare row placeholder should remain.");
    }
}

function calculateRowTotal(element) {
    const row = element.closest(".spare-row");
    const qty = parseFloat(row.querySelector(".spare-qty").value) || 0;
    const price = parseFloat(row.querySelector(".spare-price").value) || 0;
    const total = qty * price;
    row.querySelector(".row-total-text").innerText = total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " ETB";
}
</script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    if "user" not in session:
        session["user"] = {"name": "Demberu Tefera", "role": "Head of Workshop"}
    
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    logs = garage_data["maintenance_logs"]
    
    filtered_logs = logs
    if start_date and end_date:
        filtered_logs = [
            l for l in logs 
            if start_date <= l["start_time"].split(" ")[0] <= end_date
        ]
        
    def aggregate_metrics(log_list):
        total_jobs = len(log_list)
        total_work_hours = sum(l["effective_hours"] for l in log_list)
        total_spares_cost = sum(sum(sp["total_cost"] for sp in l.get("replaced_spares", [])) for l in log_list)
        total_lubrication_cost = sum(l.get("lubrication_cost", 0.0) for l in log_list)
        total_battery_cost = sum(l.get("battery_cost", 0.0) for l in log_list)
        total_tire_cost = sum(l.get("tire_cost", 0.0) for l in log_list)
        total_expenditure = total_spares_cost + total_lubrication_cost + total_battery_cost + total_tire_cost
        
        return {
            "total_jobs": total_jobs,
            "total_work_hours": round(total_work_hours, 2),
            "total_expenditure": total_expenditure
        }

    weekly = aggregate_metrics(logs[-7:]) if logs else aggregate_metrics([])
    monthly = aggregate_metrics(logs[-30:]) if logs else aggregate_metrics([])
    
    return render_template_string(
        HTML_TEMPLATE,
        user=session["user"],
        weekly=weekly,
        monthly=monthly,
        logs=filtered_logs,
        inventory=garage_data["spare_parts"]
    )

@app.route("/add_work_order", methods=["POST"])
def add_work_order():
    sn = request.form.get("sn")
    wo_no = request.form.get("wo_no")
    vehicle = request.form.get("vehicle")
    model = request.form.get("model")
    reading_value = int(request.form.get("reading_value", 0))
    reading_unit = request.form.get("reading_unit", "KM")
    next_service = calculate_next_service(reading_value, reading_unit)
    driver = request.form.get("driver")
    technicians = request.form.get("technicians")
    maintenance_type = request.form.get("maintenance_type")
    work_status = request.form.get("work_status")
    start_time = request.form.get("start_time").replace("T", " ")
    finish_time = request.form.get("finish_time").replace("T", " ")
    effective_hours = calculate_effective_hours(request.form.get("start_time"), request.form.get("finish_time"))
    description = request.form.get("description")
    
    spare_names = request.form.getlist("spare_name[]")
    spare_specs = request.form.getlist("spare_spec[]")
    spare_qtys = request.form.getlist("spare_qty[]")
    spare_prices = request.form.getlist("spare_price[]")
    
    replaced_spares = []
    for i in range(len(spare_names)):
        if spare_names[i].strip():
            q = int(spare_qtys[i]) if i < len(spare_qtys) else 1
            p = float(spare_prices[i]) if i < len(spare_prices) else 0.0
            replaced_spares.append({
                "part_name": spare_names[i],
                "spec": spare_specs[i] if i < len(spare_specs) else "",
                "qty": q,
                "unit_price": p,
                "total_cost": q * p
            })
            
    battery_cost = float(request.form.get("battery_cost", 0.0))
    lubrication_cost = float(request.form.get("lubrication_cost", 0.0))
    tire_cost = float(request.form.get("tire_cost", 0.0))
    
    new_id = max([l["id"] for l in garage_data["maintenance_logs"]], default=0) + 1
    
    new_log = {
        "id": new_id,
        "sn": sn,
        "wo_no": wo_no,
        "vehicle": vehicle,
        "model": model,
        "reading_value": reading_value,
        "reading_unit": reading_unit,
        "next_service": next_service,
        "driver": driver,
        "technicians": technicians,
        "maintenance_type": maintenance_type,
        "work_status": work_status,
        "start_time": start_time,
        "finish_time": finish_time,
        "effective_hours": effective_hours,
        "description": description,
        "replaced_spares": replaced_spares,
        "battery_cost": battery_cost,
        "lubrication_cost": lubrication_cost,
        "tire_cost": tire_cost
    }
    
    garage_data["maintenance_logs"].append(new_log)
    return redirect(url_for("index"))

@app.route("/add_spare_part", methods=["POST"])
def add_spare_part():
    part_name = request.form.get("part_name")
    spec = request.form.get("spec")
    for_vehicle = request.form.get("for_vehicle")
    qty = int(request.form.get("qty", 1))
    unit_price = float(request.form.get("unit_price", 0.0))
    
    new_spare_id = max([p["id"] for p in garage_data["spare_parts"]], default=0) + 1
    
    new_part = {
        "id": new_spare_id,
        "part_name": part_name,
        "spec": spec,
        "for_vehicle": for_vehicle,
        "qty": qty,
        "unit_price": unit_price
    }
    
    garage_data["spare_parts"].append(new_part)
    return redirect(url_for("index"))

@app.route("/delete_log/<int:log_id>", methods=["GET"])
def delete_log(log_id):
    garage_data["maintenance_logs"] = [l for l in garage_data["maintenance_logs"] if l["id"] != log_id]
    return redirect(url_for("index"))

@app.route("/reset_all_logs", methods=["GET"])
def reset_all_logs():
    garage_data["maintenance_logs"] = []
    return redirect(url_for("index"))

@app.route("/export/master_excel", methods=["GET"])
def export_master_excel():
    df = pd.DataFrame(garage_data["maintenance_logs"])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Master_Garage_Logs")
    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="SteelY_Garage_Master_Report.xlsx")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
