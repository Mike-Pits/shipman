from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_number: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    invoice_type: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")

    date_of_issue: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[str | None] = mapped_column(String, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False)

    vat_applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    vat_treatment: Mapped[str | None] = mapped_column(String, nullable=True)
    vat_rate_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    vat_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)

    counterparty: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str | None] = mapped_column(String, nullable=True)

    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"), nullable=True)
    voyage_id: Mapped[int | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), nullable=False)
    claim_id: Mapped[int | None] = mapped_column(ForeignKey("claims.id"), nullable=True)
    payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)

    # Hire-only: the billing period, entered free-form since it isn't tied to a Voyage.
    # Carries the same YYYY-MM-DD[ HH:MM[:SS]] precision as Fixture.charter_period_from/to
    # so a partial final day prorates correctly instead of rounding.
    hire_period_start: Mapped[str | None] = mapped_column(String, nullable=True)
    hire_period_end: Mapped[str | None] = mapped_column(String, nullable=True)

    total_amount_due: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    # RUB value of total_amount_due frozen at issue time — used to compute the
    # billed-vs-collected variance later even if the linked Payment's amount is
    # subsequently corrected to match what was actually received.
    total_amount_due_rub: Mapped[float | None] = mapped_column(Float, nullable=True)

    lines: Mapped[list["InvoiceLine"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    # Positive for revenue lines, negative for deductions (e.g. brokerage) — the sum
    # of all lines plus vat_amount is total_amount_due.
    amount: Mapped[float] = mapped_column(Float, nullable=False)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")
