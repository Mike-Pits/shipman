import re
from datetime import datetime, timedelta

# Delivery/redelivery-type timestamps are contractual — hire runs from the exact
# time of delivery to the exact time of redelivery, so a final period is routinely
# a partial day. Accept a bare date too (assumed midnight) for callers that genuinely
# don't need that precision, and tolerate a trailing seconds field either way.
_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")

# "24:00" is the conventional way to write end-of-day on hire statements; strptime
# rejects hour 24, so it is read as midnight at the end of that date (next day 00:00).
_END_OF_DAY = re.compile(r"^(\d{4}-\d{2}-\d{2}) 24:00(?::00)?$")


DAY_DECIMALS = 3


def round_days(days: float) -> float:
    """Every day count in the app (hire quantity, off-hire, TCE, utilization) is
    rounded to 3 decimals — matching how accounting writes them on invoices — and
    amounts are computed from the rounded figure so documents multiply out."""
    return round(days, DAY_DECIMALS)


def days_between(start: datetime, end: datetime) -> float:
    return round_days((end - start).total_seconds() / 86400)


class UnparseableDateTime(ValueError):
    pass


def parse_flexible_datetime(value: str) -> datetime:
    value = value.strip()
    end_of_day = _END_OF_DAY.match(value)
    if end_of_day:
        try:
            return datetime.strptime(end_of_day.group(1), "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            pass
    for fmt in _FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise UnparseableDateTime(f"Could not parse date/time: {value!r}")
