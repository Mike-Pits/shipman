from app.services.cbr_rate_fetcher import fetch_usd_rub_rate


def get_rate_fetcher():
    """Production dependency: hits the real CBR feed. Overridden in tests."""
    return fetch_usd_rub_rate
