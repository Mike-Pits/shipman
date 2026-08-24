import re
from datetime import date, datetime

CODE_LINE = re.compile(r"^(\d{1,3})\s+(.*)$")
DATETIME_VALUE = re.compile(r"^(\d{2})(\d{2})/(\d{2}):?(\d{2})$")


class Disp01ParseError(ValueError):
    pass


def parse_report_datetime(value: str, today: date | None = None) -> datetime:
    """Parse a DISP-01 code-1 value (DDMM/HRMN or DDMM/HR:MN) per FR-18.

    Year is inferred as the current year, unless that produces a date after
    today, in which case the previous year is assumed.
    """
    today = today or date.today()
    match = DATETIME_VALUE.match(value.strip())
    if not match:
        raise Disp01ParseError(f"Unrecognized date/time value: {value!r}")

    day, month, hour, minute = (int(part) for part in match.groups())
    candidate = datetime(today.year, month, day, hour, minute)
    if candidate.date() > today:
        candidate = candidate.replace(year=today.year - 1)
    return candidate


def parse_disp01(raw_text: str) -> dict:
    """Parse a raw DISP-01 message into its coded fields.

    Lines that don't start with a recognized numeric code are treated as
    continuations of the previously seen code (covers multi-line values and
    trailing free text), matching how real-world reports are formatted.
    Everything before the first coded line (vessel name, dispatch reference)
    and the "NNNN" terminator, if present, are not treated as coded fields.
    """
    fields: dict[str, str] = {}
    last_code: str | None = None

    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "NNNN":
            continue

        match = CODE_LINE.match(stripped)
        if match:
            code, value = match.groups()
            fields[code] = value.strip()
            last_code = code
        elif last_code is not None:
            fields[last_code] = f"{fields[last_code]} {stripped}".strip()

    report_datetime = None
    if "1" in fields:
        report_datetime = parse_report_datetime(fields["1"])

    return {"fields": fields, "report_datetime": report_datetime}
