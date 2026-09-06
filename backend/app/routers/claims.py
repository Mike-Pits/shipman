from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.claim import Claim
from app.models.payment import Payment
from app.schemas.claim import ClaimCreate, ClaimRead, ClaimSettle, ClaimStatus, ClaimStatusUpdate

router = APIRouter(prefix="/claims", tags=["claims"])


def _get_claim_or_404(claim_id: int, db: Session) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="Claim not found")
    return claim


@router.post("", response_model=ClaimRead, status_code=201)
def create_claim(payload: ClaimCreate, db: Session = Depends(get_db)):
    claim = Claim(**payload.model_dump(), status="open")
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


@router.get("", response_model=list[ClaimRead])
def list_claims(status: ClaimStatus | None = None, db: Session = Depends(get_db)):
    query = db.query(Claim)
    if status is not None:
        query = query.filter(Claim.status == status)
    return query.all()


@router.get("/{claim_id}", response_model=ClaimRead)
def get_claim(claim_id: int, db: Session = Depends(get_db)):
    return _get_claim_or_404(claim_id, db)


@router.put("/{claim_id}", response_model=ClaimRead)
def update_claim(claim_id: int, payload: ClaimCreate, db: Session = Depends(get_db)):
    claim = _get_claim_or_404(claim_id, db)
    for field, value in payload.model_dump().items():
        setattr(claim, field, value)
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/{claim_id}/status", response_model=ClaimRead)
def update_claim_status(claim_id: int, payload: ClaimStatusUpdate, db: Session = Depends(get_db)):
    claim = _get_claim_or_404(claim_id, db)
    claim.status = payload.status
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/{claim_id}/settle", response_model=ClaimRead)
def settle_claim(claim_id: int, payload: ClaimSettle, db: Session = Depends(get_db)):
    claim = _get_claim_or_404(claim_id, db)
    if payload.payment_id is not None and db.get(Payment, payload.payment_id) is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    claim.status = "settled"
    claim.amount_settled = payload.amount_settled
    claim.settled_payment_id = payload.payment_id
    claim.date_resolved = date.today().isoformat()
    db.commit()
    db.refresh(claim)
    return claim
