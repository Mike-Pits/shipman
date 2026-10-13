from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.port import Port

router = APIRouter(prefix="/ports", tags=["ports"])


class PortCreate(BaseModel):
    name: str = Field(min_length=1)


class PortRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


@router.get("", response_model=list[PortRead])
def list_ports(db: Session = Depends(get_db)):
    return db.query(Port).order_by(Port.name).all()


@router.post("", response_model=PortRead, status_code=201)
def create_port(payload: PortCreate, db: Session = Depends(get_db)):
    port = Port(name=payload.name.strip())
    db.add(port)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="This port is already in the list") from exc
    db.refresh(port)
    return port


@router.delete("/{port_id}", status_code=204)
def delete_port(port_id: int, db: Session = Depends(get_db)):
    port = db.get(Port, port_id)
    if port is None:
        raise HTTPException(status_code=404, detail="Port not found")
    db.delete(port)
    db.commit()
    return Response(status_code=204)
