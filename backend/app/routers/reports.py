from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.claim import Claim
from app.models.disbursement_account import DisbursementAccount
from app.models.invoice import Invoice
from app.models.off_hire_period import OffHirePeriod
from app.models.payment import Payment
from app.models.vessel import Vessel
from app.models.voyage import Voyage
from app.models.voyage_estimate import VoyageEstimate
from app.services.excel_export import ReportFormat, rows_to_xlsx_response
from app.services.vetting import current_vetting_status

router = APIRouter(prefix="/reports", tags=["reports"])


def _estimate_reconciliation(voyage: Voyage, net_result: float, db: Session) -> dict:
    if voyage.fixture_id is None:
        return {}
    estimate = (
        db.query(VoyageEstimate).filter(VoyageEstimate.fixture_id == voyage.fixture_id).first()
    )
    if estimate is None:
        return {}

    if estimate.estimated_rate_basis == "per_tonne":
        estimated_revenue = estimate.estimated_rate * estimate.estimated_cargo_quantity_mt
    else:
        estimated_revenue = estimate.estimated_rate
    estimated_costs = estimate.estimated_bunker_cost + estimate.estimated_port_costs
    estimated_net_result = round(estimated_revenue - estimated_costs, 2)

    return {
        "estimated_net_result": estimated_net_result,
        "variance_vs_estimate": round(net_result - estimated_net_result, 2),
    }


def _voyage_or_404(voyage_id: int, db: Session) -> Voyage:
    voyage = db.get(Voyage, voyage_id)
    if voyage is None:
        raise HTTPException(status_code=404, detail="Voyage not found")
    return voyage


def _invoiced_revenue(query) -> float:
    """Sum of issued invoices' billed RUB total — frozen at issue time, independent
    of any later correction to what the linked Payment actually collected."""
    invoices = query.filter(Invoice.status == "issued").all()
    return round(sum(i.total_amount_due_rub or 0 for i in invoices), 2)


def _voyage_pnl(voyage_id: int, db: Session) -> dict:
    payments = db.query(Payment).filter(Payment.voyage_id == voyage_id).all()
    revenue = round(sum(p.rub_equivalent for p in payments if p.cost_category == "income"), 2)
    costs = round(sum(p.rub_equivalent for p in payments if p.cost_category == "expense"), 2)
    invoiced_revenue = _invoiced_revenue(db.query(Invoice).filter(Invoice.voyage_id == voyage_id))
    return {
        "voyage_id": voyage_id,
        "revenue": revenue,
        "costs": costs,
        "net_result": round(revenue - costs, 2),
        "invoiced_revenue": invoiced_revenue,
        "variance_vs_invoiced": round(revenue - invoiced_revenue, 2),
        "currency": "RUB",
    }


@router.get("/voyage-pnl/{voyage_id}")
def voyage_pnl(voyage_id: int, format: ReportFormat = "json", db: Session = Depends(get_db)):
    voyage = _voyage_or_404(voyage_id, db)
    pnl = _voyage_pnl(voyage_id, db)
    result = {**pnl, **_estimate_reconciliation(voyage, pnl["net_result"], db)}
    if format == "xlsx":
        return rows_to_xlsx_response(result, f"voyage_pnl_{voyage_id}")
    return result


@router.get("/tce/{voyage_id}")
def tce(voyage_id: int, format: ReportFormat = "json", db: Session = Depends(get_db)):
    voyage = _voyage_or_404(voyage_id, db)
    if voyage.voyage_purpose != "employment":
        raise HTTPException(
            status_code=422,
            detail="TCE only applies to employment voyages — this voyage has no revenue to divide by days",
        )
    if not voyage.end_date:
        raise HTTPException(
            status_code=422,
            detail="Voyage has no end date yet — TCE cannot be calculated until the voyage is complete",
        )

    start = datetime.strptime(voyage.start_date, "%Y-%m-%d").date()
    end = datetime.strptime(voyage.end_date, "%Y-%m-%d").date()
    duration_days = (end - start).days

    off_hire_periods = db.query(OffHirePeriod).filter(OffHirePeriod.voyage_id == voyage_id).all()
    off_hire_days = 0.0
    for period in off_hire_periods:
        period_start = datetime.strptime(period.start_datetime, "%Y-%m-%d %H:%M:%S")
        period_end = datetime.strptime(period.end_datetime, "%Y-%m-%d %H:%M:%S")
        off_hire_days += (period_end - period_start).total_seconds() / 86400
    earning_days = duration_days - off_hire_days

    pnl = _voyage_pnl(voyage_id, db)
    result = {
        **pnl,
        "duration_days": duration_days,
        "off_hire_days": round(off_hire_days, 2),
        "earning_days": round(earning_days, 2),
        "tce_per_day": round(pnl["net_result"] / earning_days, 2),
    }
    if format == "xlsx":
        return rows_to_xlsx_response(result, f"tce_{voyage_id}")
    return result


