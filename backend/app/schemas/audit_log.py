from pydantic import BaseModel, ConfigDict


class AuditLogEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    table_name: str
    record_id: int | None
    action: str
    old_values: str | None
    new_values: str | None
    user: str
    timestamp: str
