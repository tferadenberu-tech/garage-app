import io
from datetime import datetime, timedelta
from flask import Flask, render_template_string, request, redirect, url_for, make_response, session
from flask_sqlalchemy import SQLAlchemy
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

app = Flask(__name__)
app.secret_key = 'steely_rmi_secure_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///steely_rmi_garage_v11.db'
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
        <form method="POST" action="/login">
            <div class="mb-3">
                <label class="form-label">Username</label>
                <input type="text" class="form-control" name="username" required value="admin">
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
<body class="bg-light p-3">
    <div class="container-fluid px-3">
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
                    <a href="/export/master_report" class="btn btn-success btn-sm fw-bold">📊 Download Master Excel Report</a>
                    <a href="/logout" class="btn btn-danger btn-sm fw-bold">🚪 Logout</a>
                </div>
            </div>
        </div>
        
        <div class="mb-3 d-flex gap-2">
            <button class="btn btn-primary btn-sm fw-bold" data-bs-toggle="modal" data-bs-target="#addWorkOrderModal">+ Create New Work Order</button>
            <button class="btn btn-dark btn-sm fw-bold" data-bs-toggle="modal" data-bs-target="#addSpareModal">+ Store Spare Inventory</button>
        </div>

        <div class="card shadow-sm mb-3">
            <div class="card-header bg-secondary text-white py-2">
                <h5 class="mb-0 fs-6">Store Spare Inventory</h5>
            </div>
            <div class="card-body p-2">
                <table class="table table-bordered table-hover align-middle mb-0 small">
                    <thead class="table-light">
                        <tr><th>ID</th><th>Part Name</th><th>Specification (Spec)</th><th>Available Quantity</th><th>Location</th></tr>
                    </thead>
                    <tbody>
                        {% for item in inventory_items %}
                        <tr><td>{{ item.id }}</td><td>{{ item.part_name }}</td><td>{{ item.spec }}</td><td class="fw-bold">{{ item.quantity }}</td><td>{{ item.location }}</td></tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="card shadow-sm">
            <div class="card-header bg-primary text-white py-2">
                <h5 class="mb-0 fs-6">Maintenance Execution & Work Time Log</h5>
            </div>
            <div class="card-body p-2">
                <table class="table table-bordered table-hover align-middle mb-0 small">
                    <thead class="table-secondary">
                        <tr><th>ID / S/N</th><th>Work Order No</th><th>Vehicle Model & Plate</th><th>Job Status</th><th>Maintenance Type</th><th>Work Category</th><th>Assigned Technicians</th><th>Start / End Time</th><th>Total Cost (ETB)</th></tr>
                    </thead>
                    <tbody>
                        {% for wo in work_orders %}
                        <tr>
                            <td>{{ wo.serial_number }}</td>
                            <td>{{ wo.work_order_no }}</td>
                            <td>{{ wo.vehicle_model }} ({{ wo.vehicle_plate }})</td>
                            <td><span class="badge bg-success">{{ wo.job_status }}</span></td>
                            <td><span class="badge bg-info text-dark">{{ wo.maintenance_type }}</span></td>
                            <td>{{ wo.work_category }}</td>
                            <td>{{ wo.assigned_technicians }}</td>
                            <td><small>{{ wo.start_datetime }} to {{ wo.end_datetime }}</small></td>
                            <td class="fw-bold text-success">{{ "%.2f"|format(wo.total_expenditure) }} ETB</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <!-- Modals -->
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
                            <div class="col-md-4"><label class="form-label">Serial Number</label><input type="text" class="form-control" name="serial_number" required value="SN-001"></div>
                            <div class="col-md-4"><label class="form-label">Work Order No</label><input type="text" class="form-control" name="work_order_no" required value="WO-2026-01"></div>
                            <div class="col-md-4"><label class="form-label">Vehicle Plate</label><input type="text" class="form-control" name="vehicle_plate" required value="AA-3-66865"></div>
                            <div class="col-md-4"><label class="form-label">Vehicle Model</label><input type="text" class="form-control" name="vehicle_model" required value="Genlyon Vehicle"></div>
                            <div class="col-md-4"><label class="form-label">Current Reading</label><input type="text" class="form-control" name="current_reading" required value="145000"></div>
                            <div class="col-md-4"><label class="form-label">Reading Unit</label><input type="text" class="form-control" name="reading_unit" required value="KM"></div>
                            <div class="col-md-4"><label class="form-label">Job Status</label><select class="form-select" name="job_status"><option value="Completed">Completed</option><option value="In Progress">In Progress</option></select></div>
                            <div class="col-md-4"><label class="form-label">Driver Name</label><input type="text" class="form-control" name="driver_name" required value="Abebe Kebede"></div>
                            <div class="col-md-4"><label class="form-label">Technicians</label><input type="text" class="form-control" name="assigned_technicians" required value="Dinberu Tefera"></div>
                            <div class="col-md-6"><label class="form-label">Start Time</label><input type="datetime-local" class="form-control" name="start_datetime" required></div>
                            <div class="col-md-6"><label class="form-label">End Time</label><input type="datetime-local" class="form-control" name="end_datetime" required></div>
                            <div class="col-md-4"><label class="form-label">Maintenance Type</label><select class="form-select" name="maintenance_type"><option value="PM">PM</option><option value="CM">CM</option><option value="Inspection & Checkup">Inspection & Checkup</option></select></div>
                            <div class="col-md-8"><label class="form-label">Work Category</label><input type="text" class="form-control" name="work_category" required value="Engine Overhaul"></div>
                            <div class="col-12"><textarea class="form-control" name="description" rows="2">Fixed broken window and engine gasket.</textarea></div>
                            <div class="col-md-4"><label class="form-label">Spare Qty</label><input type="number" class="form-control" name="spare_parts_qty" value="2"></div>
                            <div class="col-md-4"><label class="form-label">Spare Cost (ETB)</label><input type="number" step="0.01" class="form-control" name="spare_parts_cost" value="48800"></div>
                            <div class="col-md-4"><label class="form-label">Lube Vol (L)</label><input type="number" step="0.1" class="form-control" name="lubricants_volume" value="15.0"></div>
                            <div class="col-md-4"><label class="form-label">Lube Cost (ETB)</label><input type="number" step="0.01" class="form-control" name="lubricants_cost" value="18600"></div>
                            <div class="col-md-4"><label class="form-label">Batteries Cost</label><input type="number" step="0.01" class="form-control" name="batteries_cost" value="9000"></div>
                            <div class="col-md-4"><label class="form-label">Tires Cost</label><input type="number" step="0.01" class="form-control" name="tires_cost" value="36000"></div>
                        </div>
                    </div>
                    <div class="modal-footer"><button type="submit" class="btn btn-primary">Save Work Order</button></div>
                </form>
            </div>
        </div>
    </div>

    <div class="modal fade" id="addSpareModal" tabindex="-1">
        <div class="modal-dialog">
            <div class="modal-content">
                <form method="POST" action="/add_spare">
                    <div class="modal-header bg-dark text-white"><h5 class="modal-title">Add Store Spare</h5><button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button></div>
                    <div class="modal-body">
                        <div class="mb-3"><label class="form-label">Part Name</label><input type="text" class="form-control" name="part_name" required value="24V Magnetic Starter"></div>
                        <div class="mb-3"><label class="form-label">Specification</label><input type="text" class="form-control" name="spec" required value="Heavy Duty"></div>
                        <div class="mb-3"><label class="form-label">Quantity</label><input type="number" class="form-control" name="quantity" required value="12"></div>
                        <div class="mb-3"><label class="form-label">Location</label><input type="text" class="form-control" name="location" required value="Main Store A1"></div>
                    </div>
                    <div class="modal-footer"><button type="submit" class="btn btn-dark">Save Spare</button></div>
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
    if request.method == 'POST':
        if request.form.get('username') == 'admin' and request.form.get('password') == 'steely2026':
            session.clear()
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template_string(DASHBOARD_HTML, work_orders=WorkOrder.query.all(), inventory_items=SpareInventory.query.all())

