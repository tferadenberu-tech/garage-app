import io
from datetime import datetime
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, send_file

app = Flask(__name__)

# ==========================================
# 1. DATA STORE WITH NEW FIELDS
# ==========================================
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
    # Expanded Maintenance Logs with Start/Finish Time, Effective Hours, Battery, Lubrication, Tire
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
            "lubrication_qty": 20, "lubrication_cost": 4500.0,  # Liters / ETB
            "tire_qty": 0, "tire_cost": 0.0
        },
        {
            "id": 2,
            "vehicle": "AA-3-11223",
            "type": "CM",
            "start_time": "2026-07-22 09:00",
            "finish_time": "2026-07-23 11:00",
            "effective_hours": 26.0,
            "description": "Hydraulic Pump Overhaul + Battery & Rear Tires Replacement",
            "spares_used": "Hydraulic Oil, Seal Kit",
            "spare_cost": 15000.00,
            "battery_qty": 2, "battery_cost": 18000.0,
            "lubrication_qty": 40, "lubrication_cost": 9000.0,
            "tire_qty": 2, "tire_cost": 32000.0
        }
    ]
}

# Helper to calculate Effective Work Time
def calculate_effective_hours(start_str, finish_str):
    try:
        fmt = "%Y-%m-%d %H:%M"
        t1 = datetime.strptime(start_str, fmt)
        t2 = datetime.strptime(finish_str, fmt)
        diff = (t2 - t1).total_seconds() / 3600.0
        return round(max(diff, 0.0), 2)
    except:
        return 0.0

# ==========================================
# 2. BILINGUAL DASHBOARD HTML
# ==========================================
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
        .header-title { background: linear-gradient(135deg, #1e293b, #0f172a); color: white; padding: 22px; border-radius: 12px; }
        .card-custom { border-radius: 12px; border: none; box-shadow: 0 4px 8px rgba(0,0,0,0.05); }
        .btn-excel { background-color: #16a34a; color: white; font-weight: bold; }
        .btn-excel:hover { background-color: #15803d; color: white; }
        .table-custom th { background-color: #1e293b; color: white; }
    </style>
</head>
<body>
<div class="container-fluid">
    <div class="row">
        <!-- Sidebar Navigation -->
        <div class="col-md-2 sidebar p-3">
            <h4 class="text-info fw-bold">SteelY R.M.I</h4>
            <p class="text-secondary small">የጋራዥ ጥገና ዳሽቦርድ</p>
            <hr class="border-secondary">
            <div class="d-grid gap-2 mb-4">
                <a href="/export/master_excel" class="btn btn-excel btn-sm shadow">
                    📥 EXPORT MASTER EXCEL (ALL IN ONE)
                </a>
            </div>
            <ul class="nav nav-pills flex-column">
                <li class="nav-item mb-2"><a href="#summary" class="nav-link text-white">📊 ማጠቃለያ (Summary)</a></li>
                <li class="nav-item mb-2"><a href="#maintenance" class="nav-link text-white">🛠️ የጥገና መዝገብ (Work Hours)</a></li>
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

            <!-- Weekly / Monthly Consumables Summary (Battery, Lubrication & Tire) -->
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

            <!-- Maintenance & Work Time Execution Table -->
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
                                <th>Battery (Qty/Cost)</th>
                                <th>Lubrication (Qty/Cost)</th>
                                <th>Tire (Qty/Cost)</th>
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

            <!-- Spare Parts Inventory Table -->
            <div class="card card-custom p-4 mb-4" id="spares">
                <h4 class="fw-bold text-dark mb-3">⚙️ Spare Parts Inventory & Specifications</h4>
                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-custom">
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

# ==========================================
# 3. ROUTES & EXCEL EXPORT ENGINE
# ==========================================
@app.route('/')
def dashboard():
    # Consumables Aggregation
    summary = {
        "total_battery_qty": sum(l['battery_qty'] for l in garage_data['maintenance_logs']),
        "total_battery_cost": sum(l['battery_cost'] for l in garage_data['maintenance_logs']),
        "total_lubrication_qty": sum(l['lubrication_qty'] for l in garage_data['maintenance_logs']),
        "total_lubrication_cost": sum(l['lubrication_cost'] for l in garage_data['maintenance_logs']),
        "total_tire_qty": sum(l['tire_qty'] for l in garage_data['maintenance_logs']),
        "total_tire_cost": sum(l['tire_cost'] for l in garage_data['maintenance_logs'])
    }
    return render_template_string(HTML_TEMPLATE, data=garage_data, summary=summary)

# MASTER EXCEL (ALL IN ONE) EXPORT ROUTE
@app.route('/export/master_excel')
def export_master_excel():
    output = io.BytesIO()
    
    # Sheet 1: Maintenance Logs & Effective Work Time
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
    
    # Sheet 2: Consumables Summary (Weekly / Monthly)
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
    
    # Sheet 3: Spare Parts Inventory
    spares_df = pd.DataFrame(garage_data['spare_parts'])
    spares_df.rename(columns={
        'id': 'Part ID',
        'part_name': 'Spare Part Name',
        'spec': 'Specification (Spec)',
        'qty': 'Stock Quantity',
        'unit_price': 'Unit Price (ETB)'
    }, inplace=True)
    
    # Sheet 4: Vehicle Fleet
    vehicles_df = pd.DataFrame(garage_data['vehicles'])
    
    # Write to All-in-One Master Excel Workbook
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
    # Make sure pandas and openpyxl are installed
    app.run(debug=True, port=5000)
