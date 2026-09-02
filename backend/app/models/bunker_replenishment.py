from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class BunkerReplenishment(Base):
    __tablename__ = "bunker_replenishments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), nullable=False)
    replenishment_datetime: Mapped[str] = mapped_column(String, nullable=False)
    port: Mapped[str] = mapped_column(String, nullable=False)
    supplier: Mapped[str] = mapped_column(String, nullable=False)
    invoice_number: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False)

    lines: Mapped[list["BunkerReplenishmentLine"]] = relationship(
        back_populates="replenishment", cascade="all, delete-orphan"
    )


class BunkerReplenishmentLine(Base):
    __tablename__ = "bunker_replenishment_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    replenishment_id: Mapped[int] = mapped_column(
        ForeignKey("bunker_replenishments.id"), nullable=False
    )
    fuel_grade: Mapped[str] = mapped_column(String, nullable=False)
    quantity_mt: Mapped[float] = mapped_column(Float, nullable=False)
    price_per_mt: Mapped[float] = mapped_column(Float, nullable=False)

    replenishment: Mapped[BunkerReplenishment] = relationship(back_populates="lines")
