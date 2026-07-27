from flask import Flask, render_template_string, request, redirect, url_for, send_file, session
from datetime import datetime, timedelta
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = "steely_rmi_secret_key"

# In-memory mock database for testing and demonstration
garage_data = {
    "spare_parts": [
        {"id": 1, "part_name": "Fuel Filter", "spec": "FF-501", "for_vehicle": "Howo", "qty": 15, "unit_price": 450.00},
        {"id": 2, "part_name": "Brake Pad Set", "spec": "BP-902", "for_vehicle": "Genlyon", "qty": 8, "unit_price": 2400.00},
        {"id": 3, "part_name": "Alternator Belt", "spec": "PK-1240", "for_vehicle": "Howo", "qty": 12, "unit_price": 650.00}
    ],
    "maintenance_logs": []
}

def calculate_effective_hours(start_str, finish_str):
    try:
        s = datetime.strptime(start_str, "%Y-%m-%dT%H:%M")
        f = datetime.strptime(finish_str, "%Y-%m-%dT%H:%M")
        diff = (f - s).total_seconds() / 3600.0
        return round(max(0.0, diff), 2)
    except:
        return 0.0

def calculate_next_service(current_reading, unit):
    try:
        val = int(current_reading)
        if unit.upper() == "KM":
            return f"{val + 5000} KM"
        else:
            return f"{val + 250} Hours"
    except:
        return "N/A"

@app.route("/", methods=["GET"])
def index():
    user = {"name": "Dinberu Tefera", "role": "System Admin / Head of Mechanical Workshop"}
    
    start_date_str = request.args.get("start_date")
    end_date_str = request.args.get("end_date")
    
    logs = garage_data["maintenance_logs"]
    
    filtered_logs = logs
    if start_date_str and end_date_str:
        try:
            s_date = datetime.strptime(start_date_str, "%Y-%m-%d")
            e_date = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1)
            filtered_logs = [
                log for log in logs 
                if log.get("start_time") and s_date <= datetime.strptime(log["start_time"][:10], "%Y-%m-%d") < e_date
            ]
        except:
            pass

    def compute_summary_stats(log_list):
        total_jobs = len(log_list)
        pm_jobs = sum(1 for l in log_list if l.get("maintenance_type") == "PM")
        cm_jobs = sum(1 for l in log_list if l.get("maintenance_type") == "CM")
        inspection_jobs = sum(1 for l in log_list if l.get("maintenance_type") == "Inspection")
        
        total_work_hours = round(sum(l.get("effective_hours", 0.0) for l in log_list), 2)
        total_spare_qty = sum(sum(sp.get("qty", 0) for sp in l.get("replaced_spares", [])) for l in log_list)
        total_spares_cost = sum(sum(sp.get("total_cost", 0.0) for sp in l.get("replaced_spares", [])) for l in log_list)
        
        total_battery_qty = sum(l.get("battery_qty", 0) for l in log_list)
        total_battery_cost = sum(l.get("battery_cost", 0.0) for l in log_list)
        
        total_lubrication_qty = sum(l.get("lubrication_qty", 0.0) for l in log_list)
        total_lubrication_cost = sum(l.get("lubrication_cost", 0.0) for l in log_list)
        
        total_tire_qty = sum(l.get("tire_qty", 0) for l in log_list)
        total_tire_cost = sum(l.get("tire_cost", 0.0) for l in log_list)
        
        total_expenditure = total_spares_cost + total_battery_cost + total_lubrication_cost + total_tire_cost
        
        return {
            "total_jobs": total_jobs,
            "pm_jobs": pm_jobs,
            "cm_jobs": cm_jobs,
            "inspection_jobs": inspection_jobs,
            "total_work_hours": total_work_hours,
            "total_spare_qty": total_spare_qty,
            "total_spares_cost": total_spares_cost,
            "total_battery_qty": total_battery_qty,
            "total_battery_cost": total_battery_cost,
            "total_lubrication_qty": total_lubrication_qty,
            "total_lubrication_cost": total_lubrication_cost,
            "total_tire_qty": total_tire_qty,
            "total_tire_cost": total_tire_cost,
            "total_expenditure": total_expenditure
        }

    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)
    
    weekly_logs = [l for l in logs if l.get("start_time") and datetime.strptime(l["start_time"][:10], "%Y-%m-%d") >= seven_days_ago]
    monthly_logs = [l for l in logs if l.get("start_time") and datetime.strptime(l["start_time"][:10], "%Y-%m-%d") >= thirty_days_ago]
    
    weekly_summary = compute_summary_stats(weekly_logs)
    monthly_summary = compute_summary_stats(monthly_logs)
    
    return render_template_string(
        HTML_TEMPLATE, 
        user=user, 
        weekly=weekly_summary, 
        monthly=monthly_summary, 
        logs=filtered_logs, 
        inventory=garage_data["spare_parts"]
    )

