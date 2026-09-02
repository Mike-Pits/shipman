import json
from datetime import datetime, timezone

from sqlalchemy import event, inspect

# FR-55/56: every transactional table is audited except vessels (specs) and
# system config. exchange_rates is a special case — only manual overrides are
# logged (see app/routers/exchange_rates.py's explicit write_audit_entry call),
# not routine daily fetches, so it is deliberately not registered here.
_listener_registered = False


def _serialize_row(obj) -> dict:
    mapper = inspect(obj).mapper
    return {c.key: getattr(obj, c.key) for c in mapper.column_attrs}


def _changed_fields(obj) -> tuple[dict, dict]:
    state = inspect(obj)
    old: dict = {}
    new: dict = {}
    for attr in state.mapper.column_attrs:
        history = state.attrs[attr.key].history
        if not history.has_changes():
            continue
        if history.deleted:
            old[attr.key] = history.deleted[0]
        if history.added:
            new[attr.key] = history.added[0]
    return old, new


def write_audit_entry(
    db, table_name: str, record_id: int, action: str, old_values: dict | None, new_values: dict | None
) -> None:
    """Explicit audit call for cases that don't go through the automatic
    per-model listener below (e.g. the exchange-rate manual override, the one
    field on an otherwise-unaudited table that FR-55 still requires logging)."""
    from app.models.audit_log import AuditLogEntry

    entry = AuditLogEntry(
        table_name=table_name,
        record_id=record_id,
        action=action,
        old_values=json.dumps(old_values, default=str) if old_values is not None else None,
        new_values=json.dumps(new_values, default=str) if new_values is not None else None,
        user="operator",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    db.add(entry)


def _write_entry_via_connection(connection, table_name, record_id, action, old_values, new_values) -> None:
    from app.models.audit_log import AuditLogEntry

    connection.execute(
        AuditLogEntry.__table__.insert().values(
            table_name=table_name,
            record_id=record_id,
            action=action,
            old_values=json.dumps(old_values, default=str) if old_values is not None else None,
            new_values=json.dumps(new_values, default=str) if new_values is not None else None,
            user="operator",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
    )


def register_audit_listener() -> None:
    """Registers mapper-level after_insert/after_update/after_delete events on
    every audited model. These write directly via the flush's own Core
    connection (not session.add/flush), which is the safe way to do audit
    logging from inside a flush — session-level events that try to add new
    ORM objects and re-flush hit SQLAlchemy's "Session is already flushing"
    guard. Runs once per process; safe to call multiple times."""
    global _listener_registered
    if _listener_registered:
        return
    _listener_registered = True

    from app.models.bunker_replenishment import BunkerReplenishment
    from app.models.claim import Claim
    from app.models.daily_report import DailyReport
    from app.models.disbursement_account import DisbursementAccount
    from app.models.fixture import Fixture
    from app.models.payment import Payment
    from app.models.vetting_inspection import VettingInspection
    from app.models.voyage import Voyage
    from app.models.voyage_estimate import VoyageEstimate

    audited_models = [
        DailyReport,
        Fixture,
        Voyage,
        VoyageEstimate,
        Payment,
        DisbursementAccount,
        BunkerReplenishment,
        VettingInspection,
        Claim,
    ]

    for model_cls in audited_models:
        table_name = model_cls.__tablename__

        def _after_insert(mapper, connection, target, table_name=table_name):
            _write_entry_via_connection(
                connection, table_name, target.id, "insert", None, _serialize_row(target)
            )

        def _after_update(mapper, connection, target, table_name=table_name):
            old, new = _changed_fields(target)
            if old or new:
                _write_entry_via_connection(connection, table_name, target.id, "update", old, new)

        def _after_delete(mapper, connection, target, table_name=table_name):
            _write_entry_via_connection(
                connection, table_name, target.id, "delete", _serialize_row(target), None
            )

        event.listen(model_cls, "after_insert", _after_insert)
        event.listen(model_cls, "after_update", _after_update)
        event.listen(model_cls, "after_delete", _after_delete)
