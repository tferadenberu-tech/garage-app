from datetime import datetime, timedelta
import io
import json
import pandas as pd
from flask import Flask, render_template_string, request, redirect, url_for, send_file, session

app = Flask(__name__)
app.secret_key = "steely_garage_secret_key"

# --- In-Memory System Database ---
garage_data = {
    "users": [
        {"username": "admin", "password": "password123", "name": "Dinberu Tefera", "role": "System Admin"}
    ],
    "spare_parts": [
        {"id": 1, "part_name": "Oil Filter", "spec": "LF16015 / Heavy Duty", "for_vehicle": "Sino Truck 371", "qty": 20, "unit_price": 1200.00},
        {"id": 2, "part_name": "Fuel Filter", "spec": "FF5421 / High Efficiency", "for_vehicle": "Isuzu NPR", "qty": 15, "unit_price": 1800.00},
        {"id": 3, "part_name": "Brake Shoe Set", "spec": "Rear Axle / Heavy Duty Standard", "for_vehicle": "FSR", "qty": 8, "unit_price": 4500.00}
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
           "maintenance_type": "PM",
           "work_status": "Completed",
           "start_time": "2026-07-20 08:00",
           "finish_time": "2026-07-20 14:30",
           "effective_hours": 6.5,
           "description": "Engine Oil & Filter Change",
           "replaced_spares": [
               {"part_name": "Oil Filter (LF16015)", "spec": "LF16015", "qty": 1, "unit_price": 1200.0, "total_cost": 1200.0},
               {"part_name": "Fuel Filter (FF5421)", "spec": "FF5421", "qty": 1, "unit_price": 1800.0, "total_cost": 1800.0}
           ],
           "battery_qty": 1, "battery_cost": 15000.0,
           "lubrication_qty": 20.0, "lubrication_cost": 4500.0,
           "tire_qty": 0, "tire_cost": 0.0
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

# --- Login HTML Template ---
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - SteelY R.M.I Garage Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body { background: linear-gradient(135deg, #090d16 0%, #1e293b 100%); height: 100vh; display: flex; align-items: center; justify-content: center; font-family: 'Inter', sans-serif; }
        .login-card { background: #ffffff; padding: 40px; border-radius: 16px; box-shadow: 0 10px 25px rgba(0,0,0,0.3); width: 100%; max-width: 400px; }
        .brand-title { color: #0f172a; font-size: 1.6rem; font-weight: 800; text-align: center; margin-bottom: 5px; }
        .brand-subtitle { color: #64748b; font-size: 0.85rem; text-align: center; margin-bottom: 25px; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="brand-title">SteelY R.M.I</div>
        <div class="brand-subtitle">Garage Maintenance Management Portal</div>
        {% if error %}
            <div class="alert alert-danger py-2 small text-center">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label small fw-bold">Username</label>
                <input type="text" name="username" class="form-control" placeholder="Enter username" required>
            </div>
            <div class="mb-3">
                <label class="form-label small fw-bold">Password</label>
                <input type="password" name="password" class="form-control" placeholder="Enter password" required>
            </div>
            <button type="submit" class="btn btn-primary w-100 fw-bold py-2 shadow-sm">🔐 Login to Dashboard</button>
        </form>
    </div>
</body>
</html>
"""

# --- Frontend HTML Template ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SteelY R.M.I Garage Maintenance Dashboard</title>
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
        table.table thead.table-water-blue, .table-water-blue { background: #0284c7 !important; background-color: #0284c7 !important; }
        table.table thead.table-water-blue th, .table-water-blue th { background-color: #0284c7 !important; color: #ffffff !important; font-weight: 700 !important; border-color: #0284c7 !important; }
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
            <div class="admin-badge">⚡ {{ user.role }}</div>
            
            <a href="/export/master_excel" class="btn btn-export-main shadow-sm">
                📊 Export Master Excel
            </a>

            <nav class="mt-2">
                <a href="#summary-section" class="nav-link-custom">📊 Summaries & Filter</a>
                <a href="#create-wo-section" class="nav-link-custom">➕ Create Work Order</a>
                <a href="#execution-log-section" class="nav-link-custom">🛠️ Execution & Log</a>
                <a href="#" class="nav-link-custom" data-bs-toggle="modal" data-bs-target="#inventoryModal">⚙️ Spare Inventory</a>
            </nav>
        </div>

        <!-- Right Main Workspace -->
        <div class="col-md-10 p-4">
            
            <!-- Top Header Banner -->
            <div class="main-header">
               <div>
                   <h1 class="main-title">SteelY R.M.I Garage Maintenance Dashboard</h1>
                   <div class="main-subtitle">Integrated Work Time, Consumables & Maintenance Tracking Platform</div>
               </div>
               <div class="top-user-panel">
                   <div class="user-box">
                        <span class="user-name">{{ user.name }}</span>
                       <span class="user-role">{{ user.role }}</span>
                   </div>
                   <button type="button" class="btn btn-primary btn-sm fw-bold shadow-sm" data-bs-toggle="modal" data-bs-target="#inventoryModal">⚙️ View Spare Inventory</button>
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
                           <div class="stat-line text-muted mb-0">• Inspection & Checkup: <strong>{{ weekly.inspection_jobs }}</strong></div>
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
                           <div class="stat-line text-muted mb-0">• Inspection & Checkup: <strong>{{ monthly.inspection_jobs }}</strong></div>
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

                       <!-- Maintenance Type Selection Box (PM, CM, Inspection) -->
                       <div class="col-md-3">
                           <label class="form-label small fw-bold text-primary">🔧 Maintenance Type:</label>
                           <select name="maintenance_type" class="form-select form-select-sm border-primary fw-bold" required>
                                <option value="PM">PM (Preventive Maintenance)</option>
                                <option value="CM">CM (Corrective Maintenance)</option>
                                <option value="Inspection">Inspection (Checkup)</option>
                           </select>
                       </div>

                       <div class="col-md-3">
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
                       
                       <!-- Assigned Technicians / Mechanics -->
                       <div class="col-md-3">
                           <label class="form-label small fw-bold text-primary">Assigned Technicians:</label>
                           <input type="text" name="technicians" class="form-control form-control-sm" placeholder="e.g., Ato Mihret" required>
                       </div>

                       <!-- Start Date & Time and End Date & Time -->
                       <div class="col-md-3">
                           <label class="form-label small fw-bold text-primary">🗓️ Start Date & Time:</label>
                           <input type="datetime-local" name="start_time" class="form-control form-control-sm border-primary" required>
                       </div>

                       <div class="col-md-3">
                           <label class="form-label small fw-bold text-primary">🏁 End Date & Time:</label>
                           <input type="datetime-local" name="finish_time" class="form-control form-control-sm border-primary" required>
                       </div>

                       <div class="col-md-12">
                           <label class="form-label small fw-bold">Work Description:</label>
                           <input type="text" name="description" class="form-control form-control-sm" placeholder="e.g. Maintenance details and diagnostics note" required>
                       </div>

                       <!-- Dynamic Replaced Spare Parts Section with + Add Button -->
                       <div class="col-md-12">
                           <div class="p-3 border rounded bg-light shadow-sm">
                                <div class="d-flex justify-content-between align-items-center mb-2">
                                    <h6 class="fw-bold text-dark m-0">⚙️ Replaced Spare Parts (Auto Total Calculation)</h6>
                                    <button type="button" class="btn btn-primary btn-sm fw-bold px-3 shadow-sm" onclick="addSpareRow()">+ Add Spare Part</button>
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

                       <!-- Separate Consumables Inputs -->
                       <div class="col-md-12">
                           <div class="p-3 border rounded bg-light shadow-sm">
                                <h6 class="fw-bold text-dark mb-3">🔋 Separate Consumables Tracking (Battery, Lubrication, Tire)</h6>
                                <div class="row g-3 align-items-center">
                                    <div class="col-md-4 border-end">
                                       <label class="form-label small fw-bold text-primary">Battery:</label>
                                        <div class="input-group input-group-sm mb-1">
                                           <span class="input-group-text">Qty</span>
                                           <input type="number" name="battery_qty" class="form-control" value="0">
                                        </div>
                                        <div class="input-group input-group-sm">
                                           <span class="input-group-text">Cost (ETB)</span>
                                           <input type="number" step="0.01" name="battery_cost" class="form-control" value="0.00">
                                        </div>
                                    </div>

                                    <div class="col-md-4 border-end">
                                       <label class="form-label small fw-bold text-primary">Lubrication (Oil/Grease):</label>
                                        <div class="input-group input-group-sm mb-1">
                                           <span class="input-group-text">Qty (L)</span>
                                           <input type="number" step="0.1" name="lubrication_qty" class="form-control" value="0.0">
                                        </div>
                                        <div class="input-group input-group-sm">
                                           <span class="input-group-text">Cost (ETB)</span>
                                           <input type="number" step="0.01" name="lubrication_cost" class="form-control" value="0.00">
                                        </div>
                                    </div>

                                    <div class="col-md-4">
                                       <label class="form-label small fw-bold text-primary">Tire:</label>
                                       <div class="input-group input-group-sm mb-1">
                                           <span class="input-group-text">Qty</span>
                                           <input type="number" name="tire_qty" class="form-control" value="0">
                                       </div>
                                        <div class="input-group input-group-sm">
                                           <span class="input-group-text">Cost (ETB)</span>
                                            <input type="number" step="0.01" name="tire_cost" class="form-control" value="0.00">
                                       </div>
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

            <!-- Table 1: Execution & Work Time Log (Including Spare Parts Column) -->
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
                               <th>Maint. Type</th>
                               <th>Status</th>
                               <th>Assigned Technicians</th>
                               <th>Start Time</th>
                               <th>End Time</th>
                               <th>Effective Hours</th>
                               <th>⚙️ Spare Parts Used (Column Added)</th>
                               <th>Battery Cost</th>
                               <th>Lubrication Cost</th>
                               <th>Tire Cost</th>
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
                                    {% if log.maintenance_type == 'PM' %}
                                        <span class="badge bg-primary">PM</span>
                                    {% elif log.maintenance_type == 'CM' %}
                                       <span class="badge bg-danger">CM</span>
                                    {% else %}
                                       <span class="badge bg-warning text-dark">Inspection</span>
                                    {% endif %}
                                </td>
                                <td>
                                    {% if log.work_status == 'Completed' %}
                                       <span class="badge bg-success">Completed</span>
                                    {% elif log.work_status == 'In Progress' %}
                                       <span class="badge bg-warning text-dark">In Progress</span>
                                    {% else %}
                                       <span class="badge bg-secondary">Pending</span>
                                    {% endif %}
                                </td>
                                <td class="small fw-bold text-primary">{{ log.technicians }}</td>
                                <td class="small text-muted">{{ log.start_time }}</td>
                                <td class="small text-muted">{{ log.finish_time }}</td>
                                <td class="fw-bold text-center text-success bg-light">{{ log.effective_hours }} hrs</td>
                                <td class="small bg-light">
                                    {% if log.replaced_spares %}
                                        {% for sp in log.replaced_spares %}
                                            <div>• <strong>{{ sp.part_name }}</strong> ({{ sp.spec }}) x{{ sp.qty }} — <strong>{{ "{:,.2f}".format(sp.total_cost) }} ETB</strong></div>
                                        {% endfor %}
                                    {% else %}
                                       <span class="text-muted">None</span>
                                    {% endif %}
                                </td>
                                <td class="fw-bold text-success">{{ "{:,.2f}".format(log.battery_cost) }} ETB</td>
                                <td class="fw-bold text-success">{{ "{:,.2f}".format(log.lubrication_cost) }} ETB</td>
                                <td class="fw-bold text-success">{{ "{:,.2f}".format(log.tire_cost) }} ETB</td>
                                <td class="text-center">
                                    <a href="/delete_log/{{ log.id }}" class="btn btn-outline-danger btn-sm" onclick="return confirm('Delete this record?');">✕</a>
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

<!-- Spare Inventory Modal -->
<div class="modal fade" id="inventoryModal" tabindex="-1">
  <div class="modal-dialog modal-xl modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header bg-primary text-white">
        <h5 class="modal-title fw-bold">⚙️ Spare Parts Store Inventory</h5>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
      </div>
      <div class="modal-body">
        <div class="table-responsive">
          <table class="table table-bordered table-striped align-middle">
            <thead class="table-dark">
              <tr>
                <th>ID</th>
                <th>Part Name</th>
                <th>Specification</th>
                <th>Vehicle Model</th>
                <th>Qty Stock</th>
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
                <td><span class="badge bg-success">{{ part.qty }} Pcs</span></td>
                <td class="fw-bold">{{ "{:,.2f}".format(part.unit_price) }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    function addSpareRow() {
        const container = document.getElementById('spare-rows-container');
        const newRow = document.createElement('div');
        newRow.className = 'row g-2 spare-row mb-2 align-items-center';
        newRow.innerHTML = `
            <div class="col-md-3"><input type="text" name="spare_name[]" class="form-control form-control-sm" placeholder="Spare Part Name" required></div>
            <div class="col-md-3"><input type="text" name="spare_spec[]" class="form-control form-control-sm" placeholder="Specification" required></div>
            <div class="col-md-1"><input type="number" name="spare_qty[]" class="form-control form-control-sm spare-qty" placeholder="Qty" value="1" min="1" required oninput="calculateRowTotal(this)"></div>
            <div class="col-md-2"><input type="number" step="0.01" name="spare_price[]" class="form-control form-control-sm spare-price" placeholder="Unit Price (ETB)" value="0.00" required oninput="calculateRowTotal(this)"></div>
            <div class="col-md-2"><span class="small fw-bold text-success row-total-text">0.00 ETB</span></div>
            <div class="col-md-1"><button type="button" class="btn btn-outline-danger btn-sm w-100" onclick="removeSpareRow(this)">✕</button></div>
        `;
        container.appendChild(newRow);
    }
    function removeSpareRow(button) {
        button.closest('.spare-row').remove();
    }
    function calculateRowTotal(element) {
        const row = element.closest('.spare-row');
        const qty = parseFloat(row.querySelector('.spare-qty').value) || 0;
        const price = parseFloat(row.querySelector('.spare-price').value) || 0;
        const total = qty * price;
        row.querySelector('.row-total-text').innerText = total.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' ETB';
    }
</script>
</body>
</html>
"""

# --- Flask Routes ---
@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        for u in garage_data["users"]:
            if u["username"] == username and u["password"] == password:
                session["user"] = u
                return redirect(url_for("index"))
        error = "Invalid username or password!"
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/")
def index():
    if "user" not in session:
        return redirect(url_for("login"))
    
    logs = garage_data["maintenance_logs"]
    
    # Date Filtering handling
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    filtered_logs = logs
    if start_date and end_date:
        filtered_logs = [l for l in logs if start_date <= l["start_time"][:10] <= end_date]

    # Calculations for Weekly / Monthly Summaries
    def summarize(days):
        cutoff = datetime.now() - timedelta(days=days)
        sub_logs = [l for l in logs if datetime.strptime(l["start_time"][:10], "%Y-%m-%d") >= cutoff]
        
        pm = sum(1 for l in sub_logs if l["maintenance_type"] == "PM")
        cm = sum(1 for l in sub_logs if l["maintenance_type"] == "CM")
        insp = sum(1 for l in sub_logs if l["maintenance_type"] == "Inspection")
        hours = sum(l["effective_hours"] for l in sub_logs)
        
        spare_qty = sum(sp["qty"] for l in sub_logs for sp in l.get("replaced_spares", []))
        spares_cost = sum(sp["total_cost"] for l in sub_logs for sp in l.get("replaced_spares", []))
        
        batt_qty = sum(l.get("battery_qty", 0) for l in sub_logs)
        batt_cost = sum(l.get("battery_cost", 0.0) for l in sub_logs)
        
        lub_qty = sum(l.get("lubrication_qty", 0.0) for l in sub_logs)
        lub_cost = sum(l.get("lubrication_cost", 0.0) for l in sub_logs)
        
        tire_qty = sum(l.get("tire_qty", 0) for l in sub_logs)
        tire_cost = sum(l.get("tire_cost", 0.0) for l in sub_logs)
        
        total_exp = spares_cost + batt_cost + lub_cost + tire_cost
        
        return {
            "total_jobs": len(sub_logs),
            "pm_jobs": pm,
            "cm_jobs": cm,
            "inspection_jobs": insp,
            "total_work_hours": round(hours, 2),
            "total_spare_qty": spare_qty,
            "total_spares_cost": spares_cost,
            "total_lubrication_qty": round(lub_qty, 1),
            "total_lubrication_cost": lub_cost,
            "total_battery_cost": batt_cost,
            "total_tire_cost": tire_cost,
            "total_expenditure": total_exp
        }

    return render_template_string(
        HTML_TEMPLATE,
        user=session["user"],
        logs=filtered_logs,
        inventory=garage_data["spare_parts"],
        weekly=summarize(7),
        monthly=summarize(30)
    )

@app.route("/add_work_order", methods=["POST"])
def add_work_order():
    if "user" not in session:
        return redirect(url_for("login"))
    
    start_time = request.form.get("start_time")
    finish_time = request.form.get("finish_time")
    effective_hrs = calculate_effective_hours(start_time, finish_time)
    
    reading_val = request.form.get("reading_value")
    reading_unit = request.form.get("reading_unit")
    next_serv = calculate_next_service(reading_val, reading_unit)
    
    # Process Dynamic Replaced Spares
    spare_names = request.form.getlist("spare_name[]")
    spare_specs = request.form.getlist("spare_spec[]")
    spare_qtys = request.form.getlist("spare_qty[]")
    spare_prices = request.form.getlist("spare_price[]")
    
    replaced_spares = []
    for i in range(len(spare_names)):
        if spare_names[i].strip():
            q = int(spare_qtys[i]) if spare_qtys[i] else 1
            p = float(spare_prices[i]) if spare_prices[i] else 0.0
            replaced_spares.append({
                "part_name": spare_names[i],
                "spec": spare_specs[i],
                "qty": q,
                "unit_price": p,
                "total_cost": q * p
            })

    new_log = {
       "id": len(garage_data["maintenance_logs"]) + 1,
       "sn": request.form.get("sn"),
       "wo_no": request.form.get("wo_no"),
       "vehicle": request.form.get("vehicle"),
       "model": request.form.get("model"),
       "reading_value": int(reading_val) if reading_val else 0,
       "reading_unit": reading_unit,
       "next_service": next_serv,
       "driver": request.form.get("driver"),
       "technicians": request.form.get("technicians"),
       "maintenance_type": request.form.get("maintenance_type"),
       "work_status": request.form.get("work_status"),
       "start_time": start_time.replace("T", " "),
       "finish_time": finish_time.replace("T", " "),
       "effective_hours": effective_hrs,
       "description": request.form.get("description"),
       "replaced_spares": replaced_spares,
       "battery_qty": int(request.form.get("battery_qty", 0)),
       "battery_cost": float(request.form.get("battery_cost", 0.0)),
       "lubrication_qty": float(request.form.get("lubrication_qty", 0.0)),
       "lubrication_cost": float(request.form.get("lubrication_cost", 0.0)),
       "tire_qty": int(request.form.get("tire_qty", 0)),
       "tire_cost": float(request.form.get("tire_cost", 0.0))
    }
    
    garage_data["maintenance_logs"].insert(0, new_log)
    return redirect(url_for("index"))

@app.route("/delete_log/<int:log_id>")
def delete_log(log_id):
    if "user" not in session:
        return redirect(url_for("login"))
    garage_data["maintenance_logs"] = [l for l in garage_data["maintenance_logs"] if l["id"] != log_id]
    return redirect(url_for("index"))

@app.route("/reset_all_logs")
def reset_all_logs():
    if "user" not in session:
        return redirect(url_for("login"))
    garage_data["maintenance_logs"] = []
    return redirect(url_for("index"))

@app.route("/export/master_excel")
@app.route("/export/execution_excel")
def export_excel():
    if "user" not in session:
        return redirect(url_for("login"))
    
    logs = garage_data["maintenance_logs"]
    data_rows = []
    for l in logs:
        spares_summary = ", ".join([f"{sp['part_name']} (x{sp['qty']})" for sp in l.get("replaced_spares", [])])
        data_rows.append({
            "Serial No": l["sn"],
            "Work Order No": l["wo_no"],
            "Plate No": l["vehicle"],
            "Vehicle Model": l["model"],
            "Current Reading": f"{l['reading_value']} {l['reading_unit']}",
            "Next Service Alert": l["next_service"],
            "Maintenance Type": l["maintenance_type"],
            "Status": l["work_status"],
            "Technicians": l["technicians"],
            "Start Time": l["start_time"],
            "Finish Time": l["finish_time"],
            "Effective Hours": l["effective_hours"],
            "Spare Parts Used": spares_summary,
            "Battery Cost (ETB)": l["battery_cost"],
            "Lubrication Cost (ETB)": l["lubrication_cost"],
            "Tire Cost (ETB)": l["tire_cost"]
        })
        
    df = pd.DataFrame(data_rows)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Maintenance Logs')
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', as_attachment=True, download_name='SteelY_Garage_Report.xlsx')

if __name__ == "__main__":
    app.run(debug=True, port=5000)
