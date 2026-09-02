import email
import email.message
import imaplib

from app import config


class ImapFetchError(RuntimeError):
    pass


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


def fetch_disp01_messages(folder: str) -> list[tuple[str, str]]:
    """FR-16: retrieve every message currently in `folder` as (message_id, body_text)
    pairs, without altering the mailbox in any way.

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

            messages: list[tuple[str, str]] = []
            for i, part in enumerate(msg_data):
                if not isinstance(part, tuple):
                    continue
                raw_email = part[1]
                msg = email.message_from_bytes(raw_email)
                message_id = msg.get("Message-ID") or f"{folder}:seq-{i}"
                messages.append((message_id, _extract_body(msg)))
            return messages
        finally:
            connection.logout()
    except imaplib.IMAP4.error as exc:
        raise ImapFetchError(str(exc)) from exc
    except OSError as exc:
        raise ImapFetchError(f"Could not connect to {config.IMAP_SERVER}: {exc}") from exc
