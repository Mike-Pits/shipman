from sqlalchemy import Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id: Mapped[int] = mapped_column(primary_key=True)
    rate_date: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    usd_rub_rate: Mapped[float] = mapped_column(Float, nullable=False)
    manual_override: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
