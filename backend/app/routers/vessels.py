from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.vessel import FuelConsumptionProfile, Vessel
from app.models.vetting_inspection import VettingInspection
from app.schemas.vessel import VesselCreate, VesselRead
from app.schemas.vetting_inspection import (
    VettingInspectionCreate,
    VettingInspectionRead,
    VettingStatusRead,
)
from app.services.vetting import current_vetting_status

router = APIRouter(prefix="/vessels", tags=["vessels"])


@router.post("", response_model=VesselRead, status_code=201)
def create_vessel(payload: VesselCreate, db: Session = Depends(get_db)):
    vessel = Vessel(
        **payload.model_dump(exclude={"fuel_consumption_profiles"}),
        fuel_consumption_profiles=[
            FuelConsumptionProfile(**profile.model_dump())
            for profile in payload.fuel_consumption_profiles
        ],
    )
    db.add(vessel)
    db.commit()
    db.refresh(vessel)
    return vessel


@router.get("", response_model=list[VesselRead])
def list_vessels(db: Session = Depends(get_db)):
    return db.query(Vessel).all()


@router.get("/{vessel_id}", response_model=VesselRead)
def get_vessel(vessel_id: int, db: Session = Depends(get_db)):
    vessel = db.get(Vessel, vessel_id)
    if vessel is None:
        raise HTTPException(status_code=404, detail="Vessel not found")
    return vessel


@router.put("/{vessel_id}", response_model=VesselRead)
def update_vessel(vessel_id: int, payload: VesselCreate, db: Session = Depends(get_db)):
    vessel = db.get(Vessel, vessel_id)
    if vessel is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    for field, value in payload.model_dump(exclude={"fuel_consumption_profiles"}).items():
        setattr(vessel, field, value)
    vessel.fuel_consumption_profiles = [
        FuelConsumptionProfile(**profile.model_dump())
        for profile in payload.fuel_consumption_profiles
    ]
    db.commit()
    db.refresh(vessel)
    return vessel


@router.post(
    "/{vessel_id}/vetting-inspections", response_model=VettingInspectionRead, status_code=201
)
def create_vetting_inspection(
    vessel_id: int, payload: VettingInspectionCreate, db: Session = Depends(get_db)
):
    if db.get(Vessel, vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    inspection = VettingInspection(vessel_id=vessel_id, **payload.model_dump())
    db.add(inspection)
    db.commit()
    db.refresh(inspection)
    return inspection


@router.get("/{vessel_id}/vetting-inspections", response_model=list[VettingInspectionRead])
def list_vetting_inspections(vessel_id: int, db: Session = Depends(get_db)):
    return (
        db.query(VettingInspection).filter(VettingInspection.vessel_id == vessel_id).all()
    )


@router.get("/{vessel_id}/vetting-status", response_model=VettingStatusRead)
def get_vetting_status(vessel_id: int, db: Session = Depends(get_db)):
    if db.get(Vessel, vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    result = current_vetting_status(db, vessel_id)
    if result is None:
        return VettingStatusRead(status=None)
    inspection, effective_status = result
    return VettingStatusRead(
        status=effective_status,
        inspecting_body=inspection.inspecting_body,
        expiry_date=inspection.expiry_date,
    )
