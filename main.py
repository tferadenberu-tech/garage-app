import io
import json
from datetime import datetime, timedelta
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, send_file, session

app = Flask(__name__)
app.secret_key = "steely_garage_secret_key"

# --- In-Memory System Database ---
garage_data = {
    "spare_parts": [
        {"id": 1, "part_name": "Oil Filter", "spec": "LF16015 / Heavy Duty", "used_for": "Sino Truck 371 Engine", "qty": 20, "unit_price": 1200.00},
        {"id": 2, "part_name": "Fuel Filter", "spec": "FF5421 / High Efficiency", "used_for": "Isuzu NPR Fuel System", "qty": 15, "unit_price": 1800.00},
        {"id": 3, "part_name": "Brake Shoe Set", "spec": "Rear Axle / Heavy Duty Standard", "used_for": "FSR Braking System", "qty": 8, "unit_price": 4500.00}
    ],
    "maintenance_logs": [
        {
            "id": 1,
            "sn": "SN-001",
            "wo_no": "WO-2026-001",
            "vehicle": "AA-3-12345",
            "model": "Sino Truck 371",
            "reading_value": 124500,
            "reading_unit": "KM",
            "next_service": "129,500 KM (+5000)",
            "driver": "አለማየሁ ተ.",
            "technicians": "አቶ ምህረት, አቶ ኢብራሂም",
            "type": "PM",
            "work_status": "Completed",
            "start_time": "2026-07-20 08:00",
            "finish_time": "2026-07-20 14:30",
            "effective_hours": 6.5,
            "description": "Engine Oil & Filter Change",
            "replaced_spares": [
                {"part_name": "Oil Filter", "spec": "LF16015", "qty": 1, "unit_price": 1200.0, "total_cost": 1200.0},
                {"part_name": "Fuel Filter", "spec": "FF5421", "qty": 1, "unit_price": 1800.0, "total_cost": 1800.0}
            ],
            "battery_qty": 1, "battery_cost": 15000.0, "battery_spec": "150Ah",
            "lubrication_qty": 20.0, "lubrication_cost": 4500.0, "lubrication_spec": "SAE 15W40",
            "tire_qty": 0, "tire_cost": 0.0, "tire_spec": ""
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
        return 0.0

def calculate_next_service(val, unit):
    try:
        val_int = int(val)
    except:
        return "N/A"
    
    if unit == "Hour":
        next_val = val_int + 250
        return f"{next_val:,} Hours (+250)"
    else:
        next_val = val_int + 5000
        return f"{next_val:,} KM (+5000)"

def get_summary_stats(days=None, start_date=None, end_date=None):
    logs = garage_data["maintenance_logs"]
    
    # Filter by date range if provided
    filtered_logs = []
    now = datetime.now()
    
    for log in logs:
        log_date_str = log["start_time"].split(" ")[0]
        try:
            log_date = datetime.strptime(log_date_str, "%Y-%m-%d")
        except:
            continue
            
        include = True
        if start_date and end_date:
            try:
                s_d = datetime.strptime(start_date, "%Y-%m-%d")
                e_d = datetime.strptime(end_date, "%Y-%m-%d")
                if not (s_d <= log_date <= e_d):
                    include = False
            except:
                pass
        elif days is not None:
            if (now - log_date).days > days:
                include = False
                
        if include:
            filtered_logs.append(log)

    total_jobs = len(filtered_logs)
    pm_jobs = sum(1 for l in filtered_logs if l.get("type", "PM") == "PM")
    cm_jobs = sum(1 for l in filtered_logs if l.get("type") == "CM")
    total_work_hours = sum(l.get("effective_hours", 0.0) for l in filtered_logs)
    
    total_spare_qty = 0
    total_spares_cost = 0.0
    for l in filtered_logs:
        for sp in l.get("replaced_spares", []):
            total_spare_qty += sp.get("qty", 0)
            total_spares_cost += sp.get("total_cost", 0.0)
            
    total_lubrication_qty = sum(l.get("lubrication_qty", 0.0) for l in filtered_logs)
    total_lubrication_cost = sum(l.get("lubrication_cost", 0.0) for l in filtered_logs)
    total_battery_cost = sum(l.get("battery_cost", 0.0) for l in filtered_logs)
    total_tire_cost = sum(l.get("tire_cost", 0.0) for l in filtered_logs)
    
    total_expenditure = total_spares_cost + total_lubrication_cost + total_battery_cost + total_tire_cost

    return {
        "total_jobs": total_jobs,
        "pm_jobs": pm_jobs,
        "cm_jobs": cm_jobs,
        "total_work_hours": round(total_work_hours, 2),
        "total_spare_qty": total_spare_qty,
        "total_spares_cost": total_spares_cost,
        "total_lubrication_qty": total_lubrication_qty,
        "total_lubrication_cost": total_lubrication_cost,
        "total_battery_cost": total_battery_cost,
        "total_tire_cost": total_tire_cost,
        "total_expenditure": total_expenditure
    }

# --- Frontend HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I Garage Maintnace dash Bord</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        :root {
            --bg-main: #f8fafc;
            --sidebar-bg: #090d16;
            --accent-blue: #2563eb;
            --accent-cyan: #0ea5e9;
            --card-bg: #ffffff;
            --text-main: #1e293b;
            --text-muted: #64748b;
        }
        body { font-family: 'Inter', 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: var(--bg-main); color: var(--text-main); }
        
        .sidebar { background: linear-gradient(180deg, #090d16 0%, #111827 100%); min-height: 100vh; color: #94a3b8; padding: 30px 18px; box-shadow: 4px 0 20px rgba(0,0,0,0.08); border-right: 1px solid rgba(255,255,255,0.05); }
        .sidebar .brand-title { color: #f8fafc; font-size: 1.5rem; font-weight: 800; margin-bottom: 4px; letter-spacing: -0.5px; }
        .admin-badge { background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%); color: white; font-size: 0.68rem; font-weight: 700; padding: 4px 10px; border-radius: 6px; display: inline-block; margin-bottom: 25px; text-transform: uppercase; letter-spacing: 0.8px; box-shadow: 0 2px 5px rgba(37,99,235,0.3); }
        
        .btn-export-main { background: linear-gradient(135deg, #059669 0%, #047857 100%); color: white; font-weight: 600; border: none; border-radius: 10px; width: 100%; text-align: left; padding: 12px 16px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(5,150,105,0.2); transition: all 0.2s ease; }
        .btn-export-main:hover { background: linear-gradient(135deg, #047857 100%, #065f46 100%); color: white; transform: translateY(-1px); }
        
        .nav-link-custom { color: #94a3b8; text-decoration: none; display: flex; align-items: center; gap: 12px; padding: 12px 16px; font-size: 0.93rem; font-weight: 500; border-radius: 10px; margin-bottom: 8px; transition: all 0.2s ease; }
        .nav-link-custom:hover { background-color: rgba(37, 99, 235, 0.12); color: #60a5fa; transform: translateX(3px); }
        
        .main-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 25px; background: var(--card-bg); padding: 22px 30px; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 2px 10px rgba(0,0,0,0.01); }
        .main-title { font-size: 1.7rem; font-weight: 800; color: #0f172a; margin-bottom: 2px; letter-spacing: -0.5px; }
        .main-subtitle { color: var(--text-muted); font-size: 0.88rem; font-weight: 500; }
        
        .top-user-panel { display: flex; align-items: center; gap: 18px; }
        .user-box { text-align: right; border-right: 2px solid #f1f5f9; padding-right: 18px; }
        .user-name { font-weight: 700; color: #1e293b; display: block; font-size: 0.92rem; }
        .user-role { background-color: #2563eb; color: white; font-size: 0.65rem; font-weight: 700; padding: 2px 8px; border-radius: 4px; text-transform: uppercase; letter-spacing: 0.5px; }
        
        .btn-header-logout { background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white; font-weight: 600; padding: 9px 18px; border-radius: 10px; text-decoration: none; font-size: 0.88rem; box-shadow: 0 2px 6px rgba(239,68,68,0.2); }
        .btn-header-export { background: linear-gradient(135deg, #059669 0%, #047857 100%); color: white; font-weight: 600; padding: 9px 18px; border-radius: 10px; text-decoration: none; font-size: 0.88rem; box-shadow: 0 2px 6px rgba(5,150,105,0.2); }

        .summary-card { background: var(--card-bg); border-radius: 16px; padding: 24px; border: 1px solid #e2e8f0; box-shadow: 0 4px 15px -3px rgba(0,0,0,0.03); transition: transform 0.2s ease; }
        .summary-card:hover { transform: translateY(-2px); }
        .summary-card h6 { color: #2563eb; font-weight: 700; font-size: 0.82rem; border-bottom: 2px solid #eff6ff; padding-bottom: 12px; margin-bottom: 18px; text-transform: uppercase; letter-spacing: 0.5px; }
        .stat-line { font-size: 0.92rem; margin-bottom: 10px; color: #475569; font-weight: 500; }
        .cost-line { color: #047857; font-weight: 700; font-size: 1.05rem; margin-top: 15px; background: #ecfdf5; padding: 10px 14px; border-radius: 8px; display: inline-block; border: 1px solid #d1fae5; }
        
        table.table thead.table-water-blue, 
        .table-water-blue { 
            background: #0284c7 !important; 
            background-color: #0284c7 !important; 
        }
        table.table thead.table-water-blue th, 
        .table-water-blue th { 
            background-color: #0284c7 !important; 
            color: #ffffff !important; 
            font-weight: 700 !important; 
            border-color: #0284c7 !important; 
        }

        .btn-primary { background-color: #2563eb; border: none; border-radius: 8px; font-weight: 600; padding: 8px 16px; box-shadow: 0 2px 5px rgba(37,99,235,0.2); }
        .btn-primary:hover { background-color: #1d4ed8; }
        .form-control, .form-select { border-radius: 8px; border-color: #cbd5e1; padding: 9px 12px; font-size: 0.9rem; }
        .form-control:focus, .form-select:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.15); }
    </style>
</head>
<body>
<div class="container-fluid p-0">
    <div class="row g-0">
        
        <!-- Left Sidebar Navigation -->
        <div class="col-md-2 sidebar">
            <div class="brand-title">SteelY R.M.I</div>
            <div class="admin-badge">⚡ System Admin</div>
            
            <a href="/export/master_excel" class="btn btn-export-main shadow-sm">
                📊 Export Master Excel
            </a>

            <nav class="mt-2">
                <a href="#summary-section" class="nav-link-custom">📊 Summaries & Filter</a>
                <a href="#create-wo-section" class="nav-link-custom">➕ Create Work Order</a>
                <a href="#execution-log-section" class="nav-link-custom">🛠️ Execution & Log</a>
                <a href="#" class="nav-link-custom" data-bs-toggle="modal" data-bs-target="#inventoryModal">⚙️ Store Spare Inventory</a>
            </nav>
        </div>

        <!-- Right Main Workspace -->
        <div class="col-md-10 p-4">
            
            <!-- Top Header Banner -->
            <div class="main-header">
                <div>
                    <h1 class="main-title">SteelY R.M.I Garage Maintnace dash Bord</h1>
                    <div class="main-subtitle">Integrated Work Time, Consumables & Maintenance Tracking Platform</div>
                </div>
                <div class="top-user-panel">
                    <div class="user-box">
                        <span class="user-name">{{ user.name }}</span>
                        <span class="user-role">{{ user.role }}</span>
                    </div>
                    <button type="button" class="btn btn-primary btn-sm fw-bold shadow-sm" data-bs-toggle="modal" data-bs-target="#inventoryModal">⚙️ Store Spare Inventory</button>
                    <a href="/export/master_excel" class="btn-header-export shadow-sm">📊 Export Excel</a>
                    <a href="/logout" class="btn-header-logout shadow-sm">🚪 Logout</a>
                </div>
            </div>

            <!-- Top Summary Cards -->
            <div class="row g-3 mb-4" id="summary-section">
                <div class="col-md-6">
                    <div class="summary-card">
                        <h6>WEEKLY SUMMARY (LAST 7 DAYS)</h6>
                        <div class="stat-line">Total Jobs Executed: <strong>{{ weekly.total_jobs }}</strong></div>
                        <div class="p-2 bg-light rounded mb-2 border">
                            <div class="stat-line text-muted mb-1">• Preventive Maintenance (PM): <strong>{{ weekly.pm_jobs }}</strong></div>
                            <div class="stat-line text-muted mb-1">• Corrective Maintenance (CM): <strong>{{ weekly.cm_jobs }}</strong></div>
                            <div class="stat-line text-muted mb-0">• Inspection & Checkup: <strong>0</strong></div>
                        </div>
                        <div class="stat-line text-primary fw-bold">Total Effective Work Time: <strong>{{ weekly.total_work_hours }} hrs</strong></div>
                        <hr class="my-2">
                        <div class="stat-line">Spare Parts Quantity: <strong>{{ weekly.total_spare_qty }} Pcs</strong></div>
                        <div class="stat-line">Spare Parts Cost: <strong>ETB {{ "{:,.2f}".format(weekly.total_spares_cost) }}</strong></div>
                        <div class="stat-line">Lubricants Volume: <strong>{{ weekly.total_lubrication_qty }} Liters</strong></div>
                        <div class="stat-line">Lubricants Cost: <strong>ETB {{ "{:,.2f}".format(weekly.total_lubrication_cost) }}</strong></div>
                        <div class="stat-line">Batteries Cost: <strong>ETB {{ "{:,.2f}".format(weekly.total_battery_cost) }}</strong></div>
                        <div class="stat-line">Tires Cost: <strong>ETB {{ "{:,.2f}".format(weekly.total_tire_cost) }}</strong></div>
                        <div class="cost-line w-100 text-center">Total Expenditure: ETB {{ "{:,.2f}".format(weekly.total_expenditure) }}</div>
                    </div>
                </div>

                <div class="col-md-6">
                    <div class="summary-card">
                        <h6>MONTHLY SUMMARY (LAST 30 DAYS)</h6>
                        <div class="stat-line">Total Jobs Executed: <strong>{{ monthly.total_jobs }}</strong></div>
                        <div class="p-2 bg-light rounded mb-2 border">
                            <div class="stat-line text-muted mb-1">• Preventive Maintenance (PM): <strong>{{ monthly.pm_jobs }}</strong></div>
                            <div class="stat-line text-muted mb-1">• Corrective Maintenance (CM): <strong>{{ monthly.cm_jobs }}</strong></div>
                            <div class="stat-line text-muted mb-0">• Inspection & Checkup: <strong>0</strong></div>
                        </div>
                        <div class="stat-line text-primary fw-bold">Total Effective Work Time: <strong>{{ monthly.total_work_hours }} hrs</strong></div>
                        <hr class="my-2">
                        <div class="stat-line">Spare Parts Quantity: <strong>{{ monthly.total_spare_qty }} Pcs</strong></div>
                        <div class="stat-line">Spare Parts Cost: <strong>ETB {{ "{:,.2f}".format(monthly.total_spares_cost) }}</strong></div>
                        <div class="stat-line">Lubricants Volume: <strong>{{ monthly.total_lubrication_qty }} Liters</strong></div>
                        <div class="stat-line">Lubricants Cost: <strong>ETB {{ "{:,.2f}".format(monthly.total_lubrication_cost) }}</strong></div>
                        <div class="stat-line">Batteries Cost: <strong>ETB {{ "{:,.2f}".format(monthly.total_battery_cost) }}</strong></div>
                        <div class="stat-line">Tires Cost: <strong>ETB {{ "{:,.2f}".format(monthly.total_tire_cost) }}</strong></div>
                        <div class="cost-line w-100 text-center">Total Expenditure: ETB {{ "{:,.2f}".format(monthly.total_expenditure) }}</div>
                    </div>
                </div>
            </div>

            <!-- Date Range Filter & Reset Bar -->
            <div class="summary-card mb-4 bg-white border shadow-sm">
                <form method="GET" action="/" class="row g-3 align-items-end">
                    <div class="col-md-3">
                        <label class="form-label small fw-bold text-dark">📅 Filter From Date:</label>
                        <input type="date" name="start_date" class="form-control form-control-sm" value="{{ request.args.get('start_date', '') }}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label small fw-bold text-dark">📅 Filter To Date:</label>
                        <input type="date" name="end_date" class="form-control form-control-sm" value="{{ request.args.get('end_date', '') }}">
                    </div>
                    <div class="col-md-3">
                        <button type="submit" class="btn btn-primary btn-sm fw-bold px-4 shadow-sm">🔍 Filter Report</button>
                        <a href="/" class="btn btn-outline-secondary btn-sm ms-2 px-3">Reset Filter</a>
                    </div>
                    <div class="col-md-3 text-end">
                        <a href="/reset_all_logs" class="btn btn-outline-danger btn-sm fw-bold shadow-sm" onclick="return confirm('Are you sure you want to reset/clear all execution logs?');">🔄 Reset All Logs</a>
                    </div>
                </form>
            </div>

            <!-- Form: Create New Work Order -->
            <div class="summary-card mb-4" id="create-wo-section">
                <div class="form-section-title text-primary fw-bold mb-3 fs-5">
                    📄 Create New Work Order
                </div>
                <form action="/add_work_order" method="POST" id="wo-form">
                    <div class="row g-3">
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Serial Number (S/N):</label>
                            <input type="text" name="sn" class="form-control form-control-sm" placeholder="e.g. SN-002" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Work Order No:</label>
                            <input type="text" name="wo_no" class="form-control form-control-sm" placeholder="e.g. WO-2026-002" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Vehicle Plate Number:</label>
                            <input type="text" name="vehicle" class="form-control form-control-sm" placeholder="e.g. AA-3-12345" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Vehicle Type / Model:</label>
                            <input type="text" name="model" class="form-control form-control-sm" placeholder="e.g. Sino Truck 371">
                        </div>
                        
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-danger">Current Reading:</label>
                            <input type="number" name="reading_value" class="form-control form-control-sm border-danger" placeholder="e.g. 125000" required>
                        </div>
                        <div class="col-md-2">
                            <label class="form-label small fw-bold text-danger">Reading Unit:</label>
                            <select name="reading_unit" class="form-select form-select-sm border-danger" required>
                                <option value="KM">KM (+5000)</option>
                                <option value="Hour">Hour (+250)</option>
                            </select>
                        </div>

                        <div class="col-md-2">
                            <label class="form-label small fw-bold">Job Status:</label>
                            <select name="work_status" class="form-select form-select-sm" required>
                                <option value="Completed">Completed</option>
                                <option value="In Progress">In Progress</option>
                                <option value="Pending">Pending</option>
                            </select>
                        </div>
                        <div class="col-md-3">
                            <label class="form-label small fw-bold">Driver Name:</label>
                            <input type="text" name="driver" class="form-control form-control-sm" placeholder="e.g. አበበ ከ.">
                        </div>
                        
                        <div class="col-md-5">
                            <label class="form-label small fw-bold text-primary">Assigned Technicians / Mechanics:</label>
                            <div class="input-group input-group-sm">
                                <input type="text" name="technicians" class="form-control" placeholder="e.g., Ato Mihret, Dinberu Tefera">
                            </div>
                        </div>

                        <div class="col-md-3">
                            <label class="form-label small fw-bold text-primary">🗓️ Start Date & Time:</label>
                            <input type="datetime-local" name="start_time" class="form-control form-control-sm border-primary" required>
                        </div>

                        <div class="col-md-3">
                            <label class="form-label small fw-bold text-primary">🏁 End Date & Time:</label>
                            <input type="datetime-local" name="finish_time" class="form-control form-control-sm border-primary" required>
                        </div>

                        <div class="col-md-12">
                            <label class="form-label small fw-bold">Work Category & Description:</label>
                            <input type="text" name="description" class="form-control form-control-sm" placeholder="e.g. Engine Maintenance and Spare Parts Replacement" required>
                        </div>

                        <!-- Dynamic Replaced Spare Parts Section (Using Descriptive Breakdown Schema) -->
                        <div class="col-md-12">
                            <div class="p-3 border rounded bg-light shadow-sm">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <h6 class="fw-bold text-dark m-0">⚙️ Replaced Spare Parts (Auto Total Calculation)</h6>
                                    <button type="button" class="btn btn-outline-primary btn-sm fw-bold" onclick="addSpareRow()">+ Add Spare Part Row</button>
                                </div>
                                <div id="spare-rows-container">
                                    <div class="row g-2 spare-row mb-2 align-items-center">
                                        <div class="col-md-3">
                                            <input type="text" name="spare_name[]" class="form-control form-control-sm" placeholder="Spare Part Name" required>
                                        </div>
                                        <div class="col-md-3">
                                            <input type="text" name="spare_spec[]" class="form-control form-control-sm" placeholder="Specification" required>
                                        </div>
                                        <div class="col-md-1">
                                            <input type="number" name="spare_qty[]" class="form-control form-control-sm spare-qty" placeholder="Qty" value="1" min="1" required oninput="calculateRowTotal(this)">
                                        </div>
                                        <div class="col-md-2">
                                            <input type="number" step="0.01" name="spare_price[]" class="form-control form-control-sm spare-price" placeholder="Unit Price (ETB)" value="0.00" required oninput="calculateRowTotal(this)">
                                        </div>
                                        <div class="col-md-2">
                                            <span class="small fw-bold text-success row-total-text">0.00 ETB</span>
                                        </div>
                                        <div class="col-md-1">
                                            <button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeSpareRow(this)">✕</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Separate Consumables Inputs (Battery, Lubrication, Tire) -->
                        <div class="col-md-12">
                            <div class="p-3 border rounded bg-light shadow-sm">
                                <h6 class="fw-bold text-dark mb-3">🔋 Separate Consumables Tracking (Battery, Lubrication, Tire)</h6>
                                <div class="row g-3 align-items-center">
                                    <div class="col-md-4 border-end">
                                        <label class="form-label small fw-bold text-primary">Battery (ባትሪ):</label>
                                        <div class="input-group input-group-sm mb-1">
                                            <span class="input-group-text">Qty</span>
                                            <input type="number" name="battery_qty" class="form-control" value="0" min="0">
                                        </div>
                                        <div class="input-group input-group-sm mb-2">
                                            <span class="input-group-text">Cost (ETB)</span>
                                            <input type="number" step="0.01" name="battery_cost" class="form-control" value="0.00">
                                        </div>
                                        <input type="text" name="battery_spec" class="form-control form-control-sm" placeholder="Battery Spec (e.g. 150Ah)">
                                    </div>

                                    <div class="col-md-4 border-end">
                                        <label class="form-label small fw-bold text-primary">Lubrication (ዘይት/ግሪዝ):</label>
                                        <div class="input-group input-group-sm mb-1">
                                            <span class="input-group-text">Qty (L)</span>
                                            <input type="number" step="0.1" name="lubrication_qty" class="form-control" value="0.0" min="0">
                                        </div>
                                        <div class="input-group input-group-sm mb-2">
                                            <span class="input-group-text">Cost (ETB)</span>
                                            <input type="number" step="0.01" name="lubrication_cost" class="form-control" value="0.00">
                                        </div>
                                        <input type="text" name="lubrication_spec" class="form-control form-control-sm" placeholder="Lubricant Type (e.g. SAE 15W40)">
                                    </div>

                                    <div class="col-md-4">
                                        <label class="form-label small fw-bold text-primary">Tire (ጎማ):</label>
                                        <div class="input-group input-group-sm mb-1">
                                            <span class="input-group-text">Qty</span>
                                            <input type="number" name="tire_qty" class="form-control" value="0" min="0">
                                        </div>
                                        <div class="input-group input-group-sm mb-2">
                                            <span class="input-group-text">Cost (ETB)</span>
                                            <input type="number" step="0.01" name="tire_cost" class="form-control" value="0.00">
                                        </div>
                                        <input type="text" name="tire_spec" class="form-control form-control-sm" placeholder="Tire Size (e.g. 12.00R24)">
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="col-md-12 text-end mt-3">
                            <button type="submit" class="btn btn-success btn-sm px-5 fw-bold shadow-sm">💾 Save Work Order</button>
                        </div>
                    </div>
                </form>
            </div>

            <!-- Table 1: Execution & Work Time Log -->
            <div class="summary-card mb-4" id="execution-log-section">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="fw-bold text-dark m-0">🛠️ Maintenance Execution & Work Time Log</h5>
                    <div class="d-flex gap-2">
                        <a href="/export/execution_excel" class="btn btn-success btn-sm fw-bold shadow-sm">📥 Save Report (Excel)</a>
                        <a href="/reset_all_logs" class="btn btn-outline-danger btn-sm fw-bold shadow-sm" onclick="return confirm('Are you sure you want to clear/reset all logs?');">🔄 Reset All Data</a>
                    </div>
                </div>
                <div class="table-responsive">
                    <table class="table table-bordered table-hover align-middle table-sm">
                        <thead class="table-water-blue">
                            <tr>
                                <th>Serial No (S/N)</th>
                                <th>WO #</th>
                                <th>Plate No</th>
                                <th>Current Reading</th>
                                <th>🔔 Next Service Alert</th>
                                <th>Status</th>
                                <th>Assigned Technicians</th>
                                <th>Start Time</th>
                                <th>End Time</th>
                                <th>Effective Hours</th>
                                <th>⚙️ Replaced Spares</th>
                                <th>Battery</th>
                                <th>Lubrication</th>
                                <th>Tire</th>
                                <th class="text-center text-white">Action (Delete)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for log in logs %}
                            <tr>
                                <td class="fw-bold text-primary">{{ log.sn }}</td>
                                <td class="fw-bold">{{ log.wo_no }}</td>
                                <td><span class="badge bg-secondary">{{ log.vehicle }}</span></td>
                                <td class="small fw-bold">{{ "{:,}".format(log.reading_value) }} {{ log.reading_unit }}</td>
                                <td><span class="badge bg-info text-dark fw-bold">{{ log.next_service }}</span></td>
                                <td>
                                    {% if log.work_status == 'Completed' %}
                                        <span class="badge bg-success">Completed</span>
                                    {% elif log.work_status == 'In Progress' %}
                                        <span class="badge bg-warning text-dark">In Progress</span>
                                    {% else %}
                                        <span class="badge bg-danger">Pending</span>
                                    {% endif %}
                                </td>
                                <td class="small fw-bold text-primary">{{ log.technicians }}</td>
                                <td class="small text-muted">{{ log.start_time }}</td>
                                <td class="small text-muted">{{ log.finish_time }}</td>
                                <td class="fw-bold text-center text-success bg-light">{{ log.effective_hours }} hrs</td>
                                <td class="small">
                                    {% if log.replaced_spares %}
                                        {% for sp in log.replaced_spares %}
                                            <div>• <strong>{{ sp.part_name }}</strong> ({{ sp.spec }}) x{{ sp.qty }} ({{ "{:,.2f}".format(sp.total_cost) }} ETB)</div>
                                        {% endfor %}
                                    {% else %}
                                        <span class="text-muted">None</span>
                                    {% endif %}
                                </td>
                                <td class="small">
                                    {% if log.battery_qty > 0 %}
                                        <strong>Qty:</strong> {{ log.battery_qty }} | <strong>Cost:</strong> {{ "{:,.2f}".format(log.battery_cost) }} ETB
                                        {% if log.battery_spec %}<br><span class="text-muted">({{ log.battery_spec }})</span>{% endif %}
                                    {% else %}
                                        <span class="text-muted">0</span>
                                    {% endif %}
                                </td>
                                <td class="small">
                                    {% if log.lubrication_qty > 0 %}
                                        <strong>Qty:</strong> {{ log.lubrication_qty }}L | <strong>Cost:</strong> {{ "{:,.2f}".format(log.lubrication_cost) }} ETB
                                        {% if log.lubrication_spec %}<br><span class="text-muted">({{ log.lubrication_spec }})</span>{% endif %}
                                    {% else %}
                                        <span class="text-muted">0</span>
                                    {% endif %}
                                </td>
                                <td class="small">
                                    {% if log.tire_qty > 0 %}
                                        <strong>Qty:</strong> {{ log.tire_qty }} | <strong>Cost:</strong> {{ "{:,.2f}".format(log.tire_cost) }} ETB
                                        {% if log.tire_spec %}<br><span class="text-muted">({{ log.tire_spec }})</span>{% endif %}
                                    {% else %}
                                        <span class="text-muted">0</span>
                                    {% endif %}
                                </td>
                                <td class="text-center">
                                    <a href="/delete_log/{{ log.id }}" class="btn btn-outline-danger btn-sm" onclick="return confirm('Are you sure you want to delete this log entry?');">🗑️</a>
                                </td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

        </div>
    </div>
</div>

<!-- Modal: Store Spare Inventory -->
<div class="modal fade" id="inventoryModal" tabindex="-1" aria-labelledby="inventoryModalLabel" aria-hidden="true">
    <div class="modal-dialog modal-xl">
        <div class="modal-content">
            <div class="modal-header bg-dark text-white">
                <h5 class="modal-title" id="inventoryModalLabel">⚙️ Store Spare Parts Inventory Overview</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <div class="modal-body">
                <div class="table-responsive">
                    <table class="table table-bordered table-striped table-sm align-middle">
                        <thead class="table-water-blue">
                            <tr>
                                <th>#ID</th>
                                <th>Spare Part Name</th>
                                <th>Specification</th>
                                <th>Used For / Application</th>
                                <th>Stock Qty</th>
                                <th>Unit Price (ETB)</th>
                                <th>Total Value (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for part in inventory %}
                            <tr>
                                <td>{{ part.id }}</td>
                                <td class="fw-bold">{{ part.part_name }}</td>
                                <td>{{ part.spec }}</td>
                                <td>{{ part.used_for }}</td>
                                <td class="fw-bold text-success">{{ part.qty }} Pcs</td>
                                <td>{{ "{:,.2f}".format(part.unit_price) }}</td>
                                <td class="fw-bold">{{ "{:,.2f}".format(part.qty * part.unit_price) }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
            </div>
        </div>
    </div>
</div>

<script>
    function addSpareRow() {
        const container = document.getElementById('spare-rows-container');
        const rowHTML = `
            <div class="row g-2 spare-row mb-2 align-items-center">
                <div class="col-md-3">
                    <input type="text" name="spare_name[]" class="form-control form-control-sm" placeholder="Spare Part Name" required>
                </div>
                <div class="col-md-3">
                    <input type="text" name="spare_spec[]" class="form-control form-control-sm" placeholder="Specification" required>
                </div>
                <div class="col-md-1">
                    <input type="number" name="spare_qty[]" class="form-control form-control-sm spare-qty" placeholder="Qty" value="1" min="1" required oninput="calculateRowTotal(this)">
                </div>
                <div class="col-md-2">
                    <input type="number" step="0.01" name="spare_price[]" class="form-control form-control-sm spare-price" placeholder="Unit Price (ETB)" value="0.00" required oninput="calculateRowTotal(this)">
                </div>
                <div class="col-md-2">
                    <span class="small fw-bold text-success row-total-text">0.00 ETB</span>
                </div>
                <div class="col-md-1">
                    <button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeSpareRow(this)">✕</button>
                </div>
            </div>
        `;
        container.insertAdjacentHTML('beforeend', rowHTML);
    }

    function removeSpareRow(button) {
        const row = button.closest('.spare-row');
        if (document.querySelectorAll('.spare-row').length > 1) {
            row.remove();
        } else {
            alert("At least one spare row placeholder should remain or clear the fields.");
        }
    }

    function calculateRowTotal(element) {
        const row = element.closest('.spare-row');
        const qty = parseFloat(row.querySelector('.spare-qty').value) || 0;
        const price = parseFloat(row.querySelector('.spare-price').value) || 0;
        const total = qty * price;
        row.querySelector('.row-total-text').innerText = total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " ETB";
    }
</script>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
"""

# --- Application Routes ---

@app.route("/")
def index():
    user = {"name": "System Admin", "role": "Workshop Manager"}
    
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    weekly = get_summary_stats(days=7)
    monthly = get_summary_stats(days=30)
    
    # Filter logs for main execution display table based on request args
    logs = garage_data["maintenance_logs"]
    if start_date and end_date:
        filtered_logs = []
        for log in logs:
            log_date_str = log["start_time"].split(" ")[0]
            try:
                if start_date <= log_date_str <= end_date:
                    filtered_logs.append(log)
            except:
                pass
        display_logs = filtered_logs
    else:
        display_logs = logs

    return render_template_string(
        HTML_TEMPLATE,
        user=user,
        weekly=weekly,
        monthly=monthly,
        logs=display_logs,
        inventory=garage_data["spare_parts"]
    )

@app.route("/add_work_order", methods=["POST"])
def add_work_order():
    try:
        sn = request.form.get("sn")
        wo_no = request.form.get("wo_no")
        vehicle = request.form.get("vehicle")
        model = request.form.get("model", "")
        reading_value = int(request.form.get("reading_value", 0))
        reading_unit = request.form.get("reading_unit", "KM")
        next_service = calculate_next_service(reading_value, reading_unit)
        work_status = request.form.get("work_status", "Completed")
        driver = request.form.get("driver", "")
        technicians = request.form.get("technicians", "")
        start_time = request.form.get("start_time", "").replace("T", " ")
        finish_time = request.form.get("finish_time", "").replace("T", " ")
        effective_hours = calculate_effective_hours(request.form.get("start_time"), request.form.get("finish_time"))
        description = request.form.get("description", "")

        # Replaced Spares parsing (Descriptive breakdown schema)
        spare_names = request.form.getlist("spare_name[]")
        spare_specs = request.form.getlist("spare_spec[]")
        spare_qtys = request.form.getlist("spare_qty[]")
        spare_prices = request.form.getlist("spare_price[]")

        replaced_spares = []
        for i in range(len(spare_names)):
            if spare_names[i].strip():
                qty = int(spare_qtys[i]) if i < len(spare_qtys) and spare_qtys[i] else 1
                price = float(spare_prices[i]) if i < len(spare_prices) and spare_prices[i] else 0.0
                replaced_spares.append({
                    "part_name": spare_names[i].strip(),
                    "spec": spare_specs[i].strip() if i < len(spare_specs) else "",
                    "qty": qty,
                    "unit_price": price,
                    "total_cost": qty * price
                })

        # Consumables
        battery_qty = int(request.form.get("battery_qty", 0) or 0)
        battery_cost = float(request.form.get("battery_cost", 0.0) or 0.0)
        battery_spec = request.form.get("battery_spec", "")

        lubrication_qty = float(request.form.get("lubrication_qty", 0.0) or 0.0)
        lubrication_cost = float(request.form.get("lubrication_cost", 0.0) or 0.0)
        lubrication_spec = request.form.get("lubrication_spec", "")

        tire_qty = int(request.form.get("tire_qty", 0) or 0)
        tire_cost = float(request.form.get("tire_cost", 0.0) or 0.0)
        tire_spec = request.form.get("tire_spec", "")

        new_id = max([l["id"] for l in garage_data["maintenance_logs"]], default=0) + 1

        new_log = {
            "id": new_id,
            "sn": sn,
            "wo_no": wo_no,
            "vehicle": vehicle,
            "model": model,
            "reading_value": reading_value,
            "reading_unit": reading_unit,
            "next_service": next_service,
            "driver": driver,
            "technicians": technicians,
            "type": "PM",
            "work_status": work_status,
            "start_time": start_time,
            "finish_time": finish_time,
            "effective_hours": effective_hours,
            "description": description,
            "replaced_spares": replaced_spares,
            "battery_qty": battery_qty,
            "battery_cost": battery_cost,
            "battery_spec": battery_spec,
            "lubrication_qty": lubrication_qty,
            "lubrication_cost": lubrication_cost,
            "lubrication_spec": lubrication_spec,
            "tire_qty": tire_qty,
            "tire_cost": tire_cost,
            "tire_spec": tire_spec
        }

        garage_data["maintenance_logs"].append(new_log)
    except Exception as e:
        print(f"Error saving work order: {e}")

    return redirect(url_for("index"))

@app.route("/delete_log/<int:log_id>")
def delete_log(log_id):
    garage_data["maintenance_logs"] = [l for l in garage_data["maintenance_logs"] if l["id"] != log_id]
    return redirect(url_for("index"))

@app.route("/reset_all_logs")
def reset_all_logs():
    garage_data["maintenance_logs"] = []
    return redirect(url_for("index"))

@app.route("/export/master_excel")
@app.route("/export/execution_excel")
def export_excel():
    logs = garage_data["maintenance_logs"]
    flat_data = []
    
    for l in logs:
        spares_desc = ", ".join([f"{sp['part_name']} ({sp['spec']}) x{sp['qty']}" for sp in l.get("replaced_spares", [])])
        spares_total = sum(sp.get("total_cost", 0.0) for sp in l.get("replaced_spares", []))
        
        flat_data.append({
            "Serial No": l.get("sn"),
            "WO Number": l.get("wo_no"),
            "Vehicle Plate": l.get("vehicle"),
            "Model": l.get("model"),
            "Current Reading": l.get("reading_value"),
            "Reading Unit": l.get("reading_unit"),
            "Next Service": l.get("next_service"),
            "Status": l.get("work_status"),
            "Driver": l.get("driver"),
            "Technicians": l.get("technicians"),
            "Start Time": l.get("start_time"),
            "Finish Time": l.get("finish_time"),
            "Effective Hours (hrs)": l.get("effective_hours"),
            "Work Description": l.get("description"),
            "Replaced Spares": spares_desc,
            "Spares Cost (ETB)": spares_total,
            "Battery Qty": l.get("battery_qty"),
            "Battery Spec": l.get("battery_spec"),
            "Battery Cost (ETB)": l.get("battery_cost"),
            "Lubrication Qty (L)": l.get("lubrication_qty"),
            "Lubrication Spec": l.get("lubrication_spec"),
            "Lubrication Cost (ETB)": l.get("lubrication_cost"),
            "Tire Qty": l.get("tire_qty"),
            "Tire Spec": l.get("tire_spec"),
            "Tire Cost (ETB)": l.get("tire_cost"),
            "Total Expenditure (ETB)": spares_total + l.get("battery_cost", 0) + l.get("lubrication_cost", 0) + l.get("tire_cost", 0)
        })

    df = pd.DataFrame(flat_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Maintenance Logs")
    output.seek(0)
    
    filename = f"SteelY_RMI_Garage_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