@app.route("/add_work_order", methods=["POST"])
def add_work_order():
    try:
        sn = request.form.get("sn")
        wo_no = request.form.get("wo_no")
        vehicle = request.form.get("vehicle")
        model = request.form.get("model")
        reading_val = int(request.form.get("reading_value", 0))
        reading_unit = request.form.get("reading_unit", "KM")
        maintenance_type = request.form.get("maintenance_type", "PM")
        work_status = request.form.get("work_status", "Completed")
        driver = request.form.get("driver")
        technicians = request.form.get("technicians")
        emp_rank = request.form.get("emp_rank", "Junior Mechanic")
        start_time = request.form.get("start_time")
        finish_time = request.form.get("finish_time")
        description = request.form.get("description")
        
        effective_hours = calculate_effective_hours(start_time, finish_time)
        next_service_str = calculate_next_service(reading_val, reading_unit)
        
        spare_names = request.form.getlist("spare_name[]")
        spare_specs = request.form.getlist("spare_spec[]")
        spare_qtys = request.form.getlist("spare_qty[]")
        spare_prices = request.form.getlist("spare_price[]")
        
        replaced_spares = []
        for i in range(len(spare_names)):
            if spare_names[i].strip():
                q = int(spare_qtys[i]) if i < len(spare_qtys) and spare_qtys[i] else 1
                p = float(spare_prices[i]) if i < len(spare_prices) and spare_prices[i] else 0.0
                part_name = spare_names[i].strip()
                
                for inv_item in garage_data["spare_parts"]:
                    if inv_item["part_name"].lower() == part_name.lower():
                        inv_item["qty"] = max(0, inv_item["qty"] - q)
                        break

                replaced_spares.append({
                    "part_name": part_name,
                    "spec": spare_specs[i] if i < len(spare_specs) else "",
                    "qty": q,
                    "unit_price": p,
                    "total_cost": q * p
                })
        
        battery_qty = int(request.form.get("battery_qty", 0) or 0)
        battery_cost = float(request.form.get("battery_cost", 0.0) or 0.0)
        lubrication_qty = float(request.form.get("lubrication_qty", 0.0) or 0.0)
        lubrication_cost = float(request.form.get("lubrication_cost", 0.0) or 0.0)
        tire_qty = int(request.form.get("tire_qty", 0) or 0)
        tire_cost = float(request.form.get("tire_cost", 0.0) or 0.0)
        
        new_log = {
            "id": len(garage_data["maintenance_logs"]) + 1,
            "sn": sn,
            "wo_no": wo_no,
            "vehicle": vehicle,
            "model": model,
            "reading_value": reading_val,
            "reading_unit": reading_unit,
            "next_service": next_service_str,
            "driver": driver,
            "technicians": technicians,
            "emp_rank": emp_rank,
            "maintenance_type": maintenance_type,
            "work_status": work_status,
            "start_time": start_time.replace("T", " ") if start_time else "",
            "finish_time": finish_time.replace("T", " ") if finish_time else "",
            "effective_hours": effective_hours,
            "description": description,
            "replaced_spares": replaced_spares,
            "battery_qty": battery_qty,
            "battery_cost": battery_cost,
            "lubrication_qty": lubrication_qty,
            "lubrication_cost": lubrication_cost,
            "tire_qty": tire_qty,
            "tire_cost": tire_cost
        }
        
        garage_data["maintenance_logs"].insert(0, new_log)
    except Exception as e:
        print(f"Error adding work order: {e}")
        
    return redirect(url_for("index"))

@app.route("/add_inventory_item", methods=["POST"])
def add_inventory_item():
    try:
        part_name = request.form.get("part_name")
        spec = request.form.get("spec")
        for_vehicle = request.form.get("for_vehicle")
        qty = int(request.form.get("qty", 0))
        unit_price = float(request.form.get("unit_price", 0.0))
        
        new_item = {
            "id": len(garage_data["spare_parts"]) + 1,
            "part_name": part_name,
            "spec": spec,
            "for_vehicle": for_vehicle,
            "qty": qty,
            "unit_price": unit_price
        }
        
        garage_data["spare_parts"].append(new_item)
    except Exception as e:
        print(f"Error adding inventory item: {e}")
        
    return redirect(url_for("index"))

