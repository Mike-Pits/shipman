# ShipMan v2 — Migrating the dev environment from Ubuntu to Windows

Written 2026-09-07. Covers moving work on the **new app** (`backend/`, `frontend/`,
`SRS/`) from the Ubuntu laptop to a Windows office machine. The legacy Tkinter
app at the repo root (`main.py`, `modules/`, `mvp/`, `database/`, `utils/`,
`requirements.txt`, root-level `.db` files) is being replaced and does not
need to migrate.

## 1. What actually needs to move

The repo is on GitHub (`Mike-Pits/shipman`), so code moves via `git`. Three
things are **not** tracked by git (see `.gitignore`) and must be carried over
by hand:

| Item | Path | Why it's not in git | How to carry it |
|---|---|---|---|
| Backend secrets | `backend/.env` | Contains the real IMAP mailbox password | Copy manually over a private channel (encrypted USB, password manager note, etc.) — never via email/Slack in plaintext |
| The live database | `backend/shipman.db` | Binary data file, would bloat/pollute the repo | Copy the file directly (see §4) |
| Python virtualenv | `backend/venv/` | Platform-specific binaries, doesn't work cross-OS | Rebuild on Windows (§3) |
| Node modules | `frontend/node_modules/` | Platform-specific native deps, huge | Rebuild on Windows (`npm install`) |

Also check `git status` before you leave the Ubuntu machine — as of this
writing there is an **uncommitted** modified file
(`backend/app/services/cbr_rate_fetcher.py`) and an **untracked** directory
(`backend/scripts/`, containing `backfill_exchange_rates.py`). Neither will
show up on Windows via `git pull` until they're committed and pushed. Either
commit/push them first, or copy those files across manually if you want to
keep them uncommitted.

## 2. Prerequisites on the Windows machine

Install, in this order:

- **Git for Windows** — https://git-scm.com/download/win
- **Python 3.12+** (the Ubuntu box runs 3.12.3) — from python.org, and
  **check "Add python.exe to PATH"** during install
- **Node.js 22.x** (Ubuntu box runs v22.23.0 / npm 12.0.2) — the LTS
  installer from nodejs.org is fine

Company machines sometimes lock down installers via IT policy — if `winget`
is available that's usually the path of least resistance:

```bash
winget install Git.Git Python.Python.3.12 OpenJS.NodeJS.LTS
```

## 3. Clone and set up

```bash
git clone https://github.com/Mike-Pits/shipman.git
cd shipman
```

**Backend:**

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -e ".[dev]"
```

(`venv\Scripts\activate` is the Windows equivalent of Ubuntu's
`source venv/bin/activate` — this is the main day-to-day difference you'll
retype from muscle memory.)

**Frontend:**

```bash
cd frontend
npm install
```

## 4. Bring over the secrets and the data

Copy these two files from the Ubuntu machine into the same relative location
on Windows:

- `backend/.env` → `backend/.env`
- `backend/shipman.db` → `backend/shipman.db`

If you'd rather start Windows with a clean slate instead of copying the live
DB, skip the `shipman.db` copy — the app creates a fresh empty one
automatically on first run (`Base.metadata.create_all` in
`backend/app/main.py`). But note that's also where the exchange-rate backfill
(2021-12-01 → today, 1,742 days) lives, so a fresh DB means re-running
`python -m scripts.backfill_exchange_rates` before entering any USD payments.

## 5. Run it

Backend (from `backend/`, venv activated):

```bash
uvicorn app.main:app --port 8010
```

Frontend (from `frontend/`, separate terminal):

```bash
npm run dev -- --port 5180
```

If you're also running Claude Code on the Windows box, `SRS/.claude/launch.json`
has the Ubuntu absolute paths (`/home/mike-pi/...`) hardcoded in
`runtimeArgs` — update those to the Windows checkout path, or Claude's
`preview_start` won't find the right directory.

## 6. Windows-specific gotchas

- **Line endings**: the repo has no `.gitattributes`, so without configuration
  git may check files out with CRLF on Windows. Run
  `git config --global core.autocrlf true` once, before cloning, so Python/TS
  source stays LF-clean in the repo and CRLF locally (avoids noisy diffs).
- **The sqlite URL is relative** (`sqlite:///./shipman.db` in
  `backend/app/database.py`) and forward-slash — this works unchanged on
  Windows as long as you run `uvicorn` from inside `backend/`.
- **No shell scripts** (`.sh`) exist in `backend/` or `frontend/` — nothing
  there needs a WSL/Git-Bash shim to run.
- **Backfill script re-runs are safe** either way: `backfill_exchange_rates.py`
  checks existing dates first and skips them, so running it again on Windows
  against a freshly copied `shipman.db` is a fast no-op if the data's already
  there.
- **IMAP/email import** (`email_importer.py`, `SHIPMAN_EMAIL*` vars) depends
  on outbound network access to your mail server on port 993 — confirm the
  office network/firewall allows that before relying on it there.
