from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Port(Base):
    """Operator-maintained port list; feeds the itinerary port-name suggestions in estimates."""

    __tablename__ = "ports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
