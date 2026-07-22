import os
import json
from datetime import datetime
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# Data File Path (Persistent JSON Storage)
DATA_FILE = "garage_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "equipments": [
            {
                "id": 1,
                "plate_no": "EQUIP-001",
                "model": "CAT Loader 950H",
                "type": "Loader",
                "driver": "Ato Alemu",
                "spec": "15W-40 Heavy Duty Engine Oil Filter Set",
                "current_hours": 3420.0,
                "last_service_hours": 3250.0,
                "interval_hours": 250.0
            },
            {
                "id": 2,
                "plate_no": "EQUIP-002",
                "model": "Komatsu Excavator PC200",
                "type": "Excavator",
                "driver": "Ato Tadesse",
                "spec": "Hydraulic & Engine Oil Filter Kit",
                "current_hours": 1890.0,
                "last_service_hours": 1650.0,
                "interval_hours": 250.0
            }
        ],
        "spare_parts": [
            {
                "id": 1,
                "spec": "15W-40 Heavy Engine Oil (20L Drum)",
                "category": "Fluids & Lubricants",
                "quantity": 18,
                "unit": "Drums",
                "min_stock": 5
            },
            {
                "id": 2,
                "spec": "CAT Oil Filter Element (1R-1808)",
                "category": "Filters",
                "quantity": 12,
                "unit": "Pcs",
                "min_stock": 4
            }
        ],
        "service_logs": [
            {
                "id": 1,
                "plate_no": "EQUIP-001",
                "service_type": "250 Hrs Routine Oil & Filter Change",
                "hour_meter": 3250.0,
                "spec_used": "15W-40 Heavy Engine Oil + Filter",
                "technician": "Workshop Maintenance Team",
                "date": "2026-07-01"
            }
        ]
    }

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I Garage Maintnace dash Bord</title>
    <style>
        :root {
            --primary-color: #1e3a8a;
            --primary-dark: #0f172a;
            --accent-color: #2563eb;
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --border-color: #e2e8f0;
            --success: #16a34a;
            --warning: #ca8a04;
            --danger: #dc2626;
        }

        * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        body { background-color: var(--bg-color); color: var(--text-main); margin: 0; padding: 20px; }
        .container { max-width: 1280px; margin: 0 auto; }
        
        .header {
            background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
            color: white;
            padding: 24px 30px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(30, 58, 138, 0.15);
            margin-bottom: 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 { margin: 0; font-size: 26px; }
        .header p { margin: 5px 0 0 0; opacity: 0.85; font-size: 14px; }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 18px;
            margin-bottom: 25px;
        }
        .stat-card {
            background: var(--card-bg);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        }
        .stat-card .title { font-size: 13px; color: #64748b; font-weight: 600; text-transform: uppercase; }
        .stat-card .value { font-size: 28px; font-weight: 700; color: var(--primary-color); margin-top: 8px; }

        .section-card {
            background: var(--card-bg);
            padding: 25px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            margin-bottom: 30px;
        }
        .section-card h2 {
            margin-top: 0;
            color: var(--primary-color);
            font-size: 18px;
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 10px;
            margin-bottom: 20px;
        }

        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        .form-group { display: flex; flex-direction: column; gap: 6px; }
        .form-group label { font-size: 13px; font-weight: 600; color: #475569; }
        input, select {
            padding: 10px 12px;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-size: 14px;
            outline: none;
        }
        input:focus, select:focus { border-color: var(--accent-color); }
        
        .btn-submit {
            background-color: var(--primary-color);
            color: white;
            border: none;
            padding: 11px 22px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
            margin-top: auto;
        }
        .btn-submit:hover { background-color: var(--accent-color); }

        table { width: 100%; border-collapse: collapse; font-size: 14px; text-align: left; }
        th { background-color: #f1f5f9; color: #334155; font-weight: 700; padding: 12px 14px; border-bottom: 2px solid var(--border-color); }
        td { padding: 12px 14px; border-bottom: 1px solid var(--border-color); color: #334155; }
        tr:hover { background-color: #f8fafc; }

        .badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 700;
        }
        .badge-ok { background-color: #dcfce7; color: #15803d; }
        .badge-warning { background-color: #fef9c3; color: #a16207; }
        .badge-danger { background-color: #fee2e2; color: #b91c1c; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>SteelY R.M.I Garage Maintnace dash Bord</h1>
                <p>Fleet Equipment Management & 250-Hour Oil Service Tracking System</p>
            </div>
            <div>
                <span class="badge badge-ok" style="font-size: 14px; padding: 8px 14px;">● System Active</span>
            </div>
        </div>

        <!-- 📊 Dashboard Summary Metrics -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="title">Total Fleet Equipment</div>
                <div class="value">{{ equipments|length }}</div>
            </div>
            <div class="stat-card">
                <div class="title">Service Alerts Needed</div>
                <div class="value" style="color: var(--danger);">{{ urgent_count }}</div>
            </div>
            <div class="stat-card">
                <div class="title">Spare Parts Registered</div>
                <div class="value">{{ spare_parts|length }}</div>
            </div>
            <div class="stat-card">
                <div class="title">Logged Maintenance History</div>
                <div class="value">{{ service_logs|length }}</div>
            </div>
        </div>

        <!-- 🚜 SECTION 1: Equipment & 250-Hour Oil Service Tracker -->
        <div class="section-card">
            <h2>🚜 1. Equipment & 250-Hour Oil Service Tracker</h2>
            
            <form action="/add_equipment" method="POST">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Plate No / ID</label>
                        <input type="text" name="plate_no" placeholder="e.g. EQUIP-003" required>
                    </div>
                    <div class="form-group">
                        <label>Equipment Model</label>
                        <input type="text" name="model" placeholder="e.g. CAT Loader 950H" required>
                    </div>
                    <div class="form-group">
                        <label>Equipment Type</label>
                        <select name="type" required>
                            <option value="Loader">Loader</option>
                            <option value="Excavator">Excavator</option>
                            <option value="Forklift">Forklift</option>
                            <option value="Dump Truck">Dump Truck</option>
                            <option value="Other">Other Equipment</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Driver / Operator</label>
                        <input type="text" name="driver" placeholder="Operator Name" required>
                    </div>
                    <div class="form-group">
                        <label>Spare Part Name (spec)</label>
                        <input type="text" name="spec" placeholder="e.g. 15W-40 Oil & Filter Set" required>
                    </div>
                    <div class="form-group">
                        <label>Current Hour Meter</label>
                        <input type="number" step="0.1" name="current_hours" placeholder="0.0" required>
                    </div>
                    <div class="form-group">
                        <label>Last Service Hour Meter</label>
                        <input type="number" step="0.1" name="last_service_hours" placeholder="0.0" required>
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn-submit">+ Add Equipment</button>
                    </div>
                </div>
            </form>

            <table style="margin-top:20px;">
                <thead>
                    <tr>
                        <th>Plate / ID</th>
                        <th>Model</th>
                        <th>Type</th>
                        <th>Spare Part Name (spec)</th>
                        <th>Current Hours</th>
                        <th>Last Service</th>
                        <th>Next Service Due (250h)</th>
                        <th>Remaining Hours</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for eq in equipments %}
                    {% set next_due = eq.last_service_hours + eq.interval_hours %}
                    {% set rem = next_due - eq.current_hours %}
                    <tr>
                        <td><strong>{{ eq.plate_no }}</strong></td>
                        <td>{{ eq.model }}</td>
                        <td>{{ eq.type }}</td>
                        <td>{{ eq.spec }}</td>
                        <td>{{ eq.current_hours }} hrs</td>
                        <td>{{ eq.last_service_hours }} hrs</td>
                        <td>{{ next_due }} hrs</td>
                        <td>
                            {% if rem <= 0 %}
                                <strong style="color:var(--danger);">{{ rem }} hrs (Overdue!)</strong>
                            {% elif rem <= 30 %}
                                <strong style="color:var(--warning);">{{ rem }} hrs remaining</strong>
                            {% else %}
                                <strong style="color:var(--success);">{{ rem }} hrs remaining</strong>
                            {% endif %}
                        </td>
                        <td>
                            {% if rem <= 0 %}
                                <span class="badge badge-danger">⚠️ Overdue Service</span>
                            {% elif rem <= 30 %}
                                <span class="badge badge-warning">⚡ Service Soon</span>
                            {% else %}
                                <span class="badge badge-ok">✅ Normal</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- 📦 SECTION 2: Spare Parts Inventory Tracking -->
        <div class="section-card">
            <h2>📦 2. Spare Parts Inventory Tracking</h2>
            
            <form action="/add_spare_part" method="POST">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Spare Part Name (spec)</label>
                        <input type="text" name="spec" placeholder="e.g. CAT Oil Filter 1R-1808" required>
                    </div>
                    <div class="form-group">
                        <label>Category</label>
                        <select name="category" required>
                            <option value="Filters">Filters</option>
                            <option value="Fluids & Lubricants">Fluids & Lubricants</option>
                            <option value="Hoses & Fittings">Hoses & Fittings</option>
                            <option value="Engine Parts">Engine Parts</option>
                            <option value="Hydraulic Parts">Hydraulic Parts</option>
                            <option value="Other">Other Spare Parts</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Stock Quantity</label>
                        <input type="number" name="quantity" placeholder="0" required>
                    </div>
                    <div class="form-group">
                        <label>Unit</label>
                        <input type="text" name="unit" placeholder="e.g. Pcs, Liters, Drums" required>
                    </div>
                    <div class="form-group">
                        <label>Min Stock Warning</label>
                        <input type="number" name="min_stock" placeholder="5" required>
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn-submit">+ Add Spare Part</button>
                    </div>
                </div>
            </form>

            <table style="margin-top:20px;">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Spare Part Name (spec)</th>
                        <th>Category</th>
                        <th>Current Stock</th>
                        <th>Unit</th>
                        <th>Min Stock Threshold</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for sp in spare_parts %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td><strong>{{ sp.spec }}</strong></td>
                        <td>{{ sp.category }}</td>
                        <td><strong>{{ sp.quantity }}</strong></td>
                        <td>{{ sp.unit }}</td>
                        <td>{{ sp.min_stock }} {{ sp.unit }}</td>
                        <td>
                            {% if sp.quantity <= sp.min_stock %}
                                <span class="badge badge-danger">⚠️ Reorder Needed</span>
                            {% else %}
                                <span class="badge badge-ok">✅ In Stock</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <!-- 🛠️ SECTION 3: Service & Maintenance Log -->
        <div class="section-card">
            <h2>🛠️ 3. Service & Maintenance History Log</h2>
            
            <form action="/add_service_log" method="POST">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Select Equipment</label>
                        <select name="plate_no" required>
                            {% for eq in equipments %}
                            <option value="{{ eq.plate_no }}">{{ eq.plate_no }} - {{ eq.model }}</option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Service Type</label>
                        <input type="text" name="service_type" placeholder="e.g. 250 Hrs Routine Service" required>
                    </div>
                    <div class="form-group">
                        <label>Service Hour Meter</label>
                        <input type="number" step="0.1" name="hour_meter" placeholder="3250.0" required>
                    </div>
                    <div class="form-group">
                        <label>Spare Part Used (spec)</label>
                        <input type="text" name="spec_used" placeholder="e.g. 20L Oil + 1 Filter" required>
                    </div>
                    <div class="form-group">
                        <label>Technician Name</label>
                        <input type="text" name="technician" placeholder="Mechanic Name" required>
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn-submit">+ Log Service</button>
                    </div>
                </div>
            </form>

            <table style="margin-top:20px;">
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Plate No</th>
                        <th>Service Type</th>
                        <th>Hour Meter At Service</th>
                        <th>Spare Part Used (spec)</th>
                        <th>Technician</th>
                    </tr>
                </thead>
                <tbody>
                    {% for log in service_logs %}
                    <tr>
                        <td>{{ log.date }}</td>
                        <td><strong>{{ log.plate_no }}</strong></td>
                        <td>{{ log.service_type }}</td>
                        <td>{{ log.hour_meter }} hrs</td>
                        <td>{{ log.spec_used }}</td>
                        <td>{{ log.technician }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

    </div>
</body>
</html>
"""

@app.route('/')
def home():
    data = load_data()
    
    urgent_count = 0
    for eq in data.get("equipments", []):
        rem = (eq["last_service_hours"] + eq.get("interval_hours", 250.0)) - eq["current_hours"]
        if rem <= 30:
            urgent_count += 1
            
    return render_template_string(
        HTML_TEMPLATE,
        equipments=data.get("equipments", []),
        spare_parts=data.get("spare_parts", []),
        service_logs=data.get("service_logs", []),
        urgent_count=urgent_count
    )

@app.route('/add_equipment', methods=['POST'])
def add_equipment():
    data = load_data()
    new_eq = {
        "id": len(data["equipments"]) + 1,
        "plate_no": request.form.get("plate_no"),
        "model": request.form.get("model"),
        "type": request.form.get("type"),
        "driver": request.form.get("driver"),
        "spec": request.form.get("spec"),
        "current_hours": float(request.form.get("current_hours")),
        "last_service_hours": float(request.form.get("last_service_hours")),
        "interval_hours": 250.0
    }
    data["equipments"].append(new_eq)
    save_data(data)
    return redirect(url_for('home'))

@app.route('/add_spare_part', methods=['POST'])
def add_spare_part():
    data = load_data()
    new_sp = {
        "id": len(data["spare_parts"]) + 1,
        "spec": request.form.get("spec"),
        "category": request.form.get("category"),
        "quantity": int(request.form.get("quantity")),
        "unit": request.form.get("unit"),
        "min_stock": int(request.form.get("min_stock"))
    }
    data["spare_parts"].append(new_sp)
    save_data(data)
    return redirect(url_for('home'))

@app.route('/add_service_log', methods=['POST'])
def add_service_log():
    data = load_data()
    plate_no = request.form.get("plate_no")
    hour_meter = float(request.form.get("hour_meter"))
    
    for eq in data["equipments"]:
        if eq["plate_no"] == plate_no:
            eq["last_service_hours"] = hour_meter
            
    new_log = {
        "id": len(data["service_logs"]) + 1,
        "plate_no": plate_no,
        "service_type": request.form.get("service_type"),
        "hour_meter": hour_meter,
        "spec_used": request.form.get("spec_used"),
        "technician": request.form.get("technician"),
        "date": datetime.now().strftime("%Y-%m-%d")
    }
    data["service_logs"].append(new_log)
    save_data(data)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
