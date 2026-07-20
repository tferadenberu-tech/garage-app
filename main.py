from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import pandas as pd
import io

app = FastAPI(title="Steely R.M.I Garage Maintenance Dashboard")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# 1. Data Models
# ----------------------------------------------------
class SparePartItem(BaseModel):
    description: str
    qty: int = 1
    unit_cost: float = 0.0

class JobCreate(BaseModel):
    serial_number: str
    vehicle_plate: str
    vehicle_type: str
    driver_name: str
    technicians: str
    work_type: str 
    issue_description: str
    additional_unplanned_work: Optional[str] = ""
    start_time: str
    end_time: Optional[str] = ""
    
    spare_parts: List[SparePartItem] = []

    lubricant_liters: float = 0.0
    lubricant_cost: float = 0.0
    battery_cost: float = 0.0
    tire_cost: float = 0.0

class JobUpdate(BaseModel):
    technicians: Optional[str] = None
    status: Optional[str] = None
    end_time: Optional[str] = None
    additional_unplanned_work: Optional[str] = None
    
    spare_parts: Optional[List[SparePartItem]] = None

    lubricant_liters: Optional[float] = None
    lubricant_cost: Optional[float] = None
    battery_cost: Optional[float] = None
    tire_cost: Optional[float] = None

class JobResponse(JobCreate):
    id: int
    status: str
    duration: str
    spare_parts_qty: int
    spare_parts_cost: float
    total_cost: float

# ----------------------------------------------------
# 2. In-Memory Database & Helpers
# ----------------------------------------------------
jobs_db = []
job_id_counter = 1

