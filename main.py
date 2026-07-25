import io
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steely_rmi_garage.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# የዳታቤዝ ሞዴል (Spare Inventory እና Maintenance ሪኮርዶችን ለመያዝ)
class MaintenanceRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vehicle_model = db.Column(db.String(100), nullable=False)
    spare_part_name = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(100), nullable=False)
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

# የዳሽቦርድ HTML ቴምፕሌት (ከ Add Store Spare Inventory ጋር)
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
        
        <div class="mb-4">
            <a href="/export/excel" class="btn btn-success">Export Report to Excel</a>
        </div>

        <!-- Store Spare Inventory Section -->
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-dark text-white d-flex justify-content-between align-items-center">
                <h4 class="mb-0">Store Spare Inventory</h4>
                <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#addSpareModal">+ Add Store Spare Inventory</button>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID</th>
                            <th>Part Name</th>
                            <th>Specification (Spec)</th>
                            <th>Quantity</th>
                            <th>Location</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for item in inventory_items %}
                        <tr>
                            <td>{{ item.id }}</td>
                            <td>{{ item.part_name }}</td>
                            <td>{{ item.spec }}</td>
                            <td>{{ item.quantity }}</td>
                            <td>{{ item.location }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Maintenance Records Section -->
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0">Maintenance Records</h4>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID</th>
                            <th>Vehicle Model</th>
                            <th>Spare Part Name</th>
                            <th>Specification (Spec)</th>
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
                            <input type="number" class="form-control" name="quantity" required>
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

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

@app.route('/')
def index():
    records = MaintenanceRecord.query.all()
    inventory_items = SpareInventory.query.all()
    return render_template_string(DASHBOARD_HTML, records=records, inventory_items=inventory_items)

@app.route('/add_spare', methods=['POST'])
def add_spare():
    part_name = request.form.get('part_name')
    spec = request.form.get('spec')
    quantity = request.form.get('quantity')
    location = request.form.get('location')
    
    new_spare = SpareInventory(part_name=part_name, spec=spec, quantity=quantity, location=location)
    db.session.add(new_spare)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/export/excel')
def export_excel():
    try:
        records = MaintenanceRecord.query.all()
        data = []
        for r in records:
            data.append({
                'ID': r.id,
                'Vehicle Model': r.vehicle_model,
                'Spare Part Name': r.spare_part_name,
                'Specification (Spec)': r.spec,
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
            download_name='SteelY_RMI_Garage_Report.xlsx'
        )
    except Exception as e:
        return f"Error generating Excel file: {str(e)}", 500

if __name__ == '__main__':
    app.run(debug=True)
