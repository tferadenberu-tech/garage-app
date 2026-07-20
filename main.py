from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import pandas as pd
import io

app = FastAPI(title="Garage Fleet Management System v2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# 1. Data Models (የተሻሻለ)
# ----------------------------------------------------
class JobCreate(BaseModel):
    vehicle_plate: str
    driver_name: str
    work_type: str  # የሚሰራው ስራ አይነት (ለምሳሌ፡ Preventive Maintenance, Corrective Maintenance)
    issue_description: str
    start_time: str # የተጀመረበት ሰዓትና ቀን (YYYY-MM-DD HH:MM)
    end_time: Optional[str] = "" # ያለቀበት ሰዓትና ቀን
    
    # የወጪ ዝርዝሮች
    spare_parts_cost: float = 0.0
    lubricant_cost: float = 0.0
    battery_cost: float = 0.0
    tire_cost: float = 0.0
    labor_cost: float = 0.0

class JobResponse(JobCreate):
    id: int
    status: str
    duration: str # የፈጀው ጊዜ
    total_cost: float

class StatusUpdate(BaseModel):
    status: str

# ----------------------------------------------------
# 2. In-Memory Database
# ----------------------------------------------------
jobs_db = []
job_id_counter = 1

# የጊዜ ልዩነት ማስያ ዘዴ (Duration Calculator)
def calculate_duration(start_str: str, end_str: str) -> str:
    if not start_str or not end_str:
        return "በሂደት ላይ (In Progress)"
    try:
        fmt = "%Y-%m-%dT%H:%M"
        t1 = datetime.strptime(start_str, fmt)
        t2 = datetime.strptime(end_str, fmt)
        diff = t2 - t1
        
        hours, remainder = divmod(diff.total_seconds(), 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{int(hours)} ሰዓት ከ {int(minutes)} ደቂቃ"
    except Exception:
        return "N/A"

# ----------------------------------------------------
# 3. API Endpoints
# ----------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_home():
    return """
    <!DOCTYPE html>
    <html lang="am">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>የጋራዥ መቆጣጠሪያ ሲስተም</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f7f6; }
            h1 { color: #333; }
            .container { max-width: 850px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .form-group { margin-bottom: 15px; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, select { width: 100%; padding: 8px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; }
            button { background-color: #28a745; color: white; padding: 10px 15px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
            button:hover { background-color: #218838; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 14px; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
            th { background-color: #007bff; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>የጋራዥ ጥገና እና ወጪ መመዝገቢያ</h1>
            <form id="jobForm">
                <div class="form-group">
                    <label>የታርጋ ቁጥር (Plate Number):</label>
                    <input type="text" id="vehicle_plate" required placeholder="ምሳሌ: 3-A66865">
                </div>
                <div class="form-group">
                    <label>የአሽከርካሪ ስም (Driver Name):</label>
                    <input type="text" id="driver_name" required placeholder="ምሳሌ: አበበ">
                </div>
                <div class="form-group">
                    <label>የሚሰራው ስራ አይነት (Work Type):</label>
                    <select id="work_type" required>
                        <option value="Preventive Maintenance">መደበኛ ጥገና (Preventive Maintenance)</option>
                        <option value="Corrective Maintenance">የብልሽት ጥገና (Corrective Maintenance)</option>
                        <option value="Inspection & Checkup">አጠቃላይ ፍተሻ (Inspection)</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>የብልሽት/የስራ መግለጫ (Issue Description):</label>
                    <textarea id="issue_description" required placeholder="የተሰራው ስራ ዝርዝር..."></textarea>
                </div>
                
                <h3>የጊዜ መረጃ (Time Tracking)</h3>
                <div class="form-group">
                    <label>የተጀመረበት ቀን እና ሰዓት:</label>
                    <input type="datetime-local" id="start_time" required>
                </div>
                <div class="form-group">
                    <label>ያለቀበት ቀን እና ሰዓት (ካለቀ):</label>
                    <input type="datetime-local" id="end_time">
                </div>

                <h3>የወጪ ዝርዝር (በብር)</h3>
                <div class="form-group">
                    <label>የተለዋዋጭ ዕቃዎች ወጪ (Spare Parts Cost):</label>
                    <input type="number" id="spare_parts_cost" value="0" step="0.01">
                </div>
                <div class="form-group">
                    <label>የዘይት እና ቅባት ወጪ (Lubricant Cost):</label>
                    <input type="number" id="lubricant_cost" value="0" step="0.01">
                </div>
                <div class="form-group">
                    <label>የባትሪ ወጪ (Battery Cost):</label>
                    <input type="number" id="battery_cost" value="0" step="0.01">
                </div>
                <div class="form-group">
                    <label>የጎማ ወጪ (Tire Cost):</label>
                    <input type="number" id="tire_cost" value="0" step="0.01">
                </div>
                <div class="form-group">
                    <label>የጉልበት/የስራ ወጪ (Labor Cost):</label>
                    <input type="number" id="labor_cost" value="0" step="0.01">
                </div>
                <button type="submit">መዝግብ</button>
            </form>

            <hr style="margin-top: 30px;">
            <h2>የተመዘገቡ ስራዎች ዝርዝር</h2>
            <button onclick="downloadExcel()" style="background-color: #17a2b8;">በ Excel አውርድ (Export)</button>
            <table id="jobsTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>ታርጋ</th>
                        <th>የስራ አይነት</th>
                        <th>የተጀመረበት</th>
                        <th>ያለቀበት</th>
                        <th>የፈጀው ጊዜ</th>
                        <th>ጠቅላላ ወጪ</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody></tbody>
            </table>
        </div>

        <script>
            async function fetchJobs() {
                const res = await fetch('/api/jobs');
                const jobs = await res.json();
                const tbody = document.querySelector('#jobsTable tbody');
                tbody.innerHTML = '';
                jobs.forEach(j => {
                    tbody.innerHTML += `<tr>
                        <td>${j.id}</td>
                        <td>${j.vehicle_plate}</td>
                        <td>${j.work_type}</td>
                        <td>${j.start_time.replace('T', ' ')}</td>
                        <td>${j.end_time ? j.end_time.replace('T', ' ') : '-'}</td>
                        <td><b>${j.duration}</b></td>
                        <td>${j.total_cost} ETB</td>
                        <td>${j.status}</td>
                    </tr>`;
                });
            }

            document.getElementById('jobForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                const data = {
                    vehicle_plate: document.getElementById('vehicle_plate').value,
                    driver_name: document.getElementById('driver_name').value,
                    work_type: document.getElementById('work_type').value,
                    issue_description: document.getElementById('issue_description').value,
                    start_time: document.getElementById('start_time').value,
                    end_time: document.getElementById('end_time').value,
                    spare_parts_cost: parseFloat(document.getElementById('spare_parts_cost').value) || 0,
                    lubricant_cost: parseFloat(document.getElementById('lubricant_cost').value) || 0,
                    battery_cost: parseFloat(document.getElementById('battery_cost').value) || 0,
                    tire_cost: parseFloat(document.getElementById('tire_cost').value) || 0,
                    labor_cost: parseFloat(document.getElementById('labor_cost').value) || 0
                };

                await fetch('/api/jobs', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                document.getElementById('jobForm').reset();
                fetchJobs();
            });

            function downloadExcel() {
                window.location.href = '/api/reports/excel';
            }

            fetchJobs();
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
        job.tire_cost + 
        job.labor_cost
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

@app.put("/api/jobs/{job_id}/status", response_model=JobResponse)
def update_job_status(job_id: int, status_update: StatusUpdate):
    for job in jobs_db:
        if job["id"] == job_id:
            job["status"] = status_update.status
            return job
    raise HTTPException(status_code=404, detail="Job not found")

@app.get("/api/reports/excel")
def generate_excel_report():
    if not jobs_db:
        df = pd.DataFrame(columns=[
            "ID", "Vehicle Plate", "Driver Name", "Work Type", "Issue Description",
            "Start Time", "End Time", "Duration", "Spare Parts Cost", 
            "Lubricant Cost", "Battery Cost", "Tire Cost", "Labor Cost", "Total Cost", "Status"
        ])
    else:
        df = pd.DataFrame(jobs_db)
        df = df.rename(columns={
            "id": "ID",
            "vehicle_plate": "Vehicle Plate",
            "driver_name": "Driver Name",
            "work_type": "Work Type",
            "issue_description": "Issue Description",
            "start_time": "Start Time",
            "end_time": "End Time",
            "duration": "Duration",
            "spare_parts_cost": "Spare Parts Cost",
            "lubricant_cost": "Lubricant Cost",
            "battery_cost": "Battery Cost",
            "tire_cost": "Tire Cost",
            "labor_cost": "Labor Cost",
            "total_cost": "Total Cost",
            "status": "Status"
        })

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Garage_Report')
    
    output.seek(0)
    
    headers = {
        'Content-Disposition': 'attachment; filename="garage_fleet_report.xlsx"'
    }
    return StreamingResponse(output, headers=headers, media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