def calculate_duration(start_str: str, end_str: str) -> str:
    if not start_str or not end_str:
        return "In Progress"
    try:
        fmt = "%Y-%m-%dT%H:%M"
        t1 = datetime.strptime(start_str, fmt)
        t2 = datetime.strptime(end_str, fmt)
        diff = t2 - t1
        
        hours, remainder = divmod(diff.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{int(hours)}h {int(minutes)}m"
    except Exception:
        return "N/A"

def parse_job_date(start_str: str) -> Optional[datetime]:
    try:
        return datetime.strptime(start_str, "%Y-%m-%dT%H:%M")
    except Exception:
        return None

def build_excel_response(data: List[dict], filename: str):
    excel_rows = []
    for job in data:
        parts = job.get("spare_parts", [])
        parts_str = "; ".join([f"{p['description']} (Qty: {p['qty']}, Unit Cost: ETB {p['unit_cost']})" for p in parts])
        
        row = {
            "S/N": job.get("serial_number"),
            "Vehicle Plate": job.get("vehicle_plate"),
            "Vehicle Type": job.get("vehicle_type"),
            "Driver Name": job.get("driver_name"),
            "Assigned Technicians": job.get("technicians"),
            "Work Type": job.get("work_type"),
            "Primary Issue": job.get("issue_description"),
            "Additional Unplanned Work": job.get("additional_unplanned_work"),
            "Start Time": job.get("start_time"),
            "End Time": job.get("end_time"),
            "Duration": job.get("duration"),
            "Replaced Spare Parts Breakdown": parts_str if parts_str else "None",
            "Spare Parts Total Qty": job.get("spare_parts_qty", 0),
            "Spare Parts Total Cost": job.get("spare_parts_cost", 0.0),
            "Lubricants (Liters)": job.get("lubricant_liters", 0.0),
            "Lubricant Cost": job.get("lubricant_cost", 0.0),
            "Battery Cost": job.get("battery_cost", 0.0),
            "Tire Cost": job.get("tire_cost", 0.0),
            "Total Cost": job.get("total_cost", 0.0),
            "Status": job.get("status")
        }
        excel_rows.append(row)

    df = pd.DataFrame(excel_rows) if excel_rows else pd.DataFrame(columns=[
        "S/N", "Vehicle Plate", "Vehicle Type", "Driver Name", "Assigned Technicians",
        "Work Type", "Primary Issue", "Additional Unplanned Work", "Start Time", "End Time", "Duration",
        "Replaced Spare Parts Breakdown", "Spare Parts Total Qty", "Spare Parts Total Cost",
        "Lubricants (Liters)", "Lubricant Cost", "Battery Cost", "Tire Cost", "Total Cost", "Status"
    ])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Garage_Report')
    
    output.seek(0)
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

# ----------------------------------------------------
# 3. API Endpoints
# ----------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_home():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Steely R.M.I Garage Maintenance Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
        <style>
            :root {
                --primary: #1a365d;
                --primary-light: #2b6cb0;
                --bg-main: #f1f5f9;
                --card-bg: #ffffff;
                --text-main: #0f172a;
                --border: #e2e8f0;
                --success: #10b981;
                --warning: #f59e0b;
                --info: #0284c7;
            }
            body { 
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; 
                margin: 0; padding: 25px; 
                background-color: var(--bg-main); 
                color: var(--text-main);
            }
            .container { 
                max-width: 1250px; margin: auto; 
                background: var(--card-bg); padding: 30px; 
                border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); 
            }
            h1 { color: var(--primary); font-size: 26px; margin-top: 0; font-weight: 700; border-bottom: 2px solid var(--border); padding-bottom: 12px; }
            h2 { color: var(--primary); font-size: 20px; margin-top: 25px; font-weight: 600; }
            h3 { color: var(--primary-light); font-size: 16px; margin-top: 20px; font-weight: 600; }
            
            .form-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 15px; }
            .form-group { margin-bottom: 12px; }
            .form-group.full-width { grid-column: 1 / -1; }
            
            label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 13px; color: #334155; }
            input, textarea, select { 
                width: 100%; padding: 10px; box-sizing: border-box; 
                border: 1px solid var(--border); border-radius: 6px; 
                font-size: 14px; background-color: #f8fafc; color: var(--text-main);
            }
            input:focus, textarea:focus, select:focus { border-color: var(--primary-light); outline: none; background-color: #fff; }

            button { 
                background-color: var(--primary); color: white; 
                padding: 10px 18px; border: none; border-radius: 6px; 
                cursor: pointer; font-size: 14px; font-weight: 600; 
            }
            button:hover { background-color: var(--primary-light); }
            .btn-add-part { background-color: #0284c7; margin-bottom: 12px; }
            .btn-add-part:hover { background-color: #0369a1; }
            .btn-info { background-color: var(--info); }
            .btn-info:hover { background-color: #0369a1; }
            .btn-excel { background-color: #16a34a; color: white; padding: 6px 12px; font-size: 12px; margin-top: 10px; width: 100%; }
            .btn-excel:hover { background-color: #15803d; }
            .btn-edit { background-color: var(--warning); color: #fff; padding: 5px 12px; font-size: 12px; border-radius: 4px; }
            .btn-edit:hover { background-color: #d97706; }
            .btn-filter { background-color: #475569; }
            .btn-filter:hover { background-color: #334155; }
            .btn-reset { background-color: #94a3b8; }
            .btn-reset:hover { background-color: #64748b; }
            .btn-remove { background-color: #ef4444; color: white; padding: 4px 8px; font-size: 12px; border-radius: 4px; }
            .btn-remove:hover { background-color: #dc2626; }

            .parts-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 13px; }
            .parts-table th, .parts-table td { border: 1px solid var(--border); padding: 8px; text-align: left; }
            .parts-table th { background-color: #e2e8f0; color: var(--text-main); }

            .filter-bar { 
                display: flex; gap: 12px; align-items: flex-end; 
                background: #f8fafc; padding: 15px; border-radius: 8px; 
                border: 1px solid var(--border); margin-bottom: 20px; flex-wrap: wrap;
            }
            .filter-bar .form-group { margin-bottom: 0; min-width: 180px; }

            table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
            th, td { border: 1px solid var(--border); padding: 10px; text-align: left; }
            th { background-color: var(--primary); color: white; font-weight: 600; }
            tr:nth-child(even) { background-color: #f8fafc; }
            
            .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; margin-bottom: 20px; }
            .card { background: #ffffff; border-top: 4px solid var(--primary); padding: 18px; border-radius: 8px; border: 1px solid var(--border); border-top-width: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
            .card.monthly { border-top-color: var(--success); }
            .card.custom { border-top-color: var(--info); }
            .card h4 { margin: 0 0 12px 0; color: var(--primary); text-transform: uppercase; font-size: 13px; letter-spacing: 0.5px; }
            .stat-row { display: flex; justify-content: space-between; margin-bottom: 6px; font-size: 13px; color: #475569; }
            .stat-total { font-weight: 700; border-top: 1px dashed var(--border); padding-top: 8px; margin-top: 8px; font-size: 14px; color: var(--text-main); }

            /* Modal Dialog Box */
            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(15, 23, 42, 0.6); }
            .modal-content { background-color: white; margin: 5% auto; padding: 25px; border-radius: 10px; width: 550px; max-width: 90%; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1); }
            .close-btn { color: #94a3b8; float: right; font-size: 24px; font-weight: bold; cursor: pointer; }
            .close-btn:hover { color: var(--text-main); }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Steely R.M.I Garage Maintenance Dashboard</h1>
            
            <h2>Executive Summaries & Analytics</h2>
            
            <!-- Executive Date Filter Bar -->
            <div class="filter-bar">
                <div class="form-group">
                    <label>Executive From Date:</label>
                    <input type="date" id="exec_from_date">
                </div>
                <div class="form-group">
                    <label>Executive To Date:</label>
                    <input type="date" id="exec_to_date">
                </div>
                <button type="button" class="btn-filter" onclick="fetchSummary()">Apply Date Filter</button>
                <button type="button" class="btn-reset" onclick="resetExecFilter()">Reset Summary</button>
            </div>

            <div class="summary-grid">
                <div class="card">
                    <h4>Weekly Summary (Last 7 Days)</h4>
                    <div id="weeklyStats">Loading...</div>
                    <button class="btn-excel" onclick="downloadWeeklyExcel()">Export Weekly Excel</button>
                </div>
                <div class="card monthly">
                    <h4>Monthly Summary (Last 30 Days)</h4>
                    <div id="monthlyStats">Loading...</div>
                    <button class="btn-excel" onclick="downloadMonthlyExcel()">Export Monthly Excel</button>
                </div>
                <div class="card custom">
                    <h4>Custom Date Range Summary</h4>
                    <div id="customStats">Select dates above and click Apply Filter...</div>
                </div>
            </div>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid var(--border);">

            <h2>Create Work Order</h2>
            <form id="jobForm">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Serial Number (S/N):</label>
                        <input type="text" id="serial_number" required placeholder="e.g., SN-2026-001">
                    </div>
                    <div class="form-group">
                        <label>Vehicle Plate Number:</label>
                        <input type="text" id="vehicle_plate" required placeholder="e.g., 3-A66865">
                    </div>
                    <div class="form-group">
                        <label>Vehicle Type / Model:</label>
                        <input type="text" id="vehicle_type" required placeholder="e.g., Jellion, Actros">
                    </div>
                    <div class="form-group">
                        <label>Driver Name:</label>
                        <input type="text" id="driver_name" required placeholder="e.g., Abebe Kebede">
                    </div>
                    <div class="form-group">
                        <label>Assigned Technicians / Mechanics:</label>
                        <input type="text" id="technicians" required placeholder="e.g., Ato Mihret, Dinberu Tefera">
                    </div>
                    <div class="form-group">
                        <label>Work Type / Category:</label>
                        <select id="work_type" required>
                            <option value="Preventive Maintenance">Preventive Maintenance</option>
                            <option value="Corrective Maintenance">Corrective Maintenance</option>
                            <option value="Inspection & Checkup">Inspection & Checkup</option>
                        </select>
                    </div>
                    <div class="form-group full-width">
                        <label>Primary Issue Description:</label>
                        <textarea id="issue_description" required placeholder="Detail repair scope..."></textarea>
                    </div>
                    <div class="form-group full-width">
                        <label>Additional / Unplanned Work Completed (Out of Scope):</label>
                        <textarea id="additional_unplanned_work" placeholder="Specify any additional emergency or extra work done outside original request..."></textarea>
                    </div>
                </div>
                
                <h3>Time Tracking</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label>Start Date & Time:</label>
                        <input type="datetime-local" id="start_time" required>
                    </div>
                    <div class="form-group">
                        <label>End Date & Time (Optional):</label>
                        <input type="datetime-local" id="end_time">
                    </div>
                </div>

                <h3>Replaced Spare Parts Breakdown (Description, Qty, Unit Cost)</h3>
                <button type="button" class="btn-add-part" onclick="openSparePartModal('create')">+ Add Replaced Spare Part Breakdown (Description, Qty, Unit Cost)</button>

                <table class="parts-table" id="createPartsTable">
                    <thead>
                        <tr>
                            <th>Spare Part Description</th>
                            <th>Quantity (Pcs)</th>
                            <th>Unit Cost (ETB)</th>
                            <th>Total Cost (ETB)</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr id="noPartsRow"><td colspan="5" style="text-align:center; color:#94a3b8;">No spare parts added yet. Click above to add.</td></tr>
                    </tbody>
                </table>

                <h3>Lubricants, Batteries & Tires</h3>
                <div class="form-grid">
                    <div class="form-group">
                        <label>Lubricants Quantity (Liters):</label>
                        <input type="number" id="lubricant_liters" value="0" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>Lubricant Cost (ETB):</label>
                        <input type="number" id="lubricant_cost" value="0" step="0.01">
                    </div>
                    <div class="form-group">
                        <label>Battery Cost (ETB):</label>
                        <input type="number" id="battery_cost" value="0" step="0.01">
                    </div>
                    <div class="form-group">
                        <label>Tire Cost (ETB):</label>
                        <input type="number" id="tire_cost" value="0" step="0.01">
                    </div>
                </div>
                
                <button type="submit" style="margin-top: 15px;">Submit Work Order</button>
            </form>

            <hr style="margin: 30px 0; border: none; border-top: 1px solid var(--border);">
            
            <h2>Work Orders Registry</h2>
            
            <!-- Work Order Registry Filter Bar -->
            <div class="filter-bar">
                <div class="form-group">
                    <label>From Date:</label>
                    <input type="date" id="filter_from_date">
                </div>
                <div class="form-group">
                    <label>To Date:</label>
                    <input type="date" id="filter_to_date">
                </div>
                <button type="button" class="btn-filter" onclick="fetchJobs()">Filter Records</button>
                <button type="button" class="btn-reset" onclick="resetJobsFilter()">Clear Filter / Reset</button>
                <button type="button" onclick="downloadExcel()" class="btn-info" style="margin-left: auto;">Export Excel Report</button>
            </div>

            <table id="jobsTable">
                <thead>
                    <tr>
                        <th>S/N</th>
                        <th>Plate</th>
                        <th>Vehicle Type</th>
                        <th>Technicians</th>
                        <th>Replaced Parts Breakdown</th>
                        <th>Lubricants</th>
                        <th>Unplanned Work</th>
                        <th>Duration</th>
                        <th>Total Cost</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <!-- ADD SPARE PART DIALOG BOX / MODAL -->
        <div id="sparePartModal" class="modal">
            <div class="modal-content">
                <span class="close-btn" onclick="closeSparePartModal()">&times;</span>
                <h3>Add Replaced Spare Part Breakdown</h3>
                <form id="sparePartForm">
                    <div class="form-group">
                        <label>Spare Part Description / Spec:</label>
                        <input type="text" id="modal_part_desc" required placeholder="e.g., Oil Filter, Brake Pad Set">
                    </div>
                    <div class="form-group">
                        <label>Quantity (Pcs):</label>
                        <input type="number" id="modal_part_qty" required value="1" min="1">
                    </div>
                    <div class="form-group">
                        <label>Unit Cost (ETB):</label>
                        <input type="number" id="modal_part_cost" required value="0" step="0.01">
                    </div>
                    <button type="submit" style="margin-top: 10px;">Add Part to List</button>
                    <button type="button" onclick="closeSparePartModal()" style="background-color: #64748b;">Cancel</button>
                </form>
            </div>
        </div>

        <!-- EDIT WORK ORDER MODAL DIALOG -->
        <div id="editModal" class="modal">
            <div class="modal-content" style="width:650px;">
                <span class="close-btn" onclick="closeEditModal()">&times;</span>
                <h3>Edit Work Order #<span id="editJobIdTitle"></span></h3>
                <form id="editForm">
                    <input type="hidden" id="editJobId">
                    <div class="form-group">
                        <label>Status:</label>
                        <select id="edit_status">
                            <option value="In Progress">In Progress</option>
                            <option value="Completed">Completed</option>
                            <option value="Pending Parts">Pending Parts</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Assigned Technicians:</label>
                        <input type="text" id="edit_technicians" required>
                    </div>
                    <div class="form-group">
                        <label>End Date & Time:</label>
                        <input type="datetime-local" id="edit_end_time">
                    </div>
                    <div class="form-group">
                        <label>Additional / Unplanned Work Done:</label>
                        <textarea id="edit_additional_unplanned_work"></textarea>
                    </div>

                    <h4>Replaced Spare Parts Breakdown</h4>
                    <button type="button" class="btn-add-part" onclick="openSparePartModal('edit')">+ Add Replaced Spare Part Breakdown (Description, Qty, Unit Cost)</button>
                    
                    <table class="parts-table" id="editPartsTable">
                        <thead>
                            <tr>
                                <th>Spare Part Description</th>
                                <th>Qty</th>
                                <th>Unit Cost</th>
                                <th>Total</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody></tbody>
                    </table>

                    <div class="form-group">
                        <label>Lubricants Quantity (Liters):</label>
                        <input type="number" id="edit_lubricant_liters" step="0.1">
                    </div>
                    <div class="form-group">
                        <label>Lubricant Cost (ETB):</label>
                        <input type="number" id="edit_lubricant_cost" step="0.01">
                    </div>
                    <div class="form-group">
                        <label>Battery Cost (ETB):</label>
                        <input type="number" id="edit_battery_cost" step="0.01">
                    </div>
                    <div class="form-group">
                        <label>Tire Cost (ETB):</label>
                        <input type="number" id="edit_tire_cost" step="0.01">
                    </div>
                    
                    <button type="submit" style="margin-top: 10px;">Save Changes</button>
                    <button type="button" onclick="closeEditModal()" style="background-color: #64748b;">Cancel</button>
                </form>
            </div>
        </div>

        <script>
            let allJobs = [];
            let createSpareParts = [];
            let editSpareParts = [];
            let activeModalContext = 'create'; // 'create' or 'edit'

            // --- Spare Part Modal Handlers ---
            function openSparePartModal(context) {
                activeModalContext = context;
                document.getElementById('sparePartForm').reset();
                document.getElementById('modal_part_qty').value = 1;
                document.getElementById('modal_part_cost').value = 0;
                document.getElementById('sparePartModal').style.display = 'block';
            }

            function closeSparePartModal() {
                document.getElementById('sparePartModal').style.display = 'none';
            }

            document.getElementById('sparePartForm').addEventListener('submit', (e) => {
                e.preventDefault();
                const desc = document.getElementById('modal_part_desc').value;
                const qty = parseInt(document.getElementById('modal_part_qty').value) || 1;
                const cost = parseFloat(document.getElementById('modal_part_cost').value) || 0;

                const item = { description: desc, qty: qty, unit_cost: cost };

                if(activeModalContext === 'create') {
                    createSpareParts.push(item);
                    renderCreatePartsTable();
                } else {
                    editSpareParts.push(item);
                    renderEditPartsTable();
                }

                closeSparePartModal();
            });

            function renderCreatePartsTable() {
                const tbody = document.querySelector('#createPartsTable tbody');
                tbody.innerHTML = '';
                if(createSpareParts.length === 0) {
                    tbody.innerHTML = '<tr id="noPartsRow"><td colspan="5" style="text-align:center; color:#94a3b8;">No spare parts added yet. Click above to add.</td></tr>';
                    return;
                }
                createSpareParts.forEach((p, idx) => {
                    const total = p.qty * p.unit_cost;
                    tbody.innerHTML += `<tr>
                        <td><b>${p.description}</b></td>
                        <td>${p.qty}</td>
                        <td>ETB ${p.unit_cost.toLocaleString()}</td>
                        <td>ETB ${total.toLocaleString()}</td>
                        <td><button type="button" class="btn-remove" onclick="removeCreatePart(${idx})">Delete</button></td>
                    </tr>`;
                });
            }

            function removeCreatePart(index) {
                createSpareParts.splice(index, 1);
                renderCreatePartsTable();
            }

            function renderEditPartsTable() {
                const tbody = document.querySelector('#editPartsTable tbody');
                tbody.innerHTML = '';
                if(editSpareParts.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#94a3b8;">No spare parts attached.</td></tr>';
                    return;
                }
                editSpareParts.forEach((p, idx) => {
                    const total = p.qty * p.unit_cost;
                    tbody.innerHTML += `<tr>
                        <td><b>${p.description}</b></td>
                        <td>${p.qty}</td>
                        <td>ETB ${p.unit_cost.toLocaleString()}</td>
                        <td>ETB ${total.toLocaleString()}</td>
                        <td><button type="button" class="btn-remove" onclick="removeEditPart(${idx})">Delete</button></td>
                    </tr>`;
                });
            }

            function removeEditPart(index) {
                editSpareParts.splice(index, 1);
                renderEditPartsTable();
            }

            // --- Executive Summary ---
            async function fetchSummary() {
                const execFrom = document.getElementById('exec_from_date').value;
                const execTo = document.getElementById('exec_to_date').value;
                
                let query = '';
                if(execFrom && execTo) {
                    query = `?from_date=${execFrom}&to_date=${execTo}`;
                }

                const res = await fetch(`/api/reports/executive-summary${query}`);
                const summary = await res.json();
                
                function renderCard(data) {
                    if(!data) return 'No records found for period.';
                    return `
                        <div class="stat-row"><span>Total Jobs:</span> <b>${data.total_jobs}</b></div>
                        <div class="stat-row"><span>Spare Parts Quantity:</span> <b>${data.spare_parts_qty} Pcs</b></div>
                        <div class="stat-row"><span>Spare Parts Cost:</span> <span>ETB ${data.spare_parts_cost.toLocaleString()}</span></div>
                        <div class="stat-row"><span>Lubricants Volume:</span> <b>${data.lubricant_liters} Liters</b></div>
                        <div class="stat-row"><span>Lubricants Cost:</span> <span>ETB ${data.lubricant_cost.toLocaleString()}</span></div>
                        <div class="stat-row"><span>Batteries Cost:</span> <span>ETB ${data.battery_cost.toLocaleString()}</span></div>
                        <div class="stat-row"><span>Tires Cost:</span> <span>ETB ${data.tire_cost.toLocaleString()}</span></div>
                        <div class="stat-row stat-total"><span>Total Expenditure:</span> <span>ETB ${data.total_cost.toLocaleString()}</span></div>
                    `;
                }

                document.getElementById('weeklyStats').innerHTML = renderCard(summary.weekly);
                document.getElementById('monthlyStats').innerHTML = renderCard(summary.monthly);
                if(summary.custom) {
                    document.getElementById('customStats').innerHTML = renderCard(summary.custom);
                } else {
                    document.getElementById('customStats').innerHTML = 'Select dates above and click Apply Date Filter.';
                }
            }

            function resetExecFilter() {
                document.getElementById('exec_from_date').value = '';
                document.getElementById('exec_to_date').value = '';
                fetchSummary();
            }

            // --- Job Registry ---
            async function fetchJobs() {
                const fromDate = document.getElementById('filter_from_date').value;
                const toDate = document.getElementById('filter_to_date').value;
                
                let query = '';
                if(fromDate && toDate) {
                    query = `?from_date=${fromDate}&to_date=${toDate}`;
                }

                const res = await fetch(`/api/jobs${query}`);
                allJobs = await res.json();
                const tbody = document.querySelector('#jobsTable tbody');
                tbody.innerHTML = '';
                allJobs.forEach(j => {
                    let partsText = 'None';
                    if(j.spare_parts && j.spare_parts.length > 0) {
                        partsText = j.spare_parts.map(p => `• ${p.description} (${p.qty} Pcs @ ETB ${p.unit_cost})`).join('<br>');
                    }

                    tbody.innerHTML += `<tr>
                        <td><b>${j.serial_number}</b></td>
                        <td>${j.vehicle_plate}</td>
                        <td><b>${j.vehicle_type}</b></td>
                        <td>${j.technicians}</td>
                        <td>${partsText}</td>
                        <td>${j.lubricant_liters} L</td>
                        <td>${j.additional_unplanned_work || '-'}</td>
                        <td><b>${j.duration}</b></td>
                        <td>ETB ${j.total_cost.toLocaleString()}</td>
                        <td>${j.status}</td>
                        <td><button class="btn-edit" onclick="openEditModal(${j.id})">Edit</button></td>
                    </tr>`;
                });
            }

            function resetJobsFilter() {
                document.getElementById('filter_from_date').value = '';
                document.getElementById('filter_to_date').value = '';
                fetchJobs();
            }

            // --- Form Submit ---
            document.getElementById('jobForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const data = {
                    serial_number: document.getElementById('serial_number').value,
                    vehicle_plate: document.getElementById('vehicle_plate').value,
                    vehicle_type: document.getElementById('vehicle_type').value,
                    driver_name: document.getElementById('driver_name').value,
                    technicians: document.getElementById('technicians').value,
                    work_type: document.getElementById('work_type').value,
                    issue_description: document.getElementById('issue_description').value,
                    additional_unplanned_work: document.getElementById('additional_unplanned_work').value,
                    start_time: document.getElementById('start_time').value,
                    end_time: document.getElementById('end_time').value,
                    
                    spare_parts: createSpareParts,

                    lubricant_liters: parseFloat(document.getElementById('lubricant_liters').value) || 0,
                    lubricant_cost: parseFloat(document.getElementById('lubricant_cost').value) || 0,
                    battery_cost: parseFloat(document.getElementById('battery_cost').value) || 0,
                    tire_cost: parseFloat(document.getElementById('tire_cost').value) || 0
                };

                await fetch('/api/jobs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                document.getElementById('jobForm').reset();
                createSpareParts = [];
                renderCreatePartsTable();
                fetchJobs();
                fetchSummary();
            });

            // --- Edit Modal Handlers ---
            function openEditModal(id) {
                const job = allJobs.find(j => j.id === id);
                if (!job) return;

                document.getElementById('editJobIdTitle').innerText = job.serial_number;
                document.getElementById('editJobId').value = job.id;
                document.getElementById('edit_status').value = job.status;
                document.getElementById('edit_technicians').value = job.technicians || '';
                document.getElementById('edit_end_time').value = job.end_time || '';
                document.getElementById('edit_additional_unplanned_work').value = job.additional_unplanned_work || '';
                
                editSpareParts = job.spare_parts ? JSON.parse(JSON.stringify(job.spare_parts)) : [];
                renderEditPartsTable();

                document.getElementById('edit_lubricant_liters').value = job.lubricant_liters || 0;
                document.getElementById('edit_lubricant_cost').value = job.lubricant_cost || 0;
                document.getElementById('edit_battery_cost').value = job.battery_cost || 0;
                document.getElementById('edit_tire_cost').value = job.tire_cost || 0;

                document.getElementById('editModal').style.display = 'block';
            }

            function closeEditModal() {
                document.getElementById('editModal').style.display = 'none';
            }

            document.getElementById('editForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const jobId = document.getElementById('editJobId').value;
                const data = {
                    status: document.getElementById('edit_status').value,
                    technicians: document.getElementById('edit_technicians').value,
                    end_time: document.getElementById('edit_end_time').value,
                    additional_unplanned_work: document.getElementById('edit_additional_unplanned_work').value,
                    
                    spare_parts: editSpareParts,

                    lubricant_liters: parseFloat(document.getElementById('edit_lubricant_liters').value) || 0,
                    lubricant_cost: parseFloat(document.getElementById('edit_lubricant_cost').value) || 0,
                    battery_cost: parseFloat(document.getElementById('edit_battery_cost').value) || 0,
                    tire_cost: parseFloat(document.getElementById('edit_tire_cost').value) || 0
                };

                await fetch(`/api/jobs/${jobId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                closeEditModal();
                fetchJobs();
                fetchSummary();
            });

            // --- Excel Downloads ---
            function downloadWeeklyExcel() {
                window.location.href = `/api/reports/excel/weekly`;
            }

            function downloadMonthlyExcel() {
                window.location.href = `/api/reports/excel/monthly`;
            }

            function downloadExcel() {
                const fromDate = document.getElementById('filter_from_date').value;
                const toDate = document.getElementById('filter_to_date').value;
                let query = '';
                if(fromDate && toDate) {
                    query = `?from_date=${fromDate}&to_date=${toDate}`;
                }
                window.location.href = `/api/reports/excel${query}`;
            }

            fetchJobs();
            fetchSummary();
        </script>
    </body>
    </html>
    """

@app.post("/api/jobs", response_model=JobResponse)
def create_job(job: JobCreate):
    global job_id_counter
    
    parts_cost = sum(p.qty * p.unit_cost for p in job.spare_parts)
    parts_qty = sum(p.qty for p in job.spare_parts)

    total = parts_cost + job.lubricant_cost + job.battery_cost + job.tire_cost
    duration_str = calculate_duration(job.start_time, job.end_time)
    
    job_data = job.dict()
    job_data["id"] = job_id_counter
    job_data["status"] = "Completed" if job.end_time else "In Progress"
    job_data["duration"] = duration_str
    job_data["spare_parts_qty"] = parts_qty
    job_data["spare_parts_cost"] = parts_cost
    job_data["total_cost"] = total
    
    jobs_db.append(job_data)
    job_id_counter += 1
    return job_data

@app.get("/api/jobs", response_model=List[JobResponse])
def get_jobs(from_date: Optional[str] = None, to_date: Optional[str] = None):
    if not from_date or not to_date:
        return jobs_db
    
    filtered = []
    f_date = datetime.strptime(from_date, "%Y-%m-%d")
    t_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
    
    for job in jobs_db:
        j_date = parse_job_date(job.get("start_time", ""))
        if j_date and f_date <= j_date <= t_date:
            filtered.append(job)
    return filtered

@app.put("/api/jobs/{job_id}", response_model=JobResponse)
def update_job(job_id: int, job_update: JobUpdate):
    for job in jobs_db:
        if job["id"] == job_id:
            if job_update.status is not None:
                job["status"] = job_update.status
            if job_update.technicians is not None:
                job["technicians"] = job_update.technicians
            if job_update.end_time is not None:
                job["end_time"] = job_update.end_time
            if job_update.additional_unplanned_work is not None:
                job["additional_unplanned_work"] = job_update.additional_unplanned_work

            if job_update.spare_parts is not None:
                job["spare_parts"] = [p.dict() for p in job_update.spare_parts]

            if job_update.lubricant_liters is not None: job["lubricant_liters"] = job_update.lubricant_liters
            if job_update.lubricant_cost is not None: job["lubricant_cost"] = job_update.lubricant_cost
            if job_update.battery_cost is not None: job["battery_cost"] = job_update.battery_cost
            if job_update.tire_cost is not None: job["tire_cost"] = job_update.tire_cost

            job["duration"] = calculate_duration(job["start_time"], job.get("end_time", ""))
            
            job["spare_parts_cost"] = sum(p["qty"] * p["unit_cost"] for p in job.get("spare_parts", []))
            job["spare_parts_qty"] = sum(p["qty"] for p in job.get("spare_parts", []))
            
            job["total_cost"] = (
                job["spare_parts_cost"] + 
                job["lubricant_cost"] + 
                job["battery_cost"] + 
                job["tire_cost"]
            )
            return job
    raise HTTPException(status_code=404, detail="Job not found")

@app.get("/api/reports/executive-summary")
def get_executive_summary(from_date: Optional[str] = Query(None), to_date: Optional[str] = Query(None)):
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    def summarize(period_start, period_end=None):
        summary = {
            "total_jobs": 0,
            "spare_parts_qty": 0,
            "spare_parts_cost": 0.0,
            "lubricant_liters": 0.0,
            "lubricant_cost": 0.0,
            "battery_cost": 0.0,
            "tire_cost": 0.0,
            "total_cost": 0.0
        }
        for job in jobs_db:
            job_date = parse_job_date(job.get("start_time", ""))
            if job_date:
                in_period = False
                if period_end:
                    in_period = (period_start <= job_date <= period_end)
                else:
                    in_period = (job_date >= period_start)

                if in_period:
                    summary["total_jobs"] += 1
                    summary["spare_parts_qty"] += job.get("spare_parts_qty", 0)
                    summary["spare_parts_cost"] += job.get("spare_parts_cost", 0.0)
                    summary["lubricant_liters"] += job.get("lubricant_liters", 0.0)
                    summary["lubricant_cost"] += job.get("lubricant_cost", 0.0)
                    summary["battery_cost"] += job.get("battery_cost", 0.0)
                    summary["tire_cost"] += job.get("tire_cost", 0.0)
                    summary["total_cost"] += job.get("total_cost", 0.0)
        return summary

    result = {
        "weekly": summarize(seven_days_ago),
        "monthly": summarize(thirty_days_ago),
        "custom": None
    }

    if from_date and to_date:
        f_date = datetime.strptime(from_date, "%Y-%m-%d")
        t_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
        result["custom"] = summarize(f_date, t_date)

    return result

@app.get("/api/reports/excel/weekly")
def generate_weekly_excel_report():
    seven_days_ago = datetime.now() - timedelta(days=7)
    filtered_jobs = [j for j in jobs_db if parse_job_date(j.get("start_time", "")) and parse_job_date(j.get("start_time", "")) >= seven_days_ago]
    return build_excel_response(filtered_jobs, "steely_rmi_weekly_garage_report.xlsx")

@app.get("/api/reports/excel/monthly")
def generate_monthly_excel_report():
    thirty_days_ago = datetime.now() - timedelta(days=30)
    filtered_jobs = [j for j in jobs_db if parse_job_date(j.get("start_time", "")) and parse_job_date(j.get("start_time", "")) >= thirty_days_ago]
    return build_excel_response(filtered_jobs, "steely_rmi_monthly_garage_report.xlsx")

@app.get("/api/reports/excel")
def generate_excel_report(from_date: Optional[str] = Query(None), to_date: Optional[str] = Query(None)):
    data = jobs_db
    if from_date and to_date:
        f_date = datetime.strptime(from_date, "%Y-%m-%d")
        t_date = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
        data = [j for j in jobs_db if parse_job_date(j.get("start_time", "")) and f_date <= parse_job_date(j.get("start_time", "")) <= t_date]

    return build_excel_response(data, "steely_rmi_garage_report.xlsx")
