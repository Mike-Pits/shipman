import sqlite3
import os
from contextlib import contextmanager

class DatabaseManager:
    """Handles all database connections and basic operations"""
    
    def __init__(self, db_path='shipman.db'):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database with schema if not exists"""
        if not os.path.exists(self.db_path):
            self._create_schema()
    
    def _create_schema(self):
        """Create all tables from schema.sql or fallback"""
        with self.get_connection() as conn:
            self._create_minimal_schema(conn)
    
    def _create_minimal_schema(self, conn):
        """Create minimal schema for testing"""
        # Users table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                vessel_id INTEGER,
                full_name TEXT,
                language_pref TEXT DEFAULT 'en',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Vessels table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS vessels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                imo_number TEXT UNIQUE,
                year_built INTEGER,
                flag TEXT,
                vessel_type TEXT,
                deadweight_mt REAL,
                loa REAL,
                beam REAL,
                me_power INTEGER,
                IFO_under_way INTEGER,
                IFO_idle REAL,
                IFO_boiler REAL,
                MGO_under_way REAL,
                MGO_idle REAL,
                MGO_discharging REAL,
                MGO_IGS REAL,
                speed_laden INTEGER,
                speed_ballast INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Daily reports table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vessel_id INTEGER NOT NULL,
                report_datetime TIMESTAMP NOT NULL,
                distance_run_nm REAL,
                avg_speed_knots REAL,
                rob_ifo_mt REAL,
                rob_mgo_mt REAL,
                consumption_ifo_24h_mt REAL,
                consumption_mgo_24h_mt REAL,
                operational_mode TEXT,
                next_port_name TEXT,
                free_text TEXT,
                raw_disp_text TEXT,
                is_approved BOOLEAN DEFAULT 0,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create index for faster lookups
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_daily_reports_vessel_date 
            ON daily_reports(vessel_id, date(report_datetime))
        """)
        
        # Charter parties table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS charter_parties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                vessel_id INTEGER NOT NULL,
                charter_type TEXT,
                charterer_name TEXT,
                charter_date DATE,
                contract_currency TEXT DEFAULT 'RUB',
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # Payments table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                charter_party_id INTEGER NOT NULL,
                payment_type TEXT,
                expected_amount_original REAL,
                original_currency TEXT DEFAULT 'RUB',
                expected_date DATE,
                payment_status TEXT DEFAULT 'pending'
            )
        """)
        
        # ... existing tables ...

        # Exchange rates table (required for currency features)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exchange_rates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_date DATE NOT NULL UNIQUE,
                usd_to_rub_rate REAL NOT NULL,
                source TEXT DEFAULT 'manual',
                notes TEXT,
                created_by TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert a default rate if none exists (today's rate, e.g., 92.50)
        conn.execute("""
            INSERT OR IGNORE INTO exchange_rates (rate_date, usd_to_rub_rate, source, notes)
            VALUES (date('now'), 92.50, 'default', 'Initial rate')
        """)

        # Audit log table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                username TEXT,
                table_name TEXT,
                record_id INTEGER,
                action TEXT,
                old_values TEXT,
                new_values TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Language strings table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS language_strings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                en TEXT NOT NULL,
                ru TEXT NOT NULL
            )
        """)
        
        # Insert default admin user (password: admin123)
        conn.execute("""
            INSERT OR IGNORE INTO users (username, password_hash, role, full_name)
            VALUES ('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPjFjK7R8rS6K', 'admin', 'System Administrator')
        """)
        
        # Insert basic language strings
        basic_strings = [
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
            ('remarks', 'Remarks', 'Примечания'),
            ('distance', 'Distance (nm)', 'Расстояние (мили)'),
        ]
        
        for key, en, ru in basic_strings:
            conn.execute("""
                INSERT OR IGNORE INTO language_strings (key, en, ru)
                VALUES (?, ?, ?)
            """, (key, en, ru))
        
        # Insert test vessels
        test_vessels = [
            ('SP Dudinka', '9891234', 2015, 'Russia', 'dry-cargo', 35000),
            ('SP Norilsk', '9895678', 2018, 'Russia', 'dry-cargo', 42000),
        ]
        
        for vessel in test_vessels:
            conn.execute("""
                INSERT OR IGNORE INTO vessels (name, imo_number, year_built, flag, vessel_type, deadweight_mt, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, vessel)
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()
    
    def execute_query(self, query, params=None):
        """Execute a single query and return cursor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor
    
    def fetch_all(self, query, params=None):
        """Execute query and return all rows as list of dicts"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            print(f"Database error in fetch_all: {e}")
            return []
    
    def fetch_one(self, query, params=None):
        """Execute query and return first row as dict"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"Database error in fetch_one: {e}")
            return None
    
    def insert(self, table, data):
        """Insert a record and return its ID"""
        columns = ', '.join(data.keys())
        placeholders = ', '.join(['?' for _ in data])
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, list(data.values()))
            return cursor.lastrowid
    
    def update(self, table, record_id, data):
        """Update a record by ID"""
        set_clause = ', '.join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE id = ?"
        
        params = list(data.values()) + [record_id]
        self.execute_query(query, params)
    
    def delete(self, table, record_id):
        """Delete a record by ID"""
        query = f"DELETE FROM {table} WHERE id = ?"
        self.execute_query(query, (record_id,))
    
    def backup(self, backup_path=None):
        """Create a database backup"""
        if backup_path is None:
            import datetime
            timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = f"backups/shipman_backup_{timestamp}.db"
        
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as src:
            with sqlite3.connect(backup_path) as dst:
                src.backup(dst)
        
        return backup_path

# Global instance
db = DatabaseManager()