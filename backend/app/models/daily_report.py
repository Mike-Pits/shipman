from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DailyReport(Base):
    __tablename__ = "daily_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), nullable=False)
    voyage_id: Mapped[int | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    report_datetime: Mapped[str] = mapped_column(String, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_message_id: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
