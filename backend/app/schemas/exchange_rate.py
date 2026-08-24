from pydantic import BaseModel, ConfigDict


class ExchangeRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    rate_date: str
    usd_rub_rate: float
    manual_override: bool
    stale: bool = False


class ExchangeRateOverride(BaseModel):
    usd_rub_rate: float
