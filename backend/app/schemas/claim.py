from typing import Literal

from pydantic import BaseModel, ConfigDict

ClaimType = Literal["cargo_quantity", "cargo_quality", "demurrage_dispute", "off_hire_dispute", "other"]
ClaimStatus = Literal["open", "negotiating", "settled", "rejected"]


class ClaimCreate(BaseModel):
    voyage_id: int | None = None
    fixture_id: int | None = None
    disbursement_account_id: int | None = None
    claim_type: ClaimType
    counterparty: str
    amount_claimed: float
    currency: str
    date_raised: str
    notes: str | None = None


class ClaimStatusUpdate(BaseModel):
    status: Literal["negotiating", "rejected"]


class ClaimSettle(BaseModel):
    amount_settled: float
    payment_id: int | None = None


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voyage_id: int | None
    fixture_id: int | None
    disbursement_account_id: int | None
    claim_type: ClaimType
    counterparty: str
    amount_claimed: float
    amount_settled: float | None
    currency: str
    status: ClaimStatus
    date_raised: str
    date_resolved: str | None
    settled_payment_id: int | None
    notes: str | None
