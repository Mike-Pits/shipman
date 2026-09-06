import re
from datetime import date, datetime

CODE_LINE = re.compile(r"^(\d{1,3})\s+(.*)$")
DATETIME_VALUE = re.compile(r"^(\d{2})(\d{2})/(\d{2}):?(\d{2})$")
EXPLICIT_DATETIME_VALUE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})/(\d{2}):?(\d{2})$")


class Disp01ParseError(ValueError):
    pass


def parse_report_datetime(value: str, reference_date: date | None = None) -> datetime:
    """Parse a DISP-01 code-1 value per FR-18. Two shapes are recognized:

    - Native DDMM/HHMM (or DDMM/HH:MM) — the year is not encoded at all, so it's
      inferred as reference_date's year, unless that produces a date after
      reference_date, in which case the previous year is assumed. reference_date
      defaults to today, which is only a safe anchor for messages close to the
      present (same-day manual entry, near-real-time IMAP polling) — it cannot
      disambiguate a years-old archived message, since the same DDMM recurs every
      year. Callers processing historical messages must supply a trustworthy
      reference_date instead (e.g. the source email's own Date header).
    - Explicit YYYY-MM-DD/HHMM (or YYYY-MM-DD/HH:MM) — the year is stated outright,
      so it's used as-is with no inference at all. This is the format an operator
      is expected to amend a historical report's date line to before manual entry,
      when there's no reliable automatic source for the year (FR-15/FR-19 amendment
      for multi-year historical backfill).
    """
    stripped = value.strip()

    explicit_match = EXPLICIT_DATETIME_VALUE.match(stripped)
    if explicit_match:
        year, month, day, hour, minute = (int(part) for part in explicit_match.groups())
        return datetime(year, month, day, hour, minute)

    match = DATETIME_VALUE.match(stripped)
    if not match:
        raise Disp01ParseError(f"Unrecognized date/time value: {value!r}")

    reference_date = reference_date or date.today()
    day, month, hour, minute = (int(part) for part in match.groups())
    candidate = datetime(reference_date.year, month, day, hour, minute)
    if candidate.date() > reference_date:
        candidate = candidate.replace(year=reference_date.year - 1)
    return candidate


def parse_rob(raw_value: str | None) -> tuple[float | None, float | None]:
    """Parse a DISP-01 code-31 value ("IFO/MGO", comma decimals) into (ifo_mt, mgo_mt).

    Returns (None, None) if the value is missing or not in the expected shape.
    """
    if not raw_value:
        return None, None
    parts = raw_value.split("/")
    if len(parts) != 2:
        return None, None
    try:
        ifo = float(parts[0].strip().replace(",", "."))
        mgo = float(parts[1].strip().replace(",", "."))
    except ValueError:
        return None, None
    return ifo, mgo


def parse_disp01(raw_text: str, reference_date: date | None = None) -> dict:
    """Parse a raw DISP-01 message into its coded fields.

    Lines that don't start with a recognized numeric code are treated as
    continuations of the previously seen code (covers multi-line values and
    trailing free text), matching how real-world reports are formatted.
    Everything before the first coded line (vessel name, dispatch reference)
    and the "NNNN" terminator, if present, are not treated as coded fields.

    reference_date anchors year-inference for a native-format (non-explicit-year)
    date line — see parse_report_datetime. Pass the source's own trustworthy date
    (e.g. an email's Date header) when parsing anything that isn't a same-day entry.
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
        report_datetime = parse_report_datetime(fields["1"], reference_date=reference_date)

    return {"fields": fields, "report_datetime": report_datetime}
