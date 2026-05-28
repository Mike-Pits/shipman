from database.db_manager import db
import json
from datetime import datetime

class AuditLogger:
    """Logs changes to critical tables"""
    
    def __init__(self, current_user=None):
        self.current_user = current_user
    
    def set_user(self, user):
        self.current_user = user
    
    def log(self, table_name, record_id, action, old_values=None, new_values=None):
        """Log an action to audit_log table"""
        username = self.current_user.get('username', 'system') if self.current_user else 'system'
        user_id = self.current_user.get('id') if self.current_user else None
        
        # Create audit_log table if not exists
        with db.get_connection() as conn:
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
        
        db.insert('audit_log', {
            'user_id': user_id,
            'username': username,
            'table_name': table_name,
            'record_id': record_id,
            'action': action,
            'old_values': json.dumps(old_values, ensure_ascii=False, default=str) if old_values else None,
            'new_values': json.dumps(new_values, ensure_ascii=False, default=str) if new_values else None,
        })

# Global instance
audit = AuditLogger()