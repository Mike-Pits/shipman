import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.database import Base, engine
from app.routers import (
    audit_log,
    bunker_replenishments,
    claims,
    daily_reports,
    disbursement_accounts,
    exchange_rates,
    fixtures,
    invoices,
    payments,
    ports,
    reports,
    service,
    vessels,
    voyage_estimates,
    voyages,
)
from app.services.audit import register_audit_listener
from app.services.backup import AutoBackupScheduler, ServiceError

Base.metadata.create_all(bind=engine)
register_audit_listener()



@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Tests set SHIPMAN_DISABLE_AUTO_BACKUP so the scheduler never touches the real database.
    scheduler = None
    if not os.environ.get("SHIPMAN_DISABLE_AUTO_BACKUP"):
        scheduler = AutoBackupScheduler(engine)
        scheduler.start()
    yield
    if scheduler:
        scheduler.stop()


app = FastAPI(title="ShipMan v2", lifespan=lifespan)


@app.exception_handler(ServiceError)
async def service_error_handler(_request: Request, exc: ServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


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
app.include_router(ports.router)
app.include_router(claims.router)
app.include_router(invoices.router)
app.include_router(audit_log.router)
app.include_router(service.router)
