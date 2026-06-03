#!/usr/bin/env python3
"""
Email importer for DISP-01 daily reports.
Uses sender email address to identify vessel when name is missing in body.
"""

import imaplib
import email
from email.header import decode_header
import re
from datetime import datetime, timedelta
import sys
import os
import sqlite3

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------
IMAP_SERVER = os.getenv("SHIPMAN_IMAP_SERVER")
IMAP_PORT = int(os.getenv("SHIPMAN_IMAP_PORT", "993"))
EMAIL_ADDRESS = os.getenv("SHIPMAN_EMAIL")
EMAIL_PASSWORD = os.getenv("SHIPMAN_EMAIL_PASSWORD")
MAILBOX_FOLDER = os.getenv("SHIPMAN_MAILBOX_FOLDER", "INBOX")
PROCESSED_FOLDER = os.getenv("SHIPMAN_PROCESSED_FOLDER", "INBOX/Processed")
TIME_WINDOW_HOURS = int(os.getenv("SHIPMAN_TIME_WINDOW_HOURS", "2"))
DB_PATH = os.getenv("SHIPMAN_DB_PATH", "shipman.db")

# Date search override: if set, use that date; otherwise default to last 2 days
SEARCH_SINCE = os.getenv("SHIPMAN_SEARCH_SINCE")  # e.g., "01-May-2026"

# -------------------------------------------------------------------
# Vessel mapping: (sender email domain or full address) -> vessel name
# Adjust these to match the actual sender addresses
VESSEL_BY_SENDER = {
    "np.dikson@ashipping.ru": "СП Диксон",
    "sp.dudinka@ashipping.ru": "СП Дудинка",
    # Add more as needed
}

# Fallback: search in text (keep for compatibility)
VESSEL_KEYWORDS = {
    "сп дудинка": "СП Дудинка",
    "сп диксон": "СП Диксон",
    "дудинка": "СП Дудинка",
    "диксон": "СП Диксон",
}

# -------------------------------------------------------------------
# Connect and select folder
# -------------------------------------------------------------------
def connect_imap():
    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    print(f"Logged in to {IMAP_SERVER} as {EMAIL_ADDRESS}")
    
    typ, data = mail.select(MAILBOX_FOLDER)
    if typ != 'OK':
        print(f"Could not select '{MAILBOX_FOLDER}', trying 'INBOX'...")
        typ, data = mail.select("INBOX")
        if typ != 'OK':
            raise Exception(f"Failed to select mailbox: {data}")
    print(f"Selected folder: {MAILBOX_FOLDER if typ=='OK' else 'INBOX'}")
    return mail

# -------------------------------------------------------------------
# Email parsing helpers
# -------------------------------------------------------------------
def decode_mime_header(header):
    parts = decode_header(header)
    result = ""
    for part, enc in parts:
        if isinstance(part, bytes):
            result += part.decode(enc or 'utf-8', errors='ignore')
        else:
            result += str(part)
    return result.strip()

def get_email_body(msg):
    """Extract plain text body from email."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode('utf-8', errors='ignore')
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode('utf-8', errors='ignore')
    return ""

def parse_email_date(date_str):
    from email.utils import parsedate_to_datetime
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        return dt
    except:
        return None

def is_disp_report(text):
    """Check if text looks like DISP-01 (line starting with a number)."""
    for line in text.splitlines()[:20]:
        if re.match(r'^\d+\s+', line.strip()):
            return True
    return False

def find_vessel_name(from_addr, body):
    """Determine vessel name first by sender, then by keywords in body."""
    # 1. Sender mapping
    from_lower = from_addr.lower()
    for sender, vessel in VESSEL_BY_SENDER.items():
        if sender.lower() in from_lower:
            return vessel
    # 2. Keyword search in body and from address
    combined = (from_addr + " " + body).lower()
    for keyword, vessel in VESSEL_KEYWORDS.items():
        if keyword in combined:
            return vessel
    return None

def get_vessel_id_by_name(vessel_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM vessels WHERE name = ? AND is_active = 1", (vessel_name,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def report_exists(vessel_id, report_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id FROM daily_reports
        WHERE vessel_id = ? AND date(report_datetime) = date(?)
    """, (vessel_id, report_date))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_report(vessel_id, parsed_data):
    data = {
        'vessel_id': vessel_id,
        'report_datetime': parsed_data.get('report_datetime'),
        'distance_run_nm': parsed_data.get('distance_run_nm'),
        'avg_speed_knots': parsed_data.get('avg_speed_knots'),
        'rob_ifo_mt': parsed_data.get('rob_ifo_mt'),
        'rob_mgo_mt': parsed_data.get('rob_mgo_mt'),
        'consumption_ifo_24h_mt': None,
        'consumption_mgo_24h_mt': None,
        'next_port_name': parsed_data.get('next_port_name'),
        'free_text': parsed_data.get('free_text'),
        'raw_disp_text': parsed_data.get('raw_disp_text'),
        'is_approved': 1
    }
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cols = ', '.join(data.keys())
    placeholders = ', '.join(['?' for _ in data])
    cursor.execute(f"INSERT INTO daily_reports ({cols}) VALUES ({placeholders})", list(data.values()))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    print(f"  → Inserted report ID {new_id} for vessel {vessel_id} on {data['report_datetime']}")
    return new_id

