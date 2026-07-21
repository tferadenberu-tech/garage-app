import io
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
import pandas as pd

# ==========================================
# 1. DATABASE CONFIGURATION (SQLite)
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./steely_rmi_garage.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================
# 2. SQLALCHEMY MODELS (DATABASE TABLES)
# ==========================================
class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id = Column(Integer, primary_key=True, index=True)
    serial_number = Column(String, nullable=True)
    work_order_no = Column(String, nullable=True)
    vehicle_plate = Column(String, index=True, nullable=False)
    vehicle_type = Column(String, nullable=False)
    driver_name = Column(String, nullable=True)
    current_km = Column(Float, nullable=False, default=0.0)
    next_service_km = Column(Float, nullable=False, default=0.0)
    work_type = Column(String, nullable=False)
    issue_description = Column(String, nullable=True)
    additional_unplanned_work = Column(String, nullable=True)
    status = Column(String, default="Completed")

    # Costs & Lubricants
    lubricant_liters = Column(Float, default=0.0)
    lubricant_cost = Column(Float, default=0.0)
    battery_cost = Column(Float, default=0.0)
    tire_cost = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    spare_parts = relationship("SparePartItem", back_populates="record", cascade="all, delete-orphan")
    technicians = relationship("TechnicianAssignment", back_populates="record", cascade="all, delete-orphan")


class SparePartItem(Base):
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("maintenance_records.id"), nullable=False)
    spec_name = Column(String, nullable=False)  # Spare Part Name (spec)
    qty = Column(Integer, nullable=False, default=1)
    unit_cost = Column(Float, nullable=False, default=0.0)

    record = relationship("MaintenanceRecord", back_populates="spare_parts")


class TechnicianAssignment(Base):
    __tablename__ = "technician_assignments"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("maintenance_records.id"), nullable=False)
    technician_name = Column(String, nullable=False)
    assigned_by = Column(String, nullable=True, default="Supervisor")
    assigned_at = Column(DateTime, default=datetime.utcnow)

    record = relationship("MaintenanceRecord", back_populates="technicians")

# Create Database Tables Automatically
Base.metadata.create_all(bind=engine)

# ==========================================
# 3. PYDANTIC SCHEMAS (VALIDATION)
# ==========================================
class SparePartCreate(BaseModel):
    spec_name: str
    qty: int = 1
    unit_cost: float = 0.0

class SparePartResponse(SparePartCreate):
    id: int
    class Config:
        from_attributes = True

class AssignTechnicianCreate(BaseModel):
    technician_name: str
    assigned_by: Optional[str] = "Supervisor"

class TechnicianResponse(BaseModel):
    id: int
    technician_name: str
    assigned_by: Optional[str]
    assigned_at: datetime
    class Config:
        from_attributes = True

class MaintenanceRecordCreate(BaseModel):
    serial_number: Optional[str] = ""
    work_order_no: Optional[str] = ""
    vehicle_plate: str
    vehicle_type: str
    driver_name: Optional[str] = ""
    current_km: float
    next_service_km: Optional[float] = None
    work_type: str
    issue_description: Optional[str] = ""
    additional_unplanned_work: Optional[str] = ""

    spare_parts: List[SparePartCreate] = []
    technicians: List[AssignTechnicianCreate] = []

    lubricant_liters: float = 0.0
    lubricant_cost: float = 0.0
    battery_cost: float = 0.0
    tire_cost: float = 0.0

class MaintenanceRecordResponse(BaseModel):
    id: int
    serial_number: Optional[str]
    work_order_no: Optional[str]
    vehicle_plate: str
    vehicle_type: str
    driver_name: Optional[str]
    current_km: float
    next_service_km: float
    work_type: str
    issue_description: Optional[str]
    additional_unplanned_work: Optional[str]
    status: str
    created_at: datetime

    spare_parts: List[SparePartResponse] = []
    technicians: List[TechnicianResponse] = []

    lubricant_liters: float
    lubricant_cost: float
    battery_cost: float
    tire_cost: float
    total_cost: float

    class Config:
        from_attributes = True

