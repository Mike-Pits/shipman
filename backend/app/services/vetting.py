from datetime import date

from sqlalchemy.orm import Session

from app.models.vetting_inspection import VettingInspection


def current_vetting_status(db: Session, vessel_id: int) -> tuple[VettingInspection, str] | None:
    """FR-22: current status = the most recent inspection by inspection_date.

    FR-23: an approved inspection past its expiry date is treated as expired for
    display purposes, even though the stored record still (correctly, historically)
    says "approved" — it's the expiry that lapsed, not the inspection outcome, so
    the stored record is never mutated here.

    Returns (inspection, effective_status) or None if the vessel has no inspections.
    """
    latest = (
        db.query(VettingInspection)
        .filter(VettingInspection.vessel_id == vessel_id)
        .order_by(VettingInspection.inspection_date.desc())
        .first()
    )
    if latest is None:
        return None

    effective_status = latest.status
    if effective_status == "approved" and latest.expiry_date < date.today().isoformat():
        effective_status = "expired"
    return latest, effective_status


def is_vetting_unfixable(db: Session, vessel_id: int) -> bool:
    result = current_vetting_status(db, vessel_id)
    return result is not None and result[1] in ("expired", "failed")
