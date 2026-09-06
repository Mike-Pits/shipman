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


class GenerateHireInstallmentsRequest(BaseModel):
    vessel_id: int


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

    period_start = datetime.strptime(fixture.charter_period_from, "%Y-%m-%d").date()
    period_end = datetime.strptime(fixture.charter_period_to, "%Y-%m-%d").date()
    daily_rate = (
        fixture.hire_rate if fixture.hire_rate_basis == "daily" else fixture.hire_rate / 30
    )

    installments: list[Payment] = []
    current = period_start
    frequency = timedelta(days=fixture.hire_payment_frequency_days)
    while current < period_end:
        chunk_end = min(current + frequency, period_end)
        duration_days = (chunk_end - current).days
        amount = round(daily_rate * duration_days, 2)

        if fixture.hire_payment_basis == "advance":
            invoice_date, due_date = current, current
        elif fixture.hire_payment_basis == "arrears":
            invoice_date, due_date = chunk_end, chunk_end
        else:  # days_after_invoice
            invoice_date = current
            due_date = current + timedelta(days=fixture.hire_payment_days_after_invoice)

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
