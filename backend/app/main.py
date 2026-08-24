from fastapi import FastAPI

from app.database import Base, engine
from app.routers import daily_reports, exchange_rates, fixtures, vessels, voyages

Base.metadata.create_all(bind=engine)

app = FastAPI(title="ShipMan v2")

app.include_router(vessels.router)
app.include_router(fixtures.router)
app.include_router(voyages.router)
app.include_router(daily_reports.router)
app.include_router(exchange_rates.router)
