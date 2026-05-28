from database.db_manager import db

class LanguageManager:
    """Manages bilingual UI strings (EN/RU)"""
    
    def __init__(self):
        self.current_lang = 'en'
        self.strings = {}
        # Don't load immediately - wait for database to be ready
        self._loaded = False
    
    def load_strings(self):
        """Load all language strings from database"""
        if self._loaded:
            return
        
        try:
            rows = db.fetch_all("SELECT key, en, ru FROM language_strings")
            self.strings = {row['key']: {'en': row['en'], 'ru': row['ru']} for row in rows}
            self._loaded = True
        except Exception as e:
            print(f"Error loading language strings: {e}")
            # Use fallback strings
            self._load_fallback_strings()
    
    def _load_fallback_strings(self):
        """Load fallback strings if database not available"""
        fallback = {
            'app_title': {'en': 'ShipMan', 'ru': 'ShipMan'},
            'login_title': {'en': 'Login', 'ru': 'Вход'},
            'username': {'en': 'Username', 'ru': 'Имя пользователя'},
            'password': {'en': 'Password', 'ru': 'Пароль'},
            'login_button': {'en': 'Login', 'ru': 'Войти'},
            'language': {'en': 'Language', 'ru': 'Язык'},
            'vessels_title': {'en': 'Vessels', 'ru': 'Судна'},
            'add_vessel': {'en': 'Add Vessel', 'ru': 'Добавить судно'},
            'edit_vessel': {'en': 'Edit Vessel', 'ru': 'Редактировать судно'},
            'delete_vessel': {'en': 'Delete Vessel', 'ru': 'Удалить судно'},
            'vessel_name': {'en': 'Vessel Name', 'ru': 'Название судна'},
            'imo_number': {'en': 'IMO Number', 'ru': 'Номер IMO'},
            'save': {'en': 'Save', 'ru': 'Сохранить'},
            'cancel': {'en': 'Cancel', 'ru': 'Отмена'},
            'refresh': {'en': 'Refresh', 'ru': 'Обновить'},
            'warning': {'en': 'Warning', 'ru': 'Предупреждение'},
            'success': {'en': 'Success', 'ru': 'Успех'},
            'confirm_delete': {'en': 'Are you sure?', 'ru': 'Вы уверены?'},
        }
        self.strings = fallback
        self._loaded = True
    
    def get(self, key, default=None):
        """Get string in current language"""
        self.load_strings()  # Lazy load
        if key in self.strings:
            return self.strings[key].get(self.current_lang, key)
        return default if default else key
    
    def set_language(self, lang):
        """Change current language (en or ru)"""
        if lang in ['en', 'ru']:
            self.current_lang = lang
            return True
        return False
    
    def reload(self):
        """Reload strings from database"""
        self._loaded = False
        self.load_strings()

# Global instance
lang = LanguageManager()