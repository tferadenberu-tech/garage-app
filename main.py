import io
from datetime import datetime
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, send_file

app = Flask(__name__)

# Initial Data Store
garage_data = {
    "vehicles": [
        {"id": 1, "plate": "AA-3-12345", "model": "Sino Truck 371", "status": "In Service"},
        {"id": 2, "plate": "AA-3-67890", "model": "Toyota Hilux 2022", "status": "Ready"},
        {"id": 3, "plate": "AA-3-11223", "model": "CAT Wheel Loader 950H", "status": "Under Repair"}
    ],
    "spare_parts": [
        {"id": 1, "part_name": "Oil Filter", "spec": "LF16015 / Fleetguard Heavy Duty", "qty": 18, "unit_price": 1200.00},
        {"id": 2, "part_name": "Fuel Filter", "spec": "FF5421 / High Efficiency", "qty": 12, "unit_price": 1800.00},
        {"id": 3, "part_name": "Brake Shoe Set", "spec": "Rear Axle / Sino Heavy Duty Standard", "qty": 6, "unit_price": 4500.00},
        {"id": 4, "part_name": "Hydraulic Oil", "spec": "ISO VG 68 - 20L Drum", "qty": 8, "unit_price": 15000.00}
    ],
    "maintenance_logs": [
        {
            "id": 1,
            "vehicle": "AA-3-12345",
            "type": "PM",
            "start_time": "2026-07-20 08:00",
            "finish_time": "2026-07-20 14:30",
            "effective_hours": 6.5,
            "description": "Engine Oil & Filter Change + Maintenance Check",
            "spares_used": "Oil Filter, Fuel Filter",
            "spare_cost": 3000.00,
            "battery_qty": 0, "battery_cost": 0.0,
            "lubrication_qty": 20, "lubrication_cost": 4500.0,
            "tire_qty": 0, "tire_cost": 0.0
        },
        {
            "id": 2,
            "vehicle": "AA-3-11223",
            "type": "CM",
            "start_time": "2026-07-22 09:00",
            "finish_time": "2026-07-23 11:00",
            "effective_hours": 26.0,
            "description": "Hydraulic Pump Repair + Battery & Rear Tires Replacement",
            "spares_used": "Hydraulic Oil, Seal Kit",
            "spare_cost": 15000.00,
            "battery_qty": 2, "battery_cost": 18000.0,
            "lubrication_qty": 40, "lubrication_cost": 9000.0,
            "tire_qty": 2, "tire_cost": 32000.0
        }
    ]
}

def calculate_effective_hours(start_str, finish_str):
    try:
        fmt = "%Y-%m-%dT%H:%M"
        t1 = datetime.strptime(start_str, fmt)
        t2 = datetime.strptime(finish_str, fmt)
        diff = (t2 - t1).total_seconds() / 3600.0
        return round(max(diff, 0.0), 2)
    except:
        try:
            fmt = "%Y-%m-%d %H:%M"
            t1 = datetime.strptime(start_str, fmt)
            t2 = datetime.strptime(finish_str, fmt)
            diff = (t2 - t1).total_seconds() / 3600.0
            return round(max(diff, 0.0), 2)
        except:
            return 0.0

