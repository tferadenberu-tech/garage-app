
from fastapi import FastAPI, HTTPException
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
class JobCreate(BaseModel):
    serial_number: str
    vehicle_plate: str
    vehicle_type: str
    driver_name: str
    technicians: str
    work_type: str 
    issue_description: str
    start_time: str
    end_time: Optional[str] = ""
    
    spare_parts_qty: int = 0
    spare_parts_cost: float = 0.0
    lubricant_liters: float = 0.0
    lubricant_cost: float = 0.0
    battery_cost: float = 0.0
    tire_cost: float = 0.0

class JobUpdate(BaseModel):
    technicians: Optional[str] = None
    status: Optional[str] = None
    end_time: Optional[str] = None
    spare_parts_qty: Optional[int] = None
    spare_parts_cost: Optional[float] = None
    lubricant_liters: Optional[float] = None
    lubricant_cost: Optional[float] = None
    battery_cost: Optional[float] = None
    tire_cost: Optional[float] = None

class JobResponse(JobCreate):
    id: int
    status: str
    duration: str
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
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f7f6; }
            h1, h2, h3 { color: #1a365d; }
            .container { max-width: 1100px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, select { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
            button { background-color: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 15px; margin-right: 5px; }
            button:hover { background-color: #218838; }
            .btn-info { background-color: #17a2b8; }
            .btn-info:hover { background-color: #138496; }
            .btn-edit { background-color: #ffc107; color: #212529; padding: 5px 10px; font-size: 13px; }
            .btn-edit:hover { background-color: #e0a800; }
            table { width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 13px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #1a365d; color: white; }
            
            .summary-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px; margin-bottom: 25px; }
            .card { background: #f8f9fa; border-left: 5px solid #007bff; padding: 15px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
            .card.monthly { border-left-color: #28a745; }
            .card h4 { margin: 0 0 10px 0; color: #333; text-transform: uppercase; font-size: 13px; }
            .stat-row { display: flex; justify-content: space-between; margin-bottom: 5px; font-size: 13px; }
            .stat-total { font-weight: bold; border-top: 1px dashed #ccc; padding-top: 5px; margin-top: 5px; font-size: 14px; color: #111; }

            /* Modal Dialog Box */
            .modal { display: none; position: fixed; z-index: 100; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
            .modal-content { background-color: white; margin: 3% auto; padding: 20px; border-radius: 8px; width: 500px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); max-height: 90vh; overflow-y: auto; }
            .close-btn { color: #aaa; float: right; font-size: 24px; font-weight: bold; cursor: pointer; }
            .close-btn:hover { color: black; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Steely R.M.I Garage Maintenance Dashboard</h1>
            
            <h2>Executive Summary</h2>
            <div class="summary-grid">
                <div class="card" id="weeklyCard">
                    <h4>Weekly Executive Summary (Last 7 Days)</h4>
                    <div id="weeklyStats">Loading...</div>
                </div>
                <div class="card monthly" id="monthlyCard">
                    <h4>Monthly Executive Summary (Last 30 Days)</h4>
                    <div id="monthlyStats">Loading...</div>
                </div>
            </div>

            <hr style="margin: 25px 0;">

            <h2>Create Work Order</h2>
            <form id="jobForm">
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
                    <input type="text" id="vehicle_type" required placeholder="e.g., Jellion, Actros, Land Cruiser">
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
                <div class="form-group">
                    <label>Issue Description:</label>
                    <textarea id="issue_description" required placeholder="Detail repair scope..."></textarea>
                </div>
                
                <h3>Time Tracking</h3>
                <div class="form-group">
                    <label>Start Date & Time:</label>
                    <input type="datetime-local" id="start_time" required>
                </div>
                <div class="form-group">
                    <label>End Date & Time (Optional):</label>
                    <input type="datetime-local" id="end_time">
                </div>

                <h3>Spare Parts & Lubricants Breakdown</h3>
                <div class="form-group">
                    <label>Spare Parts Quantity (Pcs):</label>
                    <input type="number" id="spare_parts_qty" value="0" min="0" step="1">
                </div>
                <div class="form-group">
                    <label>Spare Parts Cost (ETB):</label>
                    <input type="number" id="spare_parts_cost" value="0" step="0.01">
                </div>
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
                <button type="submit">Submit Work Order</button>
            </form>

            <hr style="margin: 30px 0;">
            <h2>Recent Work Orders</h2>
            <button onclick="downloadExcel()" class="btn-info">Export Excel Report</button>
            <table id="jobsTable">
                <thead>
                    <tr>
                        <th>S/N</th>
                        <th>Plate</th>
                        <th>Vehicle Type</th>
                        <th>Technicians</th>
                        <th>Parts (Pcs)</th>
                        <th>Lubricants (L)</th>
                        <th>Duration</th>
                        <th>Total Cost</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <!-- EDIT WORK ORDER MODAL DIALOG -->
        <div id="editModal" class="modal">
            <div class="modal-content">
                <span class="close-btn" onclick="closeModal()">&times;</span>
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
                        <label>Spare Parts Quantity (Pcs):</label>
                        <input type="number" id="edit_spare_parts_qty" step="1">
                    </div>
                    <div class="form-group">
                        <label>Spare Parts Cost (ETB):</label>
                        <input type="number" id="edit_spare_parts_cost" step="0.01">
                    </div>
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
                    <button type="submit">Save Changes</button>
                    <button type="button" onclick="closeModal()" style="background-color: #6c757d;">Cancel</button>
                </form>
            </div>
        </div>

        <script>
            let allJobs = [];

            async function fetchSummary() {
                const res = await fetch('/api/reports/executive-summary');
                const summary = await res.json();
                
                function renderCard(data) {
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
            }

            async function fetchJobs() {
                const res = await fetch('/api/jobs');
                allJobs = await res.json();
                const tbody = document.querySelector('#jobsTable tbody');
                tbody.innerHTML = '';
                allJobs.forEach(j => {
                    tbody.innerHTML += `<tr>
                        <td><b>${j.serial_number}</b></td>
                        <td>${j.vehicle_plate}</td>
                        <td><b>${j.vehicle_type}</b></td>
                        <td>${j.technicians}</td>
                        <td>${j.spare_parts_qty} Pcs</td>
                        <td>${j.lubricant_liters} L</td>
                        <td><b>${j.duration}</b></td>
                        <td>ETB ${j.total_cost.toLocaleString()}</td>
                        <td>${j.status}</td>
                        <td><button class="btn-edit" onclick="openEditModal(${j.id})">Edit</button></td>
                    </tr>`;
                });
            }

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
                    start_time: document.getElementById('start_time').value,
                    end_time: document.getElementById('end_time').value,
                    spare_parts_qty: parseInt(document.getElementById('spare_parts_qty').value) || 0,
                    spare_parts_cost: parseFloat(document.getElementById('spare_parts_cost').value) || 0,
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
                fetchJobs();
                fetchSummary();
            });

            function openEditModal(id) {
                const job = allJobs.find(j => j.id === id);
                if (!job) return;

                document.getElementById('editJobIdTitle').innerText = job.serial_number;
                document.getElementById('editJobId').value = job.id;
                document.getElementById('edit_status').value = job.status;
                document.getElementById('edit_technicians').value = job.technicians || '';
                document.getElementById('edit_end_time').value = job.end_time || '';
                document.getElementById('edit_spare_parts_qty').value = job.spare_parts_qty || 0;
                document.getElementById('edit_spare_parts_cost').value = job.spare_parts_cost || 0;
                document.getElementById('edit_lubricant_liters').value = job.lubricant_liters || 0;
                document.getElementById('edit_lubricant_cost').value = job.lubricant_cost || 0;
                document.getElementById('edit_battery_cost').value = job.battery_cost || 0;
                document.getElementById('edit_tire_cost').value = job.tire_cost || 0;

                document.getElementById('editModal').style.display = 'block';
            }

            function closeModal() {
                document.getElementById('editModal').style.display = 'none';
            }

            document.getElementById('editForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const jobId = document.getElementById('editJobId').value;
                const data = {
                    status: document.getElementById('edit_status').value,
                    technicians: document.getElementById('edit_technicians').value,
                    end_time: document.getElementById('edit_end_time').value,
                    spare_parts_qty: parseInt(document.getElementById('edit_spare_parts_qty').value) || 0,
                    spare_parts_cost: parseFloat(document.getElementById('edit_spare_parts_cost').value) || 0,
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

                closeModal();
                fetchJobs();
                fetchSummary();
            });

            function downloadExcel() {
                window.location.href = '/api/reports/excel';
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
    total = (
        job.spare_parts_cost + 
        job.lubricant_cost + 
        job.battery_cost + 
        job.tire_cost
    )
    duration_str = calculate_duration(job.start_time, job.end_time)
    
    job_data = job.dict()
    job_data["id"] = job_id_counter
    job_data["status"] = "Completed" if job.end_time else "In Progress"
    job_data["duration"] = duration_str
    job_data["total_cost"] = total
    
    jobs_db.append(job_data)
    job_id_counter += 1
    return job_data

@app.get("/api/jobs", response_model=List[JobResponse])
def get_jobs():
    return jobs_db

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
            if job_update.spare_parts_qty is not None:
                job["spare_parts_qty"] = job_update.spare_parts_qty
            if job_update.spare_parts_cost is not None:
                job["spare_parts_cost"] = job_update.spare_parts_cost
            if job_update.lubricant_liters is not None:
                job["lubricant_liters"] = job_update.lubricant_liters
            if job_update.lubricant_cost is not None:
                job["lubricant_cost"] = job_update.lubricant_cost
            if job_update.battery_cost is not None:
                job["battery_cost"] = job_update.battery_cost
            if job_update.tire_cost is not None:
                job["tire_cost"] = job_update.tire_cost

            # Recalculate duration & total cost
            job["duration"] = calculate_duration(job["start_time"], job.get("end_time", ""))
            job["total_cost"] = (
                job["spare_parts_cost"] + 
                job["lubricant_cost"] + 
                job["battery_cost"] + 
                job["tire_cost"]
            )
            return job
    raise HTTPException(status_code=404, detail="Job not found")

@app.get("/api/reports/executive-summary")
def get_executive_summary():
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    thirty_days_ago = now - timedelta(days=30)

    def summarize(period_start):
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
            if job_date and job_date >= period_start:
                summary["total_jobs"] += 1
                summary["spare_parts_qty"] += job.get("spare_parts_qty", 0)
                summary["spare_parts_cost"] += job.get("spare_parts_cost", 0.0)
                summary["lubricant_liters"] += job.get("lubricant_liters", 0.0)
                summary["lubricant_cost"] += job.get("lubricant_cost", 0.0)
                summary["battery_cost"] += job.get("battery_cost", 0.0)
                summary["tire_cost"] += job.get("tire_cost", 0.0)
                summary["total_cost"] += job.get("total_cost", 0.0)
        return summary

    return {
        "weekly": summarize(seven_days_ago),
        "monthly": summarize(thirty_days_ago)
    }

@app.get("/api/reports/excel")
def generate_excel_report():
    if not jobs_db:
        df = pd.DataFrame(columns=[
            "S/N", "Vehicle Plate", "Vehicle Type", "Driver Name", "Assigned Technicians",
            "Work Type", "Issue Description", "Start Time", "End Time", "Duration",
            "Spare Parts Qty (Pcs)", "Spare Parts Cost", "Lubricants (Liters)", "Lubricant Cost", 
            "Battery Cost", "Tire Cost", "Total Cost", "Status"
        ])
    else:
        df = pd.DataFrame(jobs_db)
        df = df.rename(columns={
            "serial_number": "S/N",
            "vehicle_plate": "Vehicle Plate",
            "vehicle_type": "Vehicle Type",
            "driver_name": "Driver Name",
            "technicians": "Assigned Technicians",
            "work_type": "Work Type",
            "issue_description": "Issue Description",
            "start_time": "Start Time",
            "end_time": "End Time",
            "duration": "Duration",
            "spare_parts_qty": "Spare Parts Qty (Pcs)",
            "spare_parts_cost": "Spare Parts Cost",
            "lubricant_liters": "Lubricants (Liters)",
            "lubricant_cost": "Lubricant Cost",
            "battery_cost": "Battery Cost",
            "tire_cost": "Tire Cost",
            "total_cost": "Total Cost",
            "status": "Status"
        })
        if "id" in df.columns:
            df = df.drop(columns=["id"])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Garage_Report')
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="steely_rmi_garage_report.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
