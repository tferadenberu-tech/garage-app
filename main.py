import io
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steely_rmi_garage_v3.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    work_order_no = db.Column(db.String(50), nullable=False)
    vehicle_model = db.Column(db.String(100), nullable=False)
    work_category = db.Column(db.String(50), nullable=False)  # CM, PM, Inspection
    spare_part_name = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(100), nullable=False)
    quantity_used = db.Column(db.Integer, nullable=False, default=1)
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
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addMaintenanceModal">+ Create New Work Order</button>
            <button class="btn btn-warning text-dark fw-bold" data-bs-toggle="modal" data-bs-target="#addExtraWorkModal">+ Add Extra Work</button>
        </div>

        <!-- All Records -->
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0 fs-5">Maintenance Work Orders</h4>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID</th>
                            <th>Work Order No</th>
                            <th>Vehicle Model</th>
                            <th>Work Category</th>
                            <th>Spare Part Name</th>
                            <th>Specification</th>
                            <th>Qty</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in records %}
                        <tr>
                            <td>{{ r.id }}</td>
                            <td>{{ r.work_order_no }}</td>
                            <td>{{ r.vehicle_model }}</td>
                            <td><span class="badge bg-info text-dark">{{ r.work_category }}</span></td>
                            <td>{{ r.spare_part_name }}</td>
                            <td>{{ r.spec }}</td>
                            <td>{{ r.quantity_used }}</td>
                            <td>{{ r.date }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="8" class="text-center text-muted">No maintenance records found.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Create New Work Order Modal -->
    <div class="modal fade" id="addMaintenanceModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <form method="POST" action="/add_maintenance">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">Create New Work Order</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Work Order No:</label>
                                <input type="text" class="form-control" name="work_order_no" required placeholder="e.g. WO-2026-002">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Vehicle Type / Model:</label>
                                <input type="text" class="form-control" name="vehicle_model" required placeholder="e.g. Sino Truck 371">
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Work Category (Type):</label>
                                <select class="form-select" name="work_category" required>
                                    <option value="PM">PM (Preventive Maintenance)</option>
                                    <option value="CM">CM (Corrective Maintenance)</option>
                                    <option value="Inspection">Inspection</option>
                                </select>
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Select Spare Part:</label>
                                <select class="form-select" name="spare_id" required>
                                    {% for item in inventory_items %}
                                    <option value="{{ item.id }}">{{ item.spare_part_name }} (Spec: {{ item.specification }}) - Stock: {{ item.stock_qty }}</option>
                                    {% endfor %}
                                </select>
                            </div>
                        </div>
                        <div class="row">
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Quantity Used:</label>
                                <input type="number" class="form-control" name="quantity_used" required min="1" value="1">
                            </div>
                            <div class="col-md-6 mb-3">
                                <label class="form-label">Date:</label>
                                <input type="date" class="form-control" name="date" required>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="submit" class="btn btn-primary">Save Work Order & Deduct Stock</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Add Extra Work Modal -->
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
                            <input type="text" class="form-control" name="task_description" required placeholder="e.g., Workshop welding">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Vehicle or Equipment Name</label>
                            <input type="text" class="form-control" name="vehicle_or_equipment" required placeholder="e.g., Overhead Crane">
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
    return render_template_string(DASHBOARD_HTML, records=records, inventory_items=inventory_items, extra_works=extra_works)

@app.route('/add_maintenance', methods=['POST'])
def add_maintenance():
    work_order_no = request.form.get('work_order_no')
    vehicle_model = request.form.get('vehicle_model')
    work_category = request.form.get('work_category')
    spare_id = int(request.form.get('spare_id'))
    quantity_used = int(request.form.get('quantity_used'))
    date = request.form.get('date')
    spare_item = SpareInventory.query.get(spare_id)
    if spare_item:
        if spare_item.stock_qty >= quantity_used:
            spare_item.stock_qty -= quantity_used
            new_record = MaintenanceRecord(work_order_no=work_order_no, vehicle_model=vehicle_model, work_category=work_category, spare_part_name=spare_item.spare_part_name, spec=spare_item.specification, quantity_used=quantity_used, date=date)
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
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        m_data = [{'ID': r.id, 'Work Order No': r.work_order_no, 'Vehicle Model': r.vehicle_model, 'Work Category': r.work_category, 'Spare Part Name': r.spare_part_name, 'Specification': r.spec, 'Quantity Used': r.quantity_used, 'Date': r.date} for r in MaintenanceRecord.query.all()]
        pd.DataFrame(m_data).to_excel(writer, index=False, sheet_name='Work Orders')
    output.seek(0)
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='SteelY_RMI_Garage_Report.xlsx')

if __name__ == '__main__':
    app.run(debug=True, port=5002)
