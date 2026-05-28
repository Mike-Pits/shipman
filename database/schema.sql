-- =====================================================
-- SHIPMAN MVP DATABASE SCHEMA v2.1 (CORRECTED)
-- =====================================================

-- Enable foreign keys
PRAGMA foreign_keys = ON;

-- 1. USERS & ROLES
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('master', 'operator', 'finance', 'admin')),
    vessel_id INTEGER,
    full_name TEXT,
    language_pref TEXT DEFAULT 'en' CHECK(language_pref IN ('en', 'ru')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. VESSELS
CREATE TABLE IF NOT EXISTS vessels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    imo_number TEXT UNIQUE,
    year_built INTEGER,
    flag TEXT,
    vessel_type TEXT CHECK(vessel_type IN ('tanker', 'dry-cargo', 'tug')),
    deadweight_mt REAL,
    loa_m REAL,
    beam_m REAL,
    draft_fully_laden_m REAL,
    cargo_capacity_cbm REAL,
    main_engine_kw REAL,
    speed_laden_knots REAL,
    fuel_consumption_laden_ifo_mt_per_day REAL,
    fuel_consumption_laden_mgo_mt_per_day REAL,
    speed_ballast_knots REAL,
    fuel_consumption_ballast_ifo_mt_per_day REAL,
    fuel_consumption_ballast_mgo_mt_per_day REAL,
    fuel_consumption_idle_ifo_mt_per_day REAL,
    fuel_consumption_idle_mgo_mt_per_day REAL,
    fuel_consumption_cargo_ops_ifo_mt_per_day REAL,
    fuel_consumption_cargo_ops_mgo_mt_per_day REAL,
    fuel_consumption_boilers_ifo_mt_per_day REAL,
    fuel_consumption_boilers_mgo_mt_per_day REAL,
    fuel_consumption_cargo_heating_ifo_mt_per_day REAL,
    fuel_consumption_cargo_heating_mgo_mt_per_day REAL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. CHARTER PARTIES
CREATE TABLE IF NOT EXISTS charter_parties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id INTEGER NOT NULL,
    charter_type TEXT CHECK(charter_type IN ('time', 'voyage', 'bareboat')),
    charterer_name TEXT NOT NULL,
    charter_date DATE NOT NULL,
    contract_currency TEXT NOT NULL CHECK(contract_currency IN ('RUB', 'USD')),
    hire_rate_original REAL,
    hire_rate_rub REAL,
    cargo_name TEXT,
    cargo_quantity_fixed REAL,
    freight_rate_original REAL,
    freight_rate_rub REAL,
    freight_lumpsum_original REAL,
    freight_lumpsum_rub REAL,
    payment_terms TEXT,
    laytime_allowed_days REAL,
    laytime_basis TEXT,
    demurrage_rate_original REAL,
    demurrage_rate_rub REAL,
    nor_clauses TEXT,
    port_rotation TEXT,
    agents_name TEXT,
    exchange_rate_id INTEGER,
    exchange_rate_used REAL,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. BROKERS
CREATE TABLE IF NOT EXISTS brokers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    charter_party_id INTEGER NOT NULL,
    broker_name TEXT NOT NULL,
    commission_percentage REAL NOT NULL,
    broker_order INTEGER CHECK(broker_order BETWEEN 1 AND 3)
);

-- 5. VOYAGES
CREATE TABLE IF NOT EXISTS voyages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    charter_party_id INTEGER NOT NULL,
    voyage_number TEXT,
    load_port TEXT,
    discharge_port TEXT,
    start_date DATE,
    end_date DATE,
    cargo_name TEXT,
    cargo_quantity_loaded REAL,
    is_laden BOOLEAN,
    voyage_notes TEXT
);

-- 6. DAILY REPORTS - FIXED: removed invalid UNIQUE constraint
CREATE TABLE IF NOT EXISTS daily_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id INTEGER NOT NULL,
    voyage_id INTEGER,
    report_datetime TIMESTAMP NOT NULL,
    latitude TEXT,
    longitude TEXT,
    port_name TEXT,
    distance_run_nm REAL,
    avg_speed_knots REAL,
    rob_ifo_mt REAL,
    rob_mgo_mt REAL,
    consumption_ifo_24h_mt REAL,
    consumption_mgo_24h_mt REAL,
    operational_mode TEXT CHECK(operational_mode IN ('laden', 'ballast', 'idle', 'cargo_ops', 'cargo_heating')),
    eta_next_port TIMESTAMP,
    next_port_name TEXT,
    weather_wind_dir INTEGER,
    weather_wind_speed_ms INTEGER,
    weather_sea_state_points INTEGER,
    free_text TEXT,
    raw_disp_text TEXT,
    submitted_by_master TEXT,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_approved BOOLEAN DEFAULT 0,
    approved_by_operator TEXT
);

