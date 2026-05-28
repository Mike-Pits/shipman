import re
from datetime import datetime

class Validators:
    """Collection of validation functions"""
    
    @staticmethod
    def validate_imo(imo_number):
        """Validate IMO number (7 digits)"""
        if not imo_number:
            return False
        imo_number = str(imo_number).strip()
        return bool(re.match(r'^\d{7}$', imo_number))
    
    @staticmethod
    def validate_date(date_string):
        """Validate date string"""
        try:
            datetime.strptime(date_string, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_datetime(dt_string):
        """Validate datetime string"""
        try:
            datetime.strptime(dt_string, '%Y-%m-%d %H:%M:%S')
            return True
        except ValueError:
            return False

# Global instance
validators = Validators()