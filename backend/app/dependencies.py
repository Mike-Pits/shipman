from app.services.cbr_rate_fetcher import fetch_usd_rub_rate
from app.services.imap_fetcher import fetch_disp01_messages


def get_rate_fetcher():
    """Production dependency: hits the real CBR feed. Overridden in tests."""
    return fetch_usd_rub_rate


def get_imap_fetcher():
    """Production dependency: connects to the real configured mailbox. Overridden in tests."""
    return fetch_disp01_messages
