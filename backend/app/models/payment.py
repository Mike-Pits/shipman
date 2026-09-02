from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vessel_id: Mapped[int] = mapped_column(ForeignKey("vessels.id"), nullable=False)
    voyage_id: Mapped[int | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"), nullable=True)
    disbursement_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("disbursement_accounts.id"), nullable=True
    )
    vendor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    cost_category: Mapped[str] = mapped_column(String, nullable=False)
    cost_type_name: Mapped[str] = mapped_column(String, nullable=False)

    original_currency: Mapped[str] = mapped_column(String, nullable=False)
    original_amount: Mapped[float] = mapped_column(Float, nullable=False)
    rub_equivalent: Mapped[float] = mapped_column(Float, nullable=False)
    exchange_rate_used: Mapped[float | None] = mapped_column(Float, nullable=True)
    exchange_rate_date: Mapped[str | None] = mapped_column(String, nullable=True)

    invoice_date: Mapped[str] = mapped_column(String, nullable=False)
    due_date: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_date: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="draft")

    document_number: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
