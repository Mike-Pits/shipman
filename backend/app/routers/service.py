from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import backup
from app.services.data_export import all_tables_workbook
from app.services.excel_export import XLSX_MEDIA_TYPE

router = APIRouter(prefix="/service", tags=["service"])

RESTORE_CONFIRMATION = "RESTORE"
MAX_IMPORT_BYTES = 500 * 1024 * 1024


class SettingsUpdate(BaseModel):
    backup_dir: str | None = None
    auto_backup_enabled: bool = True
    keep_daily: int = Field(default=14, ge=1, le=365)
    keep_monthly: int = Field(default=12, ge=0, le=120)


class RestoreRequest(BaseModel):
    confirm: str


def _engine(db: Session):
    return db.get_bind()


@router.get("/status")
def get_status(db: Session = Depends(get_db)):
    return backup.status(_engine(db))


@router.put("/settings")
def update_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["backup_dir"] = (data["backup_dir"] or "").strip() or None
    backup.save_settings(_engine(db), data)
    return backup.status(_engine(db))


@router.get("/backups")
def list_backups(db: Session = Depends(get_db)):
    return backup.list_backups(_engine(db))


@router.post("/backups", status_code=201)
def create_backup(db: Session = Depends(get_db)):
    manifest = backup.create_backup(_engine(db), "manual")
    backup.prune(_engine(db))
    return manifest


@router.post("/backups/import", status_code=201)
async def import_backup(request: Request, filename: str | None = Query(default=None), db: Session = Depends(get_db)):
    data = await request.body()
    if len(data) > MAX_IMPORT_BYTES:
        raise HTTPException(status_code=413, detail="File is too large")
    return backup.import_backup(_engine(db), data, filename)


@router.get("/backups/{name}/download")
def download_backup(name: str, db: Session = Depends(get_db)):
    path = backup.backup_file(_engine(db), name)
    return FileResponse(path, media_type="application/octet-stream", filename=name)


@router.delete("/backups/{name}", status_code=204)
def delete_backup(name: str, db: Session = Depends(get_db)):
    backup.delete_backup(_engine(db), name)
    return Response(status_code=204)


@router.post("/backups/{name}/restore")
def restore_backup(name: str, payload: RestoreRequest, db: Session = Depends(get_db)):
    if payload.confirm != RESTORE_CONFIRMATION:
        raise HTTPException(status_code=422, detail=f'Type "{RESTORE_CONFIRMATION}" to confirm the restore')
    return backup.restore_backup(_engine(db), name)


@router.post("/compact")
def compact_database(db: Session = Depends(get_db)):
    return backup.compact(_engine(db))


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    return backup.health_check(_engine(db))


@router.get("/export")
def export_workbook(db: Session = Depends(get_db)):
    data = all_tables_workbook(_engine(db))
    filename = f"shipman-export-{datetime.now():%Y%m%d-%H%M%S}.xlsx"
    return Response(
        content=data,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
