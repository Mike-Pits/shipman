from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field

DisbursementAccountStatus = Literal["pda_only", "fda_pending", "reconciled", "disputed"]


class DisbursementAccountLineCreate(BaseModel):
    line_type: str
    description: str
    amount: float
    currency: str


class DisbursementAccountLineRead(DisbursementAccountLineCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class DisbursementAccountCreate(BaseModel):
    voyage_id: int
    port: str
    pda_amount: float
    pda_currency: str
    pda_date: str


class FdaLinesCreate(BaseModel):
    lines: list[DisbursementAccountLineCreate]


class DisbursementAccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voyage_id: int
    port: str
    pda_amount: float
    pda_currency: str
    pda_date: str
    status: DisbursementAccountStatus
    lines: list[DisbursementAccountLineRead]

    @computed_field
    @property
    def fda_total(self) -> float:
        return round(sum(line.amount for line in self.lines), 2)

    @computed_field
    @property
    def variance(self) -> float:
        return round(self.fda_total - self.pda_amount, 2)
