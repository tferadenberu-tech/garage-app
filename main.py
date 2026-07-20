import io
import os
import sqlite3
from datetime import datetime
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Garage Fleet Management System v2")

# Enable CORS for mobile connectivity
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "garage.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL,
            plate_number TEXT NOT NULL,
            owner_name TEXT NOT NULL,
            current_km INTEGER,
            next_service_km INTEGER,
            maintenance_type TEXT,
            status TEXT DEFAULT 'Check-In',
            start_time TEXT,
            team_members TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

class JobCreate(BaseModel):
    order_number: str
    plate_number: str
    owner_name: str
    current_km: int
    next_service_km: int
    maintenance_type: str
    team_members: str

class StatusUpdate(BaseModel):
    status: str

@app.get("/api/jobs")
def get_jobs():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM jobs ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/api/jobs")
def create_job(job: JobCreate):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    start_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("""
        INSERT INTO jobs (order_number, plate_number, owner_name, current_km, next_service_km, maintenance_type, status, start_time, team_members)
        VALUES (?, ?, ?, ?, ?, ?, 'Check-In', ?, ?)
    """, (job.order_number, job.plate_number, job.owner_name, job.current_km, job.next_service_km, job.maintenance_type, start_str, job.team_members))
    conn.commit()
    conn.close()
    return {"message": "Work Order Created"}

