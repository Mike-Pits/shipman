"""Database backup, restore, compaction and health tools behind the Service page.

Every function takes the SQLAlchemy `Engine` the request is bound to, so tests operate on their
own temporary database and never touch `shipman.db`. Backups are made with SQLite's online backup
API (a plain file copy of a live database can be torn), then verified *on the copy*. Each backup
gets a JSON manifest next to it (time, size, checksum, row counts, verification result).
"""

import hashlib
import json
import re
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.engine import Engine

from app.database import Base

BACKUP_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.db$")
KINDS = ("manual", "auto", "pre-restore", "pre-compact", "imported")
SETTINGS_DEFAULTS = {"backup_dir": None, "auto_backup_enabled": True, "keep_daily": 14, "keep_monthly": 12}
KEEP_SAFETY_COPIES = 10  # newest pre-restore / pre-compact backups retained

_lock = threading.Lock()  # one backup / restore / compaction at a time


class ServiceError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def db_path(engine: Engine) -> Path:
    database = engine.url.database
    if not database or database == ":memory:":
        raise ServiceError(409, "Backups need a file-based database")
    return Path(database).resolve()


def settings_path(engine: Engine) -> Path:
    return db_path(engine).parent / "service_settings.json"


def load_settings(engine: Engine) -> dict:
    settings = dict(SETTINGS_DEFAULTS)
    path = settings_path(engine)
    if path.exists():
        try:
            settings.update(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass  # unreadable settings fall back to defaults rather than blocking backups
    return settings


def save_settings(engine: Engine, settings: dict) -> dict:
    merged = {**load_settings(engine), **settings}
    folder = resolve_backup_dir(engine, merged)
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write-test"
        probe.write_text("ok")
        probe.unlink()
    except OSError as exc:
        raise ServiceError(422, f"Backup folder is not writable: {exc}") from exc
    settings_path(engine).write_text(json.dumps(merged, indent=2), encoding="utf-8")
    return merged


def resolve_backup_dir(engine: Engine, settings: dict | None = None) -> Path:
    settings = settings or load_settings(engine)
    configured = settings.get("backup_dir")
    return Path(configured).expanduser() if configured else db_path(engine).parent / "backups"


def backup_dir(engine: Engine) -> Path:
    folder = resolve_backup_dir(engine)
    folder.mkdir(parents=True, exist_ok=True)
    return folder


# ---------------------------------------------------------------- inspection helpers


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_readonly(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)


def _table_names(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    return [r[0] for r in rows]


def _row_counts(conn: sqlite3.Connection) -> dict[str, int]:
    return {t: conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0] for t in _table_names(conn)}


def _integrity(conn: sqlite3.Connection) -> tuple[bool, list[str]]:
    rows = [r[0] for r in conn.execute("PRAGMA integrity_check").fetchall()]
    return rows == ["ok"], ([] if rows == ["ok"] else rows[:20])


def _fk_violations(conn: sqlite3.Connection) -> list[dict]:
    grouped: dict[tuple[str, str], int] = {}
    for table, _rowid, parent, _fkid in conn.execute("PRAGMA foreign_key_check").fetchall():
        grouped[(table, parent)] = grouped.get((table, parent), 0) + 1
    return [{"table": t, "parent": p, "rows": n} for (t, p), n in sorted(grouped.items())]


def schema_blockers(path: Path) -> list[str]:
    """Columns the current code needs that the backup lacks. Missing *tables* are fine (they are
    recreated at startup); extra columns in the backup are harmless."""
    blockers = []
    conn = _open_readonly(path)
    try:
        existing = set(_table_names(conn))
        for table in Base.metadata.sorted_tables:
            if table.name not in existing:
                continue
            have = {r[1] for r in conn.execute(f'PRAGMA table_info("{table.name}")').fetchall()}
            missing = sorted({c.name for c in table.columns} - have)
            if missing:
                blockers.append(f"{table.name}: {', '.join(missing)}")
    finally:
        conn.close()
    return blockers


# ---------------------------------------------------------------- backups


def _manifest_path(file: Path) -> Path:
    return file.with_name(file.name + ".json")


def _write_manifest(file: Path, kind: str) -> dict:
    conn = _open_readonly(file)
    try:
        integrity_ok, problems = _integrity(conn)
        fk = _fk_violations(conn)
        counts = _row_counts(conn)
    finally:
        conn.close()
    manifest = {
        "name": file.name,
        "kind": kind,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "size_bytes": file.stat().st_size,
        "sha256": _sha256(file),
        "sqlite_version": sqlite3.sqlite_version,
        "integrity_ok": integrity_ok,
        "integrity_problems": problems,
        "fk_violations": fk,
        "row_counts": counts,
    }
    _manifest_path(file).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def create_backup(engine: Engine, kind: str = "manual") -> dict:
    source = db_path(engine)
    folder = backup_dir(engine)
    with _lock:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = folder / f"shipman-{stamp}-{kind}.db"
        counter = 1
        while target.exists():
            counter += 1
            target = folder / f"shipman-{stamp}-{kind}-{counter}.db"
        src = sqlite3.connect(source)
        dst = sqlite3.connect(target)
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        manifest = _write_manifest(target, kind)
        if not manifest["integrity_ok"]:
            target.unlink(missing_ok=True)
            _manifest_path(target).unlink(missing_ok=True)
            raise ServiceError(500, "The backup failed its integrity check and was discarded")
    return manifest


def _entry(file: Path) -> dict:
    manifest_file = _manifest_path(file)
    manifest = None
    if manifest_file.exists():
        try:
            manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            manifest = None
    if manifest is None:  # a file dropped into the folder by hand
        stat = file.stat()
        manifest = {
            "name": file.name,
            "kind": "external",
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "size_bytes": stat.st_size,
            "sha256": None,
            "integrity_ok": None,
            "fk_violations": [],
            "row_counts": {},
        }
    try:
        blockers = schema_blockers(file)
    except sqlite3.DatabaseError:
        blockers = ["not a readable SQLite database"]
    return {**manifest, "size_bytes": file.stat().st_size, "restore_blockers": blockers}


def list_backups(engine: Engine) -> list[dict]:
    folder = resolve_backup_dir(engine)
    if not folder.exists():
        return []
    files = [f for f in folder.iterdir() if f.is_file() and f.suffix == ".db" and BACKUP_NAME.match(f.name)]
    entries = [_entry(f) for f in files]
    return sorted(entries, key=lambda e: e["created_at"], reverse=True)


def backup_file(engine: Engine, name: str) -> Path:
    if not BACKUP_NAME.match(name):
        raise ServiceError(422, "Invalid backup name")
    path = resolve_backup_dir(engine) / name
    if not path.is_file():
        raise ServiceError(404, "Backup not found")
    return path


def delete_backup(engine: Engine, name: str) -> None:
    path = backup_file(engine, name)
    path.unlink()
    _manifest_path(path).unlink(missing_ok=True)


def import_backup(engine: Engine, data: bytes, original_name: str | None) -> dict:
    """Bring a database file from another machine into the backup folder (verified, not restored)."""
    if not data.startswith(b"SQLite format 3\x00"):
        raise ServiceError(422, "That file is not a SQLite database")
    folder = backup_dir(engine)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = folder / f"shipman-{stamp}-imported.db"
    target.write_bytes(data)
    try:
        manifest = _write_manifest(target, "imported")
    except sqlite3.DatabaseError as exc:
        target.unlink(missing_ok=True)
        raise ServiceError(422, f"That file is not a usable database: {exc}") from exc
    if not manifest["integrity_ok"]:
        target.unlink(missing_ok=True)
        _manifest_path(target).unlink(missing_ok=True)
        raise ServiceError(422, "That database failed its integrity check")
    return _entry(target)


def prune(engine: Engine) -> list[str]:
    """Retention: automatic backups keep the newest per day for `keep_daily` days and the newest per
    month for `keep_monthly` months; pre-restore / pre-compact safety copies keep the newest few.
    Manual and imported backups are never pruned automatically."""
    settings = load_settings(engine)
    now = datetime.now()
    removed: list[str] = []
    entries = list_backups(engine)

    autos = [e for e in entries if e["kind"] == "auto"]  # newest first
    keep: set[str] = set()
    days_seen: set[str] = set()
    months_seen: set[str] = set()
    for e in autos:
        created = datetime.fromisoformat(e["created_at"])
        day, month = created.strftime("%Y-%m-%d"), created.strftime("%Y-%m")
        if now - created <= timedelta(days=settings["keep_daily"]) and day not in days_seen:
            days_seen.add(day)
            keep.add(e["name"])
        months_back = (now.year - created.year) * 12 + now.month - created.month
        if months_back < settings["keep_monthly"] and month not in months_seen:
            months_seen.add(month)
            keep.add(e["name"])
    for e in autos:
        if e["name"] not in keep:
            delete_backup(engine, e["name"])
            removed.append(e["name"])

    for kind in ("pre-restore", "pre-compact"):
        for e in [x for x in entries if x["kind"] == kind][KEEP_SAFETY_COPIES:]:
            delete_backup(engine, e["name"])
            removed.append(e["name"])
    return removed


# ---------------------------------------------------------------- restore / compact / health


def restore_backup(engine: Engine, name: str) -> dict:
    path = backup_file(engine, name)
    entry = _entry(path)
    if entry["restore_blockers"]:
        raise ServiceError(
            409,
            "This backup is from an older version of the app and lacks columns the current version "
            "needs (" + "; ".join(entry["restore_blockers"]) + "). It must be migrated first.",
        )
    if entry.get("sha256") and _sha256(path) != entry["sha256"]:
        raise ServiceError(409, "The backup file has changed since it was created (checksum mismatch)")
    conn = _open_readonly(path)
    try:
        ok, problems = _integrity(conn)
    finally:
        conn.close()
    if not ok:
        raise ServiceError(409, "The backup fails its integrity check: " + "; ".join(problems))

    safety = create_backup(engine, "pre-restore")
    with _lock:
        engine.dispose()
        src = sqlite3.connect(path)
        dst = sqlite3.connect(db_path(engine), timeout=5)
        try:
            src.backup(dst)
        except sqlite3.OperationalError as exc:
            raise ServiceError(409, f"The database is in use and could not be replaced: {exc}") from exc
        finally:
            dst.close()
            src.close()
        engine.dispose()
        Base.metadata.create_all(bind=engine)  # tables added since the backup was made
    prune(engine)
    return {"restored": name, "safety_backup": safety["name"]}


def compact(engine: Engine) -> dict:
    path = db_path(engine)
    safety = create_backup(engine, "pre-compact")
    with _lock:
        before = path.stat().st_size
        engine.dispose()
        conn = sqlite3.connect(path, isolation_level=None, timeout=5)
        try:
            conn.execute("VACUUM")
        except sqlite3.OperationalError as exc:
            raise ServiceError(409, f"The database is in use and could not be compacted: {exc}") from exc
        finally:
            conn.close()
        after = path.stat().st_size
    prune(engine)
    return {"size_before": before, "size_after": after, "safety_backup": safety["name"]}


def health_check(engine: Engine) -> dict:
    path = db_path(engine)
    conn = _open_readonly(path)
    try:
        ok, problems = _integrity(conn)
        fk = _fk_violations(conn)
        counts = _row_counts(conn)
        page_size = conn.execute("PRAGMA page_size").fetchone()[0]
        freelist = conn.execute("PRAGMA freelist_count").fetchone()[0]
        journal = conn.execute("PRAGMA journal_mode").fetchone()[0]
    finally:
        conn.close()
    return {
        "integrity_ok": ok,
        "integrity_problems": problems,
        "fk_violations": fk,
        "row_counts": counts,
        "size_bytes": path.stat().st_size,
        "reclaimable_bytes": freelist * page_size,
        "journal_mode": journal,
        "sqlite_version": sqlite3.sqlite_version,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
    }


def status(engine: Engine) -> dict:
    settings = load_settings(engine)
    backups = list_backups(engine)
    real = [b for b in backups if b["kind"] in ("manual", "auto", "imported", "external")]
    last = real[0] if real else None
    age_hours = None
    if last:
        age_hours = round((datetime.now() - datetime.fromisoformat(last["created_at"])).total_seconds() / 3600, 1)
    return {
        "database_path": str(db_path(engine)),
        "database_size_bytes": db_path(engine).stat().st_size,
        "backup_dir": str(resolve_backup_dir(engine, settings)),
        "backup_dir_is_default": not settings.get("backup_dir"),
        "auto_backup_enabled": settings["auto_backup_enabled"],
        "keep_daily": settings["keep_daily"],
        "keep_monthly": settings["keep_monthly"],
        "backup_count": len(backups),
        "last_backup": last,
        "last_backup_age_hours": age_hours,
    }


# ---------------------------------------------------------------- automatic backups

CHECK_INTERVAL_SECONDS = 30 * 60
AUTO_BACKUP_EVERY = timedelta(hours=24)


def auto_backup_if_due(engine: Engine) -> dict | None:
    settings = load_settings(engine)
    if not settings["auto_backup_enabled"]:
        return None
    last = status(engine)["last_backup"]
    if last and datetime.now() - datetime.fromisoformat(last["created_at"]) < AUTO_BACKUP_EVERY:
        return None
    manifest = create_backup(engine, "auto")
    prune(engine)
    return manifest


class AutoBackupScheduler:
    """Daemon thread: a backup shortly after startup if the last one is over 24 h old, then a check
    every 30 minutes. Failures are logged, never raised into the app."""

    def __init__(self, engine: Engine):
        self._engine = engine
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="auto-backup", daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        wait = 10  # let the app finish starting first
        while not self._stop.wait(wait):
            try:
                auto_backup_if_due(self._engine)
            except Exception as exc:  # noqa: BLE001 - a failed backup must not crash the server
                print(f"[auto-backup] failed: {exc}")
            wait = CHECK_INTERVAL_SECONDS
