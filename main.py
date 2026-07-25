from flask import Flask, render_template_string, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('steely_rmi_garage.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS work_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            serial_number TEXT,
            work_order_no TEXT,
            plate_number TEXT,
            vehicle_type TEXT,
            current_reading TEXT,
            reading_unit TEXT,
            job_status TEXT,
            work_category TEXT,
            driver_name TEXT,
            technicians TEXT,
            start_date TEXT,
            end_date TEXT,
            job_description TEXT,
            parts_cost REAL,
            tires_cost REAL,
            total_expenditure REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS spare_parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_order_id INTEGER,
            part_name TEXT,
            part_number TEXT,
            quantity INTEGER,
            unit_price REAL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SteelY R.M.I Garage Maintnace dash Bord</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 1200px; margin: auto; background: #fff; padding: 25px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #1e3d59; margin-bottom: 25px; }
        .summary-box { display: flex; justify-content: space-around; background: #e8f1f5; padding: 15px; border-radius: 6px; margin-bottom: 25px; font-weight: bold; }
        fieldset { border: 1px solid #cbd5e1; border-radius: 6px; padding: 15px; margin-bottom: 20px; background: #f8fafc; }
        legend { font-weight: bold; color: #1e3d59; padding: 0 8px; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 15px; }
        .form-group { display: flex; flex-direction: column; }
        label { font-size: 13px; font-weight: bold; margin-bottom: 5px; color: #475569; }
        input, select, textarea { padding: 8px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 14px; }
        button { background-color: #0284c7; color: white; border: none; padding: 10px 20px; font-size: 15px; border-radius: 4px; cursor: pointer; font-weight: bold; }
        button:hover { background-color: #0369a1; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }
        th, td { border: 1px solid #e2e8f0; padding: 10px; text-align: left; }
        th { background-color: #1e3d59; color: white; }
        tr:nth-child(even) { background-color: #f8fafc; }
    </style>
</head>
<body>
    <div class="container">
        <h1>SteelY R.M.I Garage Maintnace dash Bord</h1>

        <div class="summary-box">
            <div>Total Work Orders: {{ total_orders }}</div>
            <div>Total Expenditure: ETB {{ "%.2f"|format(total_exp) }}</div>
        </div>

        <form method="POST" action="/add">
            <fieldset>
                <legend>Create New Work Order</legend>
                <div class="form-grid">
                    <div class="form-group">
                        <label>Serial Number (S/N):</label>
                        <input type="text" name="serial_number" required placeholder="e.g. SN-001">
                    </div>
                    <div class="form-group">
                        <label>Work Order No:</label>
                        <input type="text" name="work_order_no" required placeholder="e.g. WO-2026-001">
                    </div>
                    <div class="form-group">
                        <label>Vehicle Plate Number:</label>
                        <input type="text" name="plate_number" required placeholder="e.g. AA-3-12345">
                    </div>
                    <div class="form-group">
                        <label>Vehicle Type / Model:</label>
                        <input type="text" name="vehicle_type" required placeholder="e.g. Sino Truck 371">
                    </div>
                    <div class="form-group">
                        <label>Current Reading:</label>
                        <input type="text" name="current_reading" placeholder="e.g. 125000">
                    </div>
                    <div class="form-group">
                        <label>Reading Unit:</label>
                        <select name="reading_unit">
                            <option value="KM">KM</option>
                            <option value="Hours">Hours</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Job Status:</label>
                        <select name="job_status">
                            <option value="Pending">Pending</option>
                            <option value="In Progress">In Progress</option>
                            <option value="Completed">Completed</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Work Category:</label>
                        <select name="work_category">
                            <option value="CM">CM (Corrective Maintenance)</option>
                            <option value="PM">PM (Preventive Maintenance)</option>
                            <option value="Inspection">Inspection</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Driver Name:</label>
                        <input type="text" name="driver_name" placeholder="e.g. Ato Asefa">
                    </div>
                    <div class="form-group">
                        <label>Assigned Technicians / Mechanics:</label>
                        <input type="text" name="technicians" placeholder="e.g. Ato Mihret, Dinberu Tefera">
                    </div>
                    <div class="form-group">
                        <label>Start Date & Time:</label>
                        <input type="datetime-local" name="start_date">
                    </div>
                    <div class="form-group">
                        <label>End Date & Time:</label>
                        <input type="datetime-local" name="end_date">
                    </div>
                </div>
                <div class="form-group" style="margin-bottom: 15px;">
                    <label>Job Description & Scope:</label>
                    <textarea name="job_description" rows="3" placeholder="Describe maintenance activities performed..."></textarea>
                </div>
                <div class="form-grid">
                    <div class="form-group">
                        <label>Parts Cost (ETB):</label>
                        <input type="number" step="0.01" name="parts_cost" value="0.00">
                    </div>
                    <div class="form-group">
                        <label>Tires Cost (ETB):</label>
                        <input type="number" step="0.01" name="tires_cost" value="0.00">
                    </div>
                </div>
                <button type="submit">Save Work Order</button>
            </fieldset>
        </form>

        <h2>Recent Maintenance Work Orders</h2>
        <table>
            <thead>
                <tr>
                    <th>S/N</th>
                    <th>WO No</th>
                    <th>Plate Number</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Technicians</th>
                    <th>Total Cost (ETB)</th>
                </tr>
            </thead>
            <tbody>
                {% for row in rows %}
                <tr>
                    <td>{{ row[1] }}</td>
                    <td>{{ row[2] }}</td>
                    <td>{{ row[3] }}</td>
                    <td>{{ row[8] }}</td>
                    <td>{{ row[7] }}</td>
                    <td>{{ row[10] }}</td>
                    <td>{{ "%.2f"|format(row[16]) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

@app.route('/')
def index():
    conn = sqlite3.connect('steely_rmi_garage.db')
    c = conn.cursor()
    c.execute("SELECT * FROM work_orders ORDER BY id DESC")
    rows = c.fetchall()
    total_orders = len(rows)
    total_exp = sum(r[16] for r in rows) if rows else 0.0
    conn.close()
    return render_template_string(TEMPLATE, rows=rows, total_orders=total_orders, total_exp=total_exp)

@app.route('/add', methods=['POST'])
def add():
    serial_number = request.form.get('serial_number')
    work_order_no = request.form.get('work_order_no')
    plate_number = request.form.get('plate_number')
    vehicle_type = request.form.get('vehicle_type')
    current_reading = request.form.get('current_reading')
    reading_unit = request.form.get('reading_unit')
    job_status = request.form.get('job_status')
    work_category = request.form.get('work_category')
    driver_name = request.form.get('driver_name')
    technicians = request.form.get('technicians')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    job_description = request.form.get('job_description')
    
    parts_cost = float(request.form.get('parts_cost') or 0.0)
    tires_cost = float(request.form.get('tires_cost') or 0.0)
    total_expenditure = parts_cost + tires_cost

    conn = sqlite3.connect('steely_rmi_garage.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO work_orders (
            serial_number, work_order_no, plate_number, vehicle_type, 
            current_reading, reading_unit, job_status, work_category, 
            driver_name, technicians, start_date, end_date, job_description, 
            parts_cost, tires_cost, total_expenditure
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        serial_number, work_order_no, plate_number, vehicle_type,
        current_reading, reading_unit, job_status, work_category,
        driver_name, technicians, start_date, end_date, job_description,
        parts_cost, tires_cost, total_expenditure
    ))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
