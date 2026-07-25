import io
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steely_rmi_garage_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_model = db.Column(db.String(100), nullable=False)
    spare_part_name = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(100), nullable=False)
    quantity_used = db.Column(db.Integer, nullable=False, default=1)
    operational_interval = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(50), nullable=False)

class SpareInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    spare_part_name = db.Column(db.String(100), nullable=False)
    specification = db.Column(db.String(100), nullable=False)
    used_for = db.Column(db.String(100), nullable=False)
    stock_qty = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)

class ExtraWork(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_description = db.Column(db.String(200), nullable=False)
    vehicle_or_equipment = db.Column(db.String(100), nullable=False)
    hours_spent = db.Column(db.Float, nullable=False)
    date = db.Column(db.String(50), nullable=False)

with app.app_context():
    db.create_all()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SteelY R.M.I Garage Maintnace dash Bord</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light p-4">
    <div class="container-fluid px-4">
        <h2 class="mb-4 text-primary">SteelY R.M.I Garage Maintnace dash Bord</h2>
        
        <div class="mb-4 d-flex flex-wrap gap-2">
            <a href="/export/excel" class="btn btn-success">Export All Records to Excel</a>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addMaintenanceModal">+ Add Maintenance Record</button>
            <button class="btn btn-warning text-dark fw-bold" data-bs-toggle="modal" data-bs-target="#addExtraWorkModal">+ Add Extra Work</button>
        </div>

        <!-- Summaries Section Side-by-Side and Compact -->
        <div class="row mb-4">
            <!-- Weekly Summary -->
            <div class="col-xl-6 mb-3 mb-xl-0">
                <div class="card shadow-sm border-warning h-100">
                    <div class="card-header bg-warning text-dark d-flex justify-content-between align-items-center py-2">
                        <h6 class="mb-0 fw-bold">Weekly Summary (Last 7 Days)</h6>
                        <a href="/export/weekly" class="btn btn-dark btn-sm py-0 px-2" style="font-size: 12px;">Save Excel</a>
                    </div>
                    <div class="card-body p-2">
                        <p class="mb-1 small"><b>Total Jobs:</b> {{ weekly_records|length }}</p>
                        <div class="table-responsive">
                            <table class="table table-bordered table-sm align-middle mb-0" style="font-size: 13px;">
                                <thead class="table-secondary">
                                    <tr>
                                        <th>ID</th>
                                        <th>Model</th>
                                        <th>Spare Part Name</th>
                                        <th>Qty</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for r in weekly_records %}
                                    <tr>
                                        <td>{{ r.id }}</td>
                                        <td>{{ r.vehicle_model }}</td>
                                        <td>{{ r.spare_part_name }}</td>
                                        <td>{{ r.quantity_used }}</td>
                                        <td>{{ r.date }}</td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="5" class="text-center text-muted">No records found.</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Monthly Summary -->
            <div class="col-xl-6">
                <div class="card shadow-sm border-info h-100">
                    <div class="card-header bg-info text-dark d-flex justify-content-between align-items-center py-2">
                        <h6 class="mb-0 fw-bold">Monthly Summary (Last 30 Days)</h6>
                        <a href="/export/monthly" class="btn btn-dark btn-sm py-0 px-2" style="font-size: 12px;">Save Excel</a>
                    </div>
                    <div class="card-body p-2">
                        <p class="mb-1 small"><b>Total Jobs:</b> {{ monthly_records|length }}</p>
                        <div class="table-responsive">
                            <table class="table table-bordered table-sm align-middle mb-0" style="font-size: 13px;">
                                <thead class="table-secondary">
                                    <tr>
                                        <th>ID</th>
                                        <th>Model</th>
                                        <th>Spare Part Name</th>
                                        <th>Qty</th>
                                        <th>Date</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {% for r in monthly_records %}
                                    <tr>
                                        <td>{{ r.id }}</td>
                                        <td>{{ r.vehicle_model }}</td>
                                        <td>{{ r.spare_part_name }}</td>
                                        <td>{{ r.quantity_used }}</td>
                                        <td>{{ r.date }}</td>
                                    </tr>
                                    {% else %}
                                    <tr>
                                        <td colspan="5" class="text-center text-muted">No records found.</td>
                                    </tr>
                                    {% endfor %}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Inventory Overview -->
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center py-2">
                <h4 class="mb-0 fs-5">Store Spare Parts Inventory Overview</h4>
                <button class="btn btn-light btn-sm text-dark fw-bold px-3 py-1" data-bs-toggle="modal" data-bs-target="#addInventoryModal" style="font-size: 14px;">+ Add Inventory</button>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-primary text-white">
                        <tr>
                            <th>Spare Part Name</th>
                            <th>Specification</th>
                            <th>Used For / Application</th>
                            <th>Stock Qty</th>
                            <th>Unit Price (ETB)</th>
                            <th>Total Value</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in inventory_items %}
                        <tr>
                            <td>{{ item.spare_part_name }}</td>
                            <td>{{ item.specification }}</td>
                            <td>{{ item.used_for }}</td>
                            <td class="fw-bold {% if item.stock_qty < 5 %}text-danger{% else %}text-success{% endif %}">{{ item.stock_qty }} Pcs</td>
                            <td>{{ "{:,.2f}".format(item.unit_price) }}</td>
                            <td>{{ "{:,.2f}".format(item.stock_qty * item.unit_price) }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="6" class="text-center text-muted">No inventory records found. Click '+ Add Inventory' to add.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Extra Works Overview -->
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-warning text-dark d-flex justify-content-between align-items-center py-2">
                <h4 class="mb-0 fs-5">Additional / Extra Works (Non-Work Order Tasks)</h4>
                <button class="btn btn-dark btn-sm fw-bold px-3 py-1" data-bs-toggle="modal" data-bs-target="#addExtraWorkModal" style="font-size: 14px;">+ Add Extra Work</button>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID</th>
                            <th>Task Description</th>
                            <th>Vehicle / Equipment</th>
                            <th>Hours Spent (hrs)</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for ew in extra_works %}
                        <tr>
                            <td>{{ ew.id }}</td>
                            <td>{{ ew.task_description }}</td>
                            <td>{{ ew.vehicle_or_equipment }}</td>
                            <td>{{ ew.hours_spent }} hrs</td>
                            <td>{{ ew.date }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="text-center text-muted">No extra works recorded. Click '+ Add Extra Work' to add.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- All Records -->
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0 fs-5">All Maintenance Records</h4>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID</th>
                            <th>Vehicle Model</th>
                            <th>Spare Part Name</th>
                            <th>Specification</th>
                            <th>Qty Used</th>
                            <th>Operational Interval</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in records %}
                        <tr>
                            <td>{{ r.id }}</td>
                            <td>{{ r.vehicle_model }}</td>
                            <td>{{ r.spare_part_name }}</td>
                            <td>{{ r.spec }}</td>
                            <td>{{ r.quantity_used }}</td>
                            <td>{{ r.operational_interval }}</td>
                            <td>{{ r.date }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="7" class="text-center text-muted">No maintenance records found.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Modals -->
    <div class="modal fade" id="addInventoryModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form method="POST" action="/add_inventory">
                    <div class="modal-header bg-dark text-white">
                        <h5 class="modal-title">Add Store Spare Part Inventory</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Spare Part Name</label>
                            <input type="text" class="form-control" name="spare_part_name" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Specification</label>
                            <input type="text" class="form-control" name="specification" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Used For / Application</label>
                            <input type="text" class="form-control" name="used_for" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Stock Qty (Pcs)</label>
                            <input type="number" class="form-control" name="stock_qty" required min="1">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Unit Price (ETB)</label>
                            <input type="number" step="0.01" class="form-control" name="unit_price" required>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="submit" class="btn btn-dark">Save Inventory</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <div class="modal fade" id="addMaintenanceModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form method="POST" action="/add_maintenance">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">Add Maintenance Record</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Vehicle Model</label>
                            <input type="text" class="form-control" name="vehicle_model" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Select Spare Part</label>
                            <select class="form-select" name="spare_id" required>
                                {% for item in inventory_items %}
                                <option value="{{ item.id }}">{{ item.spare_part_name }} (Spec: {{ item.specification }}) - Stock: {{ item.stock_qty }}</option>
                                {% endfor %}
                            </select>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Quantity Used</label>
                            <input type="number" class="form-control" name="quantity_used" required min="1" value="1">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Operational Interval</label>
                            <input type="text" class="form-control" name="operational_interval" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Date</label>
                            <input type="date" class="form-control" name="date" required>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="submit" class="btn btn-primary">Save Record & Deduct Stock</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <div class="modal fade" id="addExtraWorkModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form method="POST" action="/add_extrawork">
                    <div class="modal-header bg-warning text-dark">
                        <h5 class="modal-title fw-bold">Add Additional / Extra Work</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Task Description</label>
                            <input type="text" class="form-control" name="task_description" required placeholder="e.g., Workshop welding & fabrication">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Vehicle or Equipment Name</label>
                            <input type="text" class="form-control" name="vehicle_or_equipment" required placeholder="e.g., Overhead Crane / Sino Truck">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Hours Spent (hrs)</label>
                            <input type="number" step="0.5" class="form-control" name="hours_spent" required min="0.5" value="1.0">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Date</label>
                            <input type="date" class="form-control" name="date" required>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="submit" class="btn btn-warning text-dark fw-bold">Save Extra Work</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route('/')
def index():
    records = MaintenanceRecord.query.all()
    inventory_items = SpareInventory.query.all()
    extra_works = ExtraWork.query.all()
    weekly_cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    monthly_cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    weekly_records = MaintenanceRecord.query.filter(MaintenanceRecord.date >= weekly_cutoff).all()
    monthly_records = MaintenanceRecord.query.filter(MaintenanceRecord.date >= monthly_cutoff).all()
    return render_template_string(DASHBOARD_HTML, records=records, inventory_items=inventory_items, extra_works=extra_works, weekly_records=weekly_records, monthly_records=monthly_records)

@app.route('/add_inventory', methods=['POST'])
def add_inventory():
    spare_part_name = request.form.get('spare_part_name')
    specification = request.form.get('specification')
    used_for = request.form.get('used_for')
    stock_qty = int(request.form.get('stock_qty'))
    unit_price = float(request.form.get('unit_price'))
    new_item = SpareInventory(spare_part_name=spare_part_name, specification=specification, used_for=used_for, stock_qty=stock_qty, unit_price=unit_price)
    db.session.add(new_item)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/add_maintenance', methods=['POST'])
def add_maintenance():
    vehicle_model = request.form.get('vehicle_model')
    spare_id = int(request.form.get('spare_id'))
    quantity_used = int(request.form.get('quantity_used'))
    operational_interval = request.form.get('operational_interval')
    date = request.form.get('date')
    spare_item = SpareInventory.query.get(spare_id)
    if spare_item:
        if spare_item.stock_qty >= quantity_used:
            spare_item.stock_qty -= quantity_used
            new_record = MaintenanceRecord(vehicle_model=vehicle_model, spare_part_name=spare_item.spare_part_name, spec=spare_item.specification, quantity_used=quantity_used, operational_interval=operational_interval, date=date)
            db.session.add(new_record)
            db.session.commit()
        else:
            return "Error: Not enough quantity in stock!", 400
    return redirect(url_for('index'))

@app.route('/add_extrawork', methods=['POST'])
def add_extrawork():
    task_description = request.form.get('task_description')
    vehicle_or_equipment = request.form.get('vehicle_or_equipment')
    hours_spent = float(request.form.get('hours_spent'))
    date = request.form.get('date')
    new_extrawork = ExtraWork(task_description=task_description, vehicle_or_equipment=vehicle_or_equipment, hours_spent=hours_spent, date=date)
    db.session.add(new_extrawork)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/export/excel')
def export_excel():
    # Excel ፋይል ሲወርድ ዋናዎቹን ሜንቴናሶች እና ተጨማሪ ስራዎችን (Extra Works) በሁለት የተለዩ ሸቶች (Sheets) አብሮ እንዲያወርድ አድርገነዋል
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Maintenance Records
        m_data = [{'ID': r.id, 'Vehicle Model': r.vehicle_model, 'Spare Part Name': r.spare_part_name, 'Specification': r.spec, 'Quantity Used': r.quantity_used, 'Operational Interval': r.operational_interval, 'Date': r.date} for r in MaintenanceRecord.query.all()]
        pd.DataFrame(m_data).to_excel(writer, index=False, sheet_name='Maintenance Records')
        
        # Sheet 2: Extra Works
        e_data = [{'ID': ew.id, 'Task Description': ew.task_description, 'Vehicle / Equipment': ew.vehicle_or_equipment, 'Hours Spent (hrs)': ew.hours_spent, 'Date': ew.date} for ew in ExtraWork.query.all()]
        pd.DataFrame(e_data).to_excel(writer, index=False, sheet_name='Extra Works')
        
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='SteelY_RMI_Garage_Full_Report.xlsx')

@app.route('/export/weekly')
def export_weekly():
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    records = MaintenanceRecord.query.filter(MaintenanceRecord.date >= cutoff).all()
    data = [{'ID': r.id, 'Vehicle Model': r.vehicle_model, 'Spare Part Name': r.spare_part_name, 'Specification': r.spec, 'Quantity Used': r.quantity_used, 'Operational Interval': r.operational_interval, 'Date': r.date} for r in records]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Weekly Maintenance')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='SteelY_RMI_Garage_Weekly_Report.xlsx')

@app.route('/export/monthly')
def export_monthly():
    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    records = MaintenanceRecord.query.filter(MaintenanceRecord.date >= cutoff).all()
    data = [{'ID': r.id, 'Vehicle Model': r.vehicle_model, 'Spare Part Name': r.spare_part_name, 'Specification': r.spec, 'Quantity Used': r.quantity_used, 'Operational Interval': r.operational_interval, 'Date': r.date} for r in records]
    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Monthly Maintenance')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='SteelY_RMI_Garage_Monthly_Report.xlsx')

if __name__ == '__main__':
    app.run(debug=True, port=5002)