@router.get("/fleet-pnl")
def fleet_pnl(
    start_date: str, end_date: str, format: ReportFormat = "json", db: Session = Depends(get_db)
):
    payments = (
        db.query(Payment)
        .filter(Payment.invoice_date >= start_date, Payment.invoice_date <= end_date)
        .all()
    )
    revenue = round(sum(p.rub_equivalent for p in payments if p.cost_category == "income"), 2)
    costs = round(sum(p.rub_equivalent for p in payments if p.cost_category == "expense"), 2)
    voyage_ids = {p.voyage_id for p in payments if p.voyage_id is not None}
    invoiced_revenue = _invoiced_revenue(
        db.query(Invoice).filter(Invoice.date_of_issue >= start_date, Invoice.date_of_issue <= end_date)
    )
    result = {
        "start_date": start_date,
        "end_date": end_date,
        "revenue": revenue,
        "costs": costs,
        "net_result": round(revenue - costs, 2),
        "invoiced_revenue": invoiced_revenue,
        "variance_vs_invoiced": round(revenue - invoiced_revenue, 2),
        "voyage_count": len(voyage_ids),
        "currency": "RUB",
    }
    if format == "xlsx":
        return rows_to_xlsx_response(result, f"fleet_pnl_{start_date}_to_{end_date}")
    return result


def _overlap_days(start: datetime, end: datetime | None, query_start: datetime, query_end: datetime) -> float:
    """Fractional-day overlap between a period [start, end) and a query range. An
    open-ended period (end=None) is clipped to query_end."""
    effective_end = end if end is not None else query_end
    overlap_start = max(start, query_start)
    overlap_end = min(effective_end, query_end)
    if overlap_start >= overlap_end:
        return 0.0
    return (overlap_end - overlap_start).total_seconds() / 86400


@router.get("/fleet-utilization")
def fleet_utilization(
    start_date: str, end_date: str, format: ReportFormat = "json", db: Session = Depends(get_db)
):
    """SRS §4.4a: per-vessel breakdown of employment vs. unfixed ballast/idle vs.
    drydock time, plus off-hire (a subset of employment time, shown separately per
    the operator's preference — see the design discussion) and unaccounted days
    (calendar days in range with no voyage record at all — a data-entry gap flag)."""
    q_start = datetime.strptime(start_date, "%Y-%m-%d")
    q_end = datetime.strptime(end_date, "%Y-%m-%d")
    total_days = (q_end - q_start).total_seconds() / 86400

    rows = []
    for vessel in db.query(Vessel).all():
        voyages = db.query(Voyage).filter(Voyage.vessel_id == vessel.id).all()
        employment_days = ballast_days = drydock_days = 0.0
        for v in voyages:
            v_start = datetime.strptime(v.start_date, "%Y-%m-%d")
            v_end = datetime.strptime(v.end_date, "%Y-%m-%d") if v.end_date else None
            overlap = _overlap_days(v_start, v_end, q_start, q_end)
            if v.voyage_purpose == "employment":
                employment_days += overlap
            elif v.voyage_purpose == "ballast_passage":
                ballast_days += overlap
            elif v.voyage_purpose == "drydock_repair":
                drydock_days += overlap

        off_hire_days = 0.0
        voyage_ids = [v.id for v in voyages]
        if voyage_ids:
            periods = db.query(OffHirePeriod).filter(OffHirePeriod.voyage_id.in_(voyage_ids)).all()
            for period in periods:
                p_start = datetime.strptime(period.start_datetime, "%Y-%m-%d %H:%M:%S")
                p_end = datetime.strptime(period.end_datetime, "%Y-%m-%d %H:%M:%S")
                off_hire_days += _overlap_days(p_start, p_end, q_start, q_end)

        unaccounted_days = max(0.0, total_days - employment_days - ballast_days - drydock_days)

        rows.append(
            {
                "vessel_id": vessel.id,
                "vessel_name": vessel.name,
                "employment_days": round(employment_days, 2),
                "ballast_days": round(ballast_days, 2),
                "drydock_days": round(drydock_days, 2),
                "off_hire_days": round(off_hire_days, 2),
                "unaccounted_days": round(unaccounted_days, 2),
            }
        )
    if format == "xlsx":
        return rows_to_xlsx_response(rows, f"fleet_utilization_{start_date}_to_{end_date}")
    return rows


