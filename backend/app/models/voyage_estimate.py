from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VoyageEstimate(Base):
    """A preliminary TCE calculation for a candidate voyage (ported from voyage-calculator.html).

    Only inputs are stored; results are computed on read by `services/voyage_calc.py` against the
    vessel's current consumption profile. `baseline_*` freezes the figures at the moment the
    estimate is promoted to a fixture, so Voyage P&L reconciliation does not drift when the
    vessel profile is later edited.
    """

    __tablename__ = "voyage_estimates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    vessel_id: Mapped[int | None] = mapped_column(ForeignKey("vessels.id"), nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    laycan_start: Mapped[str | None] = mapped_column(String, nullable=True)
    laycan_end: Mapped[str | None] = mapped_column(String, nullable=True)
    freight_mode: Mapped[str] = mapped_column(String, nullable=False, default="per_mt")
    lumpsum_freight: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    sea_mode: Mapped[str] = mapped_column(String, nullable=False, default="laden")
    extra_sea_days: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    extra_costs: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    canal_fees: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    port_charges: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    agent_fees: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    bunker_surcharge: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    demurrage_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"), nullable=True)
    baseline_net_result: Mapped[float | None] = mapped_column(Float, nullable=True)
    baseline_tce_per_day: Mapped[float | None] = mapped_column(Float, nullable=True)

    port_stops: Mapped[list["EstimatePortStop"]] = relationship(
        cascade="all, delete-orphan", order_by="EstimatePortStop.position"
    )
    cargo_lots: Mapped[list["EstimateCargoLot"]] = relationship(
        cascade="all, delete-orphan", order_by="EstimateCargoLot.id"
    )
    fuel_prices: Mapped[list["EstimateFuelPrice"]] = relationship(
        cascade="all, delete-orphan", order_by="EstimateFuelPrice.id"
    )
    cost_items: Mapped[list["EstimateCostItem"]] = relationship(
        cascade="all, delete-orphan", order_by="EstimateCostItem.id"
    )


class EstimatePortStop(Base):
    __tablename__ = "estimate_port_stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("voyage_estimates.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    port_name: Mapped[str] = mapped_column(String, nullable=False)
    stop_type: Mapped[str] = mapped_column(String, nullable=False)  # load / discharge
    distance_nm: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    cargo_quantity_mt: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    laytime_value: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    laytime_unit: Mapped[str] = mapped_column(String, nullable=False, default="days")
    laytime_basis: Mapped[str] = mapped_column(String, nullable=False, default="SHINC")
    rate_mt_per_day: Mapped[float] = mapped_column(Float, nullable=False, default=0)


class EstimateCargoLot(Base):
    __tablename__ = "estimate_cargo_lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("voyage_estimates.id"), nullable=False)
    grade: Mapped[str] = mapped_column(String, nullable=False)
    quantity_mt: Mapped[float] = mapped_column(Float, nullable=False)
    freight_rate: Mapped[float] = mapped_column(Float, nullable=False)


class EstimateFuelPrice(Base):
    __tablename__ = "estimate_fuel_prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("voyage_estimates.id"), nullable=False)
    grade: Mapped[str] = mapped_column(String, nullable=False)
    price_per_mt: Mapped[float] = mapped_column(Float, nullable=False)


class EstimateCostItem(Base):
    __tablename__ = "estimate_cost_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    estimate_id: Mapped[int] = mapped_column(ForeignKey("voyage_estimates.id"), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
