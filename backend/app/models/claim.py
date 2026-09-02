from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    voyage_id: Mapped[int | None] = mapped_column(ForeignKey("voyages.id"), nullable=True)
    fixture_id: Mapped[int | None] = mapped_column(ForeignKey("fixtures.id"), nullable=True)
    disbursement_account_id: Mapped[int | None] = mapped_column(
        ForeignKey("disbursement_accounts.id"), nullable=True
    )
    claim_type: Mapped[str] = mapped_column(String, nullable=False)
    counterparty: Mapped[str] = mapped_column(String, nullable=False)
    amount_claimed: Mapped[float] = mapped_column(Float, nullable=False)
    amount_settled: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="open")
    date_raised: Mapped[str] = mapped_column(String, nullable=False)
    date_resolved: Mapped[str | None] = mapped_column(String, nullable=True)
    settled_payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
