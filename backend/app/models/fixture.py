from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_type: Mapped[str] = mapped_column(String, nullable=False)
    charterer: Mapped[str] = mapped_column(String, nullable=False)
    contract_currency: Mapped[str] = mapped_column(String, nullable=False)

    date_concluded: Mapped[str | None] = mapped_column(String, nullable=True)
    charter_party_ref: Mapped[str | None] = mapped_column(String(15), nullable=True)
    charter_party_type: Mapped[str | None] = mapped_column(String, nullable=True)

    # Voyage Charter fields (FR-07)
    freight_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    freight_rate_basis: Mapped[str | None] = mapped_column(String, nullable=True)
    laycan_start: Mapped[str | None] = mapped_column(String, nullable=True)
    laycan_end: Mapped[str | None] = mapped_column(String, nullable=True)
    load_port: Mapped[str | None] = mapped_column(String, nullable=True)
    discharge_port: Mapped[str | None] = mapped_column(String, nullable=True)
    cargo_grade: Mapped[str | None] = mapped_column(String, nullable=True)
    demurrage_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    despatch_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    laytime_terms: Mapped[str | None] = mapped_column(String, nullable=True)

    # Time Charter Out fields (FR-08)
    hire_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    hire_rate_basis: Mapped[str | None] = mapped_column(String, nullable=True)
    charter_period_from: Mapped[str | None] = mapped_column(String, nullable=True)
    charter_period_to: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_port: Mapped[str | None] = mapped_column(String, nullable=True)
    delivery_rob_ifo_mt: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_rob_mgo_mt: Mapped[float | None] = mapped_column(Float, nullable=True)
    redelivery_port: Mapped[str | None] = mapped_column(String, nullable=True)
    redelivery_rob_ifo_mt: Mapped[float | None] = mapped_column(Float, nullable=True)
    redelivery_rob_mgo_mt: Mapped[float | None] = mapped_column(Float, nullable=True)
    redelivery_conditions: Mapped[str | None] = mapped_column(String, nullable=True)
    hire_payment_basis: Mapped[str | None] = mapped_column(String, nullable=True)
    hire_payment_frequency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hire_payment_days_after_invoice: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # COA fields (FR-09)
    contract_period_from: Mapped[str | None] = mapped_column(String, nullable=True)
    contract_period_to: Mapped[str | None] = mapped_column(String, nullable=True)
    total_contracted_quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    number_of_lifts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_per_tonne: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_cargo_quantity_per_lift: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_cargo_quantity_per_lift: Mapped[float | None] = mapped_column(Float, nullable=True)

    brokers: Mapped[list["FixtureBroker"]] = relationship(
        back_populates="fixture", cascade="all, delete-orphan"
    )


class FixtureBroker(Base):
    __tablename__ = "fixture_brokers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[int] = mapped_column(ForeignKey("fixtures.id"), nullable=False)
    broker_name: Mapped[str] = mapped_column(String, nullable=False)
    commission_percentage: Mapped[float] = mapped_column(Float, nullable=False)

    fixture: Mapped[Fixture] = relationship(back_populates="brokers")
