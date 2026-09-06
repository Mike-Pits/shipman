import email
import email.message
import email.utils
import imaplib
from datetime import datetime

from app import config


class ImapFetchError(RuntimeError):
    pass


def _extract_date(msg: email.message.Message) -> datetime | None:
    """The email's own envelope date — the only reliable signal for which YEAR a
    message belongs to, since the DISP-01 body itself only carries day/month (see
    disp01_parser.parse_report_datetime). Returns None if the header is missing or
    unparseable; callers then fall back to comparing against today, which is only
    safe for near-real-time messages."""
    date_header = msg.get("Date")
    if not date_header:
        return None
    try:
        return email.utils.parsedate_to_datetime(date_header)
    except (TypeError, ValueError):
        return None


def _extract_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                charset = part.get_content_charset() or "utf-8"
                payload = part.get_payload(decode=True)
                return payload.decode(charset, errors="replace") if payload else ""
        return ""
    charset = msg.get_content_charset() or "utf-8"
    payload = msg.get_payload(decode=True)
    return payload.decode(charset, errors="replace") if payload else ""


def fetch_disp01_messages(folder: str) -> list[tuple[str, str, datetime | None]]:
    """FR-16: retrieve every message currently in `folder` as
    (message_id, body_text, email_date) triples, without altering the mailbox in
    any way. email_date is the message's own Date header (None if missing/
    unparseable) — used to resolve the report year for archived/historical
    messages instead of assuming the message is from today.

    Uses BODY.PEEK[] (not BODY[]) so messages are never marked as read, and opens
    the mailbox with readonly=True so no STORE/EXPUNGE is even possible over this
    connection — the two things standing between "read" and "leave intact."
    Deduplication against already-ingested messages happens in the caller (by
    comparing message_id against daily_reports.source_message_id), not here.
    """
    if not all([config.IMAP_SERVER, config.IMAP_EMAIL, config.IMAP_PASSWORD]):
        raise ImapFetchError(
            "IMAP is not configured — set SHIPMAN_IMAP_SERVER, SHIPMAN_EMAIL, "
            "SHIPMAN_EMAIL_PASSWORD"
        )

    try:
        # timeout guards against a stalled handshake/response hanging forever;
        # discovered the need for this against a real mailbox with a large backlog.
        connection = imaplib.IMAP4_SSL(config.IMAP_SERVER, config.IMAP_PORT, timeout=30)
        try:
            connection.login(config.IMAP_EMAIL, config.IMAP_PASSWORD)
            status, _ = connection.select(folder, readonly=True)
            if status != "OK":
                raise ImapFetchError(f"Could not open mailbox folder {folder!r}")

            status, data = connection.search(None, "ALL")
            if status != "OK":
                raise ImapFetchError("IMAP search failed")

            sequence_numbers = data[0].split()
            if not sequence_numbers:
                return []

            # One batched FETCH across the whole sequence set instead of one
            # round-trip per message — with a real mailbox holding hundreds of
            # messages, fetching them one at a time was impractically slow.
            sequence_set = b",".join(sequence_numbers)
            status, msg_data = connection.fetch(sequence_set, "(BODY.PEEK[])")
            if status != "OK":
                raise ImapFetchError("IMAP fetch failed")

            messages: list[tuple[str, str, datetime | None]] = []
            for i, part in enumerate(msg_data):
                if not isinstance(part, tuple):
                    continue
                raw_email = part[1]
                msg = email.message_from_bytes(raw_email)
                message_id = msg.get("Message-ID") or f"{folder}:seq-{i}"
                messages.append((message_id, _extract_body(msg), _extract_date(msg)))
            return messages
        finally:
            connection.logout()
    except imaplib.IMAP4.error as exc:
        raise ImapFetchError(str(exc)) from exc
    except OSError as exc:
        raise ImapFetchError(f"Could not connect to {config.IMAP_SERVER}: {exc}") from exc
