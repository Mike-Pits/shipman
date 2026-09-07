import re
import time
from datetime import datetime

import httpx

CBR_DAILY_RATES_URL = "https://www.cbr.ru/eng/currency_base/daily/"
CBR_HISTORICAL_RATES_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
USD_CHAR_CODE = "840"


class RateFetchError(RuntimeError):
    pass


def fetch_usd_rub_rate_for_date(rate_date: str) -> float:
    """Fetch the USD/RUB rate for a specific historical date (FR-39 backfill).

    `rate_date` is an ISO date string (YYYY-MM-DD). Uses the CBR's XML web
    service, which returns a rate for every calendar date including
    weekends (the preceding business day's rate carries forward).
    """
    parsed = datetime.strptime(rate_date, "%Y-%m-%d").date()
    date_req = parsed.strftime("%d/%m/%Y")

    max_retries = 6
    backoff = 5.0
    response: httpx.Response | None = None
    last_error = "unknown error"

    for attempt in range(max_retries):
        try:
            response = httpx.get(CBR_HISTORICAL_RATES_URL, params={"date_req": date_req}, timeout=15)
        except httpx.HTTPError as exc:
            last_error = str(exc)
            response = None
        else:
            if response.status_code == 429:
                last_error = "429 Too Many Requests"
            elif response.status_code >= 400:
                last_error = f"HTTP {response.status_code}"
            else:
                break  # success

        if attempt < max_retries - 1:
            time.sleep(backoff)
            backoff *= 2
    else:
        response = None

    if response is None:
        raise RateFetchError(f"Could not reach CBR historical rate feed for {rate_date}: {last_error}")

    text = response.content.decode("windows-1251", errors="replace")
    match = re.search(
        r"<CharCode>USD</CharCode>.*?<Value>([\d.,]+)</Value>", text, re.DOTALL
    )
    if not match:
        raise RateFetchError(f"USD row not found in CBR historical response for {rate_date}")

    return float(match.group(1).replace(",", "."))


def fetch_usd_rub_rate() -> float:
    """Fetch today's USD/RUB rate from the Central Bank of Russia (FR-39).

    This is the true external boundary for the Exchange Rate module — it is
    injected as a FastAPI dependency (see app.dependencies.get_rate_fetcher)
    so it can be swapped for a fake in tests without hitting the network.
    """
    try:
        response = httpx.get(CBR_DAILY_RATES_URL, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        raise RateFetchError(f"Could not reach CBR rate feed: {exc}") from exc

    row_pattern = re.compile(
        rf"{USD_CHAR_CODE}.*?<td[^>]*>([\d.,]+)</td>\s*</tr>", re.DOTALL
    )
    match = row_pattern.search(response.text)
    if not match:
        raise RateFetchError("USD row not found in CBR daily rates page")

    return float(match.group(1).replace(",", "."))
