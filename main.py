import io
import csv
from flask import Flask, render_template_string, request, redirect, url_for, make_response, session
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = 'steely_rmi_secure_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steely_rmi_garage_v8.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    serial_number = db.Column(db.String(50), nullable=False)
    work_order_no = db.Column(db.String(50), nullable=False)
    vehicle_plate = db.Column(db.String(50), nullable=False)
    vehicle_model = db.Column(db.String(100), nullable=False)
    current_reading = db.Column(db.String(50), nullable=False)
    reading_unit = db.Column(db.String(20), nullable=False)
    job_status = db.Column(db.String(50), nullable=False)
    driver_name = db.Column(db.String(100), nullable=False)
    assigned_technicians = db.Column(db.String(200), nullable=False)
    start_datetime = db.Column(db.String(50), nullable=False)
    end_datetime = db.Column(db.String(50), nullable=False)
    maintenance_type = db.Column(db.String(50), nullable=False) 
    work_category = db.Column(db.String(100), nullable=False) 
    description = db.Column(db.Text, nullable=True)
    spare_parts_info = db.Column(db.Text, nullable=True)
    total_expenditure = db.Column(db.Float, nullable=False, default=0.0)

class SpareInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_name = db.Column(db.String(100), nullable=False)
    spec = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
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
        <div class="d-flex justify-content-between align-items-center mb-4">
            <h2 class="text-primary fw-bold mb-0">SteelY R.M.I Garage Maintnace dash Bord</h2>
            <a href="/logout" class="btn btn-outline-danger fw-bold">🚪 Logout</a>
        </div>
        
        <div class="mb-4 d-flex gap-2">
            <a href="/export/excel" class="btn btn-success">📊 Export Master Excel Report</a>
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#addWorkOrderModal">+ Create New Work Order</button>
            <button class="btn btn-dark" data-bs-toggle="modal" data-bs-target="#addSpareModal">+ Store Spare Inventory</button>
        </div>

        <!-- Store Spare Inventory Section -->
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-secondary text-white">
                <h4 class="mb-0 fs-5">Store Spare Inventory</h4>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-light">
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
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Work Orders / Execution & Log Section -->
        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white">
                <h4 class="mb-0 fs-5">Maintenance Execution & Work Time Log</h4>
            </div>
            <div class="card-body">
                <table class="table table-bordered table-hover align-middle">
                    <thead class="table-secondary">
                        <tr>
                            <th>ID / S/N</th>
                            <th>Work Order No</th>
                            <th>Vehicle Model & Plate</th>
                            <th>Job Status</th>
                            <th>Maintenance Type</th>
                            <th>Work Category & Description</th>
                            <th>Assigned Technicians</th>
                            <th>Start / End Time</th>
                            <th>Total Cost (ETB)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for wo in work_orders %}
                        <tr>
                            <td>{{ wo.serial_number }}</td>
                            <td>{{ wo.work_order_no }}</td>
                            <td>{{ wo.vehicle_model }} ({{ wo.vehicle_plate }})</td>
                            <td>
                                {% if wo.job_status == 'Completed' %}
                                    <span class="badge bg-success">Completed</span>
                                {% else %}
                                    <span class="badge bg-warning text-dark">{{ wo.job_status }}</span>
                                {% endif %}
                            </td>
                            <td>
                                <span class="badge bg-info text-dark">{{ wo.maintenance_type }}</span>
                            </td>
                            <td>{{ wo.work_category }}</td>
                            <td>{{ wo.assigned_technicians }}</td>
                            <td><small>{{ wo.start_datetime }} to {{ wo.end_datetime }}</small></td>
                            <td class="fw-bold text-success">{{ wo.total_expenditure }} ETB</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Modal for Adding Work Order -->
    <div class="modal fade" id="addWorkOrderModal" tabindex="-1">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <form method="POST" action="/add_work_order">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title">Create New Work Order</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="row g-3">
                            <div class="col-md-4">
                                <label class="form-label">Serial Number (S/N)</label>
                                <input type="text" class="form-control" name="serial_number" required value="SN-001">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Work Order No</label>
                                <input type="text" class="form-control" name="work_order_no" required value="WO-2026-01">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Vehicle Plate Number</label>
                                <input type="text" class="form-control" name="vehicle_plate" required placeholder="e.g. AA-3-12345">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Vehicle Type / Model</label>
                                <input type="text" class="form-control" name="vehicle_model" required placeholder="e.g. Sino Truck 371">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Current Reading</label>
                                <input type="text" class="form-control" name="current_reading" required placeholder="e.g. 125000">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Reading Unit</label>
                                <input type="text" class="form-control" name="reading_unit" required value="KM">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Job Status</label>
                                <select class="form-select" name="job_status">
                                    <option value="Completed">Completed</option>
                                    <option value="In Progress">In Progress</option>
                                    <option value="Pending">Pending</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Driver Name</label>
                                <input type="text" class="form-control" name="driver_name" required placeholder="Driver Name">
                            </div>
                            <div class="col-md-4">
                                <label class="form-label">Assigned Technicians / Mechanics</label>
                                <input type="text" class="form-control" name="assigned_technicians" required value="Ato Mihret, Dinberu Tefera">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Start Date & Time</label>
                                <input type="datetime-local" class="form-control" name="start_datetime" required>
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">End Date & Time</label>
                                <input type="datetime-local" class="form-control" name="end_datetime" required>
                            </div>
                            
                            <!-- Maintenance Type & Work Category Side-by-Side Layout -->
                            <div class="col-md-4">
                                <label class="form-label fw-bold text-danger">Maintenance Type</label>
                                <select class="form-select border-danger fw-bold text-primary" name="maintenance_type" required>
                                    <option value="CM">CM (Corrective Maintenance)</option>
                                    <option value="PM">PM (Preventive Maintenance)</option>
                                    <option value="Inspection & Check">Inspection & Check</option>
                                </select>
                            </div>

                            <div class="col-md-8">
                                <label class="form-label fw-bold">Work Category & Description</label>
                                <input type="text" class="form-control mb-1" name="work_category" required placeholder="e.g. Engine Maintenance">
                            </div>

                            <div class="col-12">
                                <textarea class="form-control" name="description" rows="2" placeholder="Detailed work description or notes..."></textarea>
                            </div>

                            <div class="col-md-6">
                                <label class="form-label">Spare Parts & Consumables Info</label>
                                <input type="text" class="form-control" name="spare_parts_info" placeholder="Spare part or lubricants used">
                            </div>
                            <div class="col-md-6">
                                <label class="form-label">Total Expenditure (ETB)</label>
                                <input type="number" step="0.01" class="form-control" name="total_expenditure" required value="0.00">
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="submit" class="btn btn-primary">Save Work Order</button>
                    </div>
                </form>
            </div>
        </div>
    </div>

    <!-- Modal for Adding Spare Inventory -->
    <div class="modal fade" id="addSpareModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form method="POST" action="/add_spare">
                    <div class="modal-header bg-dark text-white">
                        <h5 class="modal-title">Add Store Spare Inventory</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <div class="mb-3">
                            <label class="form-label">Part Name</label>
                            <input type="text" class="form-control" name="part_name" required placeholder="Part Name">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Specification (Spec)</label>
                            <input type="text" class="form-control" name="spec" required placeholder="Specification">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Quantity</label>
                            <input type="number" class="form-control" name="quantity" required min="1" value="10">
                        </div>
                        <div class="mb-3">
                            <label class="form-label">Location</label>
                            <input type="text" class="form-control" name="location" required value="Main Store">
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="submit" class="btn btn-dark">Save Spare</button>
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
    work_orders = WorkOrder.query.all()
    inventory_items = SpareInventory.query.all()
    return render_template_string(DASHBOARD_HTML, work_orders=work_orders, inventory_items=inventory_items)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/add_spare', methods=['POST'])
