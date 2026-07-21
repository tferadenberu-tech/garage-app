import io
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# ==========================================
# 1. DATABASE CONFIGURATION (SQLite)
# ==========================================
SQLALCHEMY_DATABASE_URL = "sqlite:///./garage.db"

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
    vehicle_plate = Column(String, index=True, nullable=False)
    vehicle_model = Column(String, nullable=False)
    current_mileage = Column(Float, nullable=False)
    next_service_mileage = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    spare_parts = relationship("SparePartItem", back_populates="record", cascade="all, delete-orphan")
    assigned_technicians = relationship("TechnicianAssignment", back_populates="record", cascade="all, delete-orphan")


class SparePartItem(Base):
    __tablename__ = "spare_parts"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("maintenance_records.id"), nullable=False)
    spec_name = Column(String, nullable=False)  # Spare Part Name / Spec
    qty = Column(Integer, nullable=False, default=1)
    unit_cost = Column(Float, nullable=False, default=0.0)

    record = relationship("MaintenanceRecord", back_populates="spare_parts")


class TechnicianAssignment(Base):
    __tablename__ = "technician_assignments"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("maintenance_records.id"), nullable=False)
    technician_name = Column(String, nullable=False)  # Assigned Technician Name
    assigned_by = Column(String, nullable=True, default="Supervisor")
    assigned_at = Column(DateTime, default=datetime.utcnow)

    record = relationship("MaintenanceRecord", back_populates="assigned_technicians")

# Create All Tables
Base.metadata.create_all(bind=engine)

# ==========================================
# 3. PYDANTIC SCHEMAS (VALIDATION)
# ==========================================
class SparePartCreate(BaseModel):
    spec_name: str
    qty: int
    unit_cost: float

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
    vehicle_plate: str
    vehicle_model: str
    current_mileage: float
    spare_parts: List[SparePartCreate] = []
    technicians: List[AssignTechnicianCreate] = []

class MaintenanceRecordResponse(BaseModel):
    id: int
    vehicle_plate: str
    vehicle_model: str
    current_mileage: float
    next_service_mileage: float
    created_at: datetime
    spare_parts: List[SparePartResponse] = []
    assigned_technicians: List[TechnicianResponse] = []
    total_parts_cost: float

    class Config:
        from_attributes = True

# ==========================================
# 4. FASTAPI APP & ENDPOINTS
# ==========================================
app = FastAPI(title="SteelY R.M.I Garage Maintnace dash Bord")

# CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 4.1 CREATE RECORD ---
@app.post("/api/records", response_model=MaintenanceRecordResponse, status_code=status.HTTP_201_CREATED)
def create_record(payload: MaintenanceRecordCreate, db: Session = Depends(get_db)):
    # Auto-calculate next service mileage (+5000 KM)
    next_service = payload.current_mileage + 5000.0

    db_record = MaintenanceRecord(
        vehicle_plate=payload.vehicle_plate,
        vehicle_model=payload.vehicle_model,
        current_mileage=payload.current_mileage,
        next_service_mileage=next_service
    )
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    # Save Spare Parts Breakdown
    for part in payload.spare_parts:
        db.add(SparePartItem(
            record_id=db_record.id,
            spec_name=part.spec_name,
            qty=part.qty,
            unit_cost=part.unit_cost
        ))

    # Save Assigned Technicians
    for tech in payload.technicians:
        db.add(TechnicianAssignment(
            record_id=db_record.id,
            technician_name=tech.technician_name,
            assigned_by=tech.assigned_by
        ))

    db.commit()
    db.refresh(db_record)

    total_cost = sum(p.qty * p.unit_cost for p in db_record.spare_parts)

    return {
        "id": db_record.id,
        "vehicle_plate": db_record.vehicle_plate,
        "vehicle_model": db_record.vehicle_model,
        "current_mileage": db_record.current_mileage,
        "next_service_mileage": db_record.next_service_mileage,
        "created_at": db_record.created_at,
        "spare_parts": db_record.spare_parts,
        "assigned_technicians": db_record.assigned_technicians,
        "total_parts_cost": total_cost
    }

# --- 4.2 GET ALL RECORDS ---
@app.get("/api/records", response_model=List[MaintenanceRecordResponse])
def get_records(db: Session = Depends(get_db)):
    records = db.query(MaintenanceRecord).all()
    results = []
    for r in records:
        total_cost = sum(p.qty * p.unit_cost for p in r.spare_parts)
        results.append({
            "id": r.id,
            "vehicle_plate": r.vehicle_plate,
            "vehicle_model": r.vehicle_model,
            "current_mileage": r.current_mileage,
            "next_service_mileage": r.next_service_mileage,
            "created_at": r.created_at,
            "spare_parts": r.spare_parts,
            "assigned_technicians": r.assigned_technicians,
            "total_parts_cost": total_cost
        })
    return results

# --- 4.3 ASSIGN TECHNICIAN TO EXISTING RECORD ---
@app.post("/api/records/{record_id}/assign-technician", response_model=TechnicianResponse)
def assign_technician(record_id: int, payload: AssignTechnicianCreate, db: Session = Depends(get_db)):
    record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="የጥገና መዝገቡ አልተገኘም")

    new_tech = TechnicianAssignment(
        record_id=record_id,
        technician_name=payload.technician_name,
        assigned_by=payload.assigned_by
    )
    db.add(new_tech)
    db.commit()
    db.refresh(new_tech)
    return new_tech

# --- 4.4 MASTER EXCEL REPORT EXPORT ---
@app.get("/api/export-excel")
def export_master_excel(db: Session = Depends(get_db)):
    records = db.query(MaintenanceRecord).all()

    wb = openpyxl.Workbook()
    
    # Styles
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")
    left_align = Alignment(horizontal="left", vertical="center")
    thin_border = Border(
        left=Side(style='thin', color='D9D9D9'),
        right=Side(style='thin', color='D9D9D9'),
        top=Side(style='thin', color='D9D9D9'),
        bottom=Side(style='thin', color='D9D9D9')
    )

    # 1. Full Job Registry Sheet
    ws1 = wb.active
    ws1.title = "Full_Job_Registry"
    headers1 = ["Record ID", "Date", "Plate No", "Model", "Current KM", "Next Service KM", "Assigned Technicians", "Parts Summary", "Total Parts Cost (ETB)"]
    ws1.append(headers1)

    for cell in ws1[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    for r in records:
        techs = ", ".join([t.technician_name for t in r.assigned_technicians])
        parts_summary = "; ".join([f"{p.spec_name} (x{p.qty})" for p in r.spare_parts])
        total_cost = sum(p.qty * p.unit_cost for p in r.spare_parts)

        row = [
            r.id,
            r.created_at.strftime("%Y-%m-%d %H:%M"),
            r.vehicle_plate,
            r.vehicle_model,
            r.current_mileage,
            r.next_service_mileage,
            techs if techs else "Unassigned",
            parts_summary if parts_summary else "N/A",
            total_cost
        ]
        ws1.append(row)

    for row in ws1.iter_rows(min_row=2, max_row=ws1.max_row, min_col=1, max_col=9):
        for cell in row:
            cell.border = thin_border
            cell.alignment = left_align

    # Save to buffer
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    filename = f"SteelY_RMI_Garage_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
    headers = {'Content-Disposition': f'attachment; filename="{filename}"'}
    
    return StreamingResponse(
        buffer, 
        headers=headers, 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
