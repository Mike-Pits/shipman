Here is the **revised MVP schedule** based on the final SRS v2.1, incorporating:
- Full DISP-01 parser (40+ codes)
- CBR API integration for daily exchange rates
- Bunker replenishment logic
- Port call costs
- Historical currency conversion
- Limited audit log (excluding vessels/config)
- Bilingual UI

---

# ShipMan MVP Development Schedule (Revised)
## Duration: 10 weeks (part-time, solo developer on Ubuntu)

**Start assumption:** You have Python 3.10+, Tkinter, sqlite3, and basic dev environment ready.

---

## Week 1: Foundation & Database

### Days 1-2: Project Setup
- [ ] Create project structure as per SRS
- [ ] Set up Python virtual environment
- [ ] Install dependencies: `pip install pandas openpyxl requests beautifulsoup4`
- [ ] Create empty SQLite database
- [ ] Write `schema.sql` with all 12 tables (per SRS v2.1)

### Days 3-5: Database Layer & Utilities
- [ ] `db_manager.py` – connection wrapper, query helpers
- [ ] `language_manager.py` – load strings from DB, bilingual toggle
- [ ] `validators.py` – IMO, date, coordinate, fuel consumption logic
- [ ] `audit.py` – audit log writer (excluding vessels/config)
- [ ] Seed initial data: default users (operator/admin), language strings (50+ UI terms in EN/RU)

### Deliverable: Database schema loaded, app can connect and switch languages.

---

## Week 2: User Authentication & Main Window

### Days 1-2: Login System
- [ ] Login window with username/password
- [ ] Password hashing (bcrypt)
- [ ] Language toggle on login screen
- [ ] Role-based session storage

### Days 3-5: Main Window & Navigation
- [ ] Main window with menu bar (bilingual)
- [ ] Tab control framework: placeholder tabs for each module
- [ ] Status bar (user role, current currency display mode, last CBR rate update)
- [ ] Currency display toggle (RUB/USD) in toolbar
- [ ] "Update Exchange Rate" button (manual trigger)

### Deliverable: User can login, see main window, switch language, toggle currency display.

---

## Week 3: Vessel Management (No Audit Logging)

### Days 1-3: Vessel CRUD
- [ ] Vessel registration form (all technical fields – ~20 fields)
- [ ] Fuel consumption profile sub-form (6 modes × IFO/MGO)
- [ ] List view of vessels (table)
- [ ] Add/edit/delete (soft delete with is_active flag)
- [ ] **Audit log explicitly skipped for vessel changes** (per SRS)

### Days 4-5: Validation & Testing
- [ ] IMO number uniqueness check
- [ ] Required field validation
- [ ] Bilingual labels on all fields
- [ ] Test with 3 dummy vessels

### Deliverable: Operator can register and manage vessels.

---

## Week 4: DISP-01 Parser (Core Complex Module)

### Days 1-3: Parser Engine
- [ ] Write `disp_parser.py` with regex patterns for each code (1–100, plus NNNN)
- [ ] Handle multiple formats: `code value`, `code value1/value2`, `code value text`
- [ ] Date parser: `DDMM/HHMM` and `DDMM/HH:MM` → ISO format
- [ ] Coordinate parser: `DDMMN/DDDMME` → decimal degrees
- [ ] Extract ship name and voyage number from header lines

### Days 4-5: Parser Integration
- [ ] Create daily report entry form with two modes:
  - Large text box for DISP-01 paste
  - Manual field-by-field entry
- [ ] "Parse" button – fills manual form from pasted text
- [ ] Preview of extracted fields, highlight missing required
- [ ] Save to `daily_reports` table

### Deliverable: DISP-01 parser handles all codes from Appendix A correctly.

---

## Week 5: Daily Report Validation & Workflow

### Days 1-2: Validation Rules
- [ ] Duplicate check (vessel + report date)
- [ ] Future date prevention
- [ ] Fuel consumption soft warning (FR-07):
  - Calculate expected consumption from previous day's ROB
  - Check for bunker replenishment in last 24h
  - Show warning if consumption > 20% above normal and no bunkering

### Days 3-4: Approval Workflow
- [ ] Report list view (by vessel, date range, status)
- [ ] Operator can approve reports
- [ ] Approved reports become read-only (admin can override)
- [ ] Audit log records all changes

### Day 5: Overdue Detection
- [ ] Dashboard component query for overdue reports (>30 hours)
- [ ] Visual indicator (red flag) in vessel status table

### Deliverable: Complete daily report lifecycle – entry, validation, approval, overdue alerts.

---

## Week 6: Charter Parties & Voyages (Many-to-One)

### Days 1-3: Charter Party Management
- [ ] Single large form for charter data (per SRS Appendix B)
- [ ] Contract currency selection (RUB/USD)
- [ ] Dynamic broker fields (up to 3, with commission %)
- [ ] Store exchange rate used at charter date (from CBR or manual)

### Days 4-5: Voyage Management
- [ ] Voyage list under each charter party
- [ ] Create/edit voyages (ports, dates, cargo, laden flag)
- [ ] Link daily reports to voyages (dropdown when entering report)
- [ ] Validate that voyage dates align with daily report dates

### Deliverable: Charter parties with multiple voyages, linked to daily reports.

---

## Week 7: Bunker Replenishment, Port Costs & Voyage Costs

### Days 1-2: Bunker Replenishment Module
- [ ] Dedicated form for bunkering events
- [ ] Fields: vessel, datetime, port, fuel grade(s), amounts, cost, currency, supplier, invoice
- [ ] List view of bunkering history
- [ ] Integration with daily report validation (suppresses consumption warnings)

