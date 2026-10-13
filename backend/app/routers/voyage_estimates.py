from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fixture import Fixture, FixtureBroker
from app.models.vessel import Vessel
from app.models.voyage_estimate import (
    EstimateCargoLot,
    EstimateCostItem,
    EstimateFuelPrice,
    EstimatePortStop,
    VoyageEstimate,
)
from app.schemas.fixture import FixtureCreate, FixtureRead
from app.schemas.voyage_estimate import (
    EstimateResults,
    VoyageEstimateCreate,
    VoyageEstimateRead,
    VoyageEstimateStatusUpdate,
)
from app.services.vetting import is_vetting_unfixable
from app.services.voyage_calc import calculate_voyage

router = APIRouter(prefix="/voyage-estimates", tags=["voyage-estimates"])


def _get_estimate_or_404(estimate_id: int, db: Session) -> VoyageEstimate:
    estimate = db.get(VoyageEstimate, estimate_id)
    if estimate is None:
        raise HTTPException(status_code=404, detail="Voyage estimate not found")
    return estimate


def _vessel_or_422(vessel_id: int | None, db: Session) -> Vessel | None:
    if vessel_id is None:
        return None
    vessel = db.get(Vessel, vessel_id)
    if vessel is None:
        raise HTTPException(status_code=422, detail="Vessel not found")
    return vessel


def _results(estimate: VoyageEstimate, db: Session) -> EstimateResults:
    vessel = db.get(Vessel, estimate.vessel_id) if estimate.vessel_id is not None else None
    return EstimateResults(**calculate_voyage(estimate, vessel))


def _to_read(estimate: VoyageEstimate, db: Session) -> VoyageEstimateRead:
    base = VoyageEstimateRead.model_validate(estimate)
    warnings = []
    if estimate.vessel_id is not None and is_vetting_unfixable(db, estimate.vessel_id):
        warnings.append(
            "This vessel's vetting status is expired or failed — it may be commercially unfixable"
        )
    return base.model_copy(update={"warnings": warnings, "results": _results(estimate, db)})


_SCALAR_FIELDS = {
    "name", "vessel_id", "currency", "laycan_start", "laycan_end", "freight_mode",
    "lumpsum_freight", "extra_sea_days", "extra_costs", "canal_fees",
    "port_charges", "agent_fees", "bunker_surcharge", "demurrage_rate",
}


def _apply_payload(estimate: VoyageEstimate, payload: VoyageEstimateCreate) -> None:
    for field in _SCALAR_FIELDS:
        setattr(estimate, field, getattr(payload, field))
    estimate.port_stops = [
        EstimatePortStop(position=i, **stop.model_dump())
        for i, stop in enumerate(payload.port_stops)
    ]
    estimate.cargo_lots = [EstimateCargoLot(**lot.model_dump()) for lot in payload.cargo_lots]
    estimate.fuel_prices = [EstimateFuelPrice(**p.model_dump()) for p in payload.fuel_prices]
    estimate.cost_items = [EstimateCostItem(**i.model_dump()) for i in payload.cost_items]


@router.post("/calculate", response_model=EstimateResults)
def calculate_estimate(payload: VoyageEstimateCreate, db: Session = Depends(get_db)):
    """Stateless calculation of unsaved inputs — the calculator's "Calculate Voyage" button."""
    vessel = _vessel_or_422(payload.vessel_id, db)
    transient = VoyageEstimate()
    _apply_payload(transient, payload)
    return EstimateResults(**calculate_voyage(transient, vessel))


@router.post("", response_model=VoyageEstimateRead, status_code=201)
def create_voyage_estimate(payload: VoyageEstimateCreate, db: Session = Depends(get_db)):
    _vessel_or_422(payload.vessel_id, db)
    estimate = VoyageEstimate(status="draft")
    _apply_payload(estimate, payload)
    db.add(estimate)
    db.commit()
    db.refresh(estimate)
    return _to_read(estimate, db)


@router.get("", response_model=list[VoyageEstimateRead])
def list_voyage_estimates(db: Session = Depends(get_db)):
    return [_to_read(e, db) for e in db.query(VoyageEstimate).order_by(VoyageEstimate.id).all()]


@router.get("/{estimate_id}", response_model=VoyageEstimateRead)
def get_voyage_estimate(estimate_id: int, db: Session = Depends(get_db)):
    return _to_read(_get_estimate_or_404(estimate_id, db), db)


@router.put("/{estimate_id}", response_model=VoyageEstimateRead)
def update_voyage_estimate(
    estimate_id: int, payload: VoyageEstimateCreate, db: Session = Depends(get_db)
):
    estimate = _get_estimate_or_404(estimate_id, db)
    if estimate.status == "fixed":
        raise HTTPException(
            status_code=409,
            detail="A fixed estimate is the baseline for its voyage P&L and cannot be edited",
        )
    _vessel_or_422(payload.vessel_id, db)
    _apply_payload(estimate, payload)
    db.commit()
    db.refresh(estimate)
    return _to_read(estimate, db)


@router.delete("/{estimate_id}", status_code=204)
def delete_voyage_estimate(estimate_id: int, db: Session = Depends(get_db)):
    estimate = _get_estimate_or_404(estimate_id, db)
    if estimate.status == "fixed":
        raise HTTPException(
            status_code=409,
            detail="A fixed estimate is the baseline for its voyage P&L and cannot be deleted",
        )
    db.delete(estimate)
    db.commit()
    return Response(status_code=204)


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

    results = _results(estimate, db)
    estimate.status = "fixed"
    estimate.fixture_id = fixture.id
    estimate.baseline_net_result = results.net_result
    estimate.baseline_tce_per_day = results.tce_per_day
    db.commit()
    db.refresh(fixture)
    return fixture
