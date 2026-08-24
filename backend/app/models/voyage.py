from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Voyage(Base):
    __tablename__ = "voyages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), nullable=False)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), nullable=False)
    voyage_number: Mapped[str] = mapped_column(String, nullable=False)
    load_port: Mapped[str] = mapped_column(String, nullable=False)
    discharge_port: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[str] = mapped_column(String, nullable=False)
    end_date: Mapped[str | None] = mapped_column(String, nullable=True)
    cargo_grade: Mapped[str] = mapped_column(String, nullable=False)
    cargo_quantity_mt: Mapped[float] = mapped_column(Float, nullable=False)
    laden: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ice_notes: Mapped[str | None] = mapped_column(String, nullable=True)
