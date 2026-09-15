from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

VoyagePurpose = Literal["employment", "ballast_passage", "drydock_repair"]


class VoyageCreate(BaseModel):
    voyage_purpose: VoyagePurpose = "employment"
    fixture_id: int | None = None
    vessel_id: int
    voyage_number: str
    load_port: str
    discharge_port: str | None = None
    start_date: str
    end_date: str | None = None
    cargo_grade: str | None = None
    cargo_quantity_mt: float | None = None
    laden: bool = False
    ice_notes: str | None = None

    @model_validator(mode="after")
    def validate_purpose_specific_fields(self) -> "VoyageCreate":
        if self.voyage_purpose == "employment":
            if self.fixture_id is None:
                raise ValueError("fixture_id is required for an employment voyage")
            if not self.discharge_port:
                raise ValueError("discharge_port is required for an employment voyage")
            if not self.cargo_grade:
                raise ValueError("cargo_grade is required for an employment voyage")
            if self.cargo_quantity_mt is None:
                raise ValueError("cargo_quantity_mt is required for an employment voyage")
        else:
            if self.fixture_id is not None:
                raise ValueError(f"fixture_id must not be set for a {self.voyage_purpose} voyage")
            if self.voyage_purpose == "ballast_passage" and not self.discharge_port:
                raise ValueError("discharge_port (destination) is required for a ballast passage")
            self.cargo_grade = None
            self.cargo_quantity_mt = None
            self.laden = False
        return self


class VoyageRead(VoyageCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warnings: list[str] = []
