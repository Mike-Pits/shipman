from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Vessel(Base):
    __tablename__ = "vessels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    imo_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    flag: Mapped[str] = mapped_column(String, nullable=False)
    year_built: Mapped[int] = mapped_column(Integer, nullable=False)
    vessel_type: Mapped[str] = mapped_column(String, nullable=False)
    dwt: Mapped[float] = mapped_column(Float, nullable=False)
    loa: Mapped[float] = mapped_column(Float, nullable=False)
    beam: Mapped[float] = mapped_column(Float, nullable=False)
    draft: Mapped[float] = mapped_column(Float, nullable=False)
    cargo_tank_capacity_cbm: Mapped[float] = mapped_column(Float, nullable=False)
    ice_class: Mapped[str] = mapped_column(String, nullable=False)
    engine_power_kw: Mapped[float] = mapped_column(Float, nullable=False)

    fuel_consumption_profiles: Mapped[list["FuelConsumptionProfile"]] = relationship(
        back_populates="vessel", cascade="all, delete-orphan"
    )


class FuelConsumptionProfile(Base):
    __tablename__ = "fuel_consumption_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), nullable=False)
    mode: Mapped[str] = mapped_column(String, nullable=False)
    ifo_mt_per_day: Mapped[float] = mapped_column(Float, nullable=False)
    mgo_mt_per_day: Mapped[float] = mapped_column(Float, nullable=False)

    vessel: Mapped[Vessel] = relationship(back_populates="fuel_consumption_profiles")
