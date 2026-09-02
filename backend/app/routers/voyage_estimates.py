from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fixture import Fixture, FixtureBroker
from app.models.voyage_estimate import VoyageEstimate
from app.schemas.fixture import FixtureCreate, FixtureRead
from app.schemas.voyage_estimate import (
    VoyageEstimateCreate,
    VoyageEstimateRead,
    VoyageEstimateStatusUpdate,
)
from app.services.vetting import is_vetting_unfixable

router = APIRouter(prefix="/voyage-estimates", tags=["voyage-estimates"])


def _get_estimate_or_404(estimate_id: int, db: Session) -> VoyageEstimate:
    estimate = db.get(VoyageEstimate, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=404, detail="Voyage estimate not found")
    return estimate


def _to_read(estimate: VoyageEstimate, db: Session) -> VoyageEstimateRead:
    base = VoyageEstimateRead.model_validate(estimate)
    warnings = []
    if estimate.vessel_id is not None and is_vetting_unfixable(db, estimate.vessel_id):
        warnings.append(
            "This vessel's vetting status is expired or failed — it may be commercially unfixable"
        )
    return base.model_copy(update={"warnings": warnings})


@router.post("", response_model=VoyageEstimateRead, status_code=201)
def create_voyage_estimate(payload: VoyageEstimateCreate, db: Session = Depends(get_db)):
    estimate = VoyageEstimate(**payload.model_dump(), status="draft")
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return _to_read(estimate, db)


@router.get("", response_model=list[VoyageEstimateRead])
def list_voyage_estimates(db: Session = Depends(get_db)):
    return db.query(VoyageEstimate).all()


@router.get("/{estimate_id}", response_model=VoyageEstimateRead)
def get_voyage_estimate(estimate_id: int, db: Session = Depends(get_db)):
    return _to_read(_get_estimate_or_404(estimate_id, db), db)


@router.post("/{estimate_id}/status", response_model=VoyageEstimateRead)
def update_estimate_status(
    estimate_id: int, payload: VoyageEstimateStatusUpdate, db: Session = Depends(get_db)
):
    estimate = _get_estimate_or_404(estimate_id, db)
    estimate.status = payload.status
    db.commit()
    db.refresh(estimate)
    return _to_read(estimate, db)


@router.post("/{estimate_id}/promote", response_model=FixtureRead, status_code=201)
def promote_estimate_to_fixture(
    estimate_id: int, payload: FixtureCreate, db: Session = Depends(get_db)
):
    estimate = _get_estimate_or_404(estimate_id, db)

    fixture = Fixture(
        **payload.model_dump(exclude={"brokers"}),
        brokers=[FixtureBroker(**broker.model_dump()) for broker in payload.brokers],
    )
    db.add(fixture)
    db.flush()

    estimate.status = "fixed"
    estimate.fixture_id = fixture.id
    db.commit()
    db.refresh(fixture)
    return fixture
