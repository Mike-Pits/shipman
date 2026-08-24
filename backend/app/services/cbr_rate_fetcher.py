import re

import httpx

CBR_DAILY_RATES_URL = "https://www.cbr.ru/eng/currency_base/daily/"
USD_CHAR_CODE = "840"


class RateFetchError(RuntimeError):
    pass


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
