from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from app.schemas.common import Currency

InvoiceType = Literal["hire", "freight", "demurrage", "free_form"]
InvoiceStatus = Literal["draft", "issued", "void"]
VatTreatment = Literal["inclusive", "exclusive"]


class InvoiceLineInput(BaseModel):
    description: str
    quantity: float
    unit: str
    unit_price: float


class InvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    description: str
    quantity: float
    unit: str
    unit_price: float
    amount: float


class InvoiceCreate(BaseModel):
    invoice_type: InvoiceType
    date_of_issue: str
    due_date: str | None = None

    # Free-form only — ignored/overridden server-side for every other type, which
    # inherit currency and VAT terms from their linked Fixture.
    currency: Currency | None = None
    vat_applicable: bool = False
    vat_treatment: VatTreatment | None = None
    vat_rate_percent: float | None = None
    counterparty: str | None = None
    subject: str | None = None

    fixture_id: int | None = None
    voyage_id: int | None = None
    vessel_id: int | None = None
    claim_id: int | None = None

    # Hire only
    hire_period_start: str | None = None
    hire_period_end: str | None = None

    # Free-form only
    lines: list[InvoiceLineInput] = []

    @model_validator(mode="after")
    def validate_type_specific_fields(self) -> "InvoiceCreate":
        if self.invoice_type == "hire":
            if self.fixture_id is None:
                raise ValueError("fixture_id is required for a hire invoice")
            if self.vessel_id is None:
                raise ValueError("vessel_id is required for a hire invoice")
            if not self.hire_period_start or not self.hire_period_end:
                raise ValueError("hire_period_start and hire_period_end are required for a hire invoice")
        elif self.invoice_type in ("freight", "demurrage"):
            if self.voyage_id is None:
                raise ValueError(f"voyage_id is required for a {self.invoice_type} invoice")
        elif self.invoice_type == "free_form":
            if self.vessel_id is None:
                raise ValueError("vessel_id is required for a free-form invoice")
            if not self.subject:
                raise ValueError("subject is required for a free-form invoice")
            if not self.counterparty:
                raise ValueError("counterparty is required for a free-form invoice")
            if not self.currency:
                raise ValueError("currency is required for a free-form invoice")
            if self.vat_applicable and (self.vat_treatment is None or self.vat_rate_percent is None):
                raise ValueError("vat_treatment and vat_rate_percent are required when VAT is applicable")
        return self


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str | None
    invoice_type: InvoiceType
    status: InvoiceStatus

    date_of_issue: str
    due_date: str | None
    currency: Currency

    vat_applicable: bool
    vat_treatment: str | None
    vat_rate_percent: float | None
    vat_amount: float

    counterparty: str
    subject: str | None

    fixture_id: int | None
    voyage_id: int | None
    vessel_id: int
    claim_id: int | None
    payment_id: int | None

    hire_period_start: str | None
    hire_period_end: str | None

    total_amount_due: float
    total_amount_due_rub: float | None

    lines: list[InvoiceLineRead] = []
