from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.fuel_grades import normalize_grade

FuelConsumptionMode = Literal["laden", "ballast", "idle_anchor", "discharging"]


class FuelConsumptionProfileCreate(BaseModel):
    mode: FuelConsumptionMode
    ifo_mt_per_day: float
    mgo_mt_per_day: float


class FuelConsumptionProfileRead(FuelConsumptionProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class SeaConsumption(BaseModel):
    """Calculator sea-passage row; the first row of each mode supplies the passage speed."""

    model_config = ConfigDict(from_attributes=True)

    mode: Literal["laden", "ballast", "eco"]
    grade: str = Field(min_length=1)
    speed_kt: float = Field(gt=0, le=99)
    consumption_mt_per_day: float = Field(default=0, ge=0)

    @field_validator("grade")
    @classmethod
    def _canonical_grade(cls, value: str) -> str:
        return normalize_grade(value)


class PortConsumption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kind: Literal["port_load", "port_discharge", "inerting"]
    grade: str = Field(min_length=1)
    consumption_mt_per_day: float = Field(default=0, ge=0)

    @field_validator("grade")
    @classmethod
    def _canonical_grade(cls, value: str) -> str:
        return normalize_grade(value)


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
    # None on update = leave the calculator profile untouched (older clients never send it).
    sea_consumption: list[SeaConsumption] | None = None
    port_consumption: list[PortConsumption] | None = None


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
    sea_consumption: list[SeaConsumption] = []
    port_consumption: list[PortConsumption] = []
