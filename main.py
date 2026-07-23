from flask import Flask, render_template_string, request, redirect, url_for
import json
import os

app = Flask(__name__)

DATA_FILE = "garage_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return [
        {
            "id": 1,
            "plate_no": "AA-3-A12345",
            "model": "Toyota Hilux",
            "driver": "Ato Tadesse",
            "spec": "5W-30 Oil Filter Set",
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
            "spec": "15W-40 Heavy Duty Oil Filter",
            "current_val": 3420.0,
            "last_service_val": 3250.0,
            "unit": "Hours",
            "interval": 250.0
        }
    ]

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="am">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I Garage Maintnace dash Bord</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; }
        .container { max-width: 1250px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.08); }
        h1 { color: #1e3a8a; text-align: center; border-bottom: 3px solid #1e3a8a; padding-bottom: 10px; margin-bottom: 25px; font-size: 24px; }
        
        .form-card { background: #f1f5f9; padding: 20px; border-radius: 8px; margin-bottom: 25px; border: 1px solid #cbd5e1; }
        .form-card h3 { margin-top: 0; color: #1e3a8a; }
        .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }
        .form-group { display: flex; flex-direction: column; gap: 5px; }
        .form-group label { font-size: 13px; font-weight: bold; color: #334155; }
        input, select { padding: 9px; border: 1px solid #cbd5e1; border-radius: 5px; font-size: 14px; }
        .btn-add { background: #1e3a8a; color: white; border: none; padding: 10px 20px; border-radius: 5px; font-weight: bold; cursor: pointer; margin-top: 15px; }
        .btn-add:hover { background: #2563eb; }

        table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; }
        th, td { border: 1px solid #cbd5e1; padding: 12px; text-align: left; }
        th { background-color: #1e3a8a; color: white; }
        tr:nth-child(even) { background-color: #f8fafc; }
        
        .badge-ok { background-color: #dcfce7; color: #15803d; font-weight: bold; padding: 4px 8px; border-radius: 12px; }
        .badge-alert { background-color: #fee2e2; color: #b91c1c; font-weight: bold; padding: 4px 8px; border-radius: 12px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>SteelY R.M.I Garage Maintnace dash Bord</h1>

        <!-- 📝 1. ተሽከርካሪ መመዝገቢያ (KM / Hours መመሪያ ምርጫ ያለው) -->
        <div class="form-card">
            <h3>1. አዲስ ተሽከርካሪ መመዝገቢያ (Add Vehicle)</h3>
            <form action="/add" method="POST">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Plate No / ID</label>
                        <input type="text" name="plate_no" placeholder="ምሳሌ፦ AA-2-C1234" required>
                    </div>
                    <div class="form-group">
                        <label>Model</label>
                        <input type="text" name="model" placeholder="ምሳሌ፦ Toyota Hilux / CAT Loader" required>
                    </div>
                    <div class="form-group">
                        <label>Driver / Operator</label>
                        <input type="text" name="driver" placeholder="የአሽከርካሪው ስም" required>
                    </div>
                    <div class="form-group">
                        <label>Spare Part Name (spec)</label>
                        <input type="text" name="spec" placeholder="የዘይት/ፊልተር አይነት" required>
                    </div>
                    <div class="form-group">
                        <label>Current Value (የአሁኑ ቁጥር)</label>
                        <input type="number" step="0.1" name="current_val" placeholder="የአሁኑ KM ወይም Hours" required>
                    </div>
                    <div class="form-group">
                        <label>Last Service Value (የመጨረሻ ሰርቪስ)</label>
                        <input type="number" step="0.1" name="last_service_val" placeholder="የመጨረሻ ሰርቪስ የተደረገበት" required>
                    </div>
                    <div class="form-group">
                        <label>የመከታተያ መስፈርት (Unit & Interval)</label>
                        <select name="unit_type" required>
                            <option value="KM_5000">KM (ለ 5,000 KM)</option>
                            <option value="Hours_250">Hours (ለ 250 Hours)</option>
                        </select>
                    </div>
                </div>
                <button type="submit" class="btn-add">+ መዝግብ (Save)</button>
            </form>
        </div>

        <!-- 📊 2. የሰርቪስ መከታተያ ሰንጠረዥ -->
        <h3>2. Maintenance Status Tracking (KM / Hours)</h3>
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
                {% set remaining = next_due - v.current_val %}
                <tr>
                    <td><strong>{{ v.plate_no }}</strong></td>
                    <td>{{ v.model }}</td>
                    <td>{{ v.driver }}</td>
                    <td>{{ v.spec }}</td>
                    <td style="background-color: #e0f2fe;"><strong>{{ v.current_val }} {{ v.unit }}</strong></td>
                    <td>{{ v.last_service_val }} {{ v.unit }}</td>
                    <td>{{ v.interval }} {{ v.unit }}</td>
                    <td>
                        {% if remaining <= 0 %}
                            <strong style="color:red;">{{ remaining }} {{ v.unit }} (Overdue!)</strong>
                        {% else %}
                            <strong style="color:green;">{{ remaining }} {{ v.unit }} remaining</strong>
                        {% endif %}
                    </td>
                    <td>
                        {% if remaining <= 50 and v.unit == 'KM' or remaining <= 10 and v.unit == 'Hours' %}
                            <span class="badge-alert">⚠️ Service Needed</span>
                        {% else %}
                            <span class="badge-ok">✅ Normal</span>
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    vehicles = load_data()
    return render_template_string(HTML_TEMPLATE, vehicles=vehicles)

@app.route('/add', methods=['POST'])
def add_vehicle():
    vehicles = load_data()
    unit_selection = request.form.get("unit_type")
    
    if unit_selection == "KM_5000":
        unit = "KM"
        interval = 5000.0
    else:
        unit = "Hours"
        interval = 250.0

    new_v = {
        "id": len(vehicles) + 1,
        "plate_no": request.form.get("plate_no"),
        "model": request.form.get("model"),
        "driver": request.form.get("driver"),
        "spec": request.form.get("spec"),
        "current_val": float(request.form.get("current_val")),
        "last_service_val": float(request.form.get("last_service_val")),
        "unit": unit,
        "interval": interval
    }
    vehicles.append(new_v)
    save_data(vehicles)
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
