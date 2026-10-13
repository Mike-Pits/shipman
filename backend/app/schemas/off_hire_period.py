from pydantic import BaseModel, ConfigDict, computed_field, field_validator

from app.services.flexible_datetime import UnparseableDateTime, days_between, parse_flexible_datetime

_CANONICAL_FORMAT = "%Y-%m-%d %H:%M:%S"


class OffHirePeriodCreate(BaseModel):
    start_datetime: str
    end_datetime: str
    reason: str
    override_deduction: float | None = None

    @field_validator("start_datetime", "end_datetime")
    @classmethod
    def normalize_datetime(cls, value: str) -> str:
        """Accepts YYYY-MM-DD[ HH:MM[:SS]] (and 24:00 for end of day) and stores it in
        the canonical full format, so every consumer of a stored period can rely on it."""
        try:
            return parse_flexible_datetime(value).strftime(_CANONICAL_FORMAT)
        except UnparseableDateTime as exc:
            raise ValueError(f"{exc} — use YYYY-MM-DD HH:MM") from exc


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
        start = parse_flexible_datetime(self.start_datetime)
        end = parse_flexible_datetime(self.end_datetime)
        return days_between(start, end)

    @computed_field
    @property
    def effective_deduction(self) -> float:
        return self.override_deduction if self.override_deduction is not None else self.calculated_deduction
