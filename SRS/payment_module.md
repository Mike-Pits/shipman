# Revised Data Model Additions – Payments Module (Phase 1)

## 1. Overview

Phase 1 introduces core payment tracking for both **income** (receivables) and **expenses** (payables). All monetary transactions are stored in a central `payments` table, with support for dual currency (RUB/USD) and links to vessels, voyages, charter parties, vendors, and cost types.

The structure is designed to later support **TCE (Time Charter Equivalent)** calculation in Phase 2.

---

## 2. New Tables

### 2.1 `cost_types`

A lookup table that categorises each payment as either income or expense, and provides a standardised name.

```sql
CREATE TABLE cost_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL CHECK(category IN ('income', 'expense')),
    name TEXT NOT NULL UNIQUE,
    typical_vendor_type TEXT,   -- optional, e.g., 'bunker_supplier'
    default_currency TEXT CHECK(default_currency IN ('RUB', 'USD')) DEFAULT 'RUB'
);
```

**Sample data (Phase 1 – essential items):**

| id | category | name | typical_vendor_type |
|----|----------|------|----------------------|
| 1 | income | Freight | charterer |
| 2 | income | Demurrage | charterer |
| 3 | income | Hire (Time Charter) | charterer |
| 4 | expense | Bunkers | bunker_supplier |
| 5 | expense | Port Charges | port_authority |
| 6 | expense | Canal Dues | canal_authority |
| 7 | expense | Pilotage | port_authority |
| 8 | expense | Towage | tug_company |
| 9 | expense | Agency Fees | agent |
| 10 | expense | Crew Wages | crew_agency |
| 11 | expense | Insurance | insurer |
| 12 | expense | Repairs & Maintenance | repair_yard |
| 13 | expense | Spare Parts | spare_parts_supplier |
| 14 | expense | Stores / Provisions | ship_chandler |
| 15 | expense | Dry-docking Amortisation | internal |
| 16 | expense | Office & Admin | various |

### 2.2 `vendors`

Counterparties for expense payments (suppliers, authorities, agents). For income payments, the counterparty is typically the charterer, which is already stored in `charter_parties`.

```sql
CREATE TABLE vendors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_type TEXT CHECK(vendor_type IN ('bunker_supplier', 'port_authority', 'canal_authority', 'agent', 'repair_yard', 'classification_society', 'crew_agency', 'insurer', 'spare_parts', 'ship_chandler', 'other')),
    legal_name TEXT NOT NULL,
    short_name TEXT,
    tax_id TEXT,
    address TEXT,
    email TEXT,
    phone TEXT,
    notes TEXT
);
```

### 2.3 `payments` (central transaction log)

This table stores every financial transaction – both expected and actual, income and expense.

```sql
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Links
    vessel_id INTEGER,                -- which vessel (optional if not voyage-specific)
    voyage_id INTEGER,                -- link to voyages (NULL if not voyage-related)
    charter_party_id INTEGER,         -- link to charter party (e.g., for time charter hire)
    vendor_id INTEGER,                -- for expenses (FK to vendors)
    cost_type_id INTEGER NOT NULL,    -- FK to cost_types (income or expense)
    
    -- Financial fields (dual currency)
    original_currency TEXT NOT NULL CHECK(original_currency IN ('RUB', 'USD')),
    original_amount REAL NOT NULL,
    rub_amount REAL NOT NULL,          -- converted at the time of entry
    exchange_rate_used REAL,           -- the rate used for conversion
    exchange_rate_date DATE,           -- date of that rate
    
    -- Dates & status
    invoice_date DATE,
    due_date DATE,
    payment_date DATE,
    status TEXT CHECK(status IN ('draft', 'pending', 'partial', 'paid', 'overdue', 'cancelled')) DEFAULT 'draft',
    
    -- Document info
    document_number TEXT,
    description TEXT,
    notes TEXT,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    
    FOREIGN KEY (vessel_id) REFERENCES vessels(id),
    FOREIGN KEY (voyage_id) REFERENCES voyages(id),
    FOREIGN KEY (charter_party_id) REFERENCES charter_parties(id),
    FOREIGN KEY (vendor_id) REFERENCES vendors(id),
    FOREIGN KEY (cost_type_id) REFERENCES cost_types(id)
);

-- Indexes for performance
CREATE INDEX idx_payments_vessel ON payments(vessel_id);
CREATE INDEX idx_payments_voyage ON payments(voyage_id);
CREATE INDEX idx_payments_due_date ON payments(due_date);
CREATE INDEX idx_payments_status ON payments(status);
```

