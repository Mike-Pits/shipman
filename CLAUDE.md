# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Two applications live in this one repo:

- **`backend/` + `frontend/`** — the active project: **ShipMan v2**, a ground-up rewrite of a commercial ship-management tool for a Russian-flag tanker owner/operator (chartering, voyage economics, payments, reporting). This is what all current work targets.
- **Everything else at the repo root** (`main.py`, `modules/`, `mvp/`, `database/`, `utils/`, root-level `requirements.txt`, `*.db` files, `email_importer.py`, `debug_parser.py`) — the legacy **v1 Tkinter desktop app** being replaced. It is not being extended; don't confuse its code or its `README.md` (which documents v1) with the v2 spec. Treat it as read-only reference unless explicitly asked to touch it.

The authoritative spec for v2 is [`SRS/SRS_v2.md`](SRS/SRS_v2.md) (functional requirements FR-01 onward, phasing, acceptance criteria) — not the root `README.md`, which describes v1. Domain vocabulary and terminology to use (and to avoid) is in [`SRS/CONTEXT.md`](SRS/CONTEXT.md). Architecture decisions with real rationale live in `SRS/docs/adr/`:

- **ADR-0001**: local web app (FastAPI + browser frontend on the same machine) chosen over a native desktop toolkit, specifically to force a real API boundary between backend and UI and to be OS-agnostic.
- **ADR-0002 / ADR-0003**: RUB is the reporting/aggregation currency (not USD) — ADR-0002 proposed USD, the operator corrected it, ADR-0003 reverses it. USD is still fully tracked as a secondary currency, just not the storage/aggregation base.
- **ADR-0004**: year-resolution for multi-year historical daily reports — IMAP retrieval anchors year-inference to the source email's `Date:` header (not "today"), and manual entry accepts an explicit `YYYY-MM-DD/HHMM` date line for historical backfill.
- **ADR-0005**: a folder↔vessel registry (`imap_folder_vessel_mappings`) guards against misattributing IMAP-polled daily reports to the wrong vessel — a real incident (44 reports misattributed) is why this exists. A poll of a folder already registered to a different vessel is blocked (409) unless `confirm_vessel_change: true` is passed.

## Commands

### Backend (`backend/`, Python 3.12+, FastAPI + SQLAlchemy + SQLite)

```bash
cd backend
python -m venv venv && source venv/bin/activate   # first time only
pip install -e ".[dev]"                            # first time / after dependency changes
uvicorn app.main:app --port 8010                    # run the API (no --reload configured)
python -m pytest tests/ -q                          # full test suite
python -m pytest tests/test_fixtures.py -q          # one file
python -m pytest tests/test_fixtures.py::test_operator_can_create_a_time_charter_out_fixture_with_configured_payment_terms -q  # one test
```

Tests never touch `backend/shipman.db` — `conftest.py`'s `client` fixture builds a fresh SQLite file under `tmp_path` per test via `Base.metadata.create_all`, so schema changes to a model are picked up automatically in tests but **not** in the real dev database (see below).

### Frontend (`frontend/`, React 19 + TypeScript + Vite + Vitest)

```bash
cd frontend
npm install                        # first time / after dependency changes
npm run dev -- --port 5180         # dev server (proxies /api -> http://localhost:8010, see vite.config.ts)
npm run build                      # tsc -b && vite build
npm run lint                       # oxlint
npx vitest run                     # full test suite
npx vitest run src/pages/FixturesPage.test.tsx   # one file
```

Both dev servers are also declared in `SRS/.claude/launch.json` (`shipman-backend`, `shipman-frontend`) for `preview_start`.

### Applying a backend model change to the live dev database

`Base.metadata.create_all` (run at app startup) only creates missing tables — it does **not** alter existing ones. There is no migration framework (no Alembic). After changing a model:
- New column, nullable or with a default → safe to `ALTER TABLE ... ADD COLUMN` directly against `backend/shipman.db` with `sqlite3`.
- A column becoming nullable, or any other change SQLite's limited `ALTER TABLE` can't express → rebuild the table (`CREATE TABLE ..._new`, `INSERT INTO ... SELECT`, `DROP TABLE`, `RENAME TABLE`), preserving `id` values so other tables' foreign keys keep resolving. Back up the `.db` file first — this is real operator data, not fixtures.

## Architecture

### Backend layout

