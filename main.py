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
    vehicle_plate = Column(String, index=True)
    vehicle_model = Column(String)
    maintenance_type = Column(String)
    spare_part_name = Column(String)  # Spare Part Specification / Name
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
            data.append({
                "ID": r.id,
                "Date": r.date,
                "Plate Number": r.vehicle_plate,
                "Model": r.vehicle_model,
                "Maintenance Type": r.maintenance_type,
                "Spare Part Spec/Name": r.spare_part_name,
                "Quantity": r.spare_part_qty,
                "Spare Part Cost": r.spare_part_cost,
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
    
    # Alert message displayed right under the header
    alert_html = ""
    if msg == "saved":
        alert_html = """
        <div style="background-color: #d4edda; color: #155724; padding: 12px 20px; 
                    margin: 15px auto; border: 1px solid #c3e6cb; border-radius: 6px; 
                    text-align: center; font-weight: bold; font-size: 1.1em; max-width: 800px;">
            ✅ Work Order Successfully Saved!
        </div>
        """

    rows_html = ""
    for r in records:
        rows_html += f"""
        <tr>
            <td>{r.id}</td>
            <td>{r.date}</td>
            <td>{r.vehicle_plate}</td>
            <td>{r.vehicle_model}</td>
            <td>{r.maintenance_type}</td>
            <td>{r.spare_part_name or '-'}</td>
            <td>{r.spare_part_qty}</td>
            <td>{r.spare_part_cost:,.2f}</td>
            <td>{r.total_cost:,.2f}</td>
            <td><span style="color: green; font-weight: bold;">{r.status}</span></td>
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
            form {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; }}
            label {{ font-weight: bold; font-size: 0.9em; margin-bottom: 5px; display: block; }}
            input, select {{ width: 100%; padding: 8px; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
            button {{ grid-column: 1 / -1; background-color: #2b6cb0; color: white; border: none; padding: 12px; font-size: 16px; font-weight: bold; border-radius: 4px; cursor: pointer; }}
            button:hover {{ background-color: #2c5282; }}
            table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
            th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
            th {{ background-color: #2b6cb0; color: white; }}
            tr:hover {{ background-color: #f1f5f9; }}
        </style>
    </head>
    <body>
        <!-- Header -->
        <h1>SteelY R.M.I Garage Maintnace dash Bord</h1>
        
        <!-- Success Alert Message -->
        {alert_html}

        <div class="card">
            <h2>New Work Order Entry</h2>
            <form action="/add-record" method="post">
                <div>
                    <label>Date:</label>
                    <input type="date" name="date" required>
                </div>
                <div>
                    <label>Plate Number:</label>
                    <input type="text" name="vehicle_plate" placeholder="e.g. 3-XXXXX" required>
                </div>
                <div>
                    <label>Vehicle Model:</label>
                    <input type="text" name="vehicle_model" placeholder="e.g. Isuzu, Sino Truck" required>
                </div>
                <div>
                    <label>Maintenance Type:</label>
                    <select name="maintenance_type">
                        <option value="Preventive">Preventive Maintenance</option>
                        <option value="Corrective">Corrective Maintenance</option>
                        <option value="Overhaul">Overhaul</option>
                    </select>
                </div>
                <div>
                    <label>Spare Part Spec / Name:</label>
                    <input type="text" name="spare_part_name" placeholder="Enter spare part specification/name">
                </div>
                <div>
                    <label>Quantity:</label>
                    <input type="number" name="spare_part_qty" value="1" min="0">
                </div>
                <div>
                    <label>Spare Part Unit Cost:</label>
                    <input type="number" step="0.01" name="spare_part_cost" value="0.00">
                </div>
                <button type="submit">Submit Work Order</button>
            </form>
        </div>

        <div class="card">
            <h2>Maintenance Records Log</h2>
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Date</th>
                        <th>Plate No.</th>
                        <th>Model</th>
                        <th>Type</th>
                        <th>Spare Part Spec/Name</th>
                        <th>Qty</th>
                        <th>Part Cost</th>
                        <th>Total Cost</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html if rows_html else '<tr><td colspan="10" style="text-align:center;">No maintenance records found.</td></tr>'}
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
    vehicle_plate: str = Form(...),
    vehicle_model: str = Form(...),
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
        vehicle_plate=vehicle_plate,
        vehicle_model=vehicle_model,
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
