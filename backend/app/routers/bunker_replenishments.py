from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.bunker_replenishment import BunkerReplenishment, BunkerReplenishmentLine
from app.models.vessel import Vessel
from app.schemas.bunker_replenishment import BunkerReplenishmentCreate, BunkerReplenishmentRead

router = APIRouter(prefix="/bunker-replenishments", tags=["bunker-replenishments"])


@router.post("", response_model=BunkerReplenishmentRead, status_code=201)
def create_bunker_replenishment(payload: BunkerReplenishmentCreate, db: Session = Depends(get_db)):
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    replenishment = BunkerReplenishment(
        **payload.model_dump(exclude={"lines"}),
        lines=[BunkerReplenishmentLine(**line.model_dump()) for line in payload.lines],
    )
    db.add(replenishment)
    db.commit()
    db.refresh(replenishment)
    return replenishment


@router.get("", response_model=list[BunkerReplenishmentRead])
def list_bunker_replenishments(db: Session = Depends(get_db)):
    return db.query(BunkerReplenishment).all()


@router.get("/{replenishment_id}", response_model=BunkerReplenishmentRead)
def get_bunker_replenishment(replenishment_id: int, db: Session = Depends(get_db)):
    replenishment = db.get(BunkerReplenishment, replenishment_id)
    if replenishment is None:
        raise HTTPException(status_code=404, detail="Bunker replenishment not found")
    return replenishment


@router.put("/{replenishment_id}", response_model=BunkerReplenishmentRead)
def update_bunker_replenishment(
    replenishment_id: int, payload: BunkerReplenishmentCreate, db: Session = Depends(get_db)
):
    replenishment = db.get(BunkerReplenishment, replenishment_id)
    if replenishment is None:
        raise HTTPException(status_code=404, detail="Bunker replenishment not found")
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    for field, value in payload.model_dump(exclude={"lines"}).items():
        setattr(replenishment, field, value)
    replenishment.lines = [BunkerReplenishmentLine(**line.model_dump()) for line in payload.lines]
    db.commit()
    db.refresh(replenishment)
    return replenishment
