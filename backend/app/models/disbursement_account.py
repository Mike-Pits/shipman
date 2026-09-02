from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DisbursementAccount(Base):
    __tablename__ = "disbursement_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    voyage_id: Mapped[int] = mapped_column(ForeignKey("voyages.id"), nullable=False)
    port: Mapped[str] = mapped_column(String, nullable=False)
    pda_amount: Mapped[float] = mapped_column(Float, nullable=False)
    pda_currency: Mapped[str] = mapped_column(String, nullable=False)
    pda_date: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pda_only")

    lines: Mapped[list["DisbursementAccountLine"]] = relationship(
        back_populates="disbursement_account", cascade="all, delete-orphan"
    )


class DisbursementAccountLine(Base):
    __tablename__ = "disbursement_account_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    disbursement_account_id: Mapped[int] = mapped_column(
        ForeignKey("disbursement_accounts.id"), nullable=False
    )
    line_type: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)

    disbursement_account: Mapped[DisbursementAccount] = relationship(back_populates="lines")
