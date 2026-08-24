from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_rate_fetcher
from app.models.exchange_rate import ExchangeRate
from app.schemas.exchange_rate import ExchangeRateOverride, ExchangeRateRead
from app.services.cbr_rate_fetcher import RateFetchError

router = APIRouter(prefix="/exchange-rates", tags=["exchange-rates"])


@router.post("/fetch", response_model=ExchangeRateRead)
def fetch_todays_rate(
    db: Session = Depends(get_db),
    rate_fetcher=Depends(get_rate_fetcher),
):
    today_str = date.today().isoformat()

    try:
        rate_value = rate_fetcher()
    except RateFetchError:
        last_known = (
            db.query(ExchangeRate).order_by(ExchangeRate.rate_date.desc()).first()
        )
        if last_known is None:
            raise HTTPException(
                status_code=503,
                detail="Rate fetch failed and no previously known rate is available",
            )
        result = ExchangeRateRead.model_validate(last_known)
        result.stale = True
        return result

    existing = db.query(ExchangeRate).filter(ExchangeRate.rate_date == today_str).first()
    if existing is not None:
        existing.usd_rub_rate = rate_value
        existing.manual_override = False
    else:
        existing = ExchangeRate(rate_date=today_str, usd_rub_rate=rate_value, manual_override=False)
        db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


@router.get("/{rate_date}", response_model=ExchangeRateRead)
def get_rate_for_date(rate_date: str, db: Session = Depends(get_db)):
    rate = db.query(ExchangeRate).filter(ExchangeRate.rate_date == rate_date).first()
    if rate is None:
        raise HTTPException(status_code=404, detail="No rate stored for this date")
    return rate


@router.put("/{rate_date}", response_model=ExchangeRateRead)
def override_rate_for_date(
    rate_date: str, payload: ExchangeRateOverride, db: Session = Depends(get_db)
):
    rate = db.query(ExchangeRate).filter(ExchangeRate.rate_date == rate_date).first()
    if rate is not None:
        rate.usd_rub_rate = payload.usd_rub_rate
        rate.manual_override = True
    else:
        rate = ExchangeRate(
            rate_date=rate_date, usd_rub_rate=payload.usd_rub_rate, manual_override=True
        )
        db.add(rate)
    db.commit()
    db.refresh(rate)
    return rate