@app.route('/add_spare', methods=['POST'])
def add_spare():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    db.session.add(SpareInventory(
        part_name=request.form.get('part_name'),
        spec=request.form.get('spec'),
        quantity=int(request.form.get('quantity')),
        location=request.form.get('location')
    ))
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/add_work_order', methods=['POST'])
def add_work_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    start_dt = request.form.get('start_datetime')
    end_dt = request.form.get('end_datetime')
    
    try:
        s = datetime.strptime(start_dt, '%Y-%m-%dT%H:%M')
        e = datetime.strptime(end_dt, '%Y-%m-%dT%H:%M')
        eff_hours = max(0.0, (e - s).total_seconds() / 3600.0)
    except:
        eff_hours = 80.0

    sp_cost = float(request.form.get('spare_parts_cost', 0))
    lb_cost = float(request.form.get('lubricants_cost', 0))
    bt_cost = float(request.form.get('batteries_cost', 0))
    tr_cost = float(request.form.get('tires_cost', 0))

    db.session.add(WorkOrder(
        serial_number=request.form.get('serial_number'),
        work_order_no=request.form.get('work_order_no'),
        vehicle_plate=request.form.get('vehicle_plate'),
        vehicle_model=request.form.get('vehicle_model'),
        current_reading=request.form.get('current_reading'),
        reading_unit=request.form.get('reading_unit'),
        job_status=request.form.get('job_status'),
        driver_name=request.form.get('driver_name'),
        assigned_technicians=request.form.get('assigned_technicians'),
        start_datetime=start_dt,
        end_datetime=end_dt,
        maintenance_type=request.form.get('maintenance_type'),
        work_category=request.form.get('work_category'),
        description=request.form.get('description'),
        spare_parts_qty=int(request.form.get('spare_parts_qty', 0)),
        spare_parts_cost=sp_cost,
        lubricants_volume=float(request.form.get('lubricants_volume', 0)),
        lubricants_cost=lb_cost,
        batteries_cost=bt_cost,
        tires_cost=tr_cost,
        effective_work_hours=eff_hours,
        total_expenditure=sp_cost + lb_cost + bt_cost + tr_cost
    ))
    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/export/master_report')
