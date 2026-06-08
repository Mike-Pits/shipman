#!/usr/bin/env python3
"""
Migration script for Payments Phase 1.
Run this once before starting the app with the new Payments module.
"""

import sqlite3
import os

DB_PATH = "shipman.db"

def run_migration():
    if not os.path.exists(DB_PATH):
        print(f"Database {DB_PATH} not found. Please run main.py first to create it.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Create cost_types table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cost_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL CHECK(category IN ('income', 'expense')),
            name TEXT NOT NULL UNIQUE,
            typical_vendor_type TEXT,
            default_currency TEXT CHECK(default_currency IN ('RUB', 'USD')) DEFAULT 'RUB'
        )
    """)

    # 2. Create vendors table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS vendors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_type TEXT,
            legal_name TEXT NOT NULL,
            short_name TEXT,
            tax_id TEXT,
            address TEXT,
            email TEXT,
            phone TEXT,
            notes TEXT
        )
    """)

    # 3. Create payments table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vessel_id INTEGER,
            voyage_id INTEGER,
            charter_party_id INTEGER,
            vendor_id INTEGER,
            cost_type_id INTEGER NOT NULL,
            original_currency TEXT NOT NULL CHECK(original_currency IN ('RUB', 'USD')),
            original_amount REAL NOT NULL,
            rub_amount REAL NOT NULL,
            exchange_rate_used REAL,
            exchange_rate_date DATE,
            invoice_date DATE,
            due_date DATE,
            payment_date DATE,
            status TEXT CHECK(status IN ('draft', 'pending', 'partial', 'paid', 'overdue', 'cancelled')) DEFAULT 'draft',
            document_number TEXT,
            description TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by TEXT,
            FOREIGN KEY (vessel_id) REFERENCES vessels(id),
            FOREIGN KEY (voyage_id) REFERENCES voyages(id),
            FOREIGN KEY (charter_party_id) REFERENCES charter_parties(id),
            FOREIGN KEY (vendor_id) REFERENCES vendors(id),
            FOREIGN KEY (cost_type_id) REFERENCES cost_types(id)
        )
    """)

    # 4. Add vessel_id column to voyages (if not exists)
    cursor.execute("PRAGMA table_info(voyages)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'vessel_id' not in columns:
        cursor.execute("ALTER TABLE voyages ADD COLUMN vessel_id INTEGER REFERENCES vessels(id)")
        # Backfill vessel_id from charter_parties
        cursor.execute("""
            UPDATE voyages
            SET vessel_id = (SELECT vessel_id FROM charter_parties WHERE charter_parties.id = voyages.charter_party_id)
            WHERE charter_party_id IS NOT NULL
        """)
        print("Added vessel_id column to voyages and backfilled data.")

    # 5. Seed cost_types
    cost_types_data = [
        ('income', 'Freight', 'charterer', 'USD'),
        ('income', 'Demurrage', 'charterer', 'USD'),
        ('income', 'Hire (Time Charter)', 'charterer', 'USD'),
        ('expense', 'Bunkers', 'bunker_supplier', 'USD'),
        ('expense', 'Port Charges', 'port_authority', 'RUB'),
        ('expense', 'Canal Dues', 'canal_authority', 'USD'),
        ('expense', 'Pilotage', 'port_authority', 'RUB'),
        ('expense', 'Towage', 'tug_company', 'RUB'),
        ('expense', 'Agency Fees', 'agent', 'RUB'),
        ('expense', 'Crew Wages', 'crew_agency', 'RUB'),
        ('expense', 'Insurance', 'insurer', 'USD'),
        ('expense', 'Repairs & Maintenance', 'repair_yard', 'RUB'),
        ('expense', 'Spare Parts', 'spare_parts_supplier', 'RUB'),
        ('expense', 'Stores / Provisions', 'ship_chandler', 'RUB'),
        ('expense', 'Dry-docking Amortisation', 'internal', 'RUB'),
        ('expense', 'Office & Admin', 'various', 'RUB'),
    ]
    for cat, name, vendor_type, default_curr in cost_types_data:
        cursor.execute("""
            INSERT OR IGNORE INTO cost_types (category, name, typical_vendor_type, default_currency)
            VALUES (?, ?, ?, ?)
        """, (cat, name, vendor_type, default_curr))

    # 6. Seed a few default vendors (optional)
    vendors_data = [
        ('bunker_supplier', 'Lukoil Bunker', 'Lukoil', None, None, None, None, None),
        ('port_authority', 'Murmansk Commercial Sea Port', 'Murmansk Port', None, None, None, None, None),
        ('agent', 'Inchcape Shipping Services', 'Inchcape', None, None, None, None, None),
    ]
    for vtype, legal, short, tax, addr, email, phone, notes in vendors_data:
        cursor.execute("""
            INSERT OR IGNORE INTO vendors (vendor_type, legal_name, short_name, tax_id, address, email, phone, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (vtype, legal, short, tax, addr, email, phone, notes))

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

if __name__ == "__main__":
    run_migration()