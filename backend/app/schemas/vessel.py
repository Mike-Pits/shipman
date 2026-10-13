from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FuelConsumptionMode = Literal["laden", "ballast", "idle_anchor", "discharging"]


class FuelConsumptionProfileCreate(BaseModel):
    mode: FuelConsumptionMode
    ifo_mt_per_day: float
    mgo_mt_per_day: float
    speed_kt: float | None = Field(default=None, gt=0, le=99)


class FuelConsumptionProfileRead(FuelConsumptionProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class VesselCreate(BaseModel):
    name: str
    imo_number: str
    flag: str
    year_built: int
    vessel_type: str
    dwt: float
    loa: float
    beam: float
    draft: float
    cargo_tank_capacity_cbm: float
    ice_class: str
    engine_power_kw: float
    fuel_consumption_profiles: list[FuelConsumptionProfileCreate] = []


class VesselRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    imo_number: str
    flag: str
    year_built: int
    vessel_type: str
    dwt: float
    loa: float
    beam: float
    draft: float
    cargo_tank_capacity_cbm: float
    ice_class: str
    engine_power_kw: float
    fuel_consumption_profiles: list[FuelConsumptionProfileRead] = []

