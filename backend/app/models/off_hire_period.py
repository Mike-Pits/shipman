from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OffHirePeriod(Base):
    __tablename__ = "off_hire_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    voyage_id: Mapped[int] = mapped_column(ForeignKey("voyages.id"), nullable=False)
    start_datetime: Mapped[str] = mapped_column(String, nullable=False)
    end_datetime: Mapped[str] = mapped_column(String, nullable=False)
    reason: Mapped[str] = mapped_column(String, nullable=False)
    calculated_deduction: Mapped[float] = mapped_column(Float, nullable=False)
    override_deduction: Mapped[float | None] = mapped_column(Float, nullable=True)