@router.get("/current-vessel-status")
def current_vessel_status(db: Session = Depends(get_db)):
    """Dashboard tile: which vessels have no open employment voyage covering
    today — i.e. currently idle/ballast, in drydock, or entirely unaccounted for."""
    today = date.today().isoformat()
    rows = []
    for vessel in db.query(Vessel).all():
        voyages = db.query(Voyage).filter(Voyage.vessel_id == vessel.id).all()
        matches = [v for v in voyages if v.start_date <= today and (v.end_date is None or v.end_date >= today)]
        current = max(matches, key=lambda v: v.start_date) if matches else None
        rows.append(
            {
                "vessel_id": vessel.id,
                "vessel_name": vessel.name,
                "status": current.voyage_purpose if current is not None else "unaccounted",
                "voyage_id": current.id if current is not None else None,
            }
        )
    return rows


@router.get("/da-reconciliation")
def da_reconciliation(format: ReportFormat = "json", db: Session = Depends(get_db)):
    """FR-51: PDA vs. FDA totals and variance per port call, flagging unreconciled
    or disputed DAs. Returns every DA whose status is not yet 'reconciled'."""
    das = (
        db.query(DisbursementAccount)
        .filter(DisbursementAccount.status.in_(["pda_only", "fda_pending", "disputed"]))
        .all()
    )
    rows = []
    for da in das:
        fda_total = round(sum(line.amount for line in da.lines), 2)
        rows.append(
            {
                "id": da.id,
                "voyage_id": da.voyage_id,
                "port": da.port,
                "status": da.status,
                "pda_amount": da.pda_amount,
                "fda_total": fda_total,
                "variance": round(fda_total - da.pda_amount, 2),
            }
        )
    if format == "xlsx":
        return rows_to_xlsx_response(rows, "da_reconciliation")
    return rows


@router.get("/vetting-status")
def fleet_vetting_status(format: ReportFormat = "json", db: Session = Depends(get_db)):
    """FR-52: current vetting status and next expiry per vessel, fleet-wide."""
    rows = []
    for vessel in db.query(Vessel).all():
        result = current_vetting_status(db, vessel.id)
        rows.append(
            {
                "vessel_id": vessel.id,
                "vessel_name": vessel.name,
                "status": result[1] if result else None,
                "expiry_date": result[0].expiry_date if result else None,
            }
        )
    if format == "xlsx":
        return rows_to_xlsx_response(rows, "vetting_status")
    return rows


@router.get("/claims-status")
def claims_status(format: ReportFormat = "json", db: Session = Depends(get_db)):
    """FR-53: open/negotiating claims with amounts and age."""
    today = date.today()
    claims = db.query(Claim).filter(Claim.status.in_(["open", "negotiating"])).all()
    rows = []
    for claim in claims:
        raised = datetime.strptime(claim.date_raised, "%Y-%m-%d").date()
        rows.append(
            {
                "id": claim.id,
                "voyage_id": claim.voyage_id,
                "claim_type": claim.claim_type,
                "counterparty": claim.counterparty,
                "amount_claimed": claim.amount_claimed,
                "currency": claim.currency,
                "status": claim.status,
                "age_days": (today - raised).days,
            }
        )
    if format == "xlsx":
        return rows_to_xlsx_response(rows, "claims_status")
    return rows