# HTML DASHBOARD TEMPLATE WITH FORM
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="am">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I Garage Maintnace dash Bord</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f1f5f9; }
        .sidebar { min-height: 100vh; background-color: #0f172a; color: white; }
        .header-title { background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 20px; border-radius: 12px; }
        .card-custom { border-radius: 12px; border: none; box-shadow: 0 4px 10px rgba(0,0,0,0.06); }
        .btn-excel { background-color: #16a34a; color: white; font-weight: bold; }
        .btn-excel:hover { background-color: #15803d; color: white; }
        .form-section { background-color: #ffffff; border-left: 5px solid #2563eb; }
    </style>
</head>
<body>
<div class="container-fluid">
    <div class="row">
        <!-- Sidebar -->
        <div class="col-md-2 sidebar p-3">
            <h4 class="text-info fw-bold">SteelY R.M.I</h4>
            <p class="text-secondary small">የጋራዥ ጥገና ዳሽቦርድ</p>
            <hr class="border-secondary">
            <div class="d-grid gap-2 mb-4">
                <a href="/export/master_excel" class="btn btn-excel btn-sm shadow">
                    📥 EXPORT MASTER EXCEL
                </a>
            </div>
            <ul class="nav nav-pills flex-column">
                <li class="nav-item mb-2"><a href="#add-form" class="nav-link text-white fw-bold">➕ አዲስ ጥገና መመዝገቢያ (Form)</a></li>
                <li class="nav-item mb-2"><a href="#summary" class="nav-link text-white">📊 ማጠቃለያ (Summary)</a></li>
                <li class="nav-item mb-2"><a href="#maintenance" class="nav-link text-white">🛠️ የጥገና መዝገብ (Logs)</a></li>
                <li class="nav-item mb-2"><a href="#spares" class="nav-link text-white">⚙️ እስፔር ፓርት (Spare Parts)</a></li>
            </ul>
        </div>

        <!-- Main Content -->
        <div class="col-md-10 p-4">
            <!-- Header Banner -->
            <div class="header-title mb-4 d-flex justify-content-between align-items-center">
                <div>
                    <h2 class="fw-bold mb-1">SteelY R.M.I Garage Maintnace dash Bord</h2>
                    <p class="mb-0 text-light opacity-75">Integrated Maintenance, Consumables & Work Time Dashboard</p>
                </div>
                <a href="/export/master_excel" class="btn btn-success btn-lg shadow-sm">
                    📊 Export Master Excel (All in One)
                </a>
            </div>

            <!-- 📝 1. NEW WORK ORDER INPUT FORM -->
            <div class="card card-custom p-4 mb-4 form-section" id="add-form">
                <h4 class="fw-bold text-primary mb-3">📝 አዲስ የጥገና እና ወጪ መመዝገቢያ ፎርም (Create Work Order)</h4>
                <form action="/add_work_order" method="POST">
                    <div class="row g-3">
                        <div class="col-md-3">
                            <label class="form-label fw-bold small">የሰሌዳ ቁጥር (Vehicle Plate):</label>
                            <input type="text" name="vehicle" class="form-control" placeholder="e.g. AA-3-12345" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label fw-bold small">የጥገና ዓይነት (Type):</label>
                            <select name="type" class="form-select" required>
                                <option value="PM">PM (መደበኛ ጥገና / Preventive)</option>
                                <option value="CM">CM (ድንገተኛ ጥገና / Corrective)</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label fw-bold small">የተጀመረበት ቀንና ሰዓት (Start Time):</label>
                            <input type="datetime-local" name="start_time" class="form-control" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label fw-bold small">የተጠናቀቀበት ቀንና ሰዓት (Finish Time):</label>
                            <input type="datetime-local" name="finish_time" class="form-control" required>
                        </div>

                        <div class="col-md-6">
                            <label class="form-label fw-bold small">የተከናወነ የጥገና ሥራ መግለጫ (Work Description):</label>
                            <input type="text" name="description" class="form-control" placeholder="e.g. Engine Oil Change & Brake Adjustment" required>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label fw-bold small">ጥቅም ላይ የዋለ እስፔር ፓርት (Spares Used):</label>
                            <input type="text" name="spares_used" class="form-control" placeholder="e.g. Oil Filter, Fuel Filter">
                        </div>
                        <div class="col-md-3">
                            <label class="form-label fw-bold small">የእስፔር ፓርት ወጪ (Spare Cost - ETB):</label>
                            <input type="number" step="0.01" name="spare_cost" class="form-control" value="0.00">
                        </div>

                        <div class="col-md-2">
                            <label class="form-label fw-bold small text-warning">ባታሪ ብዛት (Battery Qty):</label>
                            <input type="number" name="battery_qty" class="form-control" value="0">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label fw-bold small text-warning">ባታሪ ወጪ (Battery Cost):</label>
                            <input type="number" step="0.01" name="battery_cost" class="form-control" value="0.00">
                        </div>

                        <div class="col-md-2">
                            <label class="form-label fw-bold small text-info">ሉብሪኬሽን/ዘይት (Liters):</label>
                            <input type="number" step="0.1" name="lubrication_qty" class="form-control" value="0.0">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label fw-bold small text-info">ሉብሪኬሽን ወጪ (Lubricant Cost):</label>
                            <input type="number" step="0.01" name="lubrication_cost" class="form-control" value="0.00">
                        </div>

                        <div class="col-md-2">
                            <label class="form-label fw-bold small text-danger">ጎማ ብዛት (Tire Qty):</label>
                            <input type="number" name="tire_qty" class="form-control" value="0">
                        </div>
                        <div class="col-md-2">
                            <label class="form-label fw-bold small text-danger">ጎማ ወጪ (Tire Cost):</label>
                            <input type="number" step="0.01" name="tire_cost" class="form-control" value="0.00">
                        </div>

                        <div class="col-md-12 text-end mt-3">
                            <button type="submit" class="btn btn-primary px-4 fw-bold">💾 መዝግብ (Save Work Order)</button>
                        </div>
                    </div>
                </form>
            </div>

            <!-- Weekly / Monthly Consumables Summary -->
            <div class="card card-custom p-4 mb-4" id="summary">
                <h4 class="fw-bold text-dark mb-3">🔋 Weekly & Monthly Consumables Summary (ባታሪ፣ ሉብሪኬሽን እና ጎማ ማጠቃለያ)</h4>
                <div class="row g-3">
                    <div class="col-md-4">
                        <div class="p-3 border rounded bg-white border-start border-warning border-4">
                            <h6 class="text-muted fw-bold">Total Battery (ባታሪ)</h6>
                            <p class="mb-1"><strong>Qty:</strong> {{ summary.total_battery_qty }} Pcs</p>
                            <p class="mb-0 text-primary fw-bold"><strong>Cost:</strong> {{ "{:,.2f}".format(summary.total_battery_cost) }} ETB</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 border rounded bg-white border-start border-info border-4">
                            <h6 class="text-muted fw-bold">Total Lubrication (ዘይት/ቅባት)</h6>
                            <p class="mb-1"><strong>Qty:</strong> {{ summary.total_lubrication_qty }} Liters</p>
                            <p class="mb-0 text-primary fw-bold"><strong>Cost:</strong> {{ "{:,.2f}".format(summary.total_lubrication_cost) }} ETB</p>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="p-3 border rounded bg-white border-start border-danger border-4">
                            <h6 class="text-muted fw-bold">Total Tires (ጎማ)</h6>
                            <p class="mb-1"><strong>Qty:</strong> {{ summary.total_tire_qty }} Pcs</p>
                            <p class="mb-0 text-primary fw-bold"><strong>Cost:</strong> {{ "{:,.2f}".format(summary.total_tire_cost) }} ETB</p>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Maintenance Table -->
            <div class="card card-custom p-4 mb-4" id="maintenance">
                <h4 class="fw-bold text-dark mb-3">🛠️ Work Time & Maintenance Execution Log</h4>
                <div class="table-responsive">
                    <table class="table table-bordered align-middle">
                        <thead class="table-dark">
                            <tr>
                                <th>WO #</th>
                                <th>Plate No</th>
                                <th>Type</th>
                                <th>Start Date & Hour</th>
                                <th>Finished Date & Hour</th>
                                <th>Effective Work Time</th>
                                <th>Work Description</th>
                                <th>Battery</th>
                                <th>Lubrication</th>
                                <th>Tire</th>
                                <th>Spare Cost (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in data.maintenance_logs %}
                            <tr>
                                <td>WO-{{ log.id }}</td>
                                <td><span class="badge bg-secondary">{{ log.vehicle }}</span></td>
                                <td><span class="badge bg-{{ 'success' if log.type == 'PM' else 'danger' }}">{{ log.type }}</span></td>
                                <td class="small">{{ log.start_time }}</td>
                                <td class="small">{{ log.finish_time }}</td>
                                <td class="fw-bold text-center text-primary bg-light">{{ log.effective_hours }} hrs</td>
                                <td class="small">{{ log.description }}</td>
                                <td class="small">{{ log.battery_qty }} pcs / {{ "{:,.0f}".format(log.battery_cost) }} ETB</td>
                                <td class="small">{{ log.lubrication_qty }} L / {{ "{:,.0f}".format(log.lubrication_cost) }} ETB</td>
                                <td class="small">{{ log.tire_qty }} pcs / {{ "{:,.0f}".format(log.tire_cost) }} ETB</td>
                                <td class="fw-bold text-end">{{ "{:,.2f}".format(log.spare_cost) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Spare Parts Table -->
            <div class="card card-custom p-4 mb-4" id="spares">
                <h4 class="fw-bold text-dark mb-3">⚙️ Spare Parts Inventory & Specifications</h4>
                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-dark">
                            <tr>
                                <th>#</th>
                                <th>Spare Part Name</th>
                                <th>Specification (Spec)</th>
                                <th>Stock Qty</th>
                                <th>Unit Price (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for part in data.spare_parts %}
                            <tr>
                                <td>{{ part.id }}</td>
                                <td class="fw-bold text-dark">{{ part.part_name }}</td>
                                <td><span class="badge bg-light text-dark border">{{ part.spec }}</span></td>
                                <td>{{ part.qty }}</td>
                                <td>{{ "{:,.2f}".format(part.unit_price) }} ETB</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    </div>
</div>
</body>
</html>
"""

# ROUTES
@app.route('/')
def dashboard():
    summary = {
        "total_battery_qty": sum(l['battery_qty'] for l in garage_data['maintenance_logs']),
        "total_battery_cost": sum(l['battery_cost'] for l in garage_data['maintenance_logs']),
        "total_lubrication_qty": sum(l['lubrication_qty'] for l in garage_data['maintenance_logs']),
        "total_lubrication_cost": sum(l['lubrication_cost'] for l in garage_data['maintenance_logs']),
        "total_tire_qty": sum(l['tire_qty'] for l in garage_data['maintenance_logs']),
        "total_tire_cost": sum(l['tire_cost'] for l in garage_data['maintenance_logs'])
    }
    return render_template_string(HTML_TEMPLATE, data=garage_data, summary=summary)

@app.route('/add_work_order', methods=['POST'])
def add_work_order():
    start_raw = request.form.get('start_time')
    finish_raw = request.form.get('finish_time')
    
    start_disp = start_raw.replace('T', ' ') if start_raw else ''
    finish_disp = finish_raw.replace('T', ' ') if finish_raw else ''
    
    eff_hours = calculate_effective_hours(start_raw, finish_raw)
    
    new_id = len(garage_data['maintenance_logs']) + 1
    new_log = {
        "id": new_id,
        "vehicle": request.form.get('vehicle', 'N/A'),
        "type": request.form.get('type', 'PM'),
        "start_time": start_disp,
        "finish_time": finish_disp,
        "effective_hours": eff_hours,
        "description": request.form.get('description', ''),
        "spares_used": request.form.get('spares_used', ''),
        "spare_cost": float(request.form.get('spare_cost', 0) or 0),
        "battery_qty": int(request.form.get('battery_qty', 0) or 0),
        "battery_cost": float(request.form.get('battery_cost', 0) or 0),
        "lubrication_qty": float(request.form.get('lubrication_qty', 0) or 0),
        "lubrication_cost": float(request.form.get('lubrication_cost', 0) or 0),
        "tire_qty": int(request.form.get('tire_qty', 0) or 0),
        "tire_cost": float(request.form.get('tire_cost', 0) or 0)
    }
    garage_data['maintenance_logs'].append(new_log)
    return redirect(url_for('dashboard'))

@app.route('/export/master_excel')
def export_master_excel():
    output = io.BytesIO()
    
    logs_df = pd.DataFrame(garage_data['maintenance_logs'])
    logs_df.rename(columns={
        'id': 'Work Order ID',
        'vehicle': 'Vehicle Plate',
        'type': 'Type (PM/CM)',
        'start_time': 'Starting Date & Hour',
        'finish_time': 'Finished Date & Hour',
        'effective_hours': 'Effective Work Time (Hours)',
        'description': 'Work Executed',
        'spares_used': 'Spares Used',
        'spare_cost': 'Spare Parts Cost (ETB)',
        'battery_qty': 'Battery Qty (Pcs)',
        'battery_cost': 'Battery Cost (ETB)',
        'lubrication_qty': 'Lubrication Qty (Liters)',
        'lubrication_cost': 'Lubrication Cost (ETB)',
        'tire_qty': 'Tire Qty (Pcs)',
        'tire_cost': 'Tire Cost (ETB)'
    }, inplace=True)
    
    consumables_summary = [{
        'Category': 'Battery (ባታሪ)',
        'Total Quantity (Pcs)': sum(l['battery_qty'] for l in garage_data['maintenance_logs']),
        'Total Cost (ETB)': sum(l['battery_cost'] for l in garage_data['maintenance_logs'])
    }, {
        'Category': 'Lubrication (ዘይት/ቅባት)',
        'Total Quantity (Liters)': sum(l['lubrication_qty'] for l in garage_data['maintenance_logs']),
        'Total Cost (ETB)': sum(l['lubrication_cost'] for l in garage_data['maintenance_logs'])
    }, {
        'Category': 'Tire (ጎማ)',
        'Total Quantity (Pcs)': sum(l['tire_qty'] for l in garage_data['maintenance_logs']),
        'Total Cost (ETB)': sum(l['tire_cost'] for l in garage_data['maintenance_logs'])
    }]
    consumables_df = pd.DataFrame(consumables_summary)
    
    spares_df = pd.DataFrame(garage_data['spare_parts'])
    spares_df.rename(columns={
        'id': 'Part ID',
        'part_name': 'Spare Part Name',
        'spec': 'Specification (Spec)',
        'qty': 'Stock Quantity',
        'unit_price': 'Unit Price (ETB)'
    }, inplace=True)
    
    vehicles_df = pd.DataFrame(garage_data['vehicles'])
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        logs_df.to_excel(writer, sheet_name='Maintenance & Work Hours', index=False)
        consumables_df.to_excel(writer, sheet_name='Consumables Summary', index=False)
        spares_df.to_excel(writer, sheet_name='Spare Parts Inventory', index=False)
        vehicles_df.to_excel(writer, sheet_name='Vehicle Fleet', index=False)
        
    output.seek(0)
    
    return send_file(
        output,
        download_name='SteelY_Master_Garage_Maintenance_Report.xlsx',
        as_attachment=True,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

if __name__ == '__main__':
    app.run(debug=True, port=5000)
