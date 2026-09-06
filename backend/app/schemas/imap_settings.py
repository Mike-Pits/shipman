from pydantic import BaseModel, ConfigDict

from app.schemas.daily_report import DailyReportRead


class ImapSettingsUpdate(BaseModel):
    folder: str


class ImapPollRequest(BaseModel):
    vessel_id: int
    confirm_vessel_change: bool = False


class ImapSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    folder: str


class ImapPollResult(BaseModel):
    ingested: list[DailyReportRead]
    skipped_duplicates: list[str]
    errors: list[dict]


class ImapFolderMappingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    folder: str
    vessel_id: int