@app.route("/export/master_excel")
@app.route("/export/execution_excel")
def export_excel():
    logs = garage_data["maintenance_logs"]
    flat_data = []
    for log in logs:
        flat_data.append({
            "Serial No": log.get("sn"),
            "Work Order #": log.get("wo_no"),
            "Vehicle Plate": log.get("vehicle"),
            "Model": log.get("model"),
            "Current Reading": log.get("reading_value"),
            "Reading Unit": log.get("reading_unit"),
            "Next Service Alert": log.get("next_service"),
            "Maintenance Type": log.get("maintenance_type"),
            "Status": log.get("work_status"),
            "Technicians": log.get("technicians"),
            "Employee Rank": log.get("emp_rank"),
            "Start Time": log.get("start_time"),
            "Finish Time": log.get("finish_time"),
            "Effective Hours": log.get("effective_hours"),
            "Battery Cost (ETB)": log.get("battery_cost"),
            "Lubrication Cost (ETB)": log.get("lubrication_cost"),
            "Tire Cost (ETB)": log.get("tire_cost")
        })
    
    df = pd.DataFrame(flat_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Maintenance Logs")
    output.seek(0)
    
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"SteelY_Garage_Master_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    )

@app.route("/reset_all_logs")
def reset_all_logs():
    garage_data["maintenance_logs"] = []
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Main UI layout template string placeholder
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>SteelY R.M.I Garage Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <div class="container-fluid py-4">
        <h2 class="mb-4">SteelY R.M.I Garage Management Dashboard</h2>
        <p>Welcome, {{ user.name }} ({{ user.role }})</p>
        
        <!-- Summary Cards Layout -->
        <div class="row mb-4">
            <div class="col-md-6">
                <div class="card shadow-sm">
                    <div class="card-header bg-dark text-white fw-bold">📅 Weekly Summary (Last 7 Days)</div>
                    <div class="card-body">
                        <p>Total Jobs: <strong>{{ weekly.total_jobs }}</strong> (PM: {{ weekly.pm_jobs }}, CM: {{ weekly.cm_jobs }})</p>
                        <p>Total Work Hours: <strong>{{ weekly.total_work_hours }} hrs</strong></p>
                        <p>Total Expenditure: <strong class="text-danger">{{ "{:,.2f}".format(weekly.total_expenditure) }} ETB</strong></p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card shadow-sm">
                    <div class="card-header bg-dark text-white fw-bold">📊 Monthly Summary (Last 30 Days)</div>
                    <div class="card-body">
                        <p>Total Jobs: <strong>{{ monthly.total_jobs }}</strong> (PM: {{ monthly.pm_jobs }}, CM: {{ monthly.cm_jobs }})</p>
                        <p>Total Work Hours: <strong>{{ monthly.total_work_hours }} hrs</strong></p>
                        <p>Total Expenditure: <strong class="text-danger">{{ "{:,.2f}".format(monthly.total_expenditure) }} ETB</strong></p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Action Buttons -->
        <div class="mb-3">
            <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#inventoryModal">View Inventory</button>
            <button class="btn btn-success btn-sm" data-bs-toggle="modal" data-bs-target="#addInventoryModal">+ Add Spare Part</button>
            <a href="/export/master_excel" class="btn btn-secondary btn-sm">Export to Excel</a>
        </div>

        <!-- Inventory Modal -->
        <div class="modal fade" id="inventoryModal" tabindex="-1">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header bg-primary text-white">
                        <h5 class="modal-title fw-bold">⚙️ SteelY R.M.I Spare Parts Inventory</h5>
                        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <table class="table table-bordered table-sm">
                            <thead class="table-dark">
                                <tr>
                                    <th>ID</th>
                                    <th>Part Name</th>
                                    <th>Specification</th>
                                    <th>Vehicle Model</th>
                                    <th>Available Qty</th>
                                    <th>Unit Price (ETB)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for part in inventory %}
                                <tr>
                                    <td>{{ part.id }}</td>
                                    <td class="fw-bold">{{ part.part_name }}</td>
                                    <td>{{ part.spec }}</td>
                                    <td>{{ part.for_vehicle }}</td>
                                    <td class="fw-bold text-success">{{ part.qty }}</td>
                                    <td>{{ "{:,.2f}".format(part.unit_price) }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Add Spare Part Modal -->
        <div class="modal fade" id="addInventoryModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <form action="{{ url_for('add_inventory_item') }}" method="POST">
                        <div class="modal-header bg-success text-white">
                            <h5 class="modal-title fw-bold">➕ Add New Spare Part to Inventory</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Part Name</label>
                                <input type="text" name="part_name" class="form-control form-control-sm" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Specification</label>
                                <input type="text" name="spec" class="form-control form-control-sm" required>
                            </div>
                            <div class="mb-3">
                                <label class="form-label small fw-bold">Vehicle Model</label>
                                <input type="text" name="for_vehicle" class="form-control form-control-sm" placeholder="e.g., Howo / Genlyon">
                            </div>
                            <div class="row">
                                <div class="col-md-6 mb-3">
                                    <label class="form-label small fw-bold">Initial Quantity</label>
                                    <input type="number" name="qty" class="form-control form-control-sm" value="1" min="1" required>
                                </div>
                                <div class="col-md-6 mb-3">
                                    <label class="form-label small fw-bold">Unit Price (ETB)</label>
                                    <input type="number" step="0.01" name="unit_price" class="form-control form-control-sm" value="0.00" required>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button type="submit" class="btn btn-success btn-sm">Save Part</button>
                        </div>
                    </form>
                </div>
            </div>
        </div>

    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
