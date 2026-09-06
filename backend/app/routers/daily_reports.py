from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import config
from app.database import get_db
from app.dependencies import get_imap_fetcher
from app.models.bunker_replenishment import BunkerReplenishment
from app.models.daily_report import DailyReport
from app.models.imap_settings import ImapFolderVesselMapping, ImapSettings
from app.models.vessel import FuelConsumptionProfile, Vessel
from app.models.voyage import Voyage
from app.schemas.daily_report import DailyReportCreate, DailyReportRead, DailyReportUpdate
from app.schemas.imap_settings import (
    ImapFolderMappingRead,
    ImapPollRequest,
    ImapPollResult,
    ImapSettingsRead,
    ImapSettingsUpdate,
)
from app.services.disp01_parser import Disp01ParseError, parse_disp01, parse_rob

router = APIRouter(prefix="/daily-reports", tags=["daily-reports"])

FUEL_WARNING_THRESHOLD_MULTIPLIER = 1.2


def _has_recent_replenishment(db: Session, vessel_id: int, grade: str, window_start: datetime, window_end: datetime) -> bool:
    replenishments = (
        db.query(BunkerReplenishment).filter(BunkerReplenishment.vessel_id == vessel_id).all()
    )
    for replenishment in replenishments:
        try:
            replenishment_dt = datetime.strptime(
                replenishment.replenishment_datetime, "%Y-%m-%d %H:%M:%S"
            )
        except ValueError:
            continue
        if window_start <= replenishment_dt <= window_end:
            if any(line.fuel_grade.upper() == grade for line in replenishment.lines):
                return True
    return False


def _compute_fuel_warnings(report: DailyReport, db: Session) -> list[str]:
    """FR-19 / FR-25: soft warning when consumption exceeds 20% of the vessel's normal
    daily rate for its current mode, unless a matching bunker replenishment was recorded
    in the prior 24 hours."""
    if report.voyage_id is None:
        return []
    voyage = db.get(Voyage, report.voyage_id)
    if voyage is None:
        return []
    mode = "laden" if voyage.laden else "ballast"

    profile = (
        db.query(FuelConsumptionProfile)
        .filter(FuelConsumptionProfile.vessel_id == report.vessel_id, FuelConsumptionProfile.mode == mode)
        .first()
    )
    if profile is None:
        return []

    previous = (
        db.query(DailyReport)
        .filter(
            DailyReport.vessel_id == report.vessel_id,
            DailyReport.report_datetime < report.report_datetime,
            DailyReport.id != report.id,
        )
        .order_by(DailyReport.report_datetime.desc())
        .first()
    )
    if previous is None:
        return []

    prev_ifo, prev_mgo = parse_rob(previous.fields.get("31"))
    curr_ifo, curr_mgo = parse_rob(report.fields.get("31"))
    current_dt = datetime.strptime(report.report_datetime, "%Y-%m-%d %H:%M:%S")
    window_start = current_dt - timedelta(hours=24)

    warnings: list[str] = []
    for grade, prev_val, curr_val, normal_rate in (
        ("IFO", prev_ifo, curr_ifo, profile.ifo_mt_per_day),
        ("MGO", prev_mgo, curr_mgo, profile.mgo_mt_per_day),
    ):
        if prev_val is None or curr_val is None:
            continue
        consumption = prev_val - curr_val
        if consumption <= normal_rate * FUEL_WARNING_THRESHOLD_MULTIPLIER:
            continue
        if _has_recent_replenishment(db, report.vessel_id, grade, window_start, current_dt):
            continue
        warnings.append(
            f"{grade} consumption of {consumption:.2f} MT exceeds the normal {mode} rate of "
            f"{normal_rate:.2f} MT/day with no matching bunker replenishment in the last 24h"
        )
    return warnings


def _to_read(report: DailyReport, db: Session) -> DailyReportRead:
    base = DailyReportRead.model_validate(report)
    return base.model_copy(update={"warnings": _compute_fuel_warnings(report, db)})


