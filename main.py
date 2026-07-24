from flask import Flask, render_template_string, request, jsonify, send_file, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import pandas as pd
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'steely_garage_secure_key_2026'

DATA_FILE = 'garage_data.json'

# --- LOGIN SETUP & USER ACCOUNTS ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# የሲስተሙ ተጠቃሚዎች (ለእያንዳንዱ ሰራተኛ Username እና Password)
USERS = {
    "admin": {
        "password": generate_password_hash("admin123"),
        "role": "Manager"
    },
    "garage": {
        "password": generate_password_hash("garage123"),
        "role": "Technician"
    },
    "mihret": {
        "password": generate_password_hash("mihret123"),
        "role": "Technician"
    },
    "ibrahim": {
        "password": generate_password_hash("ibrahim123"),
        "role": "Technician"
    }
}

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    if user_id in USERS:
        return User(user_id)
    return None

# --- JSON DATA HELPERS ---
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- CALCULATE WEEKLY & MONTHLY SUMMARIES ---
def calculate_summaries(data):
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    weekly = {"total": 0, "pm": 0, "cm": 0, "inspection": 0, "parts_cost": 0}
    monthly = {"total": 0, "pm": 0, "cm": 0, "inspection": 0, "parts_cost": 0}

    for item in data:
        try:
            item_date = datetime.strptime(item.get('date', '')[:10], "%Y-%m-%d")
        except:
            continue

        work_type = item.get('work_type', '')
        cost = float(item.get('total_parts_cost', 0))

        # 7 ቀናት (Weekly)
        if item_date >= seven_days_ago:
            weekly["total"] += 1
            weekly["parts_cost"] += cost
            if "Preventive" in work_type:
                weekly["pm"] += 1
            elif "Corrective" in work_type:
                weekly["cm"] += 1
            elif "Inspection" in work_type:
                weekly["inspection"] += 1

        # 30 ቀናት (Monthly)
        if item_date >= thirty_days_ago:
            monthly["total"] += 1
            monthly["parts_cost"] += cost
            if "Preventive" in work_type:
                monthly["pm"] += 1
            elif "Corrective" in work_type:
                monthly["cm"] += 1
            elif "Inspection" in work_type:
                monthly["inspection"] += 1

    return weekly, monthly

# --- LOGIN TEMPLATE ---
LOGIN_HTML = '''
<!DOCTYPE html>
<html lang="am">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I Garage - Login</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #eef2f3; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .login-card { background: white; padding: 40px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.15); width: 340px; text-align: center; }
        .login-card h2 { margin-bottom: 4px; color: #1e293b; font-size: 22px; }
        .login-card p { color: #64748b; font-size: 13px; margin-bottom: 24px; }
        .input-group { margin-bottom: 18px; text-align: left; }
        .input-group label { display: block; margin-bottom: 6px; font-size: 13px; color: #334155; font-weight: 600; }
        .input-group input { width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; font-size: 14px; outline: none; }
        .input-group input:focus { border-color: #2563eb; }
        .btn-login { width: 100%; padding: 12px; background: #2563eb; color: white; border: none; border-radius: 6px; font-weight: bold; font-size: 15px; cursor: pointer; transition: 0.2s; }
        .btn-login:hover { background: #1d4ed8; }
        .error { background: #fee2e2; color: #dc2626; padding: 10px; border-radius: 6px; font-size: 13px; margin-bottom: 15px; border: 1px solid #fca5a5; }
    </style>
</head>
<body>
    <div class="login-card">
        <h2>SteelY R.M.I</h2>
        <p>Garage Maintenance Dashboard</p>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <div class="error">{{ messages[0] }}</div>
          {% endif %}
        {% endwith %}
        <form method="POST" action="/login">
            <div class="input-group">
                <label>Username / የተጠቃሚ ስም</label>
                <input type="text" name="username" required placeholder="የተጠቃሚ ስም">
            </div>
            <div class="input-group">
                <label>Password / ምስጢር ቁልፍ</label>
                <input type="password" name="password" required placeholder="••••••••">
            </div>
            <button type="submit" class="btn-login">Sign In / ግባ</button>
        </form>
    </div>
</body>
</html>
'''

