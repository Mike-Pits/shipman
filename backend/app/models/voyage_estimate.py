from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VoyageEstimate(Base):
    __tablename__ = "voyage_estimates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vessel_id: Mapped[int | None] = mapped_column(ForeignKey("vessels.id"), nullable=True)
    load_port: Mapped[str] = mapped_column(String, nullable=False)
    discharge_port: Mapped[str] = mapped_column(String, nullable=False)
    laycan_start: Mapped[str] = mapped_column(String, nullable=False)
    laycan_end: Mapped[str] = mapped_column(String, nullable=False)
    cargo_grade: Mapped[str] = mapped_column(String, nullable=False)
    estimated_cargo_quantity_mt: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_rate: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_rate_basis: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    estimated_bunker_consumption_mt: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_bunker_cost: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_port_costs: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_duration_days: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"), nullable=True)
