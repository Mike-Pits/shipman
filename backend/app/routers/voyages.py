from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fixture import Fixture
from app.models.off_hire_period import OffHirePeriod
from app.models.vessel import Vessel
from app.models.voyage import Voyage
from app.schemas.off_hire_period import OffHirePeriodCreate, OffHirePeriodRead
from app.schemas.voyage import VoyageCreate, VoyageRead
from app.services.vat import apply_vat
from app.services.vetting import is_vetting_unfixable

router = APIRouter(prefix="/voyages", tags=["voyages"])


def _to_read(voyage: Voyage, db: Session) -> VoyageRead:
    base = VoyageRead.model_validate(voyage)
    warnings = []
    if is_vetting_unfixable(db, voyage.vessel_id):
        warnings.append(
            "This vessel's vetting status is expired or failed — it may be commercially unfixable"
        )
    return base.model_copy(update={"warnings": warnings})


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
    return _to_read(voyage, db)


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
    return _to_read(voyage, db)


@router.put("/{voyage_id}", response_model=VoyageRead)
def update_voyage(voyage_id: int, payload: VoyageCreate, db: Session = Depends(get_db)):
    voyage = db.get(Voyage, voyage_id)
    if voyage is None:
        raise HTTPException(status_code=404, detail="Voyage not found")
    if db.get(Fixture, payload.fixture_id) is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    for field, value in payload.model_dump().items():
        setattr(voyage, field, value)
    db.commit()
    db.refresh(voyage)
    return _to_read(voyage, db)


def _daily_hire_rate(fixture: Fixture) -> float:
    return fixture.hire_rate if fixture.hire_rate_basis == "daily" else fixture.hire_rate / 30


def _tc_out_fixture_or_422(voyage: Voyage, db: Session) -> Fixture:
    fixture = db.get(Fixture, voyage.fixture_id)
    if fixture is None or fixture.fixture_type != "time_charter_out":
        raise HTTPException(
            status_code=422,
            detail="Off-hire periods can only be recorded for a Time Charter Out voyage",
        )
    return fixture


def _calculated_deduction(fixture: Fixture, payload: OffHirePeriodCreate) -> float:
    start = datetime.strptime(payload.start_datetime, "%Y-%m-%d %H:%M:%S")
    end = datetime.strptime(payload.end_datetime, "%Y-%m-%d %H:%M:%S")
    duration_days = (end - start).total_seconds() / 86400
    # off-hire deducts hire that would otherwise have been earned (and invoiced) for that
    # time, so the deduction is computed on the same VAT basis as the hire installments
    return apply_vat(round(_daily_hire_rate(fixture) * duration_days, 2), fixture)


@router.post(
    "/{voyage_id}/off-hire-periods", response_model=OffHirePeriodRead, status_code=201
)
def create_off_hire_period(
    voyage_id: int, payload: OffHirePeriodCreate, db: Session = Depends(get_db)
):
    voyage = db.get(Voyage, voyage_id)
    if voyage is None:
        raise HTTPException(status_code=404, detail="Voyage not found")
    fixture = _tc_out_fixture_or_422(voyage, db)

    period = OffHirePeriod(
        voyage_id=voyage_id,
        start_datetime=payload.start_datetime,
        end_datetime=payload.end_datetime,
        reason=payload.reason,
        calculated_deduction=_calculated_deduction(fixture, payload),
        override_deduction=payload.override_deduction,
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@router.get("/{voyage_id}/off-hire-periods", response_model=list[OffHirePeriodRead])
def list_off_hire_periods(voyage_id: int, db: Session = Depends(get_db)):
    return db.query(OffHirePeriod).filter(OffHirePeriod.voyage_id == voyage_id).all()


@router.put("/{voyage_id}/off-hire-periods/{period_id}", response_model=OffHirePeriodRead)
def update_off_hire_period(
    voyage_id: int, period_id: int, payload: OffHirePeriodCreate, db: Session = Depends(get_db)
):
    voyage = db.get(Voyage, voyage_id)
    if voyage is None:
        raise HTTPException(status_code=404, detail="Voyage not found")
    period = db.get(OffHirePeriod, period_id)
    if period is None or period.voyage_id != voyage_id:
        raise HTTPException(status_code=404, detail="Off-hire period not found")
    fixture = _tc_out_fixture_or_422(voyage, db)

    period.start_datetime = payload.start_datetime
    period.end_datetime = payload.end_datetime
    period.reason = payload.reason
    period.override_deduction = payload.override_deduction
    period.calculated_deduction = _calculated_deduction(fixture, payload)
    db.commit()
    db.refresh(period)
    return period