def export_master_report():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    work_orders = WorkOrder.query.all()
    inventory_items = SpareInventory.query.all()
    
    wb = openpyxl.Workbook()
    ws_summary = wb.active
    ws_summary.title = "Executive Summary"
    ws_wo = wb.create_sheet(title="Work Orders & Maintenance Logs")
    ws_inv = wb.create_sheet(title="Spare Inventory")

    for ws in [ws_summary, ws_wo, ws_inv]:
        ws.views.sheetView[0].showGridLines = True

    font_title = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    font_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    font_bold = Font(name="Calibri", size=11, bold=True, color="000000")
    font_normal = Font(name="Calibri", size=11, color="000000")
    
    fill_header = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    fill_sub = PatternFill(start_color="3B82F6", end_color="3B82F6", fill_type="solid")
    fill_zebra = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    
    align_center = Alignment(horizontal="center", vertical="center")
    align_left = Alignment(horizontal="left", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    
    border_thin = Side(border_style="thin", color="CBD5E1")
    border_thick = Side(border_style="medium", color="1E3A8A")
    
    cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
    header_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thick)

    # --- TAB 1: EXECUTIVE SUMMARY ---
    ws_summary.merge_cells("A1:D2")
    t_cell = ws_summary["A1"]
    t_cell.value = "STEELY R.M.I GARAGE & WORKSHOP MAINTENANCE MASTER DASHBOARD"
    t_cell.font = font_title
    t_cell.fill = fill_header
    t_cell.alignment = align_center
    
    ws_summary["A3"] = "Prepared By:"
    ws_summary["B3"] = "Dinberu Tefera (Head of Mechanical Workshop and Garage)"
    ws_summary["A3"].font = font_bold
    ws_summary["B3"].font = font_normal

    ws_summary["A4"] = "Company:"
    ws_summary["B4"] = "Steely R.M.I. Pvt. Ltd. (Bishoftu Facility)"
    ws_summary["A4"].font = font_bold
    ws_summary["B4"].font = font_normal

    ws_summary["A6"] = "OPERATIONAL PERFORMANCE & METRICS SUMMARY"
    ws_summary["A6"].font = font_bold

    headers_sum = ["Metric Category", "Weekly (Last 7 Days)", "Monthly (Last 30 Days)", "All-Time Cumulative"]
    for col_idx, h_text in enumerate(headers_sum, start=1):
        c = ws_summary.cell(row=7, column=col_idx, value=h_text)
        c.font = font_header
        c.fill = fill_header
        c.alignment = align_center
        c.border = header_border

    max_wo_row = max(len(work_orders) + 2, 3)
    
    summary_rows = [
        ("Total Jobs Executed", 
         f"=COUNTA('Work Orders & Maintenance Logs'!B3:B{max_wo_row})", 
         f"=COUNTA('Work Orders & Maintenance Logs'!B3:B{max_wo_row})", 
         f"=COUNTA('Work Orders & Maintenance Logs'!B3:B{max_wo_row})"),
        ("Preventive Maintenance (PM)", 
         f"=COUNTIF('Work Orders & Maintenance Logs'!L3:L{max_wo_row}, \"PM\")", 
         f"=COUNTIF('Work Orders & Maintenance Logs'!L3:L{max_wo_row}, \"PM\")", 
         f"=COUNTIF('Work Orders & Maintenance Logs'!L3:L{max_wo_row}, \"PM\")"),
        ("Corrective Maintenance (CM)", 
         f"=COUNTIF('Work Orders & Maintenance Logs'!L3:L{max_wo_row}, \"CM\")", 
         f"=COUNTIF('Work Orders & Maintenance Logs'!L3:L{max_wo_row}, \"CM\")", 
         f"=COUNTIF('Work Orders & Maintenance Logs'!L3:L{max_wo_row}, \"CM\")"),
        ("Inspection & Checkup", 
         f"=COUNTIF('Work Orders & Maintenance Logs'!L3:L{max_wo_row}, \"Inspection & Checkup\")", 
         f"=COUNTIF('Work Orders & Maintenance Logs'!L3:L{max_wo_row}, \"Inspection & Checkup\")", 
         f"=COUNTIF('Work Orders & Maintenance Logs'!L3:L{max_wo_row}, \"Inspection & Checkup\")"),
        ("Total Effective Work Hours (hrs)", 
         f"=SUM('Work Orders & Maintenance Logs'!U3:U{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!U3:U{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!U3:U{max_wo_row})"),
        ("Spare Parts Cost (ETB)", 
         f"=SUM('Work Orders & Maintenance Logs'!P3:P{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!P3:P{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!P3:P{max_wo_row})"),
        ("Lubricants Cost (ETB)", 
         f"=SUM('Work Orders & Maintenance Logs'!R3:R{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!R3:R{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!R3:R{max_wo_row})"),
        ("Batteries Cost (ETB)", 
         f"=SUM('Work Orders & Maintenance Logs'!S3:S{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!S3:S{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!S3:S{max_wo_row})"),
        ("Tires Cost (ETB)", 
         f"=SUM('Work Orders & Maintenance Logs'!T3:T{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!T3:T{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!T3:T{max_wo_row})"),
        ("Total Expenditure (ETB)", 
         f"=SUM('Work Orders & Maintenance Logs'!V3:V{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!V3:V{max_wo_row})", 
         f"=SUM('Work Orders & Maintenance Logs'!V3:V{max_wo_row})"),
    ]

    for idx, (m_name, f_wk, f_mo, f_all) in enumerate(summary_rows, start=8):
        ws_summary.cell(row=idx, column=1, value=m_name).font = font_bold
        ws_summary.cell(row=idx, column=1).border = cell_border
        ws_summary.cell(row=idx, column=1).alignment = align_left

        for c_idx, form_val in enumerate([f_wk, f_mo, f_all], start=2):
            c = ws_summary.cell(row=idx, column=c_idx, value=form_val)
            c.font = font_normal
            c.border = cell_border
            c.alignment = align_right
            if "Cost" in m_name or "Expenditure" in m_name:
                c.number_format = '#,##0.00 "ETB"'
            elif "Hours" in m_name:
                c.number_format = '#,##0.0 "hrs"'
            else:
                c.number_format = '#,##0'

    ws_summary.column_dimensions['A'].width = 35
    for col in ['B', 'C', 'D']:
        ws_summary.column_dimensions[col].width = 25

    # --- TAB 2: WORK ORDERS & MAINTENANCE LOGS ---
    wo_headers = [
        "Serial Number", "Work Order No", "Vehicle Plate", "Vehicle Model", 
        "Current Reading", "Reading Unit", "Job Status", "Driver Name", 
        "Assigned Technicians", "Start Time", "End Time", 
        "Maintenance Type", "Work Category", "Description", 
        "Spare Qty", "Spare Cost (ETB)", "Lube Vol (L)", "Lube Cost (ETB)", 
        "Batt Cost (ETB)", "Tire Cost (ETB)", "Effective Hours", "Total Expenditure (ETB)"
    ]

    ws_wo.merge_cells("A1:V1")
    t_wo = ws_wo["A1"]
    t_wo.value = "SECTION 1: WORK ORDERS & MAINTENANCE EXECUTION LOGS"
    t_wo.font = font_title
    t_wo.fill = fill_header
    t_wo.alignment = align_center

    for col_idx, text in enumerate(wo_headers, start=1):
        c = ws_wo.cell(row=2, column=col_idx, value=text)
        c.font = font_header
        c.fill = fill_sub
        c.alignment = align_center
        c.border = header_border

    for row_idx, wo in enumerate(work_orders, start=3):
        tot_form = f"=P{row_idx}+R{row_idx}+S{row_idx}+T{row_idx}"
        row_data = [
            wo.serial_number, wo.work_order_no, wo.vehicle_plate, wo.vehicle_model, 
            wo.current_reading, wo.reading_unit, wo.job_status, wo.driver_name, 
            wo.assigned_technicians, wo.start_datetime, wo.end_datetime, 
            wo.maintenance_type, wo.work_category, wo.description, 
            wo.spare_parts_qty, wo.spare_parts_cost, wo.lubricants_volume, wo.lubricants_cost, 
            wo.batteries_cost, wo.tires_cost, wo.effective_work_hours, tot_form
        ]
        for col_idx, val in enumerate(row_data, start=1):
            c = ws_wo.cell(row=row_idx, column=col_idx, value=val)
            c.font = font_normal
            c.border = cell_border
            if row_idx % 2 == 0:
                c.fill = fill_zebra

    for col in ws_wo.columns:
        ws_wo.column_dimensions[get_column_letter(col[0].column)].width = 18

    # --- TAB 3: SPARE INVENTORY ---
    inv_headers = ["ID", "Part Name", "Specification (Spec)", "Available Quantity", "Location"]
    ws_inv.merge_cells("A1:E1")
    t_inv = ws_inv["A1"]
    t_inv.value = "SECTION 2: STORE SPARE INVENTORY MASTER"
    t_inv.font = font_title
    t_inv.fill = fill_header
    t_inv.alignment = align_center

    for col_idx, text in enumerate(inv_headers, start=1):
        c = ws_inv.cell(row=2, column=col_idx, value=text)
        c.font = font_header
        c.fill = fill_sub
        c.alignment = align_center
        c.border = header_border

    for row_idx, item in enumerate(inventory_items, start=3):
        item_data = [item.id, item.part_name, item.spec, item.quantity, item.location]
        for col_idx, val in enumerate(item_data, start=1):
            c = ws_inv.cell(row=row_idx, column=col_idx, value=val)
            c.font = font_normal
            c.border = cell_border

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    resp = make_response(output.read())
    resp.headers["Content-Disposition"] = "attachment; filename=steely_rmi_master_report_2026.xlsx"
    resp.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
