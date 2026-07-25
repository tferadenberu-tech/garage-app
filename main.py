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
        {"id": 1, "part_name": "Oil Filter", "spec": "LF16015 / Heavy Duty", "qty": 20, "unit_price": 1200.00},
        {"id": 2, "part_name": "Fuel Filter", "spec": "FF5421 / High Efficiency", "qty": 15, "unit_price": 1800.00},
        {"id": 3, "part_name": "Brake Shoe Set", "spec": "Rear Axle / Heavy Duty Standard", "qty": 8, "unit_price": 4500.00}
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
                {"part_name": "Oil Filter (LF16015)", "qty": 1, "unit_price": 1200.0, "total_cost": 1200.0},
                {"part_name": "Fuel Filter (FF5421)", "qty": 1, "unit_price": 1800.0, "total_cost": 1800.0}
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
                <a href="#inventory-section" class="nav-link-custom">⚙️ Spare Inventory</a>
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
                        
                        <!-- Assigned Technicians / Mechanics -->
                        <div class="col-md-5">
                            <label class="form-label small fw-bold text-primary">Assigned Technicians / Mechanics:</label>
                            <div class="input-group input-group-sm">
                                <input type="text" name="technicians" class="form-control" placeholder="e.g., Ato Mihret, Dinberu Tefera">
                                <button type="button" class="btn btn-outline-primary fw-semibold px-3">+ Assign</button>
                            </div>
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

            <!-- Table 1: Execution & Work Time Log (Water Blue Header with Save Report & Action Delete) -->
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
                                <td class="fw-bold text-success">{{ "{:,.2f}".format(log.battery_cost) }} ETB</td>
                                <td class="fw-bold text-success">{{ "{:,.2f}".format(log.lubrication_cost) }} ETB</td>
                                <td class="fw-bold text-success">{{ "{:,.2f}".format(log.tire_cost) }} ETB</td>
                                <td class="text-center">
                                    <a href="/delete_log/{{ log.id }}" class="btn btn-outline-danger btn-sm px-2 py-0 fw-bold" onclick="return confirm('Delete this specific log row?');">🗑️ Delete Row</a>
                                </td>
                            </tr>
                            {% else %}
                            <tr>
                                <td colspan="15" class="text-center text-muted py-3">No maintenance logs found.</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Table 2: Spare Parts Inventory -->
            <div class="summary-card mb-4" id="inventory-section">
                <h5 class="fw-bold text-dark mb-3">⚙️ Spare Parts Inventory</h5>
                <div class="table-responsive">
                    <table class="table table-hover align-middle table-sm">
                        <thead class="table-water-blue">
                            <tr>
                                <th>#</th>
                                <th>Spare Part Name</th>
                                <th>Specification</th>
                                <th>Stock Qty</th>
                                <th>Unit Price (ETB)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for part in inventory %}
                            <tr>
                                <td>{{ part.id }}</td>
                                <td class="fw-bold">{{ part.part_name }}</td>
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