-- Create index instead of UNIQUE constraint
CREATE INDEX IF NOT EXISTS idx_daily_reports_vessel_date ON daily_reports(vessel_id, date(report_datetime));

-- 7. BUNKER REPLENISHMENTS
CREATE TABLE IF NOT EXISTS bunker_replenishments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vessel_id INTEGER NOT NULL,
    replenishment_datetime TIMESTAMP NOT NULL,
    port_name TEXT,
    fuel_grade TEXT CHECK(fuel_grade IN ('IFO', 'MGO', 'both')),
    ifo_amount_mt REAL,
    mgo_amount_mt REAL,
    cost_original REAL,
    cost_currency TEXT CHECK(cost_currency IN ('RUB', 'USD')),
    cost_rub REAL,
    supplier TEXT,
    invoice_number TEXT,
    exchange_rate_id INTEGER,
    exchange_rate_used REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. VOYAGE COSTS
CREATE TABLE IF NOT EXISTS voyage_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id INTEGER NOT NULL,
    cost_type TEXT CHECK(cost_type IN ('d_as', 'fuel_price', 'pilotage', 'ice_breakers', 'towage', 'port_charges', 'canal_dues', 'agency_fees', 'other')),
    description TEXT,
    original_currency TEXT NOT NULL CHECK(original_currency IN ('RUB', 'USD')),
    amount_original REAL NOT NULL,
    amount_rub REAL NOT NULL,
    invoice_date DATE,
    paid_date DATE,
    payment_status TEXT DEFAULT 'pending' CHECK(payment_status IN ('pending', 'paid')),
    exchange_rate_id INTEGER,
    exchange_rate_used REAL,
    notes TEXT
);

-- 9. PORT CALL COSTS
CREATE TABLE IF NOT EXISTS port_call_costs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    voyage_id INTEGER NOT NULL,
    port_name TEXT NOT NULL,
    cost_type TEXT CHECK(cost_type IN ('d_as', 'pilotage', 'towage', 'port_charges', 'agency_fees', 'other')),
    description TEXT,
    original_currency TEXT NOT NULL CHECK(original_currency IN ('RUB', 'USD')),
    amount_original REAL NOT NULL,
    amount_rub REAL NOT NULL,
    invoice_date DATE,
    paid_date DATE,
    payment_status TEXT DEFAULT 'pending' CHECK(payment_status IN ('pending', 'paid')),
    exchange_rate_id INTEGER,
    exchange_rate_used REAL,
    notes TEXT
);

-- 10. PAYMENTS
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    charter_party_id INTEGER NOT NULL,
    payment_type TEXT CHECK(payment_type IN ('hire', 'freight', 'demurrage', 'commission')),
    description TEXT,
    original_currency TEXT NOT NULL CHECK(original_currency IN ('RUB', 'USD')),
    expected_amount_original REAL NOT NULL,
    expected_amount_rub REAL NOT NULL,
    expected_date DATE,
    invoiced_currency TEXT CHECK(invoiced_currency IN ('RUB', 'USD')),
    invoiced_amount_original REAL,
    invoiced_amount_rub REAL,
    invoiced_date DATE,
    received_currency TEXT CHECK(received_currency IN ('RUB', 'USD')),
    received_amount_original REAL DEFAULT 0,
    received_amount_rub REAL DEFAULT 0,
    received_date DATE,
    exchange_rate_id INTEGER,
    exchange_rate_used REAL,
    payment_status TEXT DEFAULT 'pending' CHECK(payment_status IN ('pending', 'invoiced', 'partial', 'received', 'overdue')),
    broker_id INTEGER,
    notes TEXT
);

-- 11. EXCHANGE RATES
CREATE TABLE IF NOT EXISTS exchange_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rate_date DATE NOT NULL UNIQUE,
    usd_to_rub_rate REAL NOT NULL,
    source TEXT DEFAULT 'cbr_api',
    notes TEXT,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 12. AUDIT LOG
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    table_name TEXT,
    record_id INTEGER,
    action TEXT CHECK(action IN ('insert', 'update', 'delete', 'approve')),
    old_values TEXT,
    new_values TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 13. LANGUAGE STRINGS
