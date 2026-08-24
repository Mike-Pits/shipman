from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.daily_report import DailyReport
from app.models.vessel import Vessel
from app.schemas.daily_report import DailyReportCreate, DailyReportRead, DailyReportUpdate
from app.services.disp01_parser import Disp01ParseError, parse_disp01

router = APIRouter(prefix="/daily-reports", tags=["daily-reports"])


def _parse_and_validate(raw_text: str) -> tuple[dict, datetime]:
    try:
        parsed = parse_disp01(raw_text)
    except Disp01ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if parsed["report_datetime"] is None:
        raise HTTPException(
            status_code=422, detail="Report is missing code 1 (date/time) — cannot be saved"
        )
    return parsed["fields"], parsed["report_datetime"]


def _check_no_duplicate(db: Session, vessel_id: int, report_date_str: str, exclude_id: int | None = None):
    query = db.query(DailyReport).filter(
        DailyReport.vessel_id == vessel_id,
        func.substr(DailyReport.report_datetime, 1, 10) == report_date_str,
    )
    if exclude_id is not None:
        query = query.filter(DailyReport.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=409, detail="A report already exists for this vessel and date"
        )


@router.post("", response_model=DailyReportRead, status_code=201)
def create_daily_report(payload: DailyReportCreate, db: Session = Depends(get_db)):
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    fields, report_datetime = _parse_and_validate(payload.raw_text)
    report_date_str = report_datetime.strftime("%Y-%m-%d")
    _check_no_duplicate(db, payload.vessel_id, report_date_str)

    report = DailyReport(
        vessel_id=payload.vessel_id,
        voyage_id=payload.voyage_id,
        report_datetime=report_datetime.strftime("%Y-%m-%d %H:%M:%S"),
        raw_text=payload.raw_text,
        fields=fields,
        approved=False,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/{report_id}", response_model=DailyReportRead)
def get_daily_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(DailyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Daily report not found")
    return report


@router.put("/{report_id}", response_model=DailyReportRead)
def update_daily_report(report_id: int, payload: DailyReportUpdate, db: Session = Depends(get_db)):
    report = db.get(DailyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Daily report not found")
    if report.approved and not payload.override:
        raise HTTPException(
            status_code=409,
            detail="Report is approved and cannot be edited without override",
        )

    fields, report_datetime = _parse_and_validate(payload.raw_text)
    report_date_str = report_datetime.strftime("%Y-%m-%d")
    _check_no_duplicate(db, report.vessel_id, report_date_str, exclude_id=report_id)

    report.raw_text = payload.raw_text
    report.fields = fields
    report.report_datetime = report_datetime.strftime("%Y-%m-%d %H:%M:%S")
    db.commit()
    db.refresh(report)
    return report


@router.post("/{report_id}/approve", response_model=DailyReportRead)
def approve_daily_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(DailyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Daily report not found")
    report.approved = True
    db.commit()
    db.refresh(report)
    return report