<script>
    function addSpareRow() {
        const container = document.getElementById('spare-rows-container');
        const newRow = document.createElement('div');
        newRow.className = 'row g-2 spare-row mb-2 align-items-center';
        newRow.innerHTML = `
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
        `;
        container.appendChild(newRow);
    }

    function removeSpareRow(button) {
        const row = button.closest('.spare-row');
        const container = document.getElementById('spare-rows-container');
        if (container.children.length > 1) {
            row.remove();
        } else {
            alert("At least one spare part row is required!");
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
</body>
</html>
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Login - SteelY R.M.I Garage</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-dark d-flex align-items-center justify-content-center vh-100">
    <div class="card p-4 shadow" style="width: 350px;">
        <h3 class="text-center mb-3 text-primary">SteelY R.M.I</h3>
        <p class="text-center text-muted small">Garage Maintenance System Login</p>
        {% if error %}
            <div class="alert alert-danger py-1 small text-center">{{ error }}</div>
        {% endif %}
        <form method="POST">
            <div class="mb-3">
                <label class="form-label small fw-bold">Username:</label>
                <input type="text" name="username" class="form-control" required placeholder="admin">
            </div>
            <div class="mb-3">
                <label class="form-label small fw-bold">Password:</label>
                <input type="password" name="password" class="form-control" required placeholder="password">
            </div>
            <button type="submit" class="btn btn-primary w-100 fw-bold">Login</button>
        </form>
    </div>
</body>
</html>
"""

def compute_period_summary(logs_list, days):
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    period_logs = []
    for l in logs_list:
        try:
            dt = datetime.strptime(l['start_time'], "%Y-%m-%d %H:%M")
            if dt >= cutoff:
                period_logs.append(l)
        except:
            period_logs.append(l)
            
    total_jobs = len(period_logs)
    pm_jobs = sum(1 for l in period_logs if l.get('type') == 'PM')
    cm_jobs = sum(1 for l in period_logs if l.get('type') == 'CM')
    total_work_hours = round(sum(l.get('effective_hours', 0) for l in period_logs), 2)
    
    total_spare_qty = sum(sum(sp.get('qty', 0) for sp in l.get('replaced_spares', [])) for l in period_logs)
    total_spares_cost = sum(sum(sp.get('total_cost', 0) for sp in l.get('replaced_spares', [])) for l in period_logs)
    
    total_lubrication_qty = sum(l.get('lubrication_qty', 0) for l in period_logs)
    total_lubrication_cost = sum(l.get('lubrication_cost', 0) for l in period_logs)
    
    total_battery_cost = sum(l.get('battery_cost', 0) for l in period_logs)
    total_tire_cost = sum(l.get('tire_cost', 0) for l in period_logs)
    
    total_expenditure = total_spares_cost + total_lubrication_cost + total_battery_cost + total_tire_cost
    
    return {
        "total_jobs": total_jobs,
        "pm_jobs": pm_jobs,
        "cm_jobs": cm_jobs,
        "total_work_hours": total_work_hours,
        "total_spare_qty": total_spare_qty,
        "total_spares_cost": total_spares_cost,
        "total_lubrication_qty": total_lubrication_qty,
        "total_lubrication_cost": total_lubrication_cost,
        "total_battery_cost": total_battery_cost,
        "total_tire_cost": total_tire_cost,
        "total_expenditure": total_expenditure
    }

def get_summaries(logs_list):
    weekly_summary = compute_period_summary(logs_list, 7)
    monthly_summary = compute_period_summary(logs_list, 30)
    return weekly_summary, monthly_summary

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == 'admin' and password == 'admin123':
            session['logged_in'] = True
            session['user'] = {"name": "System Admin", "role": "Administrator"}
            return redirect(url_for('dashboard'))
        else:
            error = "Invalid Username or Password (use admin / admin123)"
    return render_template_string(LOGIN_TEMPLATE, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    filtered_logs = garage_data['maintenance_logs']
    if start_date and end_date:
        try:
            s_dt = datetime.strptime(start_date, "%Y-%m-%d")
            e_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
            temp_logs = []
            for l in filtered_logs:
                try:
                    l_dt = datetime.strptime(l['start_time'][:10], "%Y-%m-%d")
                    if s_dt <= l_dt < e_dt:
                        temp_logs.append(l)
                except:
                    pass
            filtered_logs = temp_logs
        except:
            pass

    weekly, monthly = get_summaries(garage_data['maintenance_logs'])
    return render_template_string(
        HTML_TEMPLATE, 
        logs=filtered_logs, 
        inventory=garage_data['spare_parts'],
        weekly=weekly,
        monthly=monthly,
        user=session.get('user')
    )

@app.route('/add_work_order', methods=['POST'])
def add_work_order():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    start_raw = request.form.get('start_time', '')
    finish_raw = request.form.get('finish_time', '')
    
    start_disp = start_raw.replace('T', ' ') if start_raw else ''
    finish_disp = finish_raw.replace('T', ' ') if finish_raw else ''
    
    eff_hours = calculate_effective_hours(start_raw, finish_raw)
    
    try:
        r_val = int(request.form.get('reading_value', 0))
    except:
        r_val = 0
        
    r_unit = request.form.get('reading_unit', 'KM')
    next_serv = calculate_next_service(r_val, r_unit)
    
    techs_input = request.form.get('technicians', '').strip()
    
    spare_names = request.form.getlist('spare_name[]')
    spare_specs = request.form.getlist('spare_spec[]')
    spare_qtys = request.form.getlist('spare_qty[]')
    spare_prices = request.form.getlist('spare_price[]')
    
    replaced_list = []
    for i in range(len(spare_names)):
        name = spare_names[i].strip()
        spec = spare_specs[i].strip() if i < len(spare_specs) else ""
        if name:
            try:
                qty = int(spare_qtys[i])
            except:
                qty = 1
            try:
                price = float(spare_prices[i])
            except:
                price = 0.0
                
            replaced_list.append({
                "part_name": name,
                "spec": spec,
                "qty": qty,
                "unit_price": price,
                "total_cost": qty * price
            })

    new_id = (max([l['id'] for l in garage_data['maintenance_logs']]) + 1) if garage_data['maintenance_logs'] else 1
    new_log = {
        "id": new_id,
        "sn": request.form.get('sn', f'SN-00{new_id}'),
        "wo_no": request.form.get('wo_no', f'WO-2026-00{new_id}'),
        "vehicle": request.form.get('vehicle', 'N/A'),
        "model": request.form.get('model', 'N/A'),
        "reading_value": r_val,
        "reading_unit": r_unit,
        "next_service": next_serv,
        "work_status": request.form.get('work_status', 'Completed'),
        "driver": request.form.get('driver', 'N/A'),
        "technicians": techs_input if techs_input else "N/A",
        "type": "PM",
        "start_time": start_disp,
        "finish_time": finish_disp,
        "effective_hours": eff_hours,
        "description": request.form.get('description', ''),
        "replaced_spares": replaced_list,
        "battery_qty": int(request.form.get('battery_qty', 0) or 0),
        "battery_cost": float(request.form.get('battery_cost', 0) or 0),
        "lubrication_qty": float(request.form.get('lubrication_qty', 0) or 0),
        "lubrication_cost": float(request.form.get('lubrication_cost', 0) or 0),
        "tire_qty": int(request.form.get('tire_qty', 0) or 0),
        "tire_cost": float(request.form.get('tire_cost', 0) or 0)
    }
    garage_data['maintenance_logs'].append(new_log)
    return redirect(url_for('dashboard'))

@app.route('/delete_log/<int:log_id>')
def delete_log(log_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    garage_data['maintenance_logs'] = [l for l in garage_data['maintenance_logs'] if l['id'] != log_id]
    return redirect(url_for('dashboard'))

@app.route('/reset_all_logs')
def reset_all_logs():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    garage_data['maintenance_logs'] = []
    return redirect(url_for('dashboard'))

@app.route('/export/execution_excel')
def export_execution_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    output = io.BytesIO()
    logs_export = []
    for l in garage_data['maintenance_logs']:
        sp_text = ", ".join([f"{sp['part_name']} ({sp['spec']}) - {sp['qty']} pcs" for sp in l.get('replaced_spares', [])])
        sp_cost = sum([sp['total_cost'] for sp in l.get('replaced_spares', [])])
        
        logs_export.append({
            'Serial Number': l['sn'],
            'Work Order No': l['wo_no'],
            'Vehicle Plate': l['vehicle'],
            'Current Reading': f"{l['reading_value']} {l['reading_unit']}",
            'Next Service Alert': l['next_service'],
            'Status': l['work_status'],
            'Assigned Technicians': l['technicians'],
            'Start Time': l['start_time'],
            'End Time': l['finish_time'],
            'Effective Hours (hrs)': l['effective_hours'],
            'Replaced Spare Parts': sp_text,
            'Spare Parts Total Cost (ETB)': sp_cost,
            'Battery Cost (ETB)': l['battery_cost'],
            'Lubrication Cost (ETB)': l['lubrication_cost'],
            'Tire Cost (ETB)': l['tire_cost']
        })
    
    logs_df = pd.DataFrame(logs_export)
    
    # Sort by Serial Number and drop any potential duplicate rows to prevent overlapping/duplication
    if not logs_df.empty:
        logs_df = logs_df.sort_values(by='Serial Number', ascending=True).drop_duplicates(subset=['Serial Number', 'Work Order No'], keep='first')

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        logs_df.to_excel(writer, sheet_name='Execution & Work Time Log', index=False)
        
    output.seek(0)
    return send_file(output, download_name='SteelY_Maintenance_Execution_Log.xlsx', as_attachment=True)

@app.route('/export/master_excel')
def export_master_excel():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    output = io.BytesIO()
    weekly, monthly = get_summaries(garage_data['maintenance_logs'])
    
    logs_export = []
    for l in garage_data['maintenance_logs']:
        sp_text = ", ".join([f"{sp['part_name']} ({sp['spec']}) ({sp['qty']} pcs)" for sp in l.get('replaced_spares', [])])
        sp_cost = sum([sp['total_cost'] for sp in l.get('replaced_spares', [])])
        
        logs_export.append({
            'Serial Number': l['sn'],
            'Work Order No': l['wo_no'],
            'Vehicle Plate': l['vehicle'],
            'Vehicle Model': l['model'],
            'Reading Value': l['reading_value'],
            'Reading Unit': l['reading_unit'],
            'Next Service Schedule': l['next_service'],
            'Work Status': l['work_status'],
            'Assigned Technicians': l['technicians'],
            'Start Time': l['start_time'],
            'End Time': l['finish_time'],
            'Effective Hours': l['effective_hours'],
            'Replaced Spare Part (spec)': sp_text,
            'Spare Parts Total Cost (ETB)': sp_cost,
            'Battery Cost (ETB)': l['battery_cost'],
            'Lubrication Cost (ETB)': l['lubrication_cost'],
            'Tire Cost (ETB)': l['tire_cost']
        })
        
    logs_df = pd.DataFrame(logs_export)
    
    # Sort by Serial Number and remove duplicates for Master Excel as well
    if not logs_df.empty:
        logs_df = logs_df.sort_values(by='Serial Number', ascending=True).drop_duplicates(subset=['Serial Number', 'Work Order No'], keep='first')

    summary_data = [
        {"Report Type": "WEEKLY SUMMARY (Last 7 Days)", "Total Jobs": weekly['total_jobs'], "PM Jobs": weekly['pm_jobs'], "CM Jobs": weekly['cm_jobs'], "Total Work Hours (hrs)": weekly['total_work_hours'], "Spare Parts Total Cost (ETB)": weekly['total_spares_cost'], "Lubricants Cost (ETB)": weekly['total_lubrication_cost'], "Batteries Cost (ETB)": weekly['total_battery_cost'], "Tires Cost (ETB)": weekly['total_tire_cost'], "Total Expenditure (ETB)": weekly['total_expenditure']},
        {"Report Type": "MONTHLY SUMMARY (Last 30 Days)", "Total Jobs": monthly['total_jobs'], "PM Jobs": monthly['pm_jobs'], "CM Jobs": monthly['cm_jobs'], "Total Work Hours (hrs)": monthly['total_work_hours'], "Spare Parts Total Cost (ETB)": monthly['total_spares_cost'], "Lubricants Cost (ETB)": monthly['total_lubrication_cost'], "Batteries Cost (ETB)": monthly['total_battery_cost'], "Tires Cost (ETB)": monthly['total_tire_cost'], "Total Expenditure (ETB)": monthly['total_expenditure']}
    ]
    summary_df = pd.DataFrame(summary_data)
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_df.to_excel(writer, sheet_name='Weekly & Monthly Summaries', index=False)
        logs_df.to_excel(writer, sheet_name='Master Maintenance Log', index=False)
        
    output.seek(0)
    return send_file(output, download_name='SteelY_Master_Garage_Report.xlsx', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
