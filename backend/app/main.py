from fastapi import FastAPI

from app.database import Base, engine
from app.routers import (
    audit_log,
    bunker_replenishments,
    claims,
    daily_reports,
    disbursement_accounts,
    exchange_rates,
    fixtures,
    payments,
    reports,
    vessels,
    voyage_estimates,
    voyages,
)
from app.services.audit import register_audit_listener

Base.metadata.create_all(bind=engine)
register_audit_listener()

app = FastAPI(title="ShipMan v2")

app.include_router(vessels.router)
app.include_router(fixtures.router)
app.include_router(voyages.router)
app.include_router(daily_reports.router)
app.include_router(exchange_rates.router)
app.include_router(bunker_replenishments.router)
app.include_router(disbursement_accounts.router)
app.include_router(payments.router)
app.include_router(reports.router)
app.include_router(voyage_estimates.router)
app.include_router(claims.router)
app.include_router(audit_log.router)
