from typing import Literal

from pydantic import BaseModel, ConfigDict

VettingStatus = Literal["approved", "pending", "expired", "failed"]


class VettingInspectionCreate(BaseModel):
    inspection_date: str
    inspecting_body: str
    inspection_type: str
    expiry_date: str
    status: VettingStatus
    observations: str | None = None


class VettingInspectionRead(VettingInspectionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vessel_id: int


class VettingStatusRead(BaseModel):
    status: VettingStatus | None
    inspecting_body: str | None = None
    expiry_date: str | None = None
