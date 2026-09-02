from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.exchange_rate import ExchangeRate


def rate_for_date(db: Session, rate_date: str) -> ExchangeRate:
    rate = db.query(ExchangeRate).filter(ExchangeRate.rate_date == rate_date).first()
    if rate is None:
        raise HTTPException(
            status_code=422,
            detail=f"No exchange rate stored for {rate_date} — fetch or set one via "
            "/exchange-rates before recording this payment",
        )
    return rate


def convert_to_rub(db: Session, currency: str, amount: float, transaction_date: str):
    """Returns (rub_equivalent, exchange_rate_used, exchange_rate_date)."""
    if currency == "RUB":
        return amount, None, None
    rate = rate_for_date(db, transaction_date)
    return round(amount * rate.usd_rub_rate, 2), rate.usd_rub_rate, transaction_date
