from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import Currency

FixtureType = Literal["voyage_charter", "time_charter_out", "coa"]
VatTreatment = Literal["inclusive", "exclusive"]


class FixtureBrokerCreate(BaseModel):
    broker_name: str
    commission_percentage: float


class FixtureBrokerRead(FixtureBrokerCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class FixtureCreate(BaseModel):
    fixture_type: FixtureType
    charterer: str
    contract_currency: Currency

    vat_applicable: bool = False
    vat_treatment: VatTreatment | None = None
    vat_rate_percent: float | None = None

    date_concluded: str | None = None
    charter_party_ref: str | None = Field(default=None, max_length=15)
    charter_party_type: str | None = None

    # Voyage Charter fields (FR-07)
    freight_rate: float | None = None
    freight_rate_basis: Literal["per_tonne", "lump_sum"] | None = None
    laycan_start: str | None = None
    laycan_end: str | None = None
    load_port: str | None = None
    discharge_port: str | None = None
    cargo_grade: str | None = None
    demurrage_rate: float | None = None
    despatch_rate: float | None = None
    laytime_terms: str | None = None

    # Time Charter Out fields (FR-08)
    hire_rate: float | None = None
    hire_rate_basis: Literal["daily", "monthly"] | None = None
    charter_period_from: str | None = None
    charter_period_to: str | None = None
    delivery_port: str | None = None
    delivery_rob_ifo_mt: float | None = None
    delivery_rob_mgo_mt: float | None = None
    redelivery_port: str | None = None
    redelivery_rob_ifo_mt: float | None = None
    redelivery_rob_mgo_mt: float | None = None
    redelivery_conditions: str | None = None
    hire_payment_basis: Literal["advance", "arrears", "days_after_invoice"] | None = None
    hire_payment_frequency_days: int | None = None
    hire_payment_days_after_invoice: int | None = None

    # COA fields (FR-09)
    contract_period_from: str | None = None
    contract_period_to: str | None = None
    total_contracted_quantity: float | None = None
    number_of_lifts: int | None = None
    rate_per_tonne: float | None = None
    min_cargo_quantity_per_lift: float | None = None
    max_cargo_quantity_per_lift: float | None = None

    brokers: list[FixtureBrokerCreate] = []

    @field_validator("brokers")
    @classmethod
    def max_three_brokers(cls, brokers: list[FixtureBrokerCreate]) -> list[FixtureBrokerCreate]:
        if len(brokers) > 3:
            raise ValueError("A fixture supports at most 3 brokers")
        return brokers

    @model_validator(mode="after")
    def validate_vat_fields(self) -> "FixtureCreate":
        if self.vat_applicable:
            if self.vat_treatment is None:
                raise ValueError("vat_treatment is required when VAT is applicable")
            if self.vat_rate_percent is None:
                raise ValueError("vat_rate_percent is required when VAT is applicable")
        return self


class FixtureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    fixture_type: FixtureType
    charterer: str
    contract_currency: Currency

    vat_applicable: bool = False
    vat_treatment: str | None = None
    vat_rate_percent: float | None = None

    date_concluded: str | None = None
    charter_party_ref: str | None = None
    charter_party_type: str | None = None

    freight_rate: float | None = None
    freight_rate_basis: str | None = None
    laycan_start: str | None = None
    laycan_end: str | None = None
    load_port: str | None = None
    discharge_port: str | None = None
    cargo_grade: str | None = None
    demurrage_rate: float | None = None
    despatch_rate: float | None = None
    laytime_terms: str | None = None

    hire_rate: float | None = None
    hire_rate_basis: str | None = None
    charter_period_from: str | None = None
    charter_period_to: str | None = None
    delivery_port: str | None = None
    delivery_rob_ifo_mt: float | None = None
    delivery_rob_mgo_mt: float | None = None
    redelivery_port: str | None = None
    redelivery_rob_ifo_mt: float | None = None
    redelivery_rob_mgo_mt: float | None = None
    redelivery_conditions: str | None = None
    hire_payment_basis: str | None = None
    hire_payment_frequency_days: int | None = None
    hire_payment_days_after_invoice: int | None = None

    contract_period_from: str | None = None
    contract_period_to: str | None = None
    total_contracted_quantity: float | None = None
    number_of_lifts: int | None = None
    rate_per_tonne: float | None = None
    min_cargo_quantity_per_lift: float | None = None
    max_cargo_quantity_per_lift: float | None = None

    brokers: list[FixtureBrokerRead] = []