---

## 3. Modifications to Existing Tables

### 3.1 `voyages` – add `vessel_id` column

To simplify joins and reporting (especially for TCE), we add `vessel_id` directly to the `voyages` table. This also makes it easier to list voyages without always joining via `charter_parties`.

```sql
-- Add vessel_id column (allow NULL temporarily, then backfill)
ALTER TABLE voyages ADD COLUMN vessel_id INTEGER REFERENCES vessels(id);

-- Backfill vessel_id from charter_parties
UPDATE voyages 
SET vessel_id = (SELECT vessel_id FROM charter_parties WHERE charter_parties.id = voyages.charter_party_id)
WHERE charter_party_id IS NOT NULL;

-- Now make vessel_id NOT NULL after backfill
-- (SQLite does not support ALTER COLUMN NOT NULL directly; recreate table or handle in app logic)
-- We will enforce NOT NULL at application level and via schema in future migration.
```

For Phase 1, we will rely on application logic to ensure `vessel_id` is set when creating a voyage.

### 3.2 `charter_parties` – no changes needed.

---

## 4. Phase 1 Implementation Scope

Phase 1 focuses on **manual entry and tracking** of payments. No automatic generation from charters, no TCE calculation yet.

### 4.1 Features included

- **Payments tab** in the main window (sub‑tab "Transactions").
- Filterable list of payments (by vessel, voyage, cost type, status, date range).
- Add / Edit / Delete payment dialog.
- Currency handling: user selects RUB or USD, system converts to RUB using exchange rate from `exchange_rates` table (or manual override).
- Link payments to:
  - Vessel (required)
  - Voyage (optional, dropdown of voyages for selected vessel)
  - Charter party (optional, dropdown of charter parties for selected vessel)
  - Vendor (for expenses, optional)
- Status management (draft → pending → paid / overdue).
- Basic reporting: simple list export to Excel (via existing `excel_exporter`).

### 4.2 Features excluded from Phase 1 (for Phase 2)

- Automatic generation of expected income from charter parties.
- Voyage cost templates.
- TCE calculation and report.
- Integration with daily reports or bunker replenishments.

---

## 5. UI Sketch (Payments Tab – Phase 1)

The new tab will be placed after the Voyages tab in the main notebook.

**Toolbar:**
- [Add Payment] [Edit] [Delete] [Refresh]

**Filter bar:**
- Vessel: dropdown
- Voyage: dropdown (filtered by selected vessel)
- Cost type: dropdown (income/expense categories)
- Status: dropdown
- Date range: from / to

**Treeview columns:**
- Date (invoice date or transaction date)
- Type (income / expense)
- Cost Type
- Vendor (if expense)
- Original Amount & Currency
- RUB Amount
- Status
- Linked Voyage
- Document #

**Double‑click** or **Edit** button opens the payment dialog.

---

## 6. Next Steps After Phase 1

Once Phase 1 is stable and tested, Phase 2 will add:

- Auto‑generation of expected income from charter parties.
- TCE calculation engine.
- Voyage performance report (TCE per day).
- Cost estimation templates.

---

## 7. Approval & Rollout

✅ The revised structure approved.  
✅ Confirmed adding `vessel_id` to `voyages`.  
✅ Phase 1 implementation will begin first.

Need to produce the complete code for:

1. Database migration (create new tables, alter voyages, seed cost_types).
2. Payments tab UI (module `payments.py`).
3. Integration into `main_window.py`.
4. Updates to `voyages` management to include `vessel_id`.

