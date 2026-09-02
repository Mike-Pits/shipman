from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class OffHirePeriodCreate(BaseModel):
    start_datetime: str
    end_datetime: str
    reason: str
    override_deduction: float | None = None


class OffHirePeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voyage_id: int
    start_datetime: str
    end_datetime: str
    reason: str
    calculated_deduction: float
    override_deduction: float | None

    @computed_field
    @property
    def duration_days(self) -> float:
        start = datetime.strptime(self.start_datetime, "%Y-%m-%d %H:%M:%S")
        end = datetime.strptime(self.end_datetime, "%Y-%m-%d %H:%M:%S")
        return round((end - start).total_seconds() / 86400, 4)

    @computed_field
    @property
    def effective_deduction(self) -> float:
        return self.override_deduction if self.override_deduction is not None else self.calculated_deduction
