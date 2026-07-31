import io
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, make_response, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'steely_rmi_secure_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steely_rmi_garage_v19.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial_number = db.Column(db.String(50), nullable=False)
    work_order_no = db.Column(db.String(50), nullable=False)
    vehicle_plate = db.Column(db.String(50), nullable=False)
    vehicle_model = db.Column(db.String(100), nullable=False)
    current_reading = db.Column(db.Float, nullable=False, default=0.0)
    reading_unit = db.Column(db.String(20), nullable=False)
    next_due_reading = db.Column(db.Float, nullable=False, default=0.0)
    job_status = db.Column(db.String(50), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    assigned_technicians = db.Column(db.String(200), nullable=False)
    start_datetime = db.Column(db.String(50), nullable=False)
    end_datetime = db.Column(db.String(50), nullable=False)
    maintenance_type = db.Column(db.String(50), nullable=False) 
    work_category = db.Column(db.String(100), nullable=False) 
    description = db.Column(db.Text, nullable=True)
    
    replaced_spare_name = db.Column(db.String(300), nullable=True, default='-')
    spare_parts_qty = db.Column(db.Integer, nullable=False, default=0)
    spare_parts_cost = db.Column(db.Float, nullable=False, default=0.0)
    
    lubricants_volume = db.Column(db.Float, nullable=False, default=0.0)
    lubricants_cost = db.Column(db.Float, nullable=False, default=0.0)
    batteries_cost = db.Column(db.Float, nullable=False, default=0.0)
    tires_cost = db.Column(db.Float, nullable=False, default=0.0)
    effective_work_hours = db.Column(db.Float, nullable=False, default=0.0)
    total_expenditure = db.Column(db.Float, nullable=False, default=0.0)

class SpareInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_name = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_cost = db.Column(db.Float, nullable=False, default=0.0)
    location = db.Column(db.String(100), nullable=False)

with app.app_context():
    db.create_all()

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SteelY R.M.I - Login</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark d-flex align-items-center justify-content-center vh-100">
    <div class="card p-4 shadow-lg" style="width: 380px; background: #1e2124; color: white; border-radius: 12px;">
        <h3 class="text-center mb-4 text-primary fw-bold">SteelY R.M.I</h3>
        {% if error %}
            <div class="alert alert-danger py-2 text-center">{{ error }}</div>
        {% endif %}
        <form method="POST" action="/login">
            <div class="mb-3">
                <label class="form-label">Username</label>
                <input type="text" class="form-control" name="username" required autocomplete="off" value="admin">
            </div>
            <div class="mb-3">
                <label class="form-label">Password</label>
                <input type="password" class="form-control" name="password" required value="steely2026">
            </div>
            <button type="submit" class="btn btn-primary w-100 py-2 fw-bold">Login to Dashboard</button>
        </form>
    </div>
</body>
</html>
"""

SHARED_MODAL_HTML = """
    <!-- Modal for Work Order -->
    <div class="modal fade" id="addWorkOrderModal" tabindex="-1">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <form method="POST" action="/add_work_order">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">Create New Work Order (+5000 KM / +250 Hours Auto Due)</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row g-3">
                            <div class="col-md-3">
                                <label class="form-label">Serial Number (S/N)</label>
                                <input type="text" class="form-control" name="serial_number" required value="SN-001">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">Work Order No</label>
                                <input type="text" class="form-control" name="work_order_no" required value="WO-2026-01">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">Vehicle Plate Number</label>
                                <input type="text" class="form-control" name="vehicle_plate" required placeholder="e.g. AA-3-12345">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">Vehicle Type / Model</label>
                                <input type="text" class="form-control" name="vehicle_model" required placeholder="e.g. Sino Truck 371">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">Current Reading</label>
                                <input type="number" step="any" class="form-control" name="current_reading" required placeholder="e.g. 125000">
                            </div>
                            <div class="col-md-3">
                                <label class="form-label fw-bold text-primary">Reading Unit</label>
                                <select class="form-select border-primary fw-bold" name="reading_unit" required>
                                    <option value="KM">KM (+5000 Next Due)</option>
                                    <option value="Hours">Hours (+250 Next Due)</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">Job Status</label>
                                <select class="form-select" name="job_status">
                                    <option value="Completed">Completed</option>
                                    <option value="In Progress">In Progress</option>
                                    <option value="Pending">Pending</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="form-label">Driver Name</label>
                                <input type="text" class="form-control" name="driver_name" required placeholder="Driver Name">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Assigned Technicians</label>
                                <input type="text" class="form-control" name="assigned_technicians" required value="Ato Mihret, Dinberu Tefera">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Start Date & Time</label>
                                <input type="datetime-local" class="form-control" name="start_datetime" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">End Date & Time</label>
                                <input type="datetime-local" class="form-control" name="end_datetime" required>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label fw-bold text-danger">Maintenance Type</label>
                                <select class="form-select border-danger fw-bold text-primary" name="maintenance_type" required>
                                    <option value="CM">CM (Corrective Maintenance)</option>
                                    <option value="PM">PM (Preventive Maintenance)</option>
                                    <option value="Inspection & Check">Inspection & Check</option>
                                </select>
                            </div>
                            <div class="col-md-8">
                                <label class="form-label fw-bold">Work Category</label>
                                <input type="text" class="form-control" name="work_category" required placeholder="e.g. Engine Maintenance">
                            </div>

                            <div class="col-12 mt-3">
                                <label class="form-label fw-bold text-primary fs-6">Replaced Spare Parts List (Multi-Row & Auto Cost)</label>
                                <div class="table-responsive">
                                    <table class="table table-bordered align-middle" id="woSpareTable">
                                        <thead class="table-dark">
                                            <tr>
                                                <th>Spare Part Name</th>
                                                <th style="width: 130px;">Quantity (Pcs)</th>
                                                <th style="width: 150px;">Unit Cost (ETB)</th>
                                                <th style="width: 150px;">Total Cost (ETB)</th>
                                                <th style="width: 80px; text-align: center;">Action</th>
                                            </tr>
                                        </thead>
                                        <tbody id="woSpareTableBody">
                                            <tr>
                                                <td><input type="text" class="form-control" name="spare_name[]" required placeholder="e.g. Oil Filter / Brake Pad"></td>
                                                <td><input type="number" class="form-control spare-qty" name="spare_qty[]" required min="1" value="1" oninput="calculateRowAndTotal(this)"></td>
                                                <td><input type="number" step="0.01" class="form-control spare-cost" name="spare_unit_cost[]" required min="0" value="0.00" oninput="calculateRowAndTotal(this)"></td>
                                                <td><input type="text" class="form-control bg-light row-total" readonly value="0.00"></td>
                                                <td class="text-center">
                                                    <button type="button" class="btn btn-danger btn-sm" onclick="removeWoSpareRow(this)">X</button>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                                <button type="button" class="btn btn-success btn-sm fw-bold mt-1" onclick="addWoSpareRow()">+ Add Row Spare Part</button>
                            </div>

                            <div class="col-md-4">
                                <label class="form-label fw-bold text-success">Total Spare Parts Cost (ETB)</label>
                                <input type="text" class="form-control fw-bold text-success bg-light" id="totalSparePartsCostDisplay" readonly value="0.00">
                                <input type="hidden" name="spare_parts_cost" id="spare_parts_cost_hidden" value="0.00">
                                <input type="hidden" name="spare_parts_qty" id="spare_parts_qty_hidden" value="0">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Lubricants Cost (ETB)</label>
                                <input type="number" step="0.01" class="form-control other-cost" name="lubricants_cost" id="lubricants_cost" value="0.00" min="0" oninput="calculateGrandTotal()">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Batteries Cost (ETB)</label>
                                <input type="number" step="0.01" class="form-control other-cost" name="batteries_cost" id="batteries_cost" value="0.00" min="0" oninput="calculateGrandTotal()">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Tires Cost (ETB)</label>
                                <input type="number" step="0.01" class="form-control other-cost" name="tires_cost" id="tires_cost" value="0.00" min="0" oninput="calculateGrandTotal()">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label fw-bold text-danger">Grand Total Expenditure (ETB)</label>
                                <input type="text" class="form-control fw-bold text-danger bg-light fs-5" id="grandTotalDisplay" readonly value="0.00">
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="submit" class="btn btn-primary fw-bold">Save Work Order</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script>
        function addWoSpareRow() {
            let tbody = document.getElementById('woSpareTableBody');
            let newRow = document.createElement('tr');
            newRow.innerHTML = `
                <td><input type="text" class="form-control" name="spare_name[]" required placeholder="e.g. Bearing"></td>
                <td><input type="number" class="form-control spare-qty" name="spare_qty[]" required min="1" value="1" oninput="calculateRowAndTotal(this)"></td>
                <td><input type="number" step="0.01" class="form-control spare-cost" name="spare_unit_cost[]" required min="0" value="0.00" oninput="calculateRowAndTotal(this)"></td>
                <td><input type="text" class="form-control bg-light row-total" readonly value="0.00"></td>
                <td class="text-center">
                    <button type="button" class="btn btn-danger btn-sm" onclick="removeWoSpareRow(this)">X</button>
                </td>
            `;
            tbody.appendChild(newRow);
            calculateGrandTotal();
        }

        function removeWoSpareRow(btn) {
            let tbody = document.getElementById('woSpareTableBody');
            if (tbody.rows.length > 1) {
                let row = btn.closest('tr');
                row.remove();
                calculateGrandTotal();
            } else {
                alert('At least one spare part row is required!');
            }
        }

        function calculateRowAndTotal(element) {
            let row = element.closest('tr');
            let qty = parseFloat(row.querySelector('.spare-qty').value) || 0;
            let unitCost = parseFloat(row.querySelector('.spare-cost').value) || 0;
            let rowTotal = qty * unitCost;
            row.querySelector('.row-total').value = rowTotal.toFixed(2);
            calculateGrandTotal();
        }

        function calculateGrandTotal() {
            let rows = document.querySelectorAll('#woSpareTableBody tr');
            let totalSpareCost = 0;
            let totalSpareQty = 0;

            rows.forEach(row => {
                let qty = parseFloat(row.querySelector('.spare-qty').value) || 0;
                let unitCost = parseFloat(row.querySelector('.spare-cost').value) || 0;
                totalSpareCost += (qty * unitCost);
                totalSpareQty += qty;
            });

            document.getElementById('totalSparePartsCostDisplay').value = totalSpareCost.toFixed(2);
            document.getElementById('spare_parts_cost_hidden').value = totalSpareCost.toFixed(2);
            document.getElementById('spare_parts_qty_hidden').value = totalSpareQty;

            let lubeCost = parseFloat(document.getElementById('lubricants_cost').value) || 0;
            let battCost = parseFloat(document.getElementById('batteries_cost').value) || 0;
            let tireCost = parseFloat(document.getElementById('tires_cost').value) || 0;

            let grandTotal = totalSpareCost + lubeCost + battCost + tireCost;
            document.getElementById('grandTotalDisplay').value = grandTotal.toFixed(2);
        }
    </script>
"""

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SteelY R.M.I Garage Maintnace dash Bord</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f6f9; }
        .main-layout-container { margin-left: 240px; padding: 20px; max-width: calc(100% - 240px); transition: all 0.3s ease; }
        .sidebar-space { position: fixed; top: 0; left: 0; width: 220px; height: 100%; background: #212529; color: white; padding: 20px; z-index: 1000; }
        @media (max-width: 992px) {
            .main-layout-container { margin-left: 0; max-width: 100%; }
            .sidebar-space { display: none; }
        }
    </style>
</head>
<body>
    <div class="sidebar-space d-none d-lg-block">
        <h5 class="text-primary fw-bold mb-4">SteelY Garage</h5>
        <ul class="nav flex-column gap-2">
            <li class="nav-item"><a href="/dashboard" class="nav-link text-white active bg-primary rounded">🏠 Dashboard</a></li>
            <li class="nav-item"><a href="/inventory" class="nav-link text-white">📦 Store Inventory</a></li>
            <li class="nav-item"><a href="#" class="nav-link text-success fw-bold" data-bs-toggle="modal" data-bs-target="#addWorkOrderModal">➕ Create New Work Order</a></li>
            <li class="nav-item"><a href="/export/master_report" class="nav-link text-white">📊 All-In-One-Master Report to Excel</a></li>
            <li class="nav-item"><a href="/export/maintenance_execution" class="nav-link text-white">📥 Execution Log</a></li>
            <li class="nav-item mt-5"><a href="/logout" class="nav-link text-danger">🚪 Logout</a></li>
        </ul>
    </div>

    <div class="main-layout-container">
        
        <!-- Header Section -->
        <div class="card shadow-sm p-3 mb-3 bg-white">
            <div class="row align-items-center g-2">
                <div class="col-md-5">
                    <h4 class="text-primary fw-bold mb-0">SteelY R.M.I Garage Maintenance</h4>
                    <small class="text-muted">Integrated Work Time, Consumables & Maintenance Platform</small>
                </div>
                <div class="col-md-7 d-flex justify-content-md-end align-items-center gap-2 flex-wrap">
                    <div class="text-start text-md-end">
                        <span class="badge bg-secondary">Dinberu Tefera</span><br>
                        <small class="text-muted fw-bold" style="font-size: 9px;">HEAD OF MECHANICAL WORKSHOP AND GARAGE</small>
                    </div>
                    <a href="/export/master_report" class="btn btn-success btn-sm fw-bold">📊 All-In-One-Master Report to Excel</a>
                    <a href="/logout" class="btn btn-danger btn-sm fw-bold d-lg-none">🚪 Logout</a>
                </div>
            </div>
        </div>
        
        <div class="mb-3 d-flex gap-2 flex-wrap">
            <button class="btn btn-primary btn-sm fw-bold" data-bs-toggle="modal" data-bs-target="#addWorkOrderModal">+ Create New Work Order</button>
            <a href="/inventory" class="btn btn-dark btn-sm fw-bold">📦 View Store Inventory</a>
        </div>

        <!-- Weekly & Monthly Summaries Row -->
        <div class="row mb-3">
            <!-- Weekly Summary -->
            <div class="col-xl-6 mb-2">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-secondary text-white py-2 d-flex justify-content-between align-items-center">
                        <h5 class="mb-0 fs-6">WEEKLY SUMMARY (LAST 7 DAYS)</h5>
                        <a href="/export/weekly_report" class="btn btn-light btn-sm text-dark fw-bold py-0" style="font-size: 11px;">📥 Export Weekly Report</a>
                    </div>
                    <div class="card-body">
                        <p class="fw-bold mb-2">Total Jobs Executed: <span class="text-primary">{{ weekly_jobs }}</span></p>
                        <div class="mb-2 small text-muted bg-light p-2 rounded border">
                            <div>CM (Corrective): <strong class="text-dark">{{ weekly_cm }}</strong></div>
                            <div>PM (Preventive): <strong class="text-dark">{{ weekly_pm }}</strong></div>
                            <div>Inspection & Check: <strong class="text-dark">{{ weekly_insp }}</strong></div>
                        </div>
                        <p class="fw-bold mb-2 text-primary">Total Effective Work Time: {{ "%.1f"|format(weekly_hours) }} hrs</p>
                        <hr class="my-2">
                        <div class="row small text-muted">
                            <div class="col-6">Spare Qty: <strong>{{ weekly_spare_qty }} Pcs</strong></div>
                            <div class="col-6">Spare Cost: <strong>ETB {{ "%.2f"|format(weekly_spare_cost) }}</strong></div>
                            <div class="col-6">Lubricants: <strong>{{ "%.1f"|format(weekly_lube_vol) }} L</strong></div>
                            <div class="col-6">Lube Cost: <strong>ETB {{ "%.2f"|format(weekly_lube_cost) }}</strong></div>
                        </div>
                        <div class="mt-2 pt-2 border-top fw-bold text-dark">
                            Total Expenditure: ETB {{ "%.2f"|format(weekly_total_exp) }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Monthly Summary -->
            <div class="col-xl-6 mb-2">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-primary text-white py-2 d-flex justify-content-between align-items-center">
                        <h5 class="mb-0 fs-6">MONTHLY SUMMARY (LAST 30 DAYS)</h5>
                        <a href="/export/monthly_report" class="btn btn-light btn-sm text-dark fw-bold py-0" style="font-size: 11px;">📥 Export Monthly Report</a>
                    </div>
                    <div class="card-body">
                        <p class="fw-bold mb-2">Total Jobs Executed: <span class="text-primary">{{ monthly_jobs }}</span></p>
                        <div class="mb-2 small text-muted bg-light p-2 rounded border">
                            <div>CM (Corrective): <strong class="text-dark">{{ monthly_cm }}</strong></div>
                            <div>PM (Preventive): <strong class="text-dark">{{ monthly_pm }}</strong></div>
                            <div>Inspection & Check: <strong class="text-dark">{{ monthly_insp }}</strong></div>
                        </div>
                        <p class="fw-bold mb-2 text-primary">Total Effective Work Time: {{ "%.1f"|format(monthly_hours) }} hrs</p>
                        <hr class="my-2">
                        <div class="row small text-muted">
                            <div class="col-6">Spare Qty: <strong>{{ monthly_spare_qty }} Pcs</strong></div>
                            <div class="col-6">Spare Cost: <strong>ETB {{ "%.2f"|format(monthly_spare_cost) }}</strong></div>
                            <div class="col-6">Lubricants: <strong>{{ "%.1f"|format(monthly_lube_vol) }} L</strong></div>
                            <div class="col-6">Lube Cost: <strong>ETB {{ "%.2f"|format(monthly_lube_cost) }}</strong></div>
                        </div>
                        <div class="mt-2 pt-2 border-top fw-bold text-success">
                            Total Expenditure: ETB {{ "%.2f"|format(monthly_total_exp) }}
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Maintenance Execution & Work Time Log with Date Filter -->
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center py-2 flex-wrap gap-2">
                <h5 class="mb-0 fs-6">Maintenance Execution & Work Time Log</h5>
                <a href="/export/maintenance_execution" class="btn btn-light btn-sm text-dark fw-bold py-0" style="font-size: 11px;">📥 Export Execution Log</a>
            </div>
            <div class="card-body p-3">
                <!-- From Date to To Date Filter Form -->
                <form method="GET" action="/dashboard" class="row g-2 align-items-center mb-3 bg-light p-2 rounded border">
                    <div class="col-md-auto">
                        <label class="form-label mb-0 fw-bold fs-7">From Date:</label>
                        <input type="date" name="from_date" class="form-control form-control-sm" value="{{ request.args.get('from_date', '') }}">
                    </div>
                    <div class="col-md-auto">
                        <label class="form-label mb-0 fw-bold fs-7">To Date:</label>
                        <input type="date" name="to_date" class="form-control form-control-sm" value="{{ request.args.get('to_date', '') }}">
                    </div>
                    <div class="col-md-auto d-flex align-items-end gap-1 mt-2 mt-md-0">
                        <button type="submit" class="btn btn-primary btn-sm fw-bold">🔍 Filter</button>
                        <a href="/dashboard" class="btn btn-outline-secondary btn-sm fw-bold">Reset</a>
                    </div>
                </form>

                <div class="table-responsive">
                    <table class="table table-bordered table-hover align-middle mb-0 small">
                        <thead class="table-secondary">
                            <tr>
                                <th>S/N</th>
                                <th>WO No</th>
                                <th>Vehicle Model & Plate</th>
                                <th>Next Due</th>
                                <th>Maintenance Type</th>
                                <th>Replaced Spare Parts & Qty</th>
                                <th>Spare Cost (ETB)</th>
                                <th>Total Cost (ETB)</th>
                                <th style="text-align: center;">Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for wo in work_orders %}
                            <tr>
                                <td>{{ wo.serial_number }}</td>
                                <td>{{ wo.work_order_no }}</td>
                                <td>{{ wo.vehicle_model }} ({{ wo.vehicle_plate }})</td>
                                <td class="fw-bold text-danger">{{ wo.next_due_reading }} {{ wo.reading_unit }}</td>
                                <td><span class="badge bg-info text-dark">{{ wo.maintenance_type }}</span></td>
                                <td class="fw-bold text-primary">{{ wo.replaced_spare_name }}</td>
                                <td>{{ "%.2f"|format(wo.spare_parts_cost) }}</td>
                                <td class="fw-bold text-success">{{ "%.2f"|format(wo.total_expenditure) }} ETB</td>
                                <td class="text-center">
                                    <form method="POST" action="/delete_work_order/{{ wo.id }}" onsubmit="return confirm('Are you sure you want to delete this work order?');" style="margin: 0;">
                                        <button type="submit" class="btn btn-danger btn-sm py-0 px-1" style="font-size: 11px;">Remove</button>
                                    </form>
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="9" class="text-center text-muted">No records found for the selected date range.</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    {{ shared_modal | safe }}

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

INVENTORY_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SteelY R.M.I - Store Inventory</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background-color: #f4f6f9; }
        .main-layout-container { margin-left: 240px; padding: 20px; max-width: calc(100% - 240px); transition: all 0.3s ease; }
        .sidebar-space { position: fixed; top: 0; left: 0; width: 220px; height: 100%; background: #212529; color: white; padding: 20px; z-index: 1000; }
        @media (max-width: 992px) {
            .main-layout-container { margin-left: 0; max-width: 100%; }
            .sidebar-space { display: none; }
        }
    </style>
</head>
<body>
    <div class="sidebar-space d-none d-lg-block">
        <h5 class="text-primary fw-bold mb-4">SteelY Garage</h5>
        <ul class="nav flex-column gap-2">
            <li class="nav-item"><a href="/dashboard" class="nav-link text-white">🏠 Dashboard</a></li>
            <li class="nav-item"><a href="/inventory" class="nav-link text-white active bg-primary rounded">📦 Store Inventory</a></li>
            <li class="nav-item"><a href="#" class="nav-link text-success fw-bold" data-bs-toggle="modal" data-bs-target="#addWorkOrderModal">➕ Create New Work Order</a></li>
            <li class="nav-item"><a href="/export/master_report" class="nav-link text-white">📊 All-In-One-Master Report to Excel</a></li>
            <li class="nav-item"><a href="/export/maintenance_execution" class="nav-link text-white">📥 Execution Log</a></li>
            <li class="nav-item mt-5"><a href="/logout" class="nav-link text-danger">🚪 Logout</a></li>
        </ul>
    </div>

    <div class="main-layout-container">
        <div class="card shadow-sm p-3 mb-3 bg-white">
            <div class="row align-items-center">
                <div class="col-md-6">
                    <h4 class="text-primary fw-bold mb-0">Store Spare Inventory Management</h4>
                    <small class="text-muted">Manage all workshop spare parts and stock levels</small>
                </div>
                <div class="col-md-6 text-md-end">
                    <button class="btn btn-dark btn-sm fw-bold" data-bs-toggle="modal" data-bs-target="#addSpareModal">+ Add New Spare Items (Multi-Row)</button>
                    <a href="/dashboard" class="btn btn-secondary btn-sm fw-bold">← Back to Dashboard</a>
                </div>
            </div>
        </div>

        <div class="card shadow-sm mb-4">
            <div class="card-header bg-secondary text-white py-2">
                <h5 class="mb-0 fs-6">Complete Store Spare Inventory</h5>
            </div>
            <div class="card-body p-3">
                <div class="table-responsive">
                    <table class="table table-bordered table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th>ID</th>
                                <th>Part Name</th>
                                <th>Specification (Spec)</th>
                                <th>Available Quantity</th>
                                <th>Unit Cost (ETB)</th>
                                <th>Location</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in inventory_items %}
                            <tr>
                                <td>{{ item.id }}</td>
                                <td class="fw-bold">{{ item.part_name }}</td>
                                <td>{{ item.spec }}</td>
                                <td>
                                    <span class="badge {% if item.quantity < 5 %}bg-danger{% else %}bg-success{% endif %} fs-6">
                                        {{ item.quantity }} Pcs
                                    </span>
                                </td>
                                <td>{{ "%.2f"|format(item.unit_cost) }} ETB</td>
                                <td>{{ item.location }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>

    <div class="modal fade" id="addSpareModal" tabindex="-1">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <form method="POST" action="/add_spare_multiple">
                    <div class="modal-header bg-dark text-white">
                        <h5 class="modal-title">Add Multiple Store Spare Items</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="table-responsive">
                            <table class="table table-bordered align-middle" id="spareTable">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Part Name</th>
                                        <th>Specification (Spec)</th>
                                        <th>Quantity</th>
                                        <th>Unit Cost (ETB)</th>
                                        <th>Location</th>
                                        <th style="width: 80px; text-align: center;">Action</th>
                                    </tr>
                                </thead>
                                <tbody id="spareTableBody">
                                    <tr>
                                        <td><input type="text" class="form-control" name="part_name[]" required placeholder="e.g. Bearing"></td>
                                        <td><input type="text" class="form-control" name="spec[]" required placeholder="e.g. 6204ZZ"></td>
                                        <td><input type="number" class="form-control" name="quantity[]" required min="1" value="10"></td>
                                        <td><input type="number" step="0.01" class="form-control" name="unit_cost[]" required min="0" value="0.00"></td>
                                        <td><input type="text" class="form-control" name="location[]" required value="Main Store"></td>
                                        <td class="text-center">
                                            <button type="button" class="btn btn-danger btn-sm" onclick="removeRow(this)">X</button>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        <button type="button" class="btn btn-success btn-sm fw-bold mt-2" onclick="addRow()">+ Add Another Row</button>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="submit" class="btn btn-dark fw-bold">Save All Inventory Items</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    {{ shared_modal | safe }}

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function addRow() {
            let tbody = document.getElementById('spareTableBody');
            let newRow = document.createElement('tr');
            newRow.innerHTML = `
                <td><input type="text" class="form-control" name="part_name[]" required placeholder="e.g. Bearing"></td>
                <td><input type="text" class="form-control" name="spec[]" required placeholder="e.g. 6204ZZ"></td>
                <td><input type="number" class="form-control" name="quantity[]" required min="1" value="10"></td>
                <td><input type="number" step="0.01" class="form-control" name="unit_cost[]" required min="0" value="0.00"></td>
                <td><input type="text" class="form-control" name="location[]" required value="Main Store"></td>
                <td class="text-center">
                    <button type="button" class="btn btn-danger btn-sm" onclick="removeRow(this)">X</button>
                </td>
            `;
            tbody.appendChild(newRow);
        }

        function removeRow(btn) {
            let tbody = document.getElementById('spareTableBody');
            if (tbody.rows.length > 1) {
                let row = btn.closest('tr');
                row.remove();
            } else {
                alert('At least one row is required!');
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'steely2026':
            session.clear()
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            error = 'Invalid username or password!'
    return render_template_string(LOGIN_HTML, error=error)

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    work_orders_query = WorkOrder.query

    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')

    if from_date and to_date:
        work_orders_query = work_orders_query.filter(
            WorkOrder.start_datetime >= f"{from_date}T00:00",
            WorkOrder.start_datetime <= f"{to_date}T23:59"
        )
    elif from_date:
        work_orders_query = work_orders_query.filter(
            WorkOrder.start_datetime >= f"{from_date}T00:00"
        )
    elif to_date:
        work_orders_query = work_orders_query.filter(
            WorkOrder.start_datetime <= f"{to_date}T23:59"
        )

    work_orders = work_orders_query.all()
    
    now = datetime.now()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    weekly_jobs = weekly_hours = weekly_spare_qty = weekly_spare_cost = 0.0
    weekly_lube_vol = weekly_lube_cost = weekly_total_exp = 0.0
    weekly_cm = weekly_pm = weekly_insp = 0

    monthly_jobs = monthly_hours = monthly_spare_qty = monthly_spare_cost = 0.0
    monthly_lube_vol = monthly_lube_cost = monthly_total_exp = 0.0
    monthly_cm = monthly_pm = monthly_insp = 0

    all_orders = WorkOrder.query.all()
    for wo in all_orders:
        try:
            wo_date = datetime.strptime(wo.start_datetime, '%Y-%m-%dT%H:%M')
        except:
            wo_date = now

        m_type = str(wo.maintenance_type).strip()

        if wo_date >= month_ago:
            monthly_jobs += 1
            monthly_hours += wo.effective_work_hours
            monthly_spare_qty += wo.spare_parts_qty
            monthly_spare_cost += wo.spare_parts_cost
            monthly_lube_vol += wo.lubricants_volume
            monthly_lube_cost += wo.lubricants_cost
            monthly_total_exp += wo.total_expenditure
            
            if m_type == 'CM':
                monthly_cm += 1
            elif m_type == 'PM':
                monthly_pm += 1
            elif m_type == 'Inspection & Check':
                monthly_insp += 1

        if wo_date >= week_ago:
            weekly_jobs += 1
            weekly_hours += wo.effective_work_hours
            weekly_spare_qty += wo.spare_parts_qty
            weekly_spare_cost += wo.spare_parts_cost
            weekly_lube_vol += wo.lubricants_volume
            weekly_lube_cost += wo.lubricants_cost
            weekly_total_exp += wo.total_expenditure

            if m_type == 'CM':
                weekly_cm += 1
            elif m_type == 'PM':
                weekly_pm += 1
            elif m_type == 'Inspection & Check':
                weekly_insp += 1

    response = make_response(render_template_string(
        DASHBOARD_HTML, 
        work_orders=work_orders, 
        weekly_jobs=int(weekly_jobs), weekly_hours=weekly_hours, weekly_spare_qty=int(weekly_spare_qty), weekly_spare_cost=weekly_spare_cost,
        weekly_lube_vol=weekly_lube_vol, weekly_lube_cost=weekly_lube_cost, weekly_total_exp=weekly_total_exp,
        weekly_cm=weekly_cm, weekly_pm=weekly_pm, weekly_insp=weekly_insp,
        monthly_jobs=int(monthly_jobs), monthly_hours=monthly_hours, monthly_spare_qty=int(monthly_spare_qty), monthly_spare_cost=monthly_spare_cost,
        monthly_lube_vol=monthly_lube_vol, monthly_lube_cost=monthly_lube_cost, monthly_total_exp=monthly_total_exp,
        monthly_cm=monthly_cm, monthly_pm=monthly_pm, monthly_insp=monthly_insp,
        shared_modal=SHARED_MODAL_HTML
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.route('/inventory')
def inventory():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    inventory_items = SpareInventory.query.all()
    response = make_response(render_template_string(
        INVENTORY_HTML, 
        inventory_items=inventory_items,
        shared_modal=SHARED_MODAL_HTML
    ))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add_spare_multiple', methods=['POST'])
def add_spare_multiple():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    part_names = request.form.getlist('part_name[]')
    specs = request.form.getlist('spec[]')
    quantities = request.form.getlist('quantity[]')
    unit_costs = request.form.getlist('unit_cost[]')
    locations = request.form.getlist('location[]')
    
    for i in range(len(part_names)):
        if part_names[i].strip():
            new_spare = SpareInventory(
                part_name=part_names[i],
                spec=specs[i],
                quantity=int(quantities[i]),
                unit_cost=float(unit_costs[i]),
                location=locations[i]
            )
            db.session.add(new_spare)
            
    db.session.commit()
    return redirect(url_for('inventory'))

@app.route('/add_work_order', methods=['POST'])
def add_work_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    serial_number = request.form.get('serial_number')
    work_order_no = request.form.get('work_order_no')
    vehicle_plate = request.form.get('vehicle_plate')
    vehicle_model = request.form.get('vehicle_model')
    current_reading = float(request.form.get('current_reading', 0.0))
    reading_unit = request.form.get('reading_unit', 'KM')
    
    increment_value = 5000.0 if reading_unit == 'KM' else 250.0
    next_due_reading = current_reading + increment_value

    job_status = request.form.get('job_status')
    driver_name = request.form.get('driver_name')
    assigned_technicians = request.form.get('assigned_technicians')
    start_datetime = request.form.get('start_datetime')
    end_datetime = request.form.get('end_datetime')
    maintenance_type = request.form.get('maintenance_type')
    work_category = request.form.get('work_category')
    description = request.form.get('description')
    
    spare_names = request.form.getlist('spare_name[]')
    spare_qtys = request.form.getlist('spare_qty[]')
    spare_unit_costs = request.form.getlist('spare_unit_cost[]')
    
    spare_summary_list = []
    total_spare_qty = 0
    total_spare_cost = 0.0
    
    for i in range(len(spare_names)):
        if spare_names[i].strip():
            q = int(spare_qtys[i]) if i < len(spare_qtys) else 1
            uc = float(spare_unit_costs[i]) if i < len(spare_unit_costs) else 0.0
            tot = q * uc
            total_spare_qty += q
            total_spare_cost += tot
            spare_summary_list.append(f"{spare_names[i]} ({q} Pcs @ {uc:.2f} = {tot:.2f} ETB)")
            
    replaced_spare_name = ", ".join(spare_summary_list) if spare_summary_list else "-"
    
    lubricants_volume = float(request.form.get('lubricants_volume', 0.0))
    lubricants_cost = float(request.form.get('lubricants_cost', 0.0))
    batteries_cost = float(request.form.get('batteries_cost', 0.0))
    tires_cost = float(request.form.get('tires_cost', 0.0))
    
    effective_hours = 0.0
    try:
        s_dt = datetime.strptime(start_datetime, '%Y-%m-%dT%H:%M')
        e_dt = datetime.strptime(end_datetime, '%Y-%m-%dT%H:%M')
        diff = (e_dt - s_dt).total_seconds() / 3600.0
        effective_hours = max(0.0, diff)
    except:
        effective_hours = 2.0

    total_expenditure = total_spare_cost + lubricants_cost + batteries_cost + tires_cost
    
    new_wo = WorkOrder(
        serial_number=serial_number,
        work_order_no=work_order_no,
        vehicle_plate=vehicle_plate,
        vehicle_model=vehicle_model,
        current_reading=current_reading,
        reading_unit=reading_unit,
        next_due_reading=next_due_reading,
        job_status=job_status,
        driver_name=driver_name,
        assigned_technicians=assigned_technicians,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        maintenance_type=maintenance_type,
        work_category=work_category,
        description=description,
        replaced_spare_name=replaced_spare_name,
        spare_parts_qty=total_spare_qty,
        spare_parts_cost=total_spare_cost,
        lubricants_volume=lubricants_volume,
        lubricants_cost=lubricants_cost,
        batteries_cost=batteries_cost,
        tires_cost=tires_cost,
        effective_work_hours=effective_hours,
        total_expenditure=total_expenditure
    )
    db.session.add(new_wo)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/delete_work_order/<int:wo_id>', methods=['POST'])
def delete_work_order(wo_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    wo = WorkOrder.query.get_or_404(wo_id)
    db.session.delete(wo)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/export/weekly_report')
def export_weekly_report():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        work_orders = WorkOrder.query.all()
        
        data = []
        for wo in work_orders:
            try:
                wo_date = datetime.strptime(wo.start_datetime, '%Y-%m-%dT%H:%M')
            except:
                wo_date = now

            if wo_date >= week_ago:
                data.append({
                    'Serial Number': wo.serial_number,
                    'Work Order No': wo.work_order_no,
                    'Vehicle Plate': wo.vehicle_plate,
                    'Vehicle Model': wo.vehicle_model,
                    'Job Status': wo.job_status,
                    'Maintenance Type': wo.maintenance_type,
                    'Work Category': wo.work_category,
                    'Start Time': wo.start_datetime,
                    'Replaced Spare Parts': wo.replaced_spare_name,
                    'Total Spare Qty': wo.spare_parts_qty,
                    'Spare Cost (ETB)': wo.spare_parts_cost,
                    'Total Expenditure (ETB)': wo.total_expenditure
                })
                
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='weekly summary report')
        output.seek(0)

        resp = make_response(output.read())
        resp.headers["Content-Disposition"] = "attachment; filename=SteelY_RMI_Weekly_Summary_Report.xlsx"
        resp.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return resp
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/export/monthly_report')
def export_monthly_report():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        now = datetime.now()
        month_ago = now - timedelta(days=30)
        work_orders = WorkOrder.query.all()
        
        data = []
        for wo in work_orders:
            try:
                wo_date = datetime.strptime(wo.start_datetime, '%Y-%m-%dT%H:%M')
            except:
                wo_date = now

            if wo_date >= month_ago:
                data.append({
                    'Serial Number': wo.serial_number,
                    'Work Order No': wo.work_order_no,
                    'Vehicle Plate': wo.vehicle_plate,
                    'Vehicle Model': wo.vehicle_model,
                    'Job Status': wo.job_status,
                    'Maintenance Type': wo.maintenance_type,
                    'Work Category': wo.work_category,
                    'Start Time': wo.start_datetime,
                    'Replaced Spare Parts': wo.replaced_spare_name,
                    'Total Spare Qty': wo.spare_parts_qty,
                    'Spare Cost (ETB)': wo.spare_parts_cost,
                    'Total Expenditure (ETB)': wo.total_expenditure
                })
                
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='monthly summary report')
        output.seek(0)

        resp = make_response(output.read())
        resp.headers["Content-Disposition"] = "attachment; filename=SteelY_RMI_Monthly_Summary_Report.xlsx"
        resp.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return resp
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/export/master_report')
def export_master_report():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        now = datetime.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        work_orders = WorkOrder.query.all()
        inventory_items = SpareInventory.query.all()
        
        # 1. Weekly Summary Data
        weekly_data = []
        for wo in work_orders:
            try:
                wo_date = datetime.strptime(wo.start_datetime, '%Y-%m-%dT%H:%M')
            except:
                wo_date = now
            if wo_date >= week_ago:
                weekly_data.append({
                    'Serial Number': wo.serial_number,
                    'Work Order No': wo.work_order_no,
                    'Vehicle Plate': wo.vehicle_plate,
                    'Vehicle Model': wo.vehicle_model,
                    'Job Status': wo.job_status,
                    'Maintenance Type': wo.maintenance_type,
                    'Work Category': wo.work_category,
                    'Start Time': wo.start_datetime,
                    'Replaced Spare Parts': wo.replaced_spare_name,
                    'Total Spare Qty': wo.spare_parts_qty,
                    'Spare Cost (ETB)': wo.spare_parts_cost,
                    'Total Expenditure (ETB)': wo.total_expenditure
                })
        df_weekly = pd.DataFrame(weekly_data)

        # 2. Monthly Summary Data
        monthly_data = []
        for wo in work_orders:
            try:
                wo_date = datetime.strptime(wo.start_datetime, '%Y-%m-%dT%H:%M')
            except:
                wo_date = now
            if wo_date >= month_ago:
                monthly_data.append({
                    'Serial Number': wo.serial_number,
                    'Work Order No': wo.work_order_no,
                    'Vehicle Plate': wo.vehicle_plate,
                    'Vehicle Model': wo.vehicle_model,
                    'Job Status': wo.job_status,
                    'Maintenance Type': wo.maintenance_type,
                    'Work Category': wo.work_category,
                    'Start Time': wo.start_datetime,
                    'Replaced Spare Parts': wo.replaced_spare_name,
                    'Total Spare Qty': wo.spare_parts_qty,
                    'Spare Cost (ETB)': wo.spare_parts_cost,
                    'Total Expenditure (ETB)': wo.total_expenditure
                })
        df_monthly = pd.DataFrame(monthly_data)

        # 3. Execution Log Data
        exec_data = []
        for wo in work_orders:
            exec_data.append({
                'Serial Number': wo.serial_number,
                'Work Order No': wo.work_order_no,
                'Vehicle Plate': wo.vehicle_plate,
                'Vehicle Model': wo.vehicle_model,
                'Current Reading': wo.current_reading,
                'Reading Unit': wo.reading_unit,
                'Next Due Reading': wo.next_due_reading,
                'Job Status': wo.job_status,
                'Driver Name': wo.driver_name,
                'Assigned Technicians': wo.assigned_technicians,
                'Start Time': wo.start_datetime,
                'End Time': wo.end_datetime,
                'Maintenance Type': wo.maintenance_type,
                'Work Category': wo.work_category,
                'Replaced Spare Parts': wo.replaced_spare_name,
                'Total Spare Qty': wo.spare_parts_qty,
                'Spare Cost (ETB)': wo.spare_parts_cost,
                'Lube Vol (L)': wo.lubricants_volume,
                'Lube Cost (ETB)': wo.lubricants_cost,
                'Batt Cost (ETB)': wo.batteries_cost,
                'Tire Cost (ETB)': wo.tires_cost,
                'Effective Hours (hrs)': wo.effective_work_hours,
                'Total Expenditure (ETB)': wo.total_expenditure
            })
        df_exec = pd.DataFrame(exec_data)

        # Write to Multi-Sheet Excel using Pandas & Openpyxl
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_weekly.to_excel(writer, index=False, sheet_name='weekly summary report')
            df_monthly.to_excel(writer, index=False, sheet_name='monthly summary report')
            df_exec.to_excel(writer, index=False, sheet_name='excution log')
            
        output.seek(0)
        
        response = make_response(output.read())
        response.headers["Content-Disposition"] = "attachment; filename=SteelY_RMI_All_In_One_Master_Report.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/export/maintenance_execution')
def export_maintenance_execution():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        work_orders = WorkOrder.query.all()
        data = []
        for wo in work_orders:
            data.append({
                'Serial Number': wo.serial_number,
                'Work Order No': wo.work_order_no,
                'Vehicle Plate': wo.vehicle_plate,
                'Vehicle Model': wo.vehicle_model,
                'Current Reading': wo.current_reading,
                'Reading Unit': wo.reading_unit,
                'Next Due Reading': wo.next_due_reading,
                'Job Status': wo.job_status,
                'Driver Name': wo.driver_name,
                'Assigned Technicians': wo.assigned_technicians,
                'Start Time': wo.start_datetime,
                'End Time': wo.end_datetime,
                'Maintenance Type': wo.maintenance_type,
                'Work Category': wo.work_category,
                'Replaced Spare Parts': wo.replaced_spare_name,
                'Total Spare Qty': wo.spare_parts_qty,
                'Spare Cost (ETB)': wo.spare_parts_cost,
                'Lube Vol (L)': wo.lubricants_volume,
                'Lube Cost (ETB)': wo.lubricants_cost,
                'Batt Cost (ETB)': wo.batteries_cost,
                'Tire Cost (ETB)': wo.tires_cost,
                'Effective Hours (hrs)': wo.effective_work_hours,
                'Total Expenditure (ETB)': wo.total_expenditure
            })
            
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='excution log')
        output.seek(0)

        response = make_response(output.read())
        response.headers["Content-Disposition"] = "attachment; filename=SteelY_RMI_Maintenance_Execution_Report.xlsx"
        response.headers["Content-type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        return response
    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
