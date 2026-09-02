from typing import Literal

from pydantic import BaseModel, ConfigDict

CostCategory = Literal["income", "expense"]
Currency = Literal["RUB", "USD"]
PaymentStatus = Literal["draft", "pending", "invoiced", "partial", "paid", "overdue"]


class PaymentCreate(BaseModel):
    vessel_id: int
    voyage_id: int | None = None
    fixture_id: int | None = None
    disbursement_account_id: int | None = None
    vendor_name: str | None = None
    cost_category: CostCategory
    cost_type_name: str

    original_currency: Currency
    original_amount: float

    invoice_date: str
    due_date: str | None = None
    payment_date: str | None = None
    status: PaymentStatus = "draft"

    document_number: str | None = None
    notes: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vessel_id: int
    voyage_id: int | None
    fixture_id: int | None
    disbursement_account_id: int | None
    vendor_name: str | None
    cost_category: CostCategory
    cost_type_name: str

    original_currency: Currency
    original_amount: float
    rub_equivalent: float
    exchange_rate_used: float | None
    exchange_rate_date: str | None

    invoice_date: str
    due_date: str | None
    payment_date: str | None
    status: PaymentStatus

    document_number: str | None
    notes: str | None


class PaymentStatusUpdate(BaseModel):
    status: PaymentStatus


class PaymentReadWithDisplay(PaymentRead):
    display_currency: Currency
    display_amount: float
