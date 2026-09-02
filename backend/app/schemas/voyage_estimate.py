from typing import Literal

from pydantic import BaseModel, ConfigDict, computed_field

EstimateStatus = Literal["draft", "under_negotiation", "fixed", "declined"]
RateBasis = Literal["per_tonne", "lump_sum"]


class VoyageEstimateCreate(BaseModel):
    vessel_id: int | None = None
    load_port: str
    discharge_port: str
    laycan_start: str
    laycan_end: str
    cargo_grade: str
    estimated_cargo_quantity_mt: float
    estimated_rate: float
    estimated_rate_basis: RateBasis
    currency: str
    estimated_bunker_consumption_mt: float
    estimated_bunker_cost: float
    estimated_port_costs: float
    estimated_duration_days: float


class VoyageEstimateStatusUpdate(BaseModel):
    status: Literal["under_negotiation", "declined"]


class VoyageEstimateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vessel_id: int | None
    load_port: str
    discharge_port: str
    laycan_start: str
    laycan_end: str
    cargo_grade: str
    estimated_cargo_quantity_mt: float
    estimated_rate: float
    estimated_rate_basis: RateBasis
    currency: str
    estimated_bunker_consumption_mt: float
    estimated_bunker_cost: float
    estimated_port_costs: float
    estimated_duration_days: float
    status: EstimateStatus
    fixture_id: int | None
    warnings: list[str] = []

    @computed_field
    @property
    def estimated_revenue(self) -> float:
        if self.estimated_rate_basis == "per_tonne":
            return round(self.estimated_rate * self.estimated_cargo_quantity_mt, 2)
        return round(self.estimated_rate, 2)

    @computed_field
    @property
    def estimated_costs(self) -> float:
        return round(self.estimated_bunker_cost + self.estimated_port_costs, 2)

    @computed_field
    @property
    def estimated_net_result(self) -> float:
        return round(self.estimated_revenue - self.estimated_costs, 2)

    @computed_field
    @property
    def estimated_tce_per_day(self) -> float:
        return round(self.estimated_net_result / self.estimated_duration_days, 2)
