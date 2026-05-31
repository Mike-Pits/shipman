import re
from datetime import datetime, timedelta
from typing import Dict, Optional

class DISPParser:
    def __init__(self):
        self.reset()
    
    def reset(self):
        self.parsed_data = {
            'raw_disp_text': '',
            'ship_name': '',
            'report_number': '',
            'report_datetime': None,
            'latitude': None,
            'longitude': None,
            'port_name': None,
            'distance_run_nm': None,
            'avg_speed_knots': None,
            'rob_ifo_mt': None,
            'rob_mgo_mt': None,
            'next_port_name': None,
            'eta_next_port': None,
            'free_text': None,
            'master_name': None,
            'wind_dir': None,
            'wind_speed_ms': None,
            'sea_state_points': None,
        }
    
    def parse(self, text: str) -> Dict:
        self.reset()
        self.parsed_data['raw_disp_text'] = text
        
        # Normalize line endings and split
        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line == 'NNNN':
                continue
            
            # Match code and value (code may be separated by space or tab)
            match = re.match(r'^(\d+)\s+(.+)$', line)
            if match:
                code = match.group(1)
                value = match.group(2).strip()
                self.parse_code(code, value)
            else:
                # Header detection
                if not self.parsed_data['ship_name'] and not re.match(r'^\d', line):
                    self.parsed_data['ship_name'] = line
                elif 'Дисп' in line or 'дисп' in line:
                    self.parsed_data['report_number'] = line
                elif 'капитан' in line.lower():
                    self.parsed_data['master_name'] = line
        
        return self.parsed_data
    
    def parse_code(self, code: str, value: str):
        # Normalize value: replace comma with dot, remove extra spaces
        value = value.replace(',', '.')
        
        if code == '1':
            dt = self._parse_datetime(value)
            if dt:
                self.parsed_data['report_datetime'] = dt
        elif code == '2':
            self._parse_coords_and_port(value)
        elif code == '3':
            self.parsed_data['port_name'] = value
        elif code == '4':
            parts = value.split('/')
            if len(parts) >= 2:
                try:
                    self.parsed_data['wind_dir'] = int(parts[0])
                    self.parsed_data['wind_speed_ms'] = float(parts[1].split()[0])
                except:
                    pass
        elif code == '5':
            parts = value.split('/')
            if len(parts) >= 2:
                try:
                    self.parsed_data['sea_state_points'] = float(parts[1])
                except:
                    pass
        elif code == '6':
            # Course/Speed – extract speed after '/'
            parts = value.split('/')
            if len(parts) >= 2:
                speed_str = parts[1].split()[0]  # take first token
                try:
                    self.parsed_data['avg_speed_knots'] = float(speed_str)
                except:
                    pass
        elif code == '10':
            # Distance run – first numeric token
            match = re.search(r'(\d+(?:\.\d+)?)', value)
            if match:
                self.parsed_data['distance_run_nm'] = float(match.group(1))
        elif code == '11':
            match = re.search(r'(\d+(?:\.\d+)?)', value)
            if match:
                self.parsed_data['distance_to_dest_nm'] = float(match.group(1))
        elif code == '31':
            # Bunker ROB IFO/MGO – format: IFO/MGO
            parts = value.split('/')
            if len(parts) >= 1:
                ifo_str = parts[0].split()[0]
                try:
                    self.parsed_data['rob_ifo_mt'] = float(ifo_str)
                except:
                    pass
            if len(parts) >= 2:
                mgo_str = parts[1].split()[0]
                try:
                    self.parsed_data['rob_mgo_mt'] = float(mgo_str)
                except:
                    pass
        elif code == '43':
            self.parsed_data['next_port_name'] = value
        elif code == '44':
            eta = self._parse_datetime(value)
            if eta:
                self.parsed_data['eta_next_port'] = eta
        elif code == '100':
            if value.startswith('NC!'):
                value = value[3:].strip()
            self.parsed_data['free_text'] = value
        else:
            # Unknown code – append to free_text
            if self.parsed_data['free_text']:
                self.parsed_data['free_text'] += f"\n{code} {value}"
            else:
                self.parsed_data['free_text'] = f"{code} {value}"
    
    def _parse_datetime(self, value: str) -> Optional[datetime]:
        value = value.split()[0]  # remove any trailing text
        patterns = [
            r'^(\d{2})(\d{2})/(\d{2})(\d{2})$',
            r'^(\d{2})(\d{2})/(\d{2}):(\d{2})$',
            r'^(\d{2})\.(\d{2})/(\d{2}):(\d{2})$'
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
                    dt = datetime(year, month, day, hour, minute)
                    if dt > datetime.now() + timedelta(days=1):
                        dt = datetime(year - 1, month, day, hour, minute)
                    return dt
                except:
                    return None
        return None
    
    def _parse_coords_and_port(self, value: str):
        # Extract coordinates (first token) and optional port name
        tokens = value.split()
        coord_token = tokens[0]
        pattern = r'^(\d{2})(\d{2})([NS])/(\d{3})(\d{2})([EW])$'
        match = re.match(pattern, coord_token.upper())
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
            self.parsed_data['latitude'] = f"{lat:.4f}"
            self.parsed_data['longitude'] = f"{lon:.4f}"
        if len(tokens) > 1:
            self.parsed_data['port_name'] = ' '.join(tokens[1:])

disp_parser = DISPParser()