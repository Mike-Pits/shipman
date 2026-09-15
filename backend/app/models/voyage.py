from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Voyage(Base):
    __tablename__ = "voyages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # "employment" (default, under a Fixture) / "ballast_passage" (unfixed, between
    # fixtures — transiting empty or waiting) / "drydock_repair" (planned maintenance,
    # vessel unavailable regardless of market). See SRS §4.4a.
    voyage_purpose: Mapped[str] = mapped_column(String, nullable=False, default="employment")
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"), nullable=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), nullable=False)
    voyage_number: Mapped[str] = mapped_column(String, nullable=False)
    load_port: Mapped[str] = mapped_column(String, nullable=False)
    discharge_port: Mapped[str | None] = mapped_column(String, nullable=True)
    start_date: Mapped[str] = mapped_column(String, nullable=False)
    end_date: Mapped[str | None] = mapped_column(String, nullable=True)
    cargo_grade: Mapped[str | None] = mapped_column(String, nullable=True)
    cargo_quantity_mt: Mapped[float | None] = mapped_column(Float, nullable=True)
    laden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ice_notes: Mapped[str | None] = mapped_column(String, nullable=True)
