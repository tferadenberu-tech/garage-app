import os
import json
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# Data File Path
DATA_FILE = "garage_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "vehicles": [
            {
                "id": 1,
                "plate_no": "AA-3-A12345",
                "model": "Toyota Hilux",
                "driver": "Ato Tadesse",
                "spec": "5W-30 Synthetic Oil Filter Kit",
                "current_val": 105000.0,
                "last_service_val": 100000.0,
                "unit": "KM",
                "interval": 5000.0
            },
            {
                "id": 2,
                "plate_no": "MAC-001",
                "model": "CAT Loader 950H",
                "driver": "Ato Alemu",
                "spec": "15W-40 Heavy Duty Engine Oil Filter",
                "current_val": 3420.0,
                "last_service_val": 3250.0,
                "unit": "Hours",
                "interval": 250.0
            }
        ],
        "parts": [
            {
                "id": 1,
                "part_name": "Engine Oil Filter",
                "spec": "15W-40 Heavy Duty",
                "qty": 4,
                "date": "2026-07-20"
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
        .container { max-width: 1250px; margin: 0 auto; }
        
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
        .header h1 { margin: 0; font-size: 24px; }
        .header p { margin: 5px 0 0 0; opacity: 0.85; font-size: 14px; }

        .section-card {
            background: var(--card-bg);
            padding: 25px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
            box-shadow: 0 2px 8px rgba(0,0,0,0.04);
            margin-bottom: 25px;
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
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
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
            margin-top: 15px;
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
        <!-- System Header -->
        <div class="header">
            <div>
                <h1>SteelY R.M.I Garage Maintnace dash Bord</h1>
                <p>Fleet & Machinery Maintenance Management System</p>
            </div>
            <div>
                <span class="badge badge-ok" style="font-size: 14px; padding: 8px 14px;">● System Active</span>
            </div>
        </div>

        <!-- 📝 1. Vehicle Registration Form -->
        <div class="section-card">
            <h2>1. Add Vehicle / Machine</h2>
            
            <form action="/add_vehicle" method="POST">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Plate No / ID</label>
                        <input type="text" name="plate_no" placeholder="e.g. AA-2-C1234 or MAC-001" required>
                    </div>
                    <div class="form-group">
                        <label>Model</label>
                        <input type="text" name="model" placeholder="e.g. Toyota Hilux / CAT Loader" required>
                    </div>
                    <div class="form-group">
                        <label>Driver / Operator</label>
                        <input type="text" name="driver" placeholder="Operator Name" required>
                    </div>
                    <div class="form-group">
                        <label>Spare Part Name (spec)</label>
                        <input type="text" name="spec" placeholder="Oil & Filter Specification" required>
                    </div>
                    <div class="form-group">
                        <label>Current Value (Hours / KM)</label>
                        <input type="number" step="0.1" name="current_val" placeholder="e.g. 105000 or 3420" required>
                    </div>
                    <div class="form-group">
                        <label>Last Service Value (Hours / KM)</label>
                        <input type="number" step="0.1" name="last_service_val" placeholder="e.g. 100000 or 3250" required>
                    </div>
                    <!-- 🎯 የፎቶው መመሪያ መምረጫ (Unit & Interval) -->
                    <div class="form-group">
                        <label>የመከታተያ መስፈርት (Unit & Interval)</label>
                        <select name="unit_type" required>
                            <option value="KM_5000">KM (ለ 5,000 KM)</option>
                            <option value="Hours_250">Hours (ለ 250 Hours)</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn-submit">+ Save Vehicle / Machine</button>
            </form>
        </div>

        <!-- 📊 2. Maintenance Status Table -->
        <div class="section-card">
            <h2>2. Vehicle & Machinery Status Tracking (KM / Hours)</h2>

            <table>
                <thead>
                    <tr>
                        <th>Plate No / ID</th>
                        <th>Model</th>
                        <th>Driver / Operator</th>
                        <th>Spare Part Name (spec)</th>
                        <th>Current Value</th>
                        <th>Last Service Value</th>
                        <th>Interval</th>
                        <th>Remaining</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for v in vehicles %}
                    {% set next_due = v.last_service_val + v.interval %}
                    {% set rem = next_due - v.current_val %}
                    <tr>
                        <td><strong>{{ v.plate_no }}</strong></td>
                        <td>{{ v.model }}</td>
                        <td>{{ v.driver }}</td>
                        <td>{{ v.spec }}</td>
                        <td style="background-color: #e0f2fe;"><strong>{{ v.current_val }} {{ v.unit }}</strong></td>
                        <td>{{ v.last_service_val }} {{ v.unit }}</td>
                        <td>{{ v.interval }} {{ v.unit }}</td>
                        <td>
                            {% if rem <= 0 %}
                                <strong style="color:var(--danger);">{{ rem }} {{ v.unit }} (Overdue!)</strong>
                            {% elif (rem <= 200 and v.unit == 'KM') or (rem <= 20 and v.unit == 'Hours') %}
                                <strong style="color:var(--warning);">{{ rem }} {{ v.unit }} remaining</strong>
                            {% else %}
                                <strong style="color:var(--success);">{{ rem }} {{ v.unit }} remaining</strong>
                            {% endif %}
                        </td>
                        <td>
                            {% if rem <= 0 %}
                                <span class="badge badge-danger">⚠️ Due For Service</span>
                            {% elif (rem <= 200 and v.unit == 'KM') or (rem <= 20 and v.unit == 'Hours') %}
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

        <!-- 🔧 3. Spare Parts Log Form -->
        <div class="section-card">
            <h2>3. Add Spare Part Record</h2>
            <form action="/add_part" method="POST">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Spare Part Name</label>
                        <input type="text" name="part_name" placeholder="e.g. Engine Oil Filter" required>
                    </div>
                    <div class="form-group">
                        <label>Specification</label>
                        <input type="text" name="spec" placeholder="e.g. 15W-40 Heavy Duty" required>
                    </div>
                    <div class="form-group">
                        <label>Quantity</label>
                        <input type="number" name="qty" placeholder="e.g. 2" required>
                    </div>
                    <div class="form-group">
                        <label>Maintenance Date</label>
                        <input type="date" name="date" required>
                    </div>
                </div>
                <button type="submit" class="btn-submit">+ Record Spare Part Usage</button>
            </form>
        </div>

        <!-- 📋 4. Spare Parts History Table -->
        <div class="section-card">
            <h2>4. Spare Parts Usage History</h2>
            <table>
                <thead>
                    <tr>
                        <th>Spare Part Name</th>
                        <th>Specification</th>
                        <th>Quantity</th>
                        <th>Maintenance Date</th>
                    </tr>
                </thead>
                <tbody>
                    {% for p in parts %}
                    <tr>
                        <td><strong>{{ p.part_name }}</strong></td>
                        <td>{{ p.spec }}</td>
                        <td>{{ p.qty }}</td>
                        <td>{{ p.date }}</td>
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
    return render_template_string(
        HTML_TEMPLATE,
        vehicles=data.get("vehicles", []),
        parts=data.get("parts", [])
    )

@app.route('/add_vehicle', methods=['POST'])
def add_vehicle():
    data = load_data()
    unit_selection = request.form.get("unit_type")
    
    if unit_selection == "KM_5000":
        unit = "KM"
        interval = 5000.0
    else:
        unit = "Hours"
        interval = 250.0

    new_v = {
        "id": len(data["vehicles"]) + 1,
        "plate_no": request.form.get("plate_no"),
        "model": request.form.get("model"),
        "driver": request.form.get("driver"),
        "spec": request.form.get("spec"),
        "current_val": float(request.form.get("current_val")),
        "last_service_val": float(request.form.get("last_service_val")),
        "unit": unit,
        "interval": interval
    }
    data["vehicles"].append(new_v)
    save_data(data)
    return redirect(url_for('home'))

@app.route('/add_part', methods=['POST'])
def add_part():
    data = load_data()
    new_part = {
        "id": len(data["parts"]) + 1,
        "part_name": request.form.get("part_name"),
        "spec": request.form.get("spec"),
        "qty": int(request.form.get("qty")),
        "date": request.form.get("date")
    }
    data["parts"].append(new_part)
    save_data(data)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
