from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fixture import Fixture, FixtureBroker
from app.models.payment import Payment
from app.models.vessel import Vessel
from app.schemas.fixture import FixtureCreate, FixtureRead
from app.schemas.payment import PaymentRead
from app.services.currency import convert_to_rub

router = APIRouter(prefix="/fixtures", tags=["fixtures"])

# Delivery/redelivery are contractually timestamps, not just dates — hire runs from the
# exact time of delivery to the exact time of redelivery, so the final installment is
# routinely a partial day. Accept a bare date too (assumed midnight) for fixtures that
# genuinely don't need that precision, and tolerate a trailing seconds field either way.
_CHARTER_DATETIME_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


def _parse_charter_datetime(value: str) -> datetime:
    for fmt in _CHARTER_DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise HTTPException(
        status_code=422,
        detail=f"Could not parse charter period date/time: {value!r}",
    )


class GenerateHireInstallmentsRequest(BaseModel):
    vessel_id: int
    invoice_date_override: str | None = None


@router.post("", response_model=FixtureRead, status_code=201)
def create_fixture(payload: FixtureCreate, db: Session = Depends(get_db)):
    fixture = Fixture(
        **payload.model_dump(exclude={"brokers"}),
        brokers=[FixtureBroker(**broker.model_dump()) for broker in payload.brokers],
    )
    db.add(fixture)
    db.commit()
    db.refresh(fixture)
    return fixture


@router.get("", response_model=list[FixtureRead])
def list_fixtures(db: Session = Depends(get_db)):
    return db.query(Fixture).all()


@router.put("/{fixture_id}", response_model=FixtureRead)
def update_fixture(fixture_id: int, payload: FixtureCreate, db: Session = Depends(get_db)):
    fixture = db.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Fixture not found")

    for field, value in payload.model_dump(exclude={"brokers"}).items():
        setattr(fixture, field, value)
    fixture.brokers = [FixtureBroker(**broker.model_dump()) for broker in payload.brokers]
    db.commit()
    db.refresh(fixture)
    return fixture


@router.get("/{fixture_id}", response_model=FixtureRead)
def get_fixture(fixture_id: int, db: Session = Depends(get_db)):
    fixture = db.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    return fixture


@router.post(
    "/{fixture_id}/generate-hire-installments",
    response_model=list[PaymentRead],
    status_code=201,
)
def generate_hire_installments(
    fixture_id: int, payload: GenerateHireInstallmentsRequest, db: Session = Depends(get_db)
):
    fixture = db.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    if fixture.fixture_type != "time_charter_out":
        raise HTTPException(
            status_code=422,
            detail="Hire installments can only be generated for a Time Charter Out fixture",
        )
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    period_start = _parse_charter_datetime(fixture.charter_period_from)
    period_end = _parse_charter_datetime(fixture.charter_period_to)
    daily_rate = (
        fixture.hire_rate if fixture.hire_rate_basis == "daily" else fixture.hire_rate / 30
    )

    # For "days_after_invoice" terms, the invoice date isn't derivable from the charter
    # schedule at all — it's whenever the owner actually issues the invoice. Operators can
    # anchor the whole installment schedule to the real first-invoice date instead of the
    # period-start default; advance/arrears dates are contractually fixed to the period
    # boundary and aren't affected by this override. This shift is date-only — invoice/due
    # dates on a Payment are accounting dates and don't carry a time of day.
    invoice_date_shift = timedelta(0)
    if payload.invoice_date_override is not None and fixture.hire_payment_basis == "days_after_invoice":
        override_date = datetime.strptime(payload.invoice_date_override, "%Y-%m-%d").date()
        invoice_date_shift = override_date - period_start.date()

    installments: list[Payment] = []
    current = period_start
    frequency = timedelta(days=fixture.hire_payment_frequency_days)
    while current < period_end:
        # current + frequency preserves the delivery time-of-day at each boundary (a "hire
        # day" runs delivery-time to delivery-time); min(..., period_end) truncates the
        # final chunk to the actual redelivery timestamp, so a partial final day is prorated
        # to the hour rather than rounded to a whole day.
        chunk_end = min(current + frequency, period_end)
        duration_days = (chunk_end - current).total_seconds() / 86400
        amount = round(daily_rate * duration_days, 2)

        if fixture.hire_payment_basis == "advance":
            invoice_date, due_date = current.date(), current.date()
        elif fixture.hire_payment_basis == "arrears":
            invoice_date, due_date = chunk_end.date(), chunk_end.date()
        else:  # days_after_invoice
            invoice_date = current.date() + invoice_date_shift
            due_date = invoice_date + timedelta(days=fixture.hire_payment_days_after_invoice)

        rub_equivalent, rate_used, rate_date = convert_to_rub(
            db, fixture.contract_currency, amount, invoice_date.isoformat()
        )
        installments.append(
            Payment(
                vessel_id=payload.vessel_id,
                fixture_id=fixture.id,
                cost_category="income",
                cost_type_name="Hire",
                original_currency=fixture.contract_currency,
                original_amount=amount,
                rub_equivalent=rub_equivalent,
                exchange_rate_used=rate_used,
                exchange_rate_date=rate_date,
                invoice_date=invoice_date.isoformat(),
                due_date=due_date.isoformat(),
                status="draft",
            )
        )
        current = chunk_end

    db.add_all(installments)
    db.commit()
    for installment in installments:
        db.refresh(installment)
    return installments