def add_spare():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    part_name = request.form.get('part_name')
    spec = request.form.get('spec')
    quantity = int(request.form.get('quantity'))
    location = request.form.get('location')
    
    new_spare = SpareInventory(part_name=part_name, spec=spec, quantity=quantity, location=location)
    db.session.add(new_spare)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/add_work_order', methods=['POST'])
def add_work_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    serial_number = request.form.get('serial_number')
    work_order_no = request.form.get('work_order_no')
    vehicle_plate = request.form.get('vehicle_plate')
    vehicle_model = request.form.get('vehicle_model')
    current_reading = request.form.get('current_reading')
    reading_unit = request.form.get('reading_unit')
    job_status = request.form.get('job_status')
    driver_name = request.form.get('driver_name')
    assigned_technicians = request.form.get('assigned_technicians')
    start_datetime = request.form.get('start_datetime')
    end_datetime = request.form.get('end_datetime')
    maintenance_type = request.form.get('maintenance_type')
    work_category = request.form.get('work_category')
    description = request.form.get('description')
    spare_parts_info = request.form.get('spare_parts_info')
    total_expenditure = float(request.form.get('total_expenditure', 0.0))
    
    new_wo = WorkOrder(
        serial_number=serial_number,
        work_order_no=work_order_no,
        vehicle_plate=vehicle_plate,
        vehicle_model=vehicle_model,
        current_reading=current_reading,
        reading_unit=reading_unit,
        job_status=job_status,
        driver_name=driver_name,
        assigned_technicians=assigned_technicians,
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        maintenance_type=maintenance_type,
        work_category=work_category,
        description=description,
        spare_parts_info=spare_parts_info,
        total_expenditure=total_expenditure
    )
    db.session.add(new_wo)
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/export/excel')
def export_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    try:
        work_orders = WorkOrder.query.all()
        si = io.StringIO()
        cw = csv.writer(si)
        
        cw.writerow([
            'Serial Number', 'Work Order No', 'Vehicle Plate', 'Vehicle Model', 
            'Current Reading', 'Reading Unit', 'Job Status', 'Driver Name', 
            'Assigned Technicians', 'Start Time', 'End Time', 
            'Maintenance Type', 'Work Category', 'Description', 'Spare Parts Info', 'Total Expenditure (ETB)'
        ])
        
        for wo in work_orders:
            cw.writerow([
                wo.serial_number, wo.work_order_no, wo.vehicle_plate, wo.vehicle_model, 
                wo.current_reading, wo.reading_unit, wo.job_status, wo.driver_name, 
                wo.assigned_technicians, wo.start_datetime, wo.end_datetime, 
                wo.maintenance_type, wo.work_category, wo.description, wo.spare_parts_info, wo.total_expenditure
            ])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = "attachment; filename=SteelY_RMI_Master_Report.csv"
        output.headers["Content-type"] = "text/csv"
        return output
    except Exception as e:
        return f"Error exporting report: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
