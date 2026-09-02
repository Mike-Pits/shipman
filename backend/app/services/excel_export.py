import io
from typing import Literal

from fastapi.responses import StreamingResponse
from openpyxl import Workbook

ReportFormat = Literal["json", "xlsx"]

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def rows_to_xlsx_response(rows: list[dict] | dict, filename: str) -> StreamingResponse:
    """FR-54: every report is exportable to Excel. Accepts either a single-row
    report (a dict, e.g. Voyage P&L) or a multi-row one (a list of dicts, e.g.
    the fleet-wide reports) and renders one worksheet with a header row."""
    if isinstance(rows, dict):
        rows = [rows]

    workbook = Workbook()
    sheet = workbook.active

    if rows:
        headers = list(rows[0].keys())
        sheet.append(headers)
        for row in rows:
            sheet.append([row.get(header) for header in headers])

    buffer = io.BytesIO()
    workbook.save(buffer)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type=XLSX_MEDIA_TYPE,
        headers={"Content-Disposition": f'attachment; filename="{filename}.xlsx"'},
    )