# --- MAIN DASHBOARD TEMPLATE ---
DASHBOARD_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I Garage Maintenance Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background-color: #f8fafc; color: #334155; }
        .container { max-width: 1200px; margin: auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #f1f5f9; padding-bottom: 15px; margin-bottom: 20px; }
        .header h1 { font-size: 22px; color: #0f172a; margin: 0; }
        .user-badge { background: #e0f2fe; color: #0369a1; padding: 6px 14px; border-radius: 20px; font-weight: bold; font-size: 13px; }
        .logout-btn { background: #ef4444; color: white; padding: 6px 14px; text-decoration: none; border-radius: 6px; font-size: 13px; margin-left: 10px; font-weight: bold; }
        
        .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 20px; margin-bottom: 25px; }
        .summary-card { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 10px; padding: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
        .summary-card h3 { margin-top: 0; font-size: 15px; color: #1e293b; border-bottom: 2px solid #2563eb; padding-bottom: 8px; }
        .summary-list { list-style: none; padding: 0; margin: 12px 0; font-size: 14px; line-height: 1.8; }
        .summary-list li { display: flex; justify-content: space-between; border-bottom: 1px dashed #f1f5f9; padding: 4px 0; }
        .total-expenditure { background: #f8fafc; padding: 12px; border-radius: 8px; font-weight: bold; margin-top: 10px; text-align: right; color: #0f172a; border: 1px solid #e2e8f0; }

        .section-title { background: #f1f5f9; padding: 10px 14px; border-radius: 6px; font-weight: bold; margin-top: 25px; margin-bottom: 15px; color: #1e293b; font-size: 15px; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 15px; }
        .form-group { display: flex; flex-direction: column; }
        .form-group label { font-size: 12px; font-weight: bold; margin-bottom: 6px; color: #475569; }
        .form-group input, .form-group select, .form-group textarea { padding: 9px; border: 1px solid #cbd5e1; border-radius: 6px; font-size: 14px; }
        .full-width { grid-column: 1 / -1; }
        .btn { padding: 10px 18px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 14px; }
        .btn-primary { background: #2563eb; color: white; }
        .btn-success { background: #16a34a; color: white; text-decoration: none; display: inline-block; }
        .btn-add { background: #0284c7; color: white; padding: 6px 12px; font-size: 12px; }
        
        table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 13px; }
        table, th, td { border: 1px solid #e2e8f0; }
        th, td { padding: 10px; text-align: left; }
        th { background: #f8fafc; color: #475569; font-weight: bold; }
        .badge { padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
        .badge-completed { background: #dcfce7; color: #15803d; }
        .badge-progress { background: #fef9c3; color: #a16207; }
        .filter-box { background: #f8fafc; padding: 18px; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>SteelY R.M.I Garage Maintenance Dashboard</h1>
            <div>
                User: <span class="user-badge">👤 {{ current_user.id }}</span>
                <a href="/logout" class="logout-btn">Logout</a>
            </div>
        </div>

        <!-- EXECUTIVE SUMMARIES (WEEKLY & MONTHLY) -->
        <div class="summary-grid">
            <!-- WEEKLY SUMMARY -->
            <div class="summary-card">
                <h3>WEEKLY SUMMARY (LAST 7 DAYS)</h3>
                <ul class="summary-list">
                    <li><span>Total Jobs Executed:</span> <b>{{ weekly.total }}</b></li>
                    <li><span>• Preventive Maintenance (PM):</span> <b>{{ weekly.pm }}</b></li>
                    <li><span>• Corrective Maintenance (CM):</span> <b>{{ weekly.cm }}</b></li>
                    <li><span>• Inspection & Checkup:</span> <b>{{ weekly.inspection }}</b></li>
                </ul>
                <div class="total-expenditure">
                    Spare Parts Cost: ETB {{ "{:,.2f}".format(weekly.parts_cost) }}
                </div>
            </div>

            <!-- MONTHLY SUMMARY -->
            <div class="summary-card">
                <h3>MONTHLY SUMMARY (LAST 30 DAYS)</h3>
                <ul class="summary-list">
                    <li><span>Total Jobs Executed:</span> <b>{{ monthly.total }}</b></li>
                    <li><span>• Preventive Maintenance (PM):</span> <b>{{ monthly.pm }}</b></li>
                    <li><span>• Corrective Maintenance (CM):</span> <b>{{ monthly.cm }}</b></li>
                    <li><span>• Inspection & Checkup:</span> <b>{{ monthly.inspection }}</b></li>
                </ul>
                <div class="total-expenditure">
                    Spare Parts Cost: ETB {{ "{:,.2f}".format(monthly.parts_cost) }}
                </div>
            </div>
        </div>

        <!-- FILTER & EXPORT SECTION -->
        <div class="filter-box">
            <form method="GET" action="/" style="display: flex; gap: 15px; align-items: flex-end; flex-wrap: wrap;">
                <div class="form-group">
                    <label>From Date:</label>
                    <input type="date" name="from_date" value="{{ from_date }}">
                </div>
                <div class="form-group">
                    <label>To Date:</label>
                    <input type="date" name="to_date" value="{{ to_date }}">
                </div>
                <button type="submit" class="btn btn-primary">Filter Reports</button>
                <a href="/export?from_date={{ from_date }}&to_date={{ to_date }}" class="btn btn-success">📊 Export Filtered Excel Report</a>
            </form>
        </div>

        <!-- CREATE WORK ORDER FORM -->
        <form id="workOrderForm" action="/add_job" method="POST">
            <div class="section-title">Create New Work Order</div>
            <div class="form-grid">
                <div class="form-group">
                    <label>Serial Number (S/N):</label>
                    <input type="text" name="sn" required placeholder="e.g., SN-001">
                </div>
                <div class="form-group">
                    <label>Work Order No (W.O No):</label>
                    <input type="text" name="wo_no" required placeholder="e.g., WO-2026-001">
                </div>
                <div class="form-group">
                    <label>Vehicle Plate Number:</label>
                    <input type="text" name="plate_no" required placeholder="e.g., 3-A66865">
                </div>
                <div class="form-group">
                    <label>Vehicle Type / Model:</label>
                    <input type="text" name="model" placeholder="e.g., Jiefang, Actros">
                </div>
                <div class="form-group">
                    <label>Driver Name:</label>
                    <input type="text" name="driver" placeholder="e.g., Abebe Kebede">
                </div>
                <div class="form-group">
                    <label>Tracking Metric Type:</label>
                    <select name="metric_type" id="metric_type" onchange="calculateNextService()">
                        <option value="KM">Kilometers (KM)</option>
                        <option value="Hours">Hours</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Current Value:</label>
                    <input type="number" name="current_metric" id="current_metric" oninput="calculateNextService()" placeholder="e.g., 145000">
                </div>
                <div class="form-group">
                    <label>Next Service Target:</label>
                    <input type="text" id="next_service_display" readonly style="background: #f1f5f9;" placeholder="Auto calculated...">
                </div>
                <div class="form-group">
                    <label>Work Type / Category:</label>
                    <select name="work_type">
                        <option value="Preventive Maintenance (PM)">Preventive Maintenance (PM)</option>
                        <option value="Corrective Maintenance (CM)">Corrective Maintenance (CM)</option>
                        <option value="Inspection & Checkup">Inspection & Checkup</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Job Status / ሁኔታ:</label>
                    <select name="status">
                        <option value="Completed">Completed (ተጠናቋል)</option>
                        <option value="Under Maintenance">Under Maintenance (በጥገና ላይ)</option>
                        <option value="Waiting for Parts">Waiting for Parts (እስፔር በጥበቃ)</option>
                    </select>
                </div>
                <div class="form-group full-width">
                    <label>Assigned Technicians / Mechanics:</label>
                    <input type="text" name="technicians" placeholder="e.g., Ato Mihret, Dinberu Tefera">
                </div>
                <div class="form-group full-width">
                    <label>Primary Issue Description:</label>
                    <textarea name="description" rows="2" placeholder="Detail repair scope..."></textarea>
                </div>
            </div>

            <!-- SPARE PARTS BREAKDOWN -->
            <div class="section-title" style="display: flex; justify-content: space-between; align-items: center;">
                <span>Replaced Spare Parts Breakdown</span>
                <button type="button" class="btn btn-add" onclick="addSparePartRow()">+ Add Spare Part Item</button>
            </div>
            <table id="sparePartsTable">
                <thead>
                    <tr>
                        <th>Spare Part Name</th>
                        <th>Quantity (Pcs)</th>
                        <th>Unit Cost (ETB)</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody id="sparePartsBody">
                    <!-- Dynamic Rows -->
                </tbody>
            </table>

            <br>
            <button type="submit" class="btn btn-primary" style="width: 100%; padding: 12px;">Save Maintenance Record</button>
        </form>

        <!-- RECENT RECORDS HISTORY -->
        <div class="section-title">Recent Maintenance Records</div>
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Recorded By</th>
                    <th>W.O No</th>
                    <th>Plate No</th>
                    <th>Work Type</th>
                    <th>Parts Cost (ETB)</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {% for job in jobs[::-1][:10] %}
                <tr>
                    <td>{{ job.date }}</td>
                    <td><b>{{ job.created_by }}</b></td>
                    <td>{{ job.wo_no }}</td>
                    <td>{{ job.plate_no }}</td>
                    <td>{{ job.work_type }}</td>
                    <td>ETB {{ "{:,.2f}".format(job.total_parts_cost) }}</td>
                    <td>
                        <span class="badge {% if job.status == 'Completed' %}badge-completed{% else %}badge-progress{% endif %}">
                            {{ job.status }}
                        </span>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="7" style="text-align: center; color: #94a3b8;">No maintenance records found yet.</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

    </div>

    <script>
        function calculateNextService() {
            let type = document.getElementById('metric_type').value;
            let current = parseFloat(document.getElementById('current_metric').value) || 0;
            let display = document.getElementById('next_service_display');
            
            if (current > 0) {
                if (type === 'KM') {
                    display.value = (current + 5000) + " KM (+5,000 KM)";
                } else {
                    display.value = (current + 250) + " Hours (+250 Hrs)";
                }
            } else {
                display.value = "";
            }
        }

        function addSparePartRow() {
            let tbody = document.getElementById('sparePartsBody');
            let row = document.createElement('tr');
            row.innerHTML = `
                <td><input type="text" name="part_name[]" placeholder="Spare part name..." required style="width:95%;"></td>
                <td><input type="number" name="part_qty[]" value="1" min="1" style="width:90%;"></td>
                <td><input type="number" name="part_cost[]" value="0" step="0.01" style="width:90%;"></td>
                <td><button type="button" onclick="this.parentElement.parentElement.remove()" style="color:red; background:none; border:none; cursor:pointer;">X</button></td>
            `;
            tbody.appendChild(row);
        }
    </script>
</body>
</html>
'''

# --- ROUTES ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in USERS and check_password_hash(USERS[username]['password'], password):
            user = User(username)
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('የተሳሳተ የተጠቃሚ ስም ወይም ምስጢር ቁልፍ!')
            
    return render_template_string(LOGIN_HTML)

@app.route('/')
@login_required
def dashboard():
    data = load_data()
    weekly, monthly = calculate_summaries(data)
    from_date = request.args.get('from_date', '')
    to_date = request.args.get('to_date', '')
    return render_template_string(DASHBOARD_HTML, current_user=current_user, weekly=weekly, monthly=monthly, jobs=data, from_date=from_date, to_date=to_date)

@app.route('/add_job', methods=['POST'])
@login_required
def add_job():
    data = load_data()
    
    part_names = request.form.getlist('part_name[]')
    part_qtys = request.form.getlist('part_qty[]')
    part_costs = request.form.getlist('part_cost[]')
    
    spare_parts = []
    total_parts_cost = 0
    for name, qty, cost in zip(part_names, part_qtys, part_costs):
        if name.strip():
            c = float(cost) if cost else 0
            q = int(qty) if qty else 1
            spare_parts.append({"name": name, "qty": q, "unit_cost": c, "total": q * c})
            total_parts_cost += (q * c)

    job = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "created_by": current_user.id,
        "sn": request.form.get('sn'),
        "wo_no": request.form.get('wo_no'),
        "plate_no": request.form.get('plate_no'),
        "model": request.form.get('model'),
        "driver": request.form.get('driver'),
        "metric_type": request.form.get('metric_type'),
        "current_metric": request.form.get('current_metric'),
        "technicians": request.form.get('technicians'),
        "work_type": request.form.get('work_type'),
        "status": request.form.get('status', 'Completed'),
        "description": request.form.get('description'),
        "spare_parts": spare_parts,
        "total_parts_cost": total_parts_cost
    }
    
    data.append(job)
    save_data(data)
    return redirect(url_for('dashboard'))

@app.route('/export')
@login_required
def export_excel():
    data = load_data()
    if not data:
        return "No data available to export", 400
        
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    
    filtered_data = []
    for item in data:
        item_date = item.get('date', '')[:10]
        if from_date and item_date < from_date:
            continue
        if to_date and item_date > to_date:
            continue
        filtered_data.append(item)
        
    if not filtered_data:
        return "No records found for the selected date range.", 400

    df = pd.DataFrame(filtered_data)
    file_path = "Garage_Maintenance_Report.xlsx"
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
