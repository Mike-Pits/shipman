from datetime import datetime

# Delivery/redelivery-type timestamps are contractual — hire runs from the exact
# time of delivery to the exact time of redelivery, so a final period is routinely
# a partial day. Accept a bare date too (assumed midnight) for callers that genuinely
# don't need that precision, and tolerate a trailing seconds field either way.
_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d")


class UnparseableDateTime(ValueError):
    pass


def parse_flexible_datetime(value: str) -> datetime:
    for fmt in _FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise UnparseableDateTime(f"Could not parse date/time: {value!r}")
