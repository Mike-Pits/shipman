from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.fixture import Fixture
from app.models.vessel import Vessel
from app.models.voyage import Voyage
from app.schemas.invoice import InvoiceCreate
from app.services.flexible_datetime import UnparseableDateTime, parse_flexible_datetime
from app.services.vat import apply_vat_terms


@dataclass
class ResolvedInvoice:
    currency: str
    vat_applicable: bool
    vat_treatment: str | None
    vat_rate_percent: float | None
    vat_amount: float
    counterparty: str
    fixture_id: int | None
    voyage_id: int | None
    vessel_id: int
    lines: list[dict]
    total_amount_due: float


def _brokerage_lines(fixture: Fixture, gross_amount: float) -> list[dict]:
    return [
        {
            "description": f"Brokerage — {broker.broker_name}",
            "quantity": 1.0,
            "unit": "%",
            "unit_price": broker.commission_percentage,
            "amount": -round(gross_amount * broker.commission_percentage / 100, 2),
        }
        for broker in fixture.brokers
    ]


def _hire_lines(fixture: Fixture, period_start_raw: str, period_end_raw: str) -> list[dict]:
    try:
        period_start = parse_flexible_datetime(period_start_raw)
        period_end = parse_flexible_datetime(period_end_raw)
    except UnparseableDateTime as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if period_end <= period_start:
        raise HTTPException(status_code=422, detail="hire_period_end must be after hire_period_start")

    duration_days = (period_end - period_start).total_seconds() / 86400
    daily_rate = fixture.hire_rate if fixture.hire_rate_basis == "daily" else fixture.hire_rate / 30
    gross = round(daily_rate * duration_days, 2)
    return [
        {"description": "Hire", "quantity": round(duration_days, 4), "unit": "day", "unit_price": daily_rate, "amount": gross}
    ] + _brokerage_lines(fixture, gross)


def _freight_lines(fixture: Fixture, voyage: Voyage) -> list[dict]:
    if fixture.fixture_type == "coa":
        quantity, unit, unit_price = voyage.cargo_quantity_mt, "MT", fixture.rate_per_tonne
    elif fixture.freight_rate_basis == "lump_sum":
        quantity, unit, unit_price = 1.0, "lump sum", fixture.freight_rate
    else:
        quantity, unit, unit_price = voyage.cargo_quantity_mt, "MT", fixture.freight_rate
    gross = round(quantity * unit_price, 2)
    return [
        {"description": "Freight", "quantity": quantity, "unit": unit, "unit_price": unit_price, "amount": gross}
    ] + _brokerage_lines(fixture, gross)


def _manual_lines(payload: InvoiceCreate, empty_message: str) -> list[dict]:
    if not payload.lines:
        raise HTTPException(status_code=422, detail=empty_message)
    return [
        {
            "description": line.description,
            "quantity": line.quantity,
            "unit": line.unit,
            "unit_price": line.unit_price,
            "amount": round(line.quantity * line.unit_price, 2),
        }
        for line in payload.lines
    ]


def _get_or_404(db: Session, model, obj_id, label: str):
    obj = db.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return obj


def resolve_invoice(payload: InvoiceCreate, db: Session) -> ResolvedInvoice:
    fixture: Fixture | None = None
    voyage: Voyage | None = None
    vessel_id: int

    if payload.invoice_type == "hire":
        fixture = _get_or_404(db, Fixture, payload.fixture_id, "Fixture")
        if fixture.fixture_type != "time_charter_out":
            raise HTTPException(status_code=422, detail="Hire invoices require a Time Charter Out fixture")
        vessel_id = payload.vessel_id
        _get_or_404(db, Vessel, vessel_id, "Vessel")
        lines = _hire_lines(fixture, payload.hire_period_start, payload.hire_period_end)

    elif payload.invoice_type == "freight":
        voyage = _get_or_404(db, Voyage, payload.voyage_id, "Voyage")
        fixture = _get_or_404(db, Fixture, voyage.fixture_id, "Fixture")
        if fixture.fixture_type not in ("voyage_charter", "coa"):
            raise HTTPException(
                status_code=422, detail="Freight invoices require a Voyage Charter or COA fixture"
            )
        vessel_id = voyage.vessel_id
        lines = _freight_lines(fixture, voyage)

    elif payload.invoice_type == "demurrage":
        voyage = _get_or_404(db, Voyage, payload.voyage_id, "Voyage")
        fixture = db.get(Fixture, voyage.fixture_id)
        vessel_id = voyage.vessel_id
        if payload.claim_id is not None:
            _get_or_404(db, Claim, payload.claim_id, "Claim")
        lines = _manual_lines(payload, "Demurrage invoices require at least one line")

    else:  # free_form
        if payload.voyage_id is not None:
            voyage = _get_or_404(db, Voyage, payload.voyage_id, "Voyage")
        vessel_id = payload.vessel_id
        _get_or_404(db, Vessel, vessel_id, "Vessel")
        lines = _manual_lines(payload, "Free-form invoices require at least one line")

    if fixture is not None:
        currency = fixture.contract_currency
        vat_applicable = fixture.vat_applicable
        vat_treatment = fixture.vat_treatment
        vat_rate_percent = fixture.vat_rate_percent
        counterparty = fixture.charterer
    else:
        currency = payload.currency
        vat_applicable = payload.vat_applicable
        vat_treatment = payload.vat_treatment
        vat_rate_percent = payload.vat_rate_percent
        counterparty = payload.counterparty

    # Mechanic A: VAT is computed on the gross (pre-deduction) revenue lines only —
    # brokerage is a VAT-neutral pass-through, it doesn't shrink the tax base.
    gross_total = round(sum(line["amount"] for line in lines if line["amount"] > 0), 2)
    vat_amount = round(
        apply_vat_terms(gross_total, vat_applicable, vat_treatment, vat_rate_percent) - gross_total, 2
    )
    total_amount_due = round(sum(line["amount"] for line in lines) + vat_amount, 2)

    return ResolvedInvoice(
        currency=currency,
        vat_applicable=vat_applicable,
        vat_treatment=vat_treatment,
        vat_rate_percent=vat_rate_percent,
        vat_amount=vat_amount,
        counterparty=counterparty,
        fixture_id=fixture.id if fixture is not None else None,
        voyage_id=voyage.id if voyage is not None else None,
        vessel_id=vessel_id,
        lines=lines,
        total_amount_due=total_amount_due,
    )