@app.put("/api/jobs/{job_id}/status")
def update_job_status(job_id: int, status_data: StatusUpdate):
    """የመኪናውን የጥገና ደረጃ በዳታቤዝ ውስጥ ማዘመሪያ"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status = ? WHERE id = ?", (status_data.status, job_id))
    conn.commit()
    conn.close()
    return {"message": "Status Updated"}

@app.get("/api/reports/excel")
def generate_excel_report():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM jobs", conn)
    conn.close()
    if df.empty:
        raise HTTPException(status_code=404, detail="No records to export")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Fleet Report')
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=garage_report.xlsx"}
    )

@app.get("/", response_class=HTMLResponse)
def serve_home_page():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Garage Fleet Dashboard</title>
        <style>
            * { box-sizing: border-box; font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; }
            body { background: #f4f6f9; padding: 15px; }
            header { background: #1e293b; color: white; padding: 20px; border-radius: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px; }
            .btn { padding: 8px 14px; border: none; border-radius: 6px; cursor: pointer; font-weight: bold; font-size: 13px; }
            .btn-success { background: #10b981; color: white; }
            .btn-primary { background: #2563eb; color: white; }
            .btn-action { background: #64748b; color: white; padding: 4px 8px; font-size: 11px; margin-top: 5px; border-radius: 4px; }
            .report-section { margin-top: 15px; background: white; padding: 15px; border-radius: 8px; display: flex; gap: 12px; align-items: center; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .kanban { display: grid; grid-template-columns: repeat(auto-fit, minmax(255px, 1fr)); gap: 15px; margin-top: 20px; }
            .column { background: #e2e8f0; padding: 15px; border-radius: 8px; min-height: 450px; }
            .column h3 { font-size: 15px; color: #334155; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 2px solid #cbd5e1; }
            .card { background: white; padding: 15px; margin-bottom: 10px; border-radius: 6px; border-left: 5px solid #3b82f6; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
            .column:nth-child(2) .card { border-left-color: #f59e0b; }
            .column:nth-child(3) .card { border-left-color: #8b5cf6; }
            .column:nth-child(4) .card { border-left-color: #10b981; }
            .type-badge { background: #fee2e2; color: #dc2626; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 11px; }
            .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; z-index: 1000; padding: 10px; }
            .modal-content { background: white; padding: 25px; border-radius: 8px; width: 100%; max-width: 480px; }
            label { display: block; margin-top: 10px; font-weight: 600; color: #475569; }
            input, select { width: 100%; padding: 10px; margin-top: 4px; border: 1px solid #cbd5e1; border-radius: 4px; }
            .actions-div { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 8px; border-top: 1px dashed #cbd5e1; padding-top: 8px; }
        </style>
    </head>
    <body>
        <header>
            <div>
                <h2>Workshop Operations Board</h2>
                <p>Live Fleet Maintenance Tracking</p>
            </div>
            <button class="btn btn-success" onclick="document.getElementById('addModal').style.display='flex'">+ Create Work Order</button>
        </header>

        <div class="report-section">
            <strong>📊 Reports:</strong>
            <a href="/api/reports/excel"><button class="btn btn-primary">Download Excel Sheet</button></a>
        </div>

        <div class="kanban">
            <div class="column"><h3>Check-In</h3><div id="todo-col"></div></div>
            <div class="column"><h3>In Progress</h3><div id="progress-col"></div></div>
            <div class="column"><h3>QC (Testing)</h3><div id="qc-col"></div></div>
            <div class="column"><h3>Completed</h3><div id="done-col"></div></div>
        </div>

        <div id="addModal" class="modal">
            <div class="modal-content">
                <h3>New Work Order Details</h3>
                <form onsubmit="saveNewJob(event)">
                    <label>Work Order Number:</label><input type="text" id="orderNo" required placeholder="WO-2026-X">
                    <label>Plate Number:</label><input type="text" id="plateNo" required>
                    <label>Owner/Driver Name:</label><input type="text" id="ownerName" required>
                    <label>Current Mileage (KM):</label><input type="number" id="currentKm" required>
                    <label>Next Service Mileage (KM):</label><input type="number" id="nextKm" required>
                    <label>Maintenance Category:</label>
                    <select id="maintType">
                        <option value="PM">PM (Preventive)</option>
                        <option value="CM">CM (Corrective)</option>
                    </select>
                    <label>Assigned Mechanics:</label><input type="text" id="team">
                    <button type="submit" class="btn btn-success" style="width:100%; margin-top:15px;">Log to Board</button>
                </form>
                <button onclick="document.getElementById('addModal').style.display='none'" style="background:#64748b; color:white; width:100%; margin-top:8px;" class="btn">Cancel</button>
            </div>
        </div>

        <script>
            async function loadJobs() {
                const response = await fetch("/api/jobs");
                const jobs = await response.json();
                
                // Clear columns
                document.getElementById('todo-col').innerHTML = '';
                document.getElementById('progress-col').innerHTML = '';
                document.getElementById('qc-col').innerHTML = '';
                document.getElementById('done-col').innerHTML = '';

                jobs.forEach(job => {
                    const card = document.createElement('div');
                    card.className = 'card';
                    
                    // Create buttons based on status
                    let actionButtons = '';
                    if (job.status === "Check-In") {
                        actionButtons = `<button class="btn-action" style="background:#f59e0b;" onclick="moveJob(${job.id}, 'In Progress')">➔ Start Repair</button>`;
                    } else if (job.status === "In Progress") {
                        actionButtons = `<button class="btn-action" style="background:#8b5cf6;" onclick="moveJob(${job.id}, 'QC')">➔ Move to QC</button>`;
                    } else if (job.status === "QC") {
                        actionButtons = `<button class="btn-action" style="background:#10b981;" onclick="moveJob(${job.id}, 'Completed')">➔ Complete Job</button>`;
                    }

                    card.innerHTML = `
                        <div style="padding:5px;">
                            <strong>${job.order_number}</strong><br>
                            Plates: <strong>${job.plate_number}</strong><br>
                            Owner: ${job.owner_name}<br>
                            Type: <span class="type-badge">${job.maintenance_type}</span><br>
                            <small>KM: ${job.current_km} | Target: ${job.next_service_km}</small><br>
                            <small style="color:#64748b">Crew: ${job.team_members || 'None'}</small>
                            <div class="actions-div">${actionButtons}</div>
                        </div>
                    `;
                    
                    if(job.status === "Check-In") document.getElementById('todo-col').appendChild(card);
                    if(job.status === "In Progress") document.getElementById('progress-col').appendChild(card);
                    if(job.status === "QC") document.getElementById('qc-col').appendChild(card);
                    if(job.status === "Completed") document.getElementById('done-col').appendChild(card);
                });
            }

            async function moveJob(jobId, newStatus) {
                await fetch(`/api/jobs/${jobId}/status`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });
                loadJobs();
            }

            async function saveNewJob(event) {
                event.preventDefault();
                const data = {
                    order_number: document.getElementById('orderNo').value,
                    plate_number: document.getElementById('plateNo').value,
                    owner_name: document.getElementById('ownerName').value,
                    current_km: parseInt(document.getElementById('currentKm').value),
                    next_service_km: parseInt(document.getElementById('nextKm').value),
                    maintenance_type: document.getElementById('maintType').value,
                    team_members: document.getElementById('team').value
                };
                await fetch("/api/jobs", {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                document.getElementById('addModal').style.display = 'none';
                document.getElementById('addModal').querySelector('form').reset();
                loadJobs();
            }
            loadJobs();
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)