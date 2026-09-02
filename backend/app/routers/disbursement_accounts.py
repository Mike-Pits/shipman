from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.disbursement_account import DisbursementAccount, DisbursementAccountLine
from app.models.voyage import Voyage
from app.schemas.disbursement_account import (
    DisbursementAccountCreate,
    DisbursementAccountRead,
    FdaLinesCreate,
)

router = APIRouter(prefix="/disbursement-accounts", tags=["disbursement-accounts"])


@router.post("", response_model=DisbursementAccountRead, status_code=201)
def create_disbursement_account(payload: DisbursementAccountCreate, db: Session = Depends(get_db)):
    if db.get(Voyage, payload.voyage_id) is None:
        raise HTTPException(status_code=404, detail="Voyage not found")

    da = DisbursementAccount(**payload.model_dump(), status="pda_only")
    db.add(da)
    db.commit()
    db.refresh(da)
    return da


@router.get("", response_model=list[DisbursementAccountRead])
def list_disbursement_accounts(db: Session = Depends(get_db)):
    return db.query(DisbursementAccount).all()


@router.get("/{da_id}", response_model=DisbursementAccountRead)
def get_disbursement_account(da_id: int, db: Session = Depends(get_db)):
    da = db.get(DisbursementAccount, da_id)
    if da is None:
        raise HTTPException(status_code=404, detail="Disbursement account not found")
    return da


def _get_da_or_404(da_id: int, db: Session) -> DisbursementAccount:
    da = db.get(DisbursementAccount, da_id)
    if da is None:
        raise HTTPException(status_code=404, detail="Disbursement account not found")
    return da


@router.post("/{da_id}/fda-lines", response_model=DisbursementAccountRead)
def add_fda_lines(da_id: int, payload: FdaLinesCreate, db: Session = Depends(get_db)):
    da = _get_da_or_404(da_id, db)
    da.lines.extend(DisbursementAccountLine(**line.model_dump()) for line in payload.lines)
    if da.status == "pda_only":
        da.status = "fda_pending"
    db.commit()
    db.refresh(da)
    return da


@router.post("/{da_id}/reconcile", response_model=DisbursementAccountRead)
def reconcile_disbursement_account(da_id: int, db: Session = Depends(get_db)):
    da = _get_da_or_404(da_id, db)
    if not da.lines:
        raise HTTPException(
            status_code=409, detail="Cannot reconcile a disbursement account with no FDA lines"
        )
    da.status = "reconciled"
    db.commit()
    db.refresh(da)
    return da


@router.post("/{da_id}/dispute", response_model=DisbursementAccountRead)
def dispute_disbursement_account(da_id: int, db: Session = Depends(get_db)):
    da = _get_da_or_404(da_id, db)
    da.status = "disputed"
    db.commit()
    db.refresh(da)
    return da
