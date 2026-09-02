from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    table_name: Mapped[str] = mapped_column(String, nullable=False)
    record_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    old_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_values: Mapped[str | None] = mapped_column(Text, nullable=True)
    user: Mapped[str] = mapped_column(String, nullable=False, default="operator")
    timestamp: Mapped[str] = mapped_column(String, nullable=False)
