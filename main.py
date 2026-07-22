import os
from flask import Flask, render_template_string, request, redirect, url_for

app = Flask(__name__)

# ተሽከርካሪዎች እና የ250 ሰዓት የዘይት ሰርቪስ መከታተያ መረጃዎች
EQUIPMENT_LIST = [
    {
        "id": 1,
        "name": "CAT Loader 950H",
        "type": "Loader",
        "spec": "Engine Oil & Filter Change (250 Hrs)",
        "current_hours": 3420,
        "last_service_hours": 3250
    },
    {
        "id": 2,
        "name": "Komatsu Excavator PC200",
        "type": "Excavator",
        "spec": "Hydraulic & Engine Service (250 Hrs)",
        "current_hours": 1890,
        "last_service_hours": 1650
    }
]

# HTML እና CSS ዳሽቦርድ ዲዛይን
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="am">
<head>
    <meta charset="UTF-8">
    <title>SteelY R.M.I Garage Maintnace dash Bord</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        h1 { color: #1e3a8a; text-align: center; border-bottom: 3px solid #1e3a8a; padding-bottom: 10px; margin-bottom: 25px; }
        .card-form { background: #eef2ff; padding: 20px; border-radius: 8px; margin-bottom: 30px; border: 1px solid #c7d2fe; }
        .form-group { display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 15px; }
        input, select { padding: 10px; border: 1px solid #ccc; border-radius: 5px; flex: 1; min-width: 180px; font-size: 14px; }
        button { background-color: #1e3a8a; color: white; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; }
        button:hover { background-color: #1e40af; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
        th { background-color: #1e3a8a; color: white; }
        .status-ok { background-color: #d1fae5; color: #065f46; font-weight: bold; padding: 4px 8px; border-radius: 4px; }
        .status-alert { background-color: #fee2e2; color: #991b1b; font-weight: bold; padding: 4px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>SteelY R.M.I Garage Maintnace dash Bord</h1>

        <!-- አዲስ ተሽከርካሪ እና ሰርቪስ ማስገቢያ -->
        <div class="card-form">
            <h3>📌 አዲስ Equipment / 250 Hrs Service መመዝገቢያ</h3>
            <form action="/add" method="POST">
                <div class="form-group">
                    <input type="text" name="name" placeholder="ተሽከርካሪ (ምሳሌ፡ CAT Loader)" required>
                    <select name="type" required>
                        <option value="Loader">Loader (ሎደር)</option>
                        <option value="Excavator">Excavator (እስካቫተር)</option>
                        <option value="Other">Other Equipment</option>
                    </select>
                    <input type="text" name="spec" placeholder="Spare Part Name / Spec" required>
                </div>
                <div class="form-group">
                    <input type="number" name="current_hours" placeholder="Current Hour Meter" required>
                    <input type="number" name="last_service_hours" placeholder="Last Service Hour Meter" required>
                    <button type="submit">መዝግብ / Add Equipment</button>
                </div>
            </form>
        </div>

        <!-- የመረጃ ሠንጠረዥ -->
        <h3>🚜 Equipment 250-Hour Oil Service Tracking List</h3>
        <table>
            <thead>
                <tr>
                    <th>ተሽከርካሪ (Equipment Name)</th>
                    <th>ዓይነት (Type)</th>
                    <th>Spare Part Name (Spec)</th>
                    <th>Current Hour Meter</th>
                    <th>Last Service Hour</th>
                    <th>Next Service Due</th>
                    <th>Remaining Hours</th>
                    <th>Status (250h Rule)</th>
                </tr>
            </thead>
            <tbody>
                {% for item in equipments %}
                {% set next_service = item.last_service_hours + 250 %}
                {% set remaining = next_service - item.current_hours %}
                <tr>
                    <td><strong>{{ item.name }}</strong></td>
                    <td>{{ item.type }}</td>
                    <td>{{ item.spec }}</td>
                    <td>{{ item.current_hours }} hrs</td>
                    <td>{{ item.last_service_hours }} hrs</td>
                    <td>{{ next_service }} hrs</td>
                    <td>
                        {% if remaining <= 0 %}
                            <span style="color:red; font-weight:bold;">{{ remaining }} hrs (አልፏል!)</span>
                        {% else %}
                            <span style="color:green; font-weight:bold;">{{ remaining }} hrs ይቀራል</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if remaining <= 20 %}
                            <span class="status-alert">⚠️ Service Needed!</span>
                        {% else %}
                            <span class="status-ok">✅ Normal</span>
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
    return render_template_string(HTML_TEMPLATE, equipments=EQUIPMENT_LIST)

@app.route('/add', methods=['POST'])
def add_equipment():
    new_id = len(EQUIPMENT_LIST) + 1
    new_item = {
        "id": new_id,
        "name": request.form.get('name'),
        "type": request.form.get('type'),
        "spec": request.form.get('spec'),
        "current_hours": float(request.form.get('current_hours')),
        "last_service_hours": float(request.form.get('last_service_hours'))
    }
    EQUIPMENT_LIST.append(new_item)
    return redirect(url_for('home'))

if __name__ == '__main__':
    # በበለጠ ቀላል በሆነው Flask ሰርቨር ማስነሳት
    print("\n--- SteelY R.M.I Garage System Starting ---")
    app.run(host='127.0.0.1', port=5000, debug=True)
