import re
from datetime import datetime, timedelta
from typing import Dict, Optional

class DISPParser:
    """Parser for DISP-01 daily report format"""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.parsed_data = {
            'raw_disp_text': '',
            'ship_name': '',
            'report_datetime': None,
            'latitude': None,
            'longitude': None,
            'port_name': None,
            'distance_run_nm': None,
            'avg_speed_knots': None,
            'rob_ifo_mt': None,
            'rob_mgo_mt': None,
            'next_port_name': None,
            'free_text': None,
            'master_name': None,
        }
    
    def parse(self, text: str) -> Dict:
        """Parse DISP-01 formatted text"""
        self.reset()
        self.parsed_data['raw_disp_text'] = text
        
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line == 'NNNN':
                continue
            
            # Parse code: value
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if match:
                code = match.group(1)
                value = match.group(2)
                self.parse_code(code, value)
            else:
                # Header line (ship name)
                if not self.parsed_data['ship_name'] and not re.match(r'^\d', line):
                    self.parsed_data['ship_name'] = line
        
        return self.parsed_data
    
    def parse_code(self, code: str, value: str):
        """Parse individual code"""
        if code == '1':
            # Date/Time
            dt = self.parse_datetime(value)
            if dt:
                self.parsed_data['report_datetime'] = dt
        elif code == '2':
            # Coordinates and port
            parts = value.split(' ', 1)
            coords = self.parse_coordinates(parts[0])
            if coords:
                self.parsed_data['latitude'] = coords['lat']
                self.parsed_data['longitude'] = coords['lon']
            if len(parts) > 1:
                self.parsed_data['port_name'] = parts[1]
        elif code == '3':
            self.parsed_data['port_name'] = value
        elif code == '6':
            # Course/Speed
            parts = value.split('/')
            if len(parts) >= 2:
                try:
                    self.parsed_data['avg_speed_knots'] = float(parts[1].replace(',', '.'))
                except ValueError:
                    pass
        elif code == '10':
            try:
                self.parsed_data['distance_run_nm'] = float(value.replace(',', '.'))
            except ValueError:
                pass
        elif code == '31':
            # Bunker ROB IFO/MGO
            parts = value.split('/')
            if len(parts) >= 1:
                try:
                    self.parsed_data['rob_ifo_mt'] = float(parts[0].replace(',', '.'))
                except ValueError:
                    pass
            if len(parts) >= 2:
                try:
                    self.parsed_data['rob_mgo_mt'] = float(parts[1].replace(',', '.'))
                except ValueError:
                    pass
        elif code == '43':
            self.parsed_data['next_port_name'] = value
        elif code == '100':
            self.parsed_data['free_text'] = value
    
    def parse_datetime(self, value: str) -> Optional[datetime]:
        """Parse DDMM/HHMM or DDMM/HH:MM format"""
        value = value.split()[0] if ' ' in value else value
        patterns = [
            r'^(\d{2})(\d{2})/(\d{2})(\d{2})$',
            r'^(\d{2})(\d{2})/(\d{2}):(\d{2})$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, value)
            if match:
                day = int(match.group(1))
                month = int(match.group(2))
                hour = int(match.group(3))
                minute = int(match.group(4))
                year = datetime.now().year
                try:
                    parsed = datetime(year, month, day, hour, minute)
                    if parsed > datetime.now() + timedelta(days=1):
                        parsed = datetime(year - 1, month, day, hour, minute)
                    return parsed
                except ValueError:
                    return None
        return None
    
    def parse_coordinates(self, value: str) -> Optional[Dict]:
        """Parse DDMMN/DDDMME format"""
        pattern = r'^(\d{2})(\d{2})([NS])/(\d{3})(\d{2})([EW])$'
        match = re.match(pattern, value.upper())
        if match:
            lat_deg = int(match.group(1))
            lat_min = int(match.group(2))
            lat_dir = match.group(3)
            lon_deg = int(match.group(4))
            lon_min = int(match.group(5))
            lon_dir = match.group(6)
            
            lat = lat_deg + lat_min / 60.0
            if lat_dir == 'S':
                lat = -lat
            
            lon = lon_deg + lon_min / 60.0
            if lon_dir == 'W':
                lon = -lon
            
            return {'lat': f"{lat:.4f}", 'lon': f"{lon:.4f}"}
        return None

disp_parser = DISPParser()