from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.claim import Claim
from app.models.invoice import Invoice, InvoiceLine
from app.models.payment import Payment
from app.schemas.invoice import InvoiceCreate, InvoiceRead
from app.services.currency import convert_to_rub
from app.services.invoice_builder import ResolvedInvoice, resolve_invoice
from app.services.invoice_numbering import next_invoice_number

router = APIRouter(prefix="/invoices", tags=["invoices"])

_COST_TYPE_LABELS = {"hire": "Hire", "freight": "Freight", "demurrage": "Demurrage"}


def _get_invoice_or_404(invoice_id: int, db: Session) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


def _apply_resolved(invoice: Invoice, payload: InvoiceCreate, resolved: ResolvedInvoice) -> None:
    invoice.invoice_type = payload.invoice_type
    invoice.date_of_issue = payload.date_of_issue
    invoice.due_date = payload.due_date
    invoice.currency = resolved.currency
    invoice.vat_applicable = resolved.vat_applicable
    invoice.vat_treatment = resolved.vat_treatment
    invoice.vat_rate_percent = resolved.vat_rate_percent
    invoice.vat_amount = resolved.vat_amount
    invoice.counterparty = resolved.counterparty
    invoice.subject = payload.subject
    invoice.fixture_id = resolved.fixture_id
    invoice.voyage_id = resolved.voyage_id
    invoice.vessel_id = resolved.vessel_id
    invoice.claim_id = payload.claim_id
    invoice.hire_period_start = payload.hire_period_start if payload.invoice_type == "hire" else None
    invoice.hire_period_end = payload.hire_period_end if payload.invoice_type == "hire" else None
    invoice.total_amount_due = resolved.total_amount_due
    invoice.lines = [InvoiceLine(**line) for line in resolved.lines]


@router.post("", response_model=InvoiceRead, status_code=201)
def create_invoice(payload: InvoiceCreate, db: Session = Depends(get_db)):
    resolved = resolve_invoice(payload, db)
    invoice = Invoice(status="draft")
    _apply_resolved(invoice, payload, resolved)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("", response_model=list[InvoiceRead])
def list_invoices(
    voyage_id: int | None = None,
    fixture_id: int | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
):
    query = db.query(Invoice)
    if voyage_id is not None:
        query = query.filter(Invoice.voyage_id == voyage_id)
    if fixture_id is not None:
        query = query.filter(Invoice.fixture_id == fixture_id)
    if status is not None:
        query = query.filter(Invoice.status == status)
    return query.all()


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    return _get_invoice_or_404(invoice_id, db)


@router.put("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(invoice_id: int, payload: InvoiceCreate, db: Session = Depends(get_db)):
    invoice = _get_invoice_or_404(invoice_id, db)
    if invoice.status != "draft":
        raise HTTPException(status_code=409, detail="Only a draft invoice can be edited")
    resolved = resolve_invoice(payload, db)
    _apply_resolved(invoice, payload, resolved)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}", status_code=204)
def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_invoice_or_404(invoice_id, db)
    if invoice.status != "draft":
        raise HTTPException(status_code=409, detail="Only a draft invoice can be deleted — void it instead")
    db.delete(invoice)
    db.commit()


@router.post("/{invoice_id}/issue", response_model=InvoiceRead)
def issue_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_invoice_or_404(invoice_id, db)
    if invoice.status != "draft":
        raise HTTPException(status_code=409, detail="Only a draft invoice can be issued")

    year = datetime.strptime(invoice.date_of_issue, "%Y-%m-%d").year
    invoice.invoice_number = next_invoice_number(db, year)

    rub_equivalent, rate_used, rate_date = convert_to_rub(
        db, invoice.currency, invoice.total_amount_due, invoice.date_of_issue
    )
    invoice.total_amount_due_rub = rub_equivalent

    cost_type_name = _COST_TYPE_LABELS.get(invoice.invoice_type, invoice.subject or "Invoice")
    payment = Payment(
        vessel_id=invoice.vessel_id,
        voyage_id=invoice.voyage_id,
        fixture_id=invoice.fixture_id,
        cost_category="income",
        cost_type_name=cost_type_name,
        original_currency=invoice.currency,
        original_amount=invoice.total_amount_due,
        rub_equivalent=rub_equivalent,
        exchange_rate_used=rate_used,
        exchange_rate_date=rate_date,
        invoice_date=invoice.date_of_issue,
        due_date=invoice.due_date,
        status="invoiced",
    )
    db.add(payment)
    db.flush()

    invoice.payment_id = payment.id
    invoice.status = "issued"

    if invoice.claim_id is not None:
        claim = db.get(Claim, invoice.claim_id)
        claim.status = "settled"
        claim.amount_settled = invoice.total_amount_due
        claim.settled_payment_id = payment.id
        claim.date_resolved = date.today().isoformat()

    db.commit()
    db.refresh(invoice)
    return invoice


@router.post("/{invoice_id}/void", response_model=InvoiceRead)
def void_invoice(invoice_id: int, db: Session = Depends(get_db)):
    invoice = _get_invoice_or_404(invoice_id, db)
    if invoice.status != "issued":
        raise HTTPException(status_code=409, detail="Only an issued invoice can be voided")

    if invoice.claim_id is not None:
        claim = db.get(Claim, invoice.claim_id)
        if claim is not None and claim.settled_payment_id == invoice.payment_id:
            claim.status = "negotiating"
            claim.settled_payment_id = None
            claim.amount_settled = None
            claim.date_resolved = None

    payment = db.get(Payment, invoice.payment_id)
    if payment is not None:
        db.delete(payment)
    invoice.payment_id = None
    invoice.status = "void"

    db.commit()
    db.refresh(invoice)
    return invoice
