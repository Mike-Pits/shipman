from pydantic import BaseModel, ConfigDict


class DailyReportCreate(BaseModel):
    vessel_id: int
    voyage_id: int | None = None
    raw_text: str


class DailyReportUpdate(BaseModel):
    raw_text: str
    override: bool = False


class DailyReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vessel_id: int
    voyage_id: int | None
    report_datetime: str
    raw_text: str
    fields: dict[str, str]
    approved: bool