def recalc_consumptions(vessel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, rob_ifo_mt, rob_mgo_mt
        FROM daily_reports
        WHERE vessel_id = ? AND rob_ifo_mt IS NOT NULL AND rob_mgo_mt IS NOT NULL
        ORDER BY report_datetime ASC
    """, (vessel_id,))
    rows = cursor.fetchall()
    if len(rows) >= 2:
        cursor.execute("UPDATE daily_reports SET consumption_ifo_24h_mt = NULL, consumption_mgo_24h_mt = NULL WHERE id = ?", (rows[0][0],))
        for i in range(1, len(rows)):
            prev = rows[i-1]
            curr = rows[i]
            ifo = round(prev[1] - curr[1], 2)
            mgo = round(prev[2] - curr[2], 2)
            if ifo < 0: ifo = 0
            if mgo < 0: mgo = 0
            cursor.execute("UPDATE daily_reports SET consumption_ifo_24h_mt = ?, consumption_mgo_24h_mt = ? WHERE id = ?", (ifo, mgo, curr[0]))
        conn.commit()
    conn.close()

# -------------------------------------------------------------------
# Main import
# -------------------------------------------------------------------
def import_emails():
    mail = connect_imap()
    
    # Determine search date
    if SEARCH_SINCE:
        date_since = SEARCH_SINCE
        print(f"Using custom SINCE date: {date_since}")
    else:
        date_since = (datetime.now() - timedelta(days=2)).strftime("%d-%b-%Y")
        print(f"Using default SINCE date (last 2 days): {date_since}")
    
    typ, msgnums = mail.search(None, f'(SINCE {date_since})')
    if typ != 'OK':
        print("No emails found.")
        mail.close()
        mail.logout()
        return
    
    email_ids = msgnums[0].split()
    print(f"Found {len(email_ids)} emails since {date_since}")
    
    for eid in email_ids:
        typ, msg_data = mail.fetch(eid, '(RFC822)')
        if typ != 'OK':
            continue
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)
        
        subject = decode_mime_header(msg.get("Subject", ""))
        from_addr = decode_mime_header(msg.get("From", ""))
        date_str = msg.get("Date", "")
        email_dt = parse_email_date(date_str)
        if not email_dt:
            print(f"Skipping email with invalid date: {subject}")
            continue
        
        # Time window check
        hour = email_dt.hour
        if not (8 - TIME_WINDOW_HOURS <= hour <= 8 + TIME_WINDOW_HOURS):
            print(f"Skipping email sent at {hour}:00 (not near 08:00): {subject}")
            continue
        
        body = get_email_body(msg)
        if not body:
            print(f"Skipping email with no plain text body: {subject}")
            continue
        
        if not is_disp_report(body):
            print(f"Skipping non-DISP email: {subject}")
            continue
        
        # Identify vessel
        vessel_name = find_vessel_name(from_addr, body)
        if not vessel_name:
            print(f"Could not determine vessel name for email from {from_addr}. Subject: {subject}")
            continue
        
        vessel_id = get_vessel_id_by_name(vessel_name)
        if not vessel_id:
            print(f"Vessel '{vessel_name}' not found in database. Skipping.")
            continue
        
        # Parse DISP-01
        from utils.disp_parser import disp_parser
        parsed = disp_parser.parse(body)
        report_dt = parsed.get('report_datetime')
        if not report_dt:
            print(f"Could not parse report datetime from email. Skipping.")
            continue
        
        if report_exists(vessel_id, report_dt.date()):
            print(f"Report already exists for {vessel_name} on {report_dt.date()}. Skipping.")
            continue
        
        save_report(vessel_id, parsed)
        recalc_consumptions(vessel_id)
        
        # Move to processed folder
        if PROCESSED_FOLDER:
            try:
                mail.create(PROCESSED_FOLDER)
            except:
                pass
            mail.copy(eid, PROCESSED_FOLDER)
            mail.store(eid, '+FLAGS', '\\Deleted')
            print(f"  → Moved email to {PROCESSED_FOLDER}")
        else:
            mail.store(eid, '+FLAGS', '\\Seen')
    
    mail.expunge()
    mail.close()
    mail.logout()
    print("Import finished.")

if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import_emails()