CREATE TABLE IF NOT EXISTS language_strings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    en TEXT NOT NULL,
    ru TEXT NOT NULL
);

-- 14. SYSTEM CONFIG
CREATE TABLE IF NOT EXISTS system_config (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT
);

-- Insert default config
INSERT OR IGNORE INTO system_config (key, value, description) VALUES
    ('overdue_report_hours', '30', 'Hours after which report is considered overdue'),
    ('payment_reminder_days', '7', 'Days before payment due to show alert'),
    ('db_version', '2.1', 'Schema version'),
    ('default_currency', 'RUB', 'Default display currency'),
    ('fuel_consumption_warning_threshold_percent', '20', 'Warning if consumption exceeds spec by this %');

-- Insert default admin user (password: admin123)
INSERT OR IGNORE INTO users (username, password_hash, role, full_name) 
VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPjFjK7R8rS6K', 'admin', 'System Administrator');

-- Insert basic language strings
INSERT OR IGNORE INTO language_strings (key, en, ru) VALUES
    ('app_title', 'ShipMan - Fleet Management', 'ShipMan - Управление флотом'),
    ('login_title', 'Login', 'Вход'),
    ('username', 'Username', 'Имя пользователя'),
    ('password', 'Password', 'Пароль'),
    ('login_button', 'Login', 'Войти'),
    ('language', 'Language', 'Язык'),
    ('vessels_title', 'Vessels', 'Судна'),
    ('add_vessel', 'Add Vessel', 'Добавить судно'),
    ('edit_vessel', 'Edit Vessel', 'Редактировать судно'),
    ('delete_vessel', 'Delete Vessel', 'Удалить судно'),
    ('vessel_name', 'Vessel Name', 'Название судна'),
    ('imo_number', 'IMO Number', 'Номер IMO'),
    ('save', 'Save', 'Сохранить'),
    ('cancel', 'Cancel', 'Отмена'),
    ('refresh', 'Refresh', 'Обновить'),
    ('warning', 'Warning', 'Предупреждение'),
    ('success', 'Success', 'Успех'),
    ('confirm_delete', 'Are you sure you want to delete this item?', 'Вы уверены, что хотите удалить этот элемент?'),
    ('dashboard_title', 'Dashboard', 'Панель управления'),
    ('daily_reports_title', 'Daily Reports', 'Суточные рапорты'),
    ('charter_parties_title', 'Charter Parties', 'Чартер-партии'),
    ('payments_title', 'Payments', 'Платежи'),
    ('reports_title', 'Reports', 'Отчеты'),
    ('new_report', 'New Report', 'Новый рапорт'),
    ('reports_list', 'Reports List', 'Список рапортов'),
    ('report_entry', 'Report Entry', 'Ввод рапорта'),
    ('save_report', 'Save Report', 'Сохранить рапорт'),
    ('approve_report', 'Approve Report', 'Утвердить рапорт'),
    ('delete_report', 'Delete Report', 'Удалить рапорт'),
    ('parse_disp', 'Parse DISP-01', 'Разобрать DISP-01'),
    ('paste_disp_text', 'Paste DISP-01 Text Below:', 'Вставьте текст DISP-01 ниже:'),
    ('enter_disp_text', 'Please enter DISP-01 text to parse', 'Пожалуйста, введите текст DISP-01 для разбора'),
    ('date', 'Date', 'Дата'),
    ('distance_nm', 'Distance (nm)', 'Расстояние (мили)'),
    ('status', 'Status', 'Статус'),
    ('pending', 'Pending', 'Ожидает'),
    ('approved', 'Approved', 'Утвержден'),
    ('select_vessel', 'Select Vessel', 'Выберите судно'),
    ('report_datetime', 'Date/Time', 'Дата/Время'),
    ('speed_knots', 'Speed (knots)', 'Скорость (узлы)'),
    ('rob_ifo', 'ROB IFO (MT)', 'Остаток IFO (MT)'),
    ('rob_mgo', 'ROB MGO (MT)', 'Остаток MGO (MT)'),
    ('next_port', 'Next Port', 'Следующий порт'),
    ('remarks', 'Remarks', 'Примечания');