Each domain module follows the same three-layer shape: `app/models/<name>.py` (SQLAlchemy ORM), `app/schemas/<name>.py` (Pydantic request/response, including cross-field validation via `@model_validator`), `app/routers/<name>.py` (FastAPI endpoints, registered in `app/main.py`). Cross-cutting logic lives in `app/services/`: `currency.py` (RUB conversion using the historical rate for a transaction's own date — never today's rate), `vat.py` (VAT-inclusive/exclusive math shared by fixtures, invoices, off-hire), `audit.py` (see below), `cbr_rate_fetcher.py` / `imap_fetcher.py` / `disp01_parser.py` (external integrations), `invoice_builder.py` / `invoice_numbering.py` (invoice line/total computation and sequential numbering), `flexible_datetime.py` (tolerant `YYYY-MM-DD[ HH:MM[:SS]]` parsing, used wherever a date field may or may not carry time precision), `excel_export.py`, `vetting.py`.

**A single flat table with a type/purpose discriminator, rather than subtype tables, is the recurring pattern for anything with multiple "shapes"**: `Fixture` (voyage_charter / time_charter_out / coa — irrelevant columns nullable per type), `Voyage` (`voyage_purpose`: employment / ballast_passage / drydock_repair — `fixture_id`, cargo fields, etc. are nullable and only required for `employment`), `Invoice` (hire / freight / demurrage / free_form). When adding a new variant to one of these, follow the same shape: nullable columns, a `model_validator(mode="after")` enforcing which fields are required for which type, and frontend form fields that show/hide per the selected type (see `FixturesPage.tsx` / `VoyagesPage.tsx` / `InvoicingPage.tsx` for the matching frontend pattern).

**Audit logging** (`app/services/audit.py`) is automatic via SQLAlchemy `after_insert`/`after_update`/`after_delete` mapper events, registered once in `app.main` for an explicit allow-list of models (`register_audit_listener`). Vessels and system config are deliberately excluded. A new transactional model needs adding to that allow-list; child line-item tables (`FixtureBroker`, `DisbursementAccountLine`, `InvoiceLine`, etc.) are **not** separately audited — only their parent is.

**Money flow**: `Payment` is the single ledger table everything settles into — `cost_category` (`income`/`expense`), original currency + amount, plus a RUB-equivalent computed at entry via `services/currency.py`. Voyage P&L, TCE, and Fleet P&L (`app/routers/reports.py`) are all just queries over `Payment` filtered by `voyage_id` or date range — they do not read Fixture rates directly. Invoicing (`app/routers/invoices.py`) is a layer on top: issuing an invoice computes a total from Fixture/Voyage data and creates exactly one linked `Payment`; voiding deletes that `Payment`. The three-way "not-earning time" split (employment / unfixed ballast / drydock) added to `Voyage` (see `SRS_v2.md` §4.17) feeds `reports.py`'s `fleet-utilization` and `current-vessel-status` endpoints — off-hire (mid-charter hire deduction, `OffHirePeriod`) and drydock (no charter in force) are intentionally kept as separate mechanisms and reported as separate figures, not merged.

### Frontend layout

`src/pages/*Page.tsx` — one component per module, each owning its own list-fetch, create/edit form, and (where relevant) inline expandable line-item rows; no shared page framework beyond the `.table-scroll` CSS class (bounds any growing list table) and the `Badge`/`Card`/`StatCard` components in `src/components/ui/`. `src/api/*.ts` — thin per-module fetch wrappers around `src/api/client.ts` (`apiGet`/`apiPost`/`apiPut`/`apiDelete`, all requests go through `/api`, proxied to the backend per ADR-0001). `src/api/types.ts` — the TypeScript shapes mirroring the backend Pydantic schemas (kept in sync by hand; a backend schema field change needs a matching edit here). `src/i18n/{en,ru}.json` — every UI string, namespaced by page; the app has no manual dark-mode or locale-detection UI beyond `LanguageToggle`, and tests reset to `en` in `src/test/setup.ts`'s `beforeEach`.

The design system ("Bridge & Chart": navy/steel-blue, automatic light/dark via `prefers-color-scheme`, dense tabular-numeric tables) is defined once in `src/index.css` (CSS custom properties, base element styles, `.table-scroll`, `.alert-danger`) and `src/App.css` (nav layout). New pages should reuse these rather than inline styles.

## Testing conventions

Backend tests hit the real FastAPI app through `TestClient` against an isolated per-test SQLite file (no mocking of the ORM layer); look at an existing `test_<module>.py` for the `*_payload()` helper-function pattern before writing a new one. Frontend tests mock `global.fetch` directly (see any `*Page.test.tsx` for the `mockFetchByUrl`/`mockFetchSequence` helper pattern — matching by URL substring is more robust than positional call-order matching once a page fires more than one fetch on mount). UI changes are expected to be verified live via the running dev servers, not just by the test suites passing.
