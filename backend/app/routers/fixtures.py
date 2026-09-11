from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.fixture import Fixture, FixtureBroker
from app.schemas.fixture import FixtureCreate, FixtureRead

router = APIRouter(prefix="/fixtures", tags=["fixtures"])


@router.post("", response_model=FixtureRead, status_code=201)
def create_fixture(payload: FixtureCreate, db: Session = Depends(get_db)):
    fixture = Fixture(
        **payload.model_dump(exclude={"brokers"}),
        brokers=[FixtureBroker(**broker.model_dump()) for broker in payload.brokers],
    )
    db.add(fixture)
    db.commit()
    db.refresh(fixture)
    return fixture


@router.get("", response_model=list[FixtureRead])
def list_fixtures(db: Session = Depends(get_db)):
    return db.query(Fixture).all()


@router.put("/{fixture_id}", response_model=FixtureRead)
def update_fixture(fixture_id: int, payload: FixtureCreate, db: Session = Depends(get_db)):
    fixture = db.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Fixture not found")

    for field, value in payload.model_dump(exclude={"brokers"}).items():
        setattr(fixture, field, value)
    fixture.brokers = [FixtureBroker(**broker.model_dump()) for broker in payload.brokers]
    db.commit()
    db.refresh(fixture)
    return fixture


@router.get("/{fixture_id}", response_model=FixtureRead)
def get_fixture(fixture_id: int, db: Session = Depends(get_db)):
    fixture = db.get(Fixture, fixture_id)
    if fixture is None:
        raise HTTPException(status_code=404, detail="Fixture not found")
    return fixture
