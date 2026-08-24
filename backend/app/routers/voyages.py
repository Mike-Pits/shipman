from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fixture import Fixture
from app.models.vessel import Vessel
from app.models.voyage import Voyage
from app.schemas.voyage import VoyageCreate, VoyageRead

router = APIRouter(prefix="/voyages", tags=["voyages"])


@router.post("", response_model=VoyageRead, status_code=201)
def create_voyage(payload: VoyageCreate, db: Session = Depends(get_db)):
    if db.get(Fixture, payload.fixture_id) is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    voyage = Voyage(**payload.model_dump())
    db.add(voyage)
    db.commit()
    db.refresh(voyage)
    return voyage


@router.get("", response_model=list[VoyageRead])
def list_voyages(
    fixture_id: int | None = None,
    vessel_id: int | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Voyage)
    if fixture_id is not None:
        query = query.filter(Voyage.fixture_id == fixture_id)
    if vessel_id is not None:
        query = query.filter(Voyage.vessel_id == vessel_id)
    return query.all()


@router.get("/{voyage_id}", response_model=VoyageRead)
def get_voyage(voyage_id: int, db: Session = Depends(get_db)):
    voyage = db.get(Voyage, voyage_id)
    if voyage is None:
        raise HTTPException(status_code=404, detail="Voyage not found")
    return voyage
