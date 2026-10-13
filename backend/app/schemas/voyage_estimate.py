from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.common import Currency
from app.services.fuel_grades import normalize_grade

EstimateStatus = Literal["draft", "under_negotiation", "fixed", "declined"]
FreightMode = Literal["per_mt", "lumpsum"]
SeaMode = Literal["laden", "ballast", "eco"]
StopType = Literal["load", "discharge"]
LaytimeUnit = Literal["hours", "days", "mt_per_hour", "mt_per_day"]
LaytimeBasis = Literal["CQD", "WIBON", "WIPON", "FIO", "SHINC", "SHEX"]

MAX_PORT_STOPS = 10
MAX_CARGO_LOTS = 3

NonNegative = Field(default=0, ge=0)


class PortStop(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    port_name: str = Field(min_length=1)
    stop_type: StopType
    distance_nm: float = NonNegative
    cargo_quantity_mt: float = NonNegative
    laytime_value: float = NonNegative
    laytime_unit: LaytimeUnit = "days"
    laytime_basis: LaytimeBasis = "SHINC"
    rate_mt_per_day: float = NonNegative


class CargoLot(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    grade: str = ""
    quantity_mt: float = NonNegative
    freight_rate: float = NonNegative


class FuelPrice(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    grade: str = Field(min_length=1)
    price_per_mt: float = Field(ge=0)

    @field_validator("grade")
    @classmethod
    def _canonical_grade(cls, value: str) -> str:
        return normalize_grade(value)


class CostItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    description: str = ""
    amount: float = Field(default=0, ge=0)


class VoyageEstimateCreate(BaseModel):
    name: str = Field(min_length=1)
    vessel_id: int | None = None
    currency: Currency
    laycan_start: str | None = None
    laycan_end: str | None = None
    freight_mode: FreightMode = "per_mt"
    lumpsum_freight: float = NonNegative
    sea_mode: SeaMode = "laden"
    extra_sea_days: float = NonNegative
    extra_costs: float = NonNegative
    canal_fees: float = NonNegative
    port_charges: float = NonNegative
    agent_fees: float = NonNegative
    bunker_surcharge: float = NonNegative
    demurrage_rate: float = NonNegative
    port_stops: list[PortStop] = Field(min_length=1, max_length=MAX_PORT_STOPS)
    cargo_lots: list[CargoLot] = Field(default_factory=list, max_length=MAX_CARGO_LOTS)
    fuel_prices: list[FuelPrice] = []
    cost_items: list[CostItem] = []

    @model_validator(mode="after")
    def _freight_is_defined(self):
        if self.freight_mode == "per_mt" and not any(
            lot.quantity_mt > 0 and lot.freight_rate > 0 for lot in self.cargo_lots
        ):
            raise ValueError("Per-MT freight needs at least one cargo lot with quantity and rate")
        return self


class VoyageEstimateStatusUpdate(BaseModel):
    status: Literal["under_negotiation", "declined"]


class EstimateResults(BaseModel):
    total_distance_nm: float
    sea_days: float
    port_days: float
    load_days: float
    discharge_days: float
    total_voyage_days: float
    effective_sea_mode: SeaMode
    fuel: dict[str, dict[str, float]]
    total_fuel_cost: float
    freight_revenue: float
    other_costs: float
    extra_items_total: float
    allowed_laytime_days: float
    excess_days: float
    demurrage: float
    total_costs: float
    net_result: float
    tce_per_day: float
    warnings: list[str]


class VoyageEstimateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    vessel_id: int | None
    currency: Currency
    laycan_start: str | None
    laycan_end: str | None
    freight_mode: FreightMode
    lumpsum_freight: float
    sea_mode: SeaMode
    extra_sea_days: float
    extra_costs: float
    canal_fees: float
    port_charges: float
    agent_fees: float
    bunker_surcharge: float
    demurrage_rate: float
    status: EstimateStatus
    fixture_id: int | None
    baseline_net_result: float | None
    baseline_tce_per_day: float | None
    port_stops: list[PortStop]
    cargo_lots: list[CargoLot]
    fuel_prices: list[FuelPrice]
    cost_items: list[CostItem]
    results: EstimateResults | None = None
    warnings: list[str] = []