def _parse_and_validate(raw_text: str, reference_date=None) -> tuple[dict, datetime]:
    try:
        parsed = parse_disp01(raw_text, reference_date=reference_date)
    except Disp01ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if parsed["report_datetime"] is None:
        raise HTTPException(
            status_code=422, detail="Report is missing code 1 (date/time) — cannot be saved"
        )
    return parsed["fields"], parsed["report_datetime"]


def _check_no_duplicate(db: Session, vessel_id: int, report_datetime_str: str, exclude_id: int | None = None):
    """A vessel can legitimately send more than one DISP-01 report on the same
    calendar day (e.g. multiple updates during busy port operations — confirmed
    against real historical data), so uniqueness is keyed on the exact reported
    datetime, not just the date."""
    query = db.query(DailyReport).filter(
        DailyReport.vessel_id == vessel_id,
        DailyReport.report_datetime == report_datetime_str,
    )
    if exclude_id is not None:
        query = query.filter(DailyReport.id != exclude_id)
    if query.first() is not None:
        raise HTTPException(
            status_code=409, detail="A report already exists for this vessel at this exact date/time"
        )


def _ingest_report(
    db: Session,
    vessel_id: int,
    raw_text: str,
    voyage_id: int | None = None,
    source_message_id: str | None = None,
    reference_date=None,
) -> DailyReport:
    """Shared by manual entry (FR-15) and IMAP retrieval (FR-16) — both channels
    go through the same parser, date rules, and duplicate check.

    reference_date anchors year-inference for a native (non-explicit-year) date
    line — see disp01_parser.parse_report_datetime. IMAP retrieval passes the
    source email's own Date header here so archived/historical messages resolve
    to their real year instead of being interpreted relative to today."""
    fields, report_datetime = _parse_and_validate(raw_text, reference_date=reference_date)
    report_datetime_str = report_datetime.strftime("%Y-%m-%d %H:%M:%S")
    _check_no_duplicate(db, vessel_id, report_datetime_str)

    report = DailyReport(
        vessel_id=vessel_id,
        voyage_id=voyage_id,
        report_datetime=report_datetime_str,
        raw_text=raw_text,
        fields=fields,
        approved=False,
        source_message_id=source_message_id,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.post("", response_model=DailyReportRead, status_code=201)
def create_daily_report(payload: DailyReportCreate, db: Session = Depends(get_db)):
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    report = _ingest_report(db, payload.vessel_id, payload.raw_text, voyage_id=payload.voyage_id)
    return _to_read(report, db)


@router.get("", response_model=list[DailyReportRead])
def list_daily_reports(vessel_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(DailyReport)
    if vessel_id is not None:
        query = query.filter(DailyReport.vessel_id == vessel_id)
    reports = query.order_by(DailyReport.report_datetime.desc()).all()
    return [_to_read(r, db) for r in reports]


def _get_or_create_imap_settings(db: Session) -> ImapSettings:
    settings = db.get(ImapSettings, 1)
    if settings is None:
        settings = ImapSettings(id=1, folder=config.IMAP_DEFAULT_FOLDER)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


# NOTE: these two literal-path routes (and poll-imap below) must be registered
# before the "/{report_id}" routes further down — FastAPI/Starlette match routes
# in registration order, and "/imap-settings" would otherwise be swallowed by
# "/{report_id}" (report_id's int type is only checked *after* the route matches,
# so it doesn't stop the match — it just 422s trying to parse "imap-settings" as
# an int). Learned this the hard way; see the git history on this file if it
# regresses.
@router.get("/imap-settings", response_model=ImapSettingsRead)
def get_imap_settings(db: Session = Depends(get_db)):
    return _get_or_create_imap_settings(db)


@router.put("/imap-settings", response_model=ImapSettingsRead)
def update_imap_settings(payload: ImapSettingsUpdate, db: Session = Depends(get_db)):
    """FR-16: the mailbox folder is an operator-chosen runtime setting, not fixed
    by the SHIPMAN_MAILBOX_FOLDER env var (which only supplies the initial default)."""
    settings = _get_or_create_imap_settings(db)
    settings.folder = payload.folder
    db.commit()
    db.refresh(settings)
    return settings


@router.get("/imap-folder-mapping/{folder}", response_model=ImapFolderMappingRead)
def get_imap_folder_mapping(folder: str, db: Session = Depends(get_db)):
    """Lets the operator check which vessel a folder is registered to *before*
    polling — the reactive 409 in poll_imap is the hard safeguard, this is the
    proactive check (see ADR-0005)."""
    mapping = db.query(ImapFolderVesselMapping).filter_by(folder=folder).first()
    if mapping is None:
        raise HTTPException(status_code=404, detail="This folder has never been polled")
    return mapping


@router.post("/poll-imap", response_model=ImapPollResult)
def poll_imap(
    payload: ImapPollRequest,
    db: Session = Depends(get_db),
    imap_fetcher=Depends(get_imap_fetcher),
):
    """FR-16: retrieve every message currently in the configured folder, ingest
    the ones not already seen (by IMAP Message-ID), and report parse failures per
    message instead of aborting the whole batch. Source emails are never touched —
    see app/services/imap_fetcher.py for how that's guaranteed."""
    if db.get(Vessel, payload.vessel_id) is None:
        raise HTTPException(status_code=404, detail="Vessel not found")

    folder = _get_or_create_imap_settings(db).folder

    mapping = db.query(ImapFolderVesselMapping).filter_by(folder=folder).first()
    if mapping is not None and mapping.vessel_id != payload.vessel_id and not payload.confirm_vessel_change:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Folder '{folder}' was last polled for vessel_id={mapping.vessel_id}, "
                f"not vessel_id={payload.vessel_id}. If this vessel selection is correct, "
                "retry with confirm_vessel_change=true."
            ),
        )

    try:
        messages = imap_fetcher(folder)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"IMAP fetch failed: {exc}") from exc

    if mapping is None:
        db.add(ImapFolderVesselMapping(folder=folder, vessel_id=payload.vessel_id))
    else:
        mapping.vessel_id = payload.vessel_id
    db.commit()

    already_ingested = {
        row[0]
        for row in db.query(DailyReport.source_message_id).filter(
            DailyReport.source_message_id.isnot(None)
        )
    }

    ingested: list[DailyReport] = []
    skipped_duplicates: list[str] = []
    errors: list[dict] = []

    for message_id, body, email_date in messages:
        if message_id in already_ingested:
            skipped_duplicates.append(message_id)
            continue
        try:
            report = _ingest_report(
                db,
                payload.vessel_id,
                body,
                source_message_id=message_id,
                reference_date=email_date.date() if email_date else None,
            )
        except HTTPException as exc:
            errors.append({"message_id": message_id, "detail": exc.detail})
            continue
        ingested.append(report)
        already_ingested.add(message_id)

    return ImapPollResult(
        ingested=[_to_read(r, db) for r in ingested],
        skipped_duplicates=skipped_duplicates,
        errors=errors,
    )


@router.get("/{report_id}", response_model=DailyReportRead)
def get_daily_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(DailyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Daily report not found")
    return _to_read(report, db)


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

    target_vessel_id = report.vessel_id
    if payload.vessel_id is not None and payload.vessel_id != report.vessel_id:
        if db.get(Vessel, payload.vessel_id) is None:
            raise HTTPException(status_code=404, detail="Vessel not found")
        target_vessel_id = payload.vessel_id

    fields, report_datetime = _parse_and_validate(payload.raw_text)
    report_datetime_str = report_datetime.strftime("%Y-%m-%d %H:%M:%S")
    _check_no_duplicate(db, target_vessel_id, report_datetime_str, exclude_id=report_id)

    report.raw_text = payload.raw_text
    report.fields = fields
    report.report_datetime = report_datetime_str
    report.vessel_id = target_vessel_id
    db.commit()
    db.refresh(report)
    return _to_read(report, db)


@router.post("/{report_id}/approve", response_model=DailyReportRead)
def approve_daily_report(report_id: int, db: Session = Depends(get_db)):
    report = db.get(DailyReport, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Daily report not found")
    report.approved = True
    db.commit()
    db.refresh(report)
    return _to_read(report, db)
