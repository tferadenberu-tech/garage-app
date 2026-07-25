import io
import pandas as pd
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steely_rmi_garage.db'
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
    part_name = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    location = db.Column(db.String(100), nullable=False)

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
    <div class="container">
        <h2 class="mb-4 text-primary">SteelY R.M.I Garage Maintnace dash Bord</h2>
        
        <!-- General Action Buttons -->
        <div class="mb-4 d-flex flex-wrap gap-2">
            <a href="/export/excel" class="btn btn-success">Export All Records to Excel</a>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addMaintenanceModal">+ Add Maintenance Record</button>
        </div>

        <!-- 2. Store Spare Inventory + Add Button Section -->
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                <h4 class="mb-0">Store Spare Inventory</h4>
                <button class="btn btn-light btn-sm text-dark fw-bold" data-bs-toggle="modal" data-bs-target="#addSpareModal">+ Add Store Spare Inventory</button>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID</th>
                            <th>Part Name</th>
                            <th>Specification (Spec)</th>
                            <th>Available Quantity</th>
                            <th>Location</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in inventory_items %}
                        <tr>
                            <td>{{ item.id }}</td>
                            <td>{{ item.part_name }}</td>
                            <td>{{ item.spec }}</td>
                            <td class="fw-bold {% if item.quantity < 5 %}text-danger{% else %}text-success{% endif %}">{{ item.quantity }}</td>
                            <td>{{ item.location }}</td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="5" class="text-center text-muted">No spare parts found in store. Please click '+ Add Store Spare Inventory' to add.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 1. Weekly Summary (Last 7 Days) with Dedicated Save Report Excel Button -->
        <div class="card shadow-sm mb-4 border-warning">
            <div class="card-header bg-warning text-dark d-flex justify-content-between align-items-center">
                <h4 class="mb-0">Weekly Summary (Last 7 Days)</h4>
                <a href="/export/weekly" class="btn btn-dark btn-sm fw-bold">Save Report Excel</a>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID</th>
                            <th>Vehicle Model</th>
                            <th>Spare Part Name</th>
                            <th>Specification (Spec)</th>
                            <th>Qty Used</th>
                            <th>Operational Interval</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in weekly_records %}
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
                            <td colspan="7" class="text-center text-muted">No maintenance records found for the last 7 days.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- 1. Monthly Summary (Last 30 Days) with Dedicated Save Report Excel Button -->
        <div class="card shadow-sm mb-4 border-info">
            <div class="card-header bg-info text-dark d-flex justify-content-between align-items-center">
                <h4 class="mb-0">Monthly Summary (Last 30 Days)</h4>
                <a href="/export/monthly" class="btn btn-dark btn-sm fw-bold">Save Report Excel</a>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID</th>
                            <th>Vehicle Model</th>
                            <th>Spare Part Name</th>
                            <th>Specification (Spec)</th>
                            <th>Qty Used</th>
                            <th>Operational Interval</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for r in monthly_records %}
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
                            <td colspan="7" class="text-center text-muted">No maintenance records found for the last 30 days.</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- All Maintenance Records Section -->
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0">All Maintenance Records</h4>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID</th>
                            <th>Vehicle Model</th>
                            <th>Spare Part Name</th>
                            <th>Specification (Spec)</th>
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
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Modal for Adding Spare Inventory -->
    <div class="modal fade" id="addSpareModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form method="POST" action="/add_spare">
                    <div class="modal-header">
                        <h5 class="modal-title">Add Store Spare Inventory</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Part Name</label>
                            <input type="text" class="form-control" name="part_name" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Specification (Spec)</label>
                            <input type="text" class="form-control" name="spec" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Quantity</label>
                            <input type="number" class="form-control" name="quantity" required min="1">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Location</label>
                            <input type="text" class="form-control" name="location" required>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="submit" class="btn btn-primary">Save Spare</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Modal for Adding Maintenance Record -->
    <div class="modal fade" id="addMaintenanceModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form method="POST" action="/add_maintenance">
                    <div class="modal-header">
                        <h5 class="modal-title">Add Maintenance Record</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Vehicle Model</label>
                            <input type="text" class="form-control" name="vehicle_model" required>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Select Spare Part (from Store)</label>
                            <select class="form-select" name="spare_id" required>
                                {% for item in inventory_items %}
                                <option value="{{ item.id }}">{{ item.part_name }} (Spec: {{ item.spec }}) - Available: {{ item.quantity }}</option>
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
                        <button type="submit" class="btn btn-primary">Save Record & Deduct Spare</button>
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
    
    weekly_cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    monthly_cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    weekly_records = MaintenanceRecord.query.filter(MaintenanceRecord.date >= weekly_cutoff).all()
    monthly_records = MaintenanceRecord.query.filter(MaintenanceRecord.date >= monthly_cutoff).all()
    
    return render_template_string(
        DASHBOARD_HTML, 
        records=records, 
        inventory_items=inventory_items,
        weekly_records=weekly_records,
        monthly_records=monthly_records
    )

@app.route('/add_spare', methods=['POST'])
def add_spare():
    part_name = request.form.get('part_name')
    spec = request.form.get('spec')
    quantity = int(request.form.get('quantity'))
    location = request.form.get('location')
    
    new_spare = SpareInventory(part_name=part_name, spec=spec, quantity=quantity, location=location)
    db.session.add(new_spare)
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
        if spare_item.quantity >= quantity_used:
            spare_item.quantity -= quantity_used
            
            new_record = MaintenanceRecord(
                vehicle_model=vehicle_model,
                spare_part_name=spare_item.part_name,
                spec=spare_item.spec,
                quantity_used=quantity_used,
                operational_interval=operational_interval,
                date=date
            )
            db.session.add(new_record)
            db.session.commit()
        else:
            return "Error: Not enough quantity in store for this spare part!", 400
            
    return redirect(url_for('index'))

@app.route('/export/excel')
def export_excel():
    return generate_report_excel(MaintenanceRecord.query.all(), 'SteelY_RMI_Garage_Report_All.xlsx')

@app.route('/export/weekly')
def export_weekly():
    cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    records = MaintenanceRecord.query.filter(MaintenanceRecord.date >= cutoff).all()
    return generate_report_excel(records, 'SteelY_RMI_Garage_Weekly_Report.xlsx')

@app.route('/export/monthly')
def export_monthly():
    cutoff = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    records = MaintenanceRecord.query.filter(MaintenanceRecord.date >= cutoff).all()
    return generate_report_excel(records, 'SteelY_RMI_Garage_Monthly_Report.xlsx')

def generate_report_excel(records, filename):
    try:
        data = []
        for r in records:
            data.append({
                'ID': r.id,
                'Vehicle Model': r.vehicle_model,
                'Spare Part Name': r.spare_part_name,
                'Specification (Spec)': r.spec,
                'Quantity Used': r.quantity_used,
                'Operational Interval': r.operational_interval,
                'Date': r.date
            })
            
        df = pd.DataFrame(data)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Garage Report')
        output.seek(0)
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return f"Error generating Excel file: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
