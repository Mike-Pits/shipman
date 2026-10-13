from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bunker_replenishment import BunkerReplenishment
from app.models.daily_report import DailyReport
from app.models.payment import Payment
from app.models.vessel import FuelConsumptionProfile, Vessel
from app.models.vetting_inspection import VettingInspection
from app.models.voyage import Voyage
from app.models.voyage_estimate import VoyageEstimate
from app.schemas.vessel import VesselCreate, VesselRead
from app.schemas.vetting_inspection import (
    VettingInspectionCreate,
    VettingInspectionRead,
    VettingStatusRead,
)
from app.services.vetting import current_vetting_status

router = APIRouter(prefix="/vessels", tags=["vessels"])

DUPLICATE_IMO_DETAIL = "A vessel with this IMO number already exists"


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
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE_IMO_DETAIL) from exc
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
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE_IMO_DETAIL) from exc
    db.refresh(vessel)
    return vessel


@router.delete("/{vessel_id}", status_code=204)
def delete_vessel(vessel_id: int, db: Session = Depends(get_db)):
    vessel = db.get(Vessel, vessel_id)
    if vessel is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    dependent_checks = (
        (Voyage, "voyages"),
        (DailyReport, "daily reports"),
        (Payment, "payments"),
        (BunkerReplenishment, "bunker replenishments"),
        (VoyageEstimate, "voyage estimates"),
    )
    for model, label in dependent_checks:
        if db.query(model).filter(model.vessel_id == vessel_id).first() is not None:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot delete vessel: it has existing {label}. "
                "Remove or reassign those records first.",
            )

    db.query(VettingInspection).filter(VettingInspection.vessel_id == vessel_id).delete()
    db.delete(vessel)
    db.commit()
    return Response(status_code=204)


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


@router.put("/{vessel_id}/vetting-inspections/{inspection_id}", response_model=VettingInspectionRead)
def update_vetting_inspection(
    vessel_id: int, inspection_id: int, payload: VettingInspectionCreate, db: Session = Depends(get_db)
):
    if db.get(Vessel, vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")
    inspection = db.get(VettingInspection, inspection_id)
    if inspection is None or inspection.vessel_id != vessel_id:
        raise HTTPException(status_code=404, detail="Vetting inspection not found")

    for field, value in payload.model_dump().items():
        setattr(inspection, field, value)
    db.commit()
    db.refresh(inspection)
    return inspection


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