### Days 3-4: Voyage Costs & Port Call Costs
- [ ] Voyage-level costs form (d/as, fuel prices, pilotage, ice-breakers, towage, port charges, canal dues, agency fees)
- [ ] Port call costs – same categories but linked to specific port
- [ ] Currency selection per cost (RUB/USD) with exchange rate at entry date

### Day 5: Testing
- [ ] Test bunker replenishment + consumption warning suppression
- [ ] Test cost entry with different currencies and dates

### Deliverable: Complete cost and bunker tracking.

---

## Week 8: Payments & Exchange Rate Automation

### Days 1-2: CBR API Integration
- [ ] `cbr_rate_fetcher.py` – HTTP GET to `https://www.cbr.ru/eng/currency_base/daily/`
- [ ] Parse HTML table, extract USD row (char code 840), get rate
- [ ] Store in `exchange_rates` table (date, rate, source='cbr_api')
- [ ] Run at application startup daily
- [ ] Fallback to last known rate if fetch fails, log error

### Days 3-4: Payment Tracking
- [ ] Auto-generate expected payments from charter party data
- [ ] Payment entry/editing form (original currency + amount)
- [ ] Display logic: when viewing in RUB mode, convert using historical rate (from transaction date)
- [ ] Payment status workflow (pending/invoiced/partial/received/overdue)
- [ ] Overdue calculation (expected_date < today and status not 'received')

### Day 5: Dashboard Payment Alerts
- [ ] Display upcoming (≤7 days) and overdue payments
- [ ] Show original amount + currency, and converted amount in current display currency

### Deliverable: Automated daily rates, dual-currency payments with historical conversion.

---

## Week 9: Reports (On-Demand Only)

### Days 1-2: Fuel Efficiency & Distance Reports
- [ ] Fuel efficiency report: actual vs spec consumption by vessel/date range/operational mode
- [ ] Distance & speed summary: total nm, avg speed
- [ ] Export to Excel (pandas)

### Days 3-4: Commercial & Financial Reports
- [ ] Total cargo carried (MT) per vessel/date range
- [ ] Total number of voyages
- [ ] Financial summary: income vs costs vs profit (with currency toggle)
- [ ] Port call cost breakdown by voyage/port
- [ ] Bunker replenishment history report

### Day 5: Report UI Integration
- [ ] Report selection window with date pickers, vessel filters
- [ ] "Generate" button → display preview (table)
- [ ] "Export to Excel" button
- [ ] No scheduled/automated reports (per SRS)

### Deliverable: All reports on-demand, exportable to Excel.

---

## Week 10: Polish, Testing & Documentation

### Days 1-2: Audit Log Verification
- [ ] Verify audit log records changes to: daily reports, charters, payments, costs, bunkering, rate overrides
- [ ] Verify audit log does NOT record: vessel changes, config changes, user changes (except role)
- [ ] Test with real scenarios

### Days 3-4: Full System Testing
- [ ] End-to-end test with 2 vessels, 30 days of DISP-01 messages
- [ ] Test bilingual UI (all strings covered)
- [ ] Test currency toggle with historical rates
- [ ] Test CBR rate fetch (mock offline mode)
- [ ] Test backup function (copy .db file)

### Day 5: Documentation & Packaging
- [ ] Write user manual (EN + RU) – PDF
- [ ] Write admin guide (backup, rate override, user management)
- [ ] Package with PyInstaller (standalone executable for Ubuntu)
- [ ] Create `.desktop` file for easy launch
- [ ] Final delivery to operator

### Deliverable: Production-ready MVP.

---

## Critical Path Dependencies

| Week | Depends On |
|------|-------------|
| Week 4 (Parser) | Week 3 (Vessels – to know vessel names for matching) |
| Week 5 (Validation) | Week 4 (Parser) + Week 7 (Bunker replenishment for warning suppression) |
| Week 7 (Bunkering) | Week 3 (Vessels) |
| Week 8 (Payments) | Week 6 (Charter parties) |
| Week 9 (Reports) | Weeks 4-8 (All data modules) |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-------------|
| DISP-01 format varies by master | Build flexible parser with manual override; preview before save |
| CBR website changes structure | Implement scraping with fallback: user can enter rate manually |
| Fuel consumption warning too noisy | Make threshold configurable (default 20% above spec) |
| Historical rates missing for old transactions | Allow manual rate entry for any date via admin panel |
| Bilingual strings incomplete | Include fallback to English if Russian missing |

---

## Tools & Libraries Summary

```txt
# requirements.txt
pandas==2.1.0
openpyxl==3.1.2
requests==2.31.0
beautifulsoup4==4.12.2
bcrypt==4.0.1
```

---

## Weekly Effort Estimate (Hours)

| Week | Hours (part-time) |
|------|------------------|
| 1 | 8-10 |
| 2 | 8-10 |
| 3 | 8-10 |
| 4 | 12-15 (parser complexity) |
| 5 | 8-10 |
| 6 | 10-12 |
| 7 | 8-10 |
| 8 | 10-12 |
| 9 | 8-10 |
| 10 | 8-10 |
| **Total** | **~90-110 hours** |

---

## Suggested Milestone Checkpoints

- **End of Week 4:** DISP-01 parser working – test with 5 example messages
- **End of Week 6:** Charter + voyages + daily report linking working
- **End of Week 8:** Payments with historical currency conversion working
- **End of Week 10:** Full system ready for user acceptance testing

---

This schedule is realistic for a solo developer working evenings/weekends. **Shall I also provide a detailed weekly task breakdown with code file names and function signatures?**