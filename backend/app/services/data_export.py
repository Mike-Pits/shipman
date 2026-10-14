import io
from datetime import date, datetime

from openpyxl import Workbook
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.database import Base


def _cell(value):
    # openpyxl rejects some types; keep dates readable and everything else as-is.
    if isinstance(value, (datetime, date, int, float, str, bool)) or value is None:
        return value
    return str(value)


def all_tables_workbook(engine: Engine) -> bytes:
    """One worksheet per table (header row + every row) — a plain-data safety net that opens in
    Excel without the app, e.g. for accountants or if the database ever becomes unreadable."""
    workbook = Workbook()
    workbook.remove(workbook.active)
    with engine.connect() as conn:
        for table in Base.metadata.sorted_tables:
            sheet = workbook.create_sheet(table.name[:31])
            columns = [c.name for c in table.columns]
            sheet.append(columns)
            for row in conn.execute(text(f'SELECT {", ".join(chr(34) + c + chr(34) for c in columns)} FROM "{table.name}"')):
                sheet.append([_cell(v) for v in row])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
