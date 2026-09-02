import os

from dotenv import load_dotenv

load_dotenv()

IMAP_SERVER = os.environ.get("SHIPMAN_IMAP_SERVER")
IMAP_PORT = int(os.environ.get("SHIPMAN_IMAP_PORT", "993"))
IMAP_EMAIL = os.environ.get("SHIPMAN_EMAIL")
IMAP_PASSWORD = os.environ.get("SHIPMAN_EMAIL_PASSWORD")
IMAP_DEFAULT_FOLDER = os.environ.get("SHIPMAN_MAILBOX_FOLDER", "INBOX")
