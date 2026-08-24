from pydantic import BaseModel, ConfigDict


class VoyageCreate(BaseModel):
    fixture_id: int
    vessel_id: int
    voyage_number: str
    load_port: str
    discharge_port: str
    start_date: str
    end_date: str | None = None
    cargo_grade: str
    cargo_quantity_mt: float
    laden: bool
    ice_notes: str | None = None


class VoyageRead(VoyageCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
