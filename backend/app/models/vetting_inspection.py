from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class VettingInspection(Base):
    __tablename__ = "vetting_inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), nullable=False)
    inspection_date: Mapped[str] = mapped_column(String, nullable=False)
    inspecting_body: Mapped[str] = mapped_column(String, nullable=False)
    inspection_type: Mapped[str] = mapped_column(String, nullable=False)
    expiry_date: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    observations: Mapped[str | None] = mapped_column(String, nullable=True)