# ==========================================
# 4. FASTAPI APP & ROUTE API
# ==========================================
app = FastAPI(title="SteelY R.M.I Garage Maintnace dash Bord")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4.1 CREATE MAINTENANCE RECORD ---
@app.post("/api/records", response_model=MaintenanceRecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(payload: MaintenanceRecordCreate, db: Session = Depends(get_db)):
    # Calculate Next Service Mileage (+5000 KM) if not manually sent
    calculated_next_km = payload.next_service_km if payload.next_service_km else (payload.current_km + 5000.0)

    db_record = MaintenanceRecord(
        serial_number=payload.serial_number,
        work_order_no=payload.work_order_no,
        vehicle_plate=payload.vehicle_plate,
        vehicle_type=payload.vehicle_type,
        driver_name=payload.driver_name,
        current_km=payload.current_km,
        next_service_km=calculated_next_km,
        work_type=payload.work_type,
        issue_description=payload.issue_description,
        additional_unplanned_work=payload.additional_unplanned_work,
        lubricant_liters=payload.lubricant_liters,
        lubricant_cost=payload.lubricant_cost,
        battery_cost=payload.battery_cost,
        tire_cost=payload.tire_cost
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    # Save Itemized Spare Parts
    for part in payload.spare_parts:
        db.add(SparePartItem(
            record_id=db_record.id,
            spec_name=part.spec_name,
            qty=part.qty,
            unit_cost=part.unit_cost
        ))

    # Save Technicians
    for tech in payload.technicians:
        db.add(TechnicianAssignment(
            record_id=db_record.id,
            technician_name=tech.technician_name,
            assigned_by=tech.assigned_by
        ))

    db.commit()
    db.refresh(db_record)

    # Calculate Total Expenditure
    parts_cost = sum(p.qty * p.unit_cost for p in db_record.spare_parts)
    total_cost = parts_cost + db_record.lubricant_cost + db_record.battery_cost + db_record.tire_cost

    res = MaintenanceRecordResponse.from_orm(db_record)
    res.total_cost = total_cost
    return res

# --- 4.2 GET RECORDS (WITH DATE FILTER) ---
@app.get("/api/records", response_model=List[MaintenanceRecordResponse])
def get_records(
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(MaintenanceRecord)

    if from_date:
        start_dt = datetime.strptime(from_date, "%Y-%m-%d")
        query = query.filter(MaintenanceRecord.created_at >= start_dt)

    if to_date:
        end_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1, microseconds=-1)
        query = query.filter(MaintenanceRecord.created_at <= end_dt)

    records = query.order_by(MaintenanceRecord.created_at.desc()).all()

    response = []
    for r in records:
        parts_cost = sum(p.qty * p.unit_cost for p in r.spare_parts)
        total_cost = parts_cost + r.lubricant_cost + r.battery_cost + r.tire_cost

        rec_dto = MaintenanceRecordResponse.from_orm(r)
        rec_dto.total_cost = total_cost
        response.append(rec_dto)

    return response

# --- 4.3 ASSIGN TECHNICIAN TO EXISTING RECORD ---
@app.post("/api/records/{record_id}/assign-technician", response_model=TechnicianResponse)
def assign_technician(record_id: int, payload: AssignTechnicianCreate, db: Session = Depends(get_db)):
    record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="የጥገና መዝገቡ አልተገኘም")

    tech = TechnicianAssignment(
        record_id=record_id,
        technician_name=payload.technician_name,
        assigned_by=payload.assigned_by
    )
    db.add(tech)
    db.commit()
    db.refresh(tech)
    return tech

# --- 4.4 EXPORT FILTERED MASTER EXCEL REPORT ---
@app.get("/api/reports/excel/custom-range")
def export_filtered_excel(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(MaintenanceRecord)

    if from_date:
        start_dt = datetime.strptime(from_date, "%Y-%m-%d")
        query = query.filter(MaintenanceRecord.created_at >= start_dt)

    if to_date:
        end_dt = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1, microseconds=-1)
        query = query.filter(MaintenanceRecord.created_at <= end_dt)

    records = query.all()

    detailed_rows = []
    total_parts = 0.0
    total_lube = 0.0
    total_batt = 0.0
    total_tire = 0.0

    for r in records:
        parts_str = "; ".join([f"{p.spec_name} (Qty: {p.qty}, Unit: ETB {p.unit_cost})" for p in r.spare_parts])
        techs_str = ", ".join([t.technician_name for t in r.technicians])
        p_cost = sum(p.qty * p.unit_cost for p in r.spare_parts)

        total_parts += p_cost
        total_lube += r.lubricant_cost
        total_batt += r.battery_cost
        total_tire += r.tire_cost

        row_total = p_cost + r.lubricant_cost + r.battery_cost + r.tire_cost

        detailed_rows.append({
            "Date": r.created_at.strftime("%Y-%m-%d %H:%M"),
            "S/N": r.serial_number,
            "W.O No": r.work_order_no,
            "Vehicle Plate": r.vehicle_plate,
            "Vehicle Type": r.vehicle_type,
            "Driver Name": r.driver_name,
            "Current KM": r.current_km,
            "Next Service KM": r.next_service_km,
            "Assigned Technicians": techs_str if techs_str else "Unassigned",
            "Work Type": r.work_type,
            "Issue Description": r.issue_description,
            "Replaced Parts Breakdown": parts_str if parts_str else "None",
            "Spare Parts Cost (ETB)": p_cost,
            "Lubricants Liters": r.lubricant_liters,
            "Lubricant Cost (ETB)": r.lubricant_cost,
            "Battery Cost (ETB)": r.battery_cost,
            "Tire Cost (ETB)": r.tire_cost,
            "Total Job Cost (ETB)": row_total
        })

    df_details = pd.DataFrame(detailed_rows)

    # Category Cost Summary Sheet
    summary_rows = [
        {"Expense Category": "Spare Parts Total", "Cost (ETB)": total_parts},
        {"Expense Category": "Lubricants Total", "Cost (ETB)": total_lube},
        {"Expense Category": "Batteries Total", "Cost (ETB)": total_batt},
        {"Expense Category": "Tires Total", "Cost (ETB)": total_tire},
        {"Expense Category": "GRAND TOTAL EXPENDITURE", "Cost (ETB)": total_parts + total_lube + total_batt + total_tire}
    ]
    df_summary = pd.DataFrame(summary_rows)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_details.to_excel(writer, index=False, sheet_name="Filtered_Detailed_Log")
        df_summary.to_excel(writer, index=False, sheet_name="Category_Cost_Summary")

    output.seek(0)
    file_name = f"SteelY_Garage_Report_{from_date if from_date else 'All'}_to_{to_date if to_date else 'All'}.xlsx"
    headers = {'Content-Disposition': f'attachment; filename="{file_name}"'}
    
    return StreamingResponse(
        output, 
        headers=headers, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
