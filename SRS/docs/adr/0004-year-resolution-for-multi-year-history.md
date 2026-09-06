---
status: accepted
---

# Year resolution for multi-year historical daily reports

DISP-01's date code (1) only encodes day/month/hour/minute — never a year. The original heuristic (infer the current year, fall back to the previous year if that's in the future) only distinguishes "this year" from "last year," which breaks down once the app needs to ingest 4–5 years of history per vessel for trend analysis: the same `DDMM` recurs every year, so an isolated message carries no way to tell 2026 from 2022.

Two independent fixes were adopted rather than one:

1. **IMAP retrieval now anchors year-inference to the source email's own `Date:` header**, not the server's current date. `imap_fetcher.fetch_disp01_messages` was extended to return each message's envelope date alongside its body, and `disp01_parser.parse_report_datetime` accepts that as a `reference_date` — so an archived message resolves against the date it was actually sent, however long ago that was, rather than against today. Per-message anchoring means a poll spanning any date range resolves every message correctly, not just recent ones. The operator organizes the mailbox into one folder per vessel per year and polls each in turn (poll-imap remains one-vessel-per-call — no per-message vessel auto-detection was added; a mismatched-vessel poll is caught the same way a live one would be).

2. **Manual entry recognizes an explicit `YYYY-MM-DD/HHMM` date line** (in addition to the native `DDMM/HHMM`), used with no year-inference at all when present. This covers historical reports with no reliable envelope — the operator amends the date line to this format before pasting, specifically for cases automatic parsing doesn't cover.

The original today-relative heuristic is kept as the fallback for native-format dates with no better reference (ordinary same-day manual entry, or an IMAP message whose `Date:` header is missing/unparseable) — it's still correct there, since "today" genuinely is a trustworthy anchor for a report describing what just happened.
