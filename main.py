import os
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ---------------------------------------------------------
# DATABASE CONFIGURATION
# ---------------------------------------------------------
DATABASE_URL = "sqlite:///./steely_rmi_garage.db"
EXCEL_BACKUP_FILE = "garage_maintenance_backup.xlsx"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------------------------------------------------
# DATABASE MODEL (SteelY R.M.I Garage Maintenance Schema)
# ---------------------------------------------------------
class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    equipment_category = Column(String) # Loader, Excavator, Grabber, Truck, etc.
    vehicle_plate = Column(String, index=True) # ID / Plate No
    vehicle_model = Column(String)
    current_hours = Column(Float, default=0.0) # Current Hour Meter
    last_service_hours = Column(Float, default=0.0) # Hour Meter at last service
    maintenance_type = Column(String)
    spare_part_name = Column(String) # Spare Part Spec / Oil / Filter Specification
    spare_part_qty = Column(Integer, default=0)
    spare_part_cost = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    status = Column(String, default="Completed")
    created_at = Column(DateTime, default=datetime.now)

# Create Database Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="SteelY R.M.I Garage Maintnace dash Bord")

# ---------------------------------------------------------
# HELPER FUNCTIONS (Excel Auto Backup)
# ---------------------------------------------------------
def backup_to_excel():
    """Exports all records from SQLite database to an Excel file backup"""
    db: Session = SessionLocal()
    try:
        records = db.query(MaintenanceRecord).all()
        data = []
        for r in records:
            hours_run = (r.current_hours or 0.0) - (r.last_service_hours or 0.0)
            data.append({
                "ID": r.id,
                "Date": r.date,
                "Category": r.equipment_category or "Machine/Vehicle",
                "Machine ID / Plate": r.vehicle_plate,
                "Model": r.vehicle_model,
                "Current Hour Meter": r.current_hours,
                "Last Service Hour Meter": r.last_service_hours,
                "Hours Run Since Service": max(0.0, hours_run),
                "Maintenance Type": r.maintenance_type,
                "Spare Part Spec / Name": r.spare_part_name,
                "Quantity": r.spare_part_qty,
                "Unit Cost": r.spare_part_cost,
                "Total Cost": r.total_cost,
                "Status": r.status,
                "Recorded Date": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else ""
            })
        
        df = pd.DataFrame(data)
        df.to_excel(EXCEL_BACKUP_FILE, index=False)
    except Exception as e:
        print(f"Excel backup error: {e}")
    finally:
        db.close()

# ---------------------------------------------------------
# DASHBOARD ROUTE
# ---------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def read_dashboard(msg: str = None):
    """Main Dashboard View"""
    db: Session = SessionLocal()
    records = db.query(MaintenanceRecord).order_by(MaintenanceRecord.id.desc()).all()
    db.close()
    
    # Alert banner
    alert_html = ""
    if msg == "saved":
        alert_html = """
        <div style="background-color: #d4edda; color: #155724; padding: 12px 20px; 
                    margin: 15px auto; border: 1px solid #c3e6cb; border-radius: 6px; 
                    text-align: center; font-weight: bold; font-size: 1.1em; max-width: 900px;">
            ✅ Work Order Successfully Saved & Service Hours Updated!
        </div>
        """

    rows_html = ""
    for r in records:
        curr_h = r.current_hours or 0.0
        last_h = r.last_service_hours or 0.0
        hours_run = curr_h - last_h
        next_due = last_h + 250.0

        # Calculate 250-hour service alert status
        if curr_h > 0 and last_h > 0:
            if hours_run >= 250.0:
                service_badge = f"""<span style="background-color: #feb2b2; color: #9b2c2c; padding: 4px 8px; border-radius: 4px; font-weight: bold;">🔴 DUE FOR 250H SERVICE</span>
                <br><small style="color: #718096;">Run: {hours_run:,.1f} hrs / Due @ {next_due:,.1f} hrs</small>"""
            else:
                remaining = 250.0 - hours_run
                service_badge = f"""<span style="background-color: #c6f6d5; color: #22543d; padding: 4px 8px; border-radius: 4px; font-weight: bold;">🟢 OK ({remaining:,.1f} hrs left)</span>
                <br><small style="color: #718096;">Next Due @ {next_due:,.1f} hrs</small>"""
        else:
            service_badge = f"""<span style="color: #4a5568; font-weight: bold;">{r.status}</span>"""

        rows_html += f"""
        <tr>
            <td>{r.id}</td>
            <td>{r.date}</td>
            <td><strong>{r.equipment_category or 'General'}</strong></td>
            <td>{r.vehicle_plate}</td>
            <td>{r.vehicle_model}</td>
            <td>{curr_h:,.1f} hrs</td>
            <td>{last_h:,.1f} hrs</td>
            <td>{service_badge}</td>
            <td>{r.maintenance_type}</td>
            <td>{r.spare_part_name or '-'}</td>
            <td>{r.spare_part_qty}</td>
            <td>{r.spare_part_cost:,.2f}</td>
            <td><strong>{r.total_cost:,.2f}</strong></td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>SteelY R.M.I Garage Maintnace dash Bord</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f4f6f9; }}
            h1 {{ color: #1a365d; text-align: center; margin-bottom: 5px; }}
            .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
            form {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; }}
            label {{ font-weight: bold; font-size: 0.88em; margin-bottom: 4px; display: block; color: #2d3748; }}
            input, select {{ width: 100%; padding: 8px; border: 1px solid #cbd5e0; border-radius: 4px; box-sizing: border-box; }}
            button {{ grid-column: 1 / -1; background-color: #2b6cb0; color: white; border: none; padding: 12px; font-size: 16px; font-weight: bold; border-radius: 4px; cursor: pointer; }}
            button:hover {{ background-color: #2c5282; }}
            table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); font-size: 0.92em; }}
            th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background-color: #2b6cb0; color: white; font-weight: 600; }}
            tr:hover {{ background-color: #f7fafc; }}
        </style>
    </head>
    <body>
        <!-- Header -->
        <h1>SteelY R.M.I Garage Maintnace dash Bord</h1>
        
        <!-- Success Alert Message -->
        {alert_html}

        <div class="card">
            <h2>New Work Order Entry (Loader / Excavator / Machine Tracking)</h2>
            <form action="/add-record" method="post">
                <div>
                    <label>Date:</label>
                    <input type="date" name="date" required>
                </div>
                <div>
                    <label>Equipment Category:</label>
                    <select name="equipment_category">
                        <option value="Loader">Loader (ሎደር)</option>
                        <option value="Excavator">Excavator (እስካቫተር)</option>
                        <option value="Grabber">Grabber (ግራበር)</option>
                        <option value="Dump Truck">Dump Truck (ትራክ)</option>
                        <option value="Forklift">Forklift (ፎርክሊፍት)</option>
                        <option value="Rolling Mill Equipment">Rolling Mill Machine</option>
                        <option value="Other Heavy Equipment">Other Heavy Machine</option>
                    </select>
                </div>
                <div>
                    <label>Plate / Machine ID No:</label>
                    <input type="text" name="vehicle_plate" placeholder="e.g. LDR-01, EXCAV-02, 3-12345" required>
                </div>
                <div>
                    <label>Machine / Vehicle Model:</label>
                    <input type="text" name="vehicle_model" placeholder="e.g. CAT 950, Komatsu PC200, XCMG" required>
                </div>
                <div>
                    <label>Current Hour Meter (hrs):</label>
                    <input type="number" step="0.1" name="current_hours" placeholder="e.g. 1500.0" value="0.0">
                </div>
                <div>
                    <label>Last Service Hour Meter (hrs):</label>
                    <input type="number" step="0.1" name="last_service_hours" placeholder="e.g. 1250.0" value="0.0">
                </div>
                <div>
                    <label>Maintenance Type:</label>
                    <select name="maintenance_type">
                        <option value="250h Oil & Filter Service">250 Hours Oil & Filter Service</option>
                        <option value="500h Hydraulic Service">500 Hours Hydraulic & System Service</option>
                        <option value="Preventive Maintenance">Preventive Maintenance</option>
                        <option value="Corrective Maintenance">Corrective Maintenance</option>
                        <option value="Overhaul">Overhaul / Major Repair</option>
                    </select>
                </div>
                <div>
                    <label>Spare Part Spec / Name:</label>
                    <input type="text" name="spare_part_name" placeholder="e.g. Engine Oil 15W40, Oil Filter, Fuel Filter">
                </div>
                <div>
                    <label>Quantity / Liters:</label>
                    <input type="number" name="spare_part_qty" value="1" min="0">
                </div>
                <div>
                    <label>Unit Cost:</label>
                    <input type="number" step="0.01" name="spare_part_cost" value="0.00">
                </div>
                <button type="submit">Submit Work Order</button>
            </form>
        </div>

        <div class="card">
            <h2>Maintenance Records & 250-Hour Service Tracking Log</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Date</th>
                        <th>Category</th>
                        <th>Machine ID/Plate</th>
                        <th>Model</th>
                        <th>Current Hours</th>
                        <th>Last Service Hours</th>
                        <th>250h Service Status</th>
                        <th>Type</th>
                        <th>Spare Part Spec/Name</th>
                        <th>Qty</th>
                        <th>Unit Cost</th>
                        <th>Total Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="13" style="text-align:center;">No maintenance records found.</td></tr>'}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return html_content

# ---------------------------------------------------------
# SAVE WORK ORDER ROUTE
# ---------------------------------------------------------
@app.post("/add-record")
def add_record(
    date: str = Form(...),
    equipment_category: str = Form(...),
    vehicle_plate: str = Form(...),
    vehicle_model: str = Form(...),
    current_hours: float = Form(0.0),
    last_service_hours: float = Form(0.0),
    maintenance_type: str = Form(...),
    spare_part_name: Optional[str] = Form(None),
    spare_part_qty: int = Form(0),
    spare_part_cost: float = Form(0.0)
):
    """Saves new Work Order to SQLite and updates Excel backup"""
    db: Session = SessionLocal()
    
    total_cost = spare_part_qty * spare_part_cost
    
    new_record = MaintenanceRecord(
        date=date,
        equipment_category=equipment_category,
        vehicle_plate=vehicle_plate,
        vehicle_model=vehicle_model,
        current_hours=current_hours,
        last_service_hours=last_service_hours if last_service_hours > 0 else current_hours,
        maintenance_type=maintenance_type,
        spare_part_name=spare_part_name,
        spare_part_qty=spare_part_qty,
        spare_part_cost=spare_part_cost,
        total_cost=total_cost,
        status="Completed"
    )
    
    db.add(new_record)
    db.commit()
    db.refresh(new_record)
    db.close()
    
    # Auto Backup to Excel
    backup_to_excel()
    
    # Redirect back with success message
    return RedirectResponse(url="/?msg=saved", status_code=303)
