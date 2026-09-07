"""One-time bulk import of historical USD/RUB exchange rates from the CBR.

Usage:
    python -m scripts.backfill_exchange_rates [start_date] [end_date]

Dates are ISO (YYYY-MM-DD). Defaults to 2021-12-01 through today. Safe to
re-run: existing rows (by rate_date) are left untouched, so a partial or
interrupted run can simply be re-invoked to pick up where it left off.
"""

import sys
import time
from datetime import date, datetime, timedelta

from app.database import SessionLocal
from app.models.exchange_rate import ExchangeRate
from app.services.cbr_rate_fetcher import RateFetchError, fetch_usd_rub_rate_for_date

DEFAULT_START = "2021-12-01"
REQUEST_DELAY_SECONDS = 0.6


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def main() -> None:
    start_str = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_START
    end_str = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()
    start = datetime.strptime(start_str, "%Y-%m-%d").date()
    end = datetime.strptime(end_str, "%Y-%m-%d").date()

    db = SessionLocal()
    existing_dates = {row.rate_date for row in db.query(ExchangeRate.rate_date).all()}

    total = (end - start).days + 1
    inserted = 0
    skipped = 0
    failed: list[str] = []

    for i, day in enumerate(daterange(start, end), start=1):
        iso = day.isoformat()
        if iso in existing_dates:
            skipped += 1
            continue

        try:
            rate = fetch_usd_rub_rate_for_date(iso)
        except RateFetchError as exc:
            failed.append(iso)
            print(f"[{i}/{total}] {iso}: FAILED — {exc}")
            continue
        finally:
            time.sleep(REQUEST_DELAY_SECONDS)

        db.add(ExchangeRate(rate_date=iso, usd_rub_rate=rate, manual_override=False))
        inserted += 1

        if inserted % 50 == 0:
            db.commit()
            print(f"[{i}/{total}] {iso}: {rate} (committed {inserted} so far)")

    db.commit()
    db.close()

    print()
    print(f"Done. Inserted {inserted}, skipped {skipped} (already present), failed {len(failed)}.")
    if failed:
        print("Failed dates (re-run this script to retry just these, or investigate):")
        for d in failed:
            print(f"  {d}")


if __name__ == "__main__":
    main()
