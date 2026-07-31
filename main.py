import os
import io
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, session, send_file

app = Flask(__name__)
app.secret_key = 'steely_garage_secret_key'

# ለጊዜው የሚያገለግል የናሙና መረጃ (Data) እና የይለፍ ቃል
USER_CREDENTIALS = {'admin': 'steely123'}

# የናሙና የጋራዥ መረጃዎች (Executive Report Data)
garage_data = [
    {"ID": 1, "Vehicle": "Genlyon (3-A66865)", "Maintenance_Type": "Engine Overhaul", "Status": "Completed", "Date": "2026-05-11"},
    {"ID": 2, "Vehicle": "Generator 24V", "Maintenance_Type": "Solenoid Replacement", "Status": "Completed", "Date": "2026-06-17"},
    {"ID": 3, "Vehicle": "Rolling Mill Stand", "Maintenance_Type": "Bearing Check", "Status": "Pending", "Date": "2026-07-28"}
]

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password:
            session['user'] = username
            return redirect(url_for('dashboard'))
        else:
            error = 'የተሳሳተ መግቢያ ስም ወይም የይለፍ ቃል። እባክዎ እንደገና ይሞክሩ።'
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Steely R.M.I - Login</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
            .login-box { background: #1e1e1e; padding: 30px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); width: 300px; text-align: center; }
            input { width: 100%; padding: 10px; margin: 10px 0; background: #2a2a2a; border: 1px solid #444; color: #fff; border-radius: 4px; }
            button { width: 100%; padding: 10px; background: #4CAF50; border: none; color: white; font-weight: bold; border-radius: 4px; cursor: pointer; }
            button:hover { background: #45a049; }
            .error { color: #ff5252; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="login-box">
            <h2>Steely R.M.I Garage</h2>
            <p>እባክዎ ይግቡ</p>
            {% if error %}<p class="error">{{ error }}</p>{% endif %}
            <form method="POST">
                <input type="text" name="username" placeholder="የተጠቃሚ ስም (Username)" required>
                <input type="password" name="password" placeholder="የይለፍ ቃል (Password)" required>
                <button type="submit">ግባ (Login)</button>
            </form>
        </div>
    </body>
    </html>
    ''', error=error)

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Steely R.M.I - Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #121212; color: #ffffff; margin: 0; padding: 20px; }
            .header { display: flex; justify-content: space-between; align-items: center; background: #1e1e1e; padding: 15px 20px; border-radius: 8px; }
            .btn { background: #ff5252; color: white; padding: 8px 15px; text-decoration: none; border-radius: 4px; font-weight: bold; }
            .btn-excel { background: #4CAF50; margin-right: 10px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; background: #1e1e1e; }
            th, td { padding: 12px; border: 1px solid #333; text-align: left; }
            th { background: #2a2a2a; color: #4CAF50; }
            .content { margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Steely R.M.I Garage & Workshop Dashboard</h2>
            <div>
                <a href="/download/excel" class="btn btn-excel">Excel ሪፖርት አውርድ</a>
                <a href="/logout" class="btn">ውጣ (Logout)</a>
            </div>
        </div>
        <div class="content">
            <h3>የቅርብ ጊዜ የጥገና ሪፖርቶች (Executive Report)</h3>
            <table>
                <tr>
                    <th>ተ.ቁ</th>
                    <th>ተሽከርካሪ / ማሽን</th>
                    <th>የጥገና ዓይነት</th>
                    <th>ሁኔታ</th>
                    <th>ቀን</th>
                </tr>
                {% for row in data %}
                <tr>
                    <td>{{ row.ID }}</td>
                    <td>{{ row.Vehicle }}</td>
                    <td>{{ row.Maintenance_Type }}</td>
                    <td>{{ row.Status }}</td>
                    <td>{{ row.Date }}</td>
                </tr>
                {% endfor %}
            </table>
        </div>
    </body>
    </html>
    ''', data=garage_data)

@app.route('/download/excel')
def download_excel():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    df = pd.DataFrame(garage_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Garage_Report')
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                     as_attachment=True, download_name='Steely_Garage_Executive_Report.xlsx')

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
