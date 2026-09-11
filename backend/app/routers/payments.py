from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.claim import Claim
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.vessel import Vessel
from app.schemas.payment import (
    Currency,
    PaymentCreate,
    PaymentRead,
    PaymentReadWithDisplay,
    PaymentStatusUpdate,
)
from app.services.currency import convert_to_rub, rate_for_date

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", response_model=PaymentRead, status_code=201)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db)):
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    rub_equivalent, rate_used, rate_date = convert_to_rub(
        db, payload.original_currency, payload.original_amount, payload.invoice_date
    )

    payment = Payment(
        **payload.model_dump(),
        rub_equivalent=rub_equivalent,
        exchange_rate_used=rate_used,
        exchange_rate_date=rate_date,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("", response_model=list[PaymentRead])
def list_payments(db: Session = Depends(get_db)):
    return db.query(Payment).all()


@router.put("/{payment_id}", response_model=PaymentRead)
def update_payment(payment_id: int, payload: PaymentCreate, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    rub_equivalent, rate_used, rate_date = convert_to_rub(
        db, payload.original_currency, payload.original_amount, payload.invoice_date
    )

    for field, value in payload.model_dump().items():
        setattr(payment, field, value)
    payment.rub_equivalent = rub_equivalent
    payment.exchange_rate_used = rate_used
    payment.exchange_rate_date = rate_date
    db.commit()
    db.refresh(payment)
    return payment


@router.delete("/{payment_id}", status_code=204)
def delete_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    if db.query(Claim).filter(Claim.settled_payment_id == payment_id).first() is not None:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete payment: it is linked to a settled claim. "
            "Remove that link first.",
        )

    linking_invoice = (
        db.query(Invoice).filter(Invoice.payment_id == payment_id, Invoice.status == "issued").first()
    )
    if linking_invoice is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot delete payment: it settles invoice {linking_invoice.invoice_number}. "
            "Void that invoice instead.",
        )

    db.delete(payment)
    db.commit()
    return Response(status_code=204)


@router.post("/{payment_id}/status", response_model=PaymentRead)
def update_payment_status(
    payment_id: int, payload: PaymentStatusUpdate, db: Session = Depends(get_db)
):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    payment.status = payload.status
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/{payment_id}")
def get_payment(
    payment_id: int,
    display_currency: Currency | None = Query(default=None),
    db: Session = Depends(get_db),
) -> PaymentReadWithDisplay | PaymentRead:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    if display_currency is None:
        return PaymentRead.model_validate(payment)

    if display_currency == payment.original_currency:
        display_amount = payment.original_amount
    elif payment.original_currency == "USD" and display_currency == "RUB":
        display_amount = payment.rub_equivalent
    else:
        rate = rate_for_date(db, payment.invoice_date)
        display_amount = round(payment.rub_equivalent / rate.usd_rub_rate, 2)

    return PaymentReadWithDisplay(
        **PaymentRead.model_validate(payment).model_dump(),
        display_currency=display_currency,
        display_amount=display_amount,
    )
