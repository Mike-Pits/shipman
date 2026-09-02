from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.audit_log import AuditLogEntry
from app.schemas.audit_log import AuditLogEntryRead

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("", response_model=list[AuditLogEntryRead])
def list_audit_log(table_name: str | None = None, db: Session = Depends(get_db)):
    query = db.query(AuditLogEntry)
    if table_name is not None:
        query = query.filter(AuditLogEntry.table_name == table_name)
    return query.order_by(AuditLogEntry.id).all()
