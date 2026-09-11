from sqlalchemy.orm import Session

from app.models.invoice import Invoice


def next_invoice_number(db: Session, year: int) -> str:
    """One shared sequence across all invoice types, per calendar year. Voided
    invoices keep their number (never reused), so counting every row — regardless
    of status — with this year's prefix gives the next number without gaps."""
    prefix = f"INV-{year}-"
    count = db.query(Invoice).filter(Invoice.invoice_number.like(f"{prefix}%")).count()
    return f"{prefix}{count + 1:04d}"
