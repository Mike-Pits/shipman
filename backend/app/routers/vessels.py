from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.vessel import FuelConsumptionProfile, Vessel
from app.schemas.vessel import VesselCreate, VesselRead

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
