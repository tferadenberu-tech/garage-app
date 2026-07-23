import os
import json
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
                "interval_hours": 250.0,
                "unit": "Hours"
            },
            {
                "id": 2,
                "plate_no": "AA-3-A12345",
                "model": "Toyota Hilux Pick-up",
                "type": "Vehicle / Car",
                "driver": "Ato Tadesse",
                "spec": "5W-30 Synthetic Oil Filter Kit",
                "current_hours": 105000.0,
                "last_service_hours": 100000.0,
                "interval_hours": 5000.0,
                "unit": "KM"
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
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
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
            margin-top: 22px;
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
                <p>Equipment 250-Hour & Vehicle 5000-KM Oil Service Monitoring</p>
            </div>
            <div>
                <span class="badge badge-ok" style="font-size: 14px; padding: 8px 14px;">● System Active</span>
            </div>
        </div>

        <!-- 📝 1. Add Equipment & Vehicle Form -->
        <div class="section-card">
            <h2>1. Add Equipment / Vehicle</h2>
            
            <form action="/add_equipment" method="POST">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Plate No / ID</label>
                        <input type="text" name="plate_no" placeholder="e.g. EQUIP-003 or AA-2-C123" required>
                    </div>
                    <div class="form-group">
                        <label>Model</label>
                        <input type="text" name="model" placeholder="e.g. CAT Loader / Toyota Hilux" required>
                    </div>
                    <div class="form-group">
                        <label>Category Type</label>
                        <select name="type" required>
                            <option value="Loader">Loader</option>
                            <option value="Excavator">Excavator</option>
                            <option value="Vehicle / Car">Vehicle / Car</option>
                            <option value="Truck">Truck</option>
                            <option value="Forklift">Forklift</option>
                            <option value="Other Equipment">Other Equipment</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Driver / Operator</label>
                        <input type="text" name="driver" placeholder="Operator Name" required>
                    </div>
                    <div class="form-group">
                        <label>Spare Part Name (spec)</label>
                        <input type="text" name="spec" placeholder="e.g. Engine Oil & Filter Spec" required>
                    </div>
                    <div class="form-group">
                        <label>Current Meter Value</label>
                        <input type="number" step="0.1" name="current_hours" placeholder="Current Value" required>
                    </div>
                    <div class="form-group">
                        <label>Last Service Meter Value</label>
                        <input type="number" step="0.1" name="last_service_hours" placeholder="Last Service Value" required>
                    </div>
                    
                    <!-- 🎯 Service Interval Options (250 Hrs and 5000 KM Side-by-Side) -->
                    <div class="form-group">
                        <label>Service Interval</label>
                        <select name="interval_option" required>
                            <option value="250_Hours" selected>250 Hours (Equipment Oil Service)</option>
                            <option value="5000_KM">5,000 KM (Vehicle Oil Service)</option>
                            <option value="500_Hours">500 Hours (Heavy Duty Service)</option>
                            <option value="10000_KM">10,000 KM (Vehicle Long Service)</option>
                            <option value="1000_KM">1,000 KM (Break-in Service)</option>
                        </select>
                    </div>
                </div>
                <div style="margin-top: 15px;">
                    <button type="submit" class="btn-submit">+ Save Equipment / Vehicle</button>
                </div>
            </form>
        </div>

        <!-- 📊 2. Current Meter & Last Service Status Table -->
        <div class="section-card">
            <h2>2. Current Hours/KM & Last Service Status</h2>

            <table>
                <thead>
                    <tr>
                        <th>Plate No / ID</th>
                        <th>Model</th>
                        <th>Type</th>
                        <th>Driver</th>
                        <th>Spare Part Name (spec)</th>
                        <th>Current Meter</th>
                        <th>Last Service</th>
                        <th>Interval</th>
                        <th>Remaining</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for eq in equipments %}
                    {% set interval = eq.interval_hours if eq.interval_hours is defined else 250.0 %}
                    {% set unit = eq.unit if eq.unit is defined else 'Hours' %}
                    {% set next_due = eq.last_service_hours + interval %}
                    {% set rem = next_due - eq.current_hours %}
                    <tr>
                        <td><strong>{{ eq.plate_no }}</strong></td>
                        <td>{{ eq.model }}</td>
                        <td>{{ eq.type }}</td>
                        <td>{{ eq.driver }}</td>
                        <td>{{ eq.spec }}</td>
                        <td><strong>{{ eq.current_hours }} {{ unit }}</strong></td>
                        <td>{{ eq.last_service_hours }} {{ unit }}</td>
                        <td>{{ interval }} {{ unit }}</td>
                        <td>
                            {% if rem <= 0 %}
                                <strong style="color:var(--danger);">{{ rem }} {{ unit }} (Overdue!)</strong>
                            {% elif rem <= 30 %}
                                <strong style="color:var(--warning);">{{ rem }} {{ unit }} remaining</strong>
                            {% else %}
                                <strong style="color:var(--success);">{{ rem }} {{ unit }} remaining</strong>
                            {% endif %}
                        </td>
                        <td>
                            {% if rem <= 0 %}
                                <span class="badge badge-danger">⚠️ Due For Service</span>
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

    </div>
</body>
</html>
"""

@app.route('/')
def home():
    data = load_data()
    return render_template_string(
        HTML_TEMPLATE,
        equipments=data.get("equipments", [])
    )

@app.route('/add_equipment', methods=['POST'])
def add_equipment():
    data = load_data()
    
    interval_raw = request.form.get("interval_option", "250_Hours")
    if "_" in interval_raw:
        val_str, unit = interval_raw.split("_")
        interval_hours = float(val_str)
    else:
        interval_hours = 250.0
        unit = "Hours"

    new_eq = {
        "id": len(data["equipments"]) + 1,
        "plate_no": request.form.get("plate_no"),
        "model": request.form.get("model"),
        "type": request.form.get("type"),
        "driver": request.form.get("driver"),
        "spec": request.form.get("spec"),
        "current_hours": float(request.form.get("current_hours")),
        "last_service_hours": float(request.form.get("last_service_hours")),
        "interval_hours": interval_hours,
        "unit": unit
    }
    data["equipments"].append(new_eq)
    save_data(data)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
