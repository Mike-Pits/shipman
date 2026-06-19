import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from database.db_manager import db
from utils.language_manager import lang
from utils.excel_exporter import excel_exporter

# -------------------------------------------------------------------
# Report Engine
# -------------------------------------------------------------------
class ReportEngine:
    @staticmethod
    def get_report_types():
        return {
            'voyage_summary': 'Voyage Summary',
            'fuel_consumption': 'Fuel Consumption (Daily)',
            'fleet_distance_speed': 'Fleet Distance & Speed',
            'voyage_pnl': 'Voyage P&L',
            'tce': 'TCE Report',
        }
    
    @staticmethod
    def get_parameters(report_type):
        if report_type in ('voyage_summary', 'voyage_pnl', 'tce'):
            return [
                ('Vessel:', 'vessel_id', 'vessel'),
                ('Voyage:', 'voyage_id', 'voyage'),
                ('Date From:', 'date_from', 'date'),
                ('Date To:', 'date_to', 'date'),
            ]
        elif report_type in ('fuel_consumption', 'fleet_distance_speed'):
            return [
                ('Vessel:', 'vessel_id', 'vessel'),
                ('Date From:', 'date_from', 'date'),
                ('Date To:', 'date_to', 'date'),
            ]
        else:
            return []
    
    @staticmethod
    def generate_report(report_type, params):
        if report_type == 'voyage_summary':
            return ReportEngine._voyage_summary(params)
        elif report_type == 'fuel_consumption':
            return ReportEngine._fuel_consumption(params)
        elif report_type == 'fleet_distance_speed':
            return ReportEngine._fleet_distance_speed(params)
        elif report_type == 'voyage_pnl':
            return ReportEngine._voyage_pnl(params)
        elif report_type == 'tce':
            return ReportEngine._tce(params)
        else:
            return None
    
    # ------------------------------------------------------------------
    # Voyage Summary Report
    # ------------------------------------------------------------------
    @staticmethod
    def _voyage_summary(params):
        vessel_id = params.get('vessel_id')
        voyage_id = params.get('voyage_id')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        
        query = """
            SELECT 
                v.id AS voyage_id,
                v.voyage_number,
                ves.name AS vessel_name,
                v.load_port,
                v.discharge_port,
                v.start_date,
                v.end_date,
                v.cargo_name,
                v.cargo_quantity_loaded,
                COUNT(dr.id) AS report_count,
                SUM(dr.distance_run_nm) AS total_distance,
                ROUND(AVG(dr.avg_speed_knots), 2) AS avg_speed,
                SUM(dr.consumption_ifo_24h_mt) AS total_ifo,
                SUM(dr.consumption_mgo_24h_mt) AS total_mgo
            FROM voyages v
            JOIN vessels ves ON v.vessel_id = ves.id
            LEFT JOIN daily_reports dr ON dr.voyage_id = v.id
            WHERE 1=1
        """
        params_list = []
        if vessel_id:
            query += " AND v.vessel_id = ?"
            params_list.append(vessel_id)
        if voyage_id:
            query += " AND v.id = ?"
            params_list.append(voyage_id)
        if date_from:
            query += " AND v.start_date >= ?"
            params_list.append(date_from)
        if date_to:
            query += " AND v.end_date <= ?"
            params_list.append(date_to)
        
        query += """
            GROUP BY v.id
            ORDER BY v.start_date DESC
        """
        rows = db.fetch_all(query, params_list)
        if not rows:
            return {'headers': [], 'data': [], 'message': 'No voyages found matching the criteria.'}
        
        headers = ['Voyage #', 'Vessel', 'Load Port', 'Discharge Port', 'Start Date', 'End Date', 
                   'Cargo', 'Qty (MT)', 'Days', 'Distance (nm)', 'Avg Speed (kn)', 
                   'Total IFO (MT)', 'Total MGO (MT)']
        data = []
        for r in rows:
            days = (datetime.strptime(r['end_date'], '%Y-%m-%d') - datetime.strptime(r['start_date'], '%Y-%m-%d')).days if r['start_date'] and r['end_date'] else None
            data.append([
                r['voyage_number'] or '',
                r['vessel_name'],
                r['load_port'] or '',
                r['discharge_port'] or '',
                r['start_date'] or '',
                r['end_date'] or '',
                r['cargo_name'] or '',
                r['cargo_quantity_loaded'] or 0,
                days or '',
                r['total_distance'] or 0,
                r['avg_speed'] or 0,
                r['total_ifo'] or 0,
                r['total_mgo'] or 0,
            ])
        return {'headers': headers, 'data': data, 'message': None}
    
    # ------------------------------------------------------------------
    # Fuel Consumption Report (Daily)
    # ------------------------------------------------------------------
    @staticmethod
    def _fuel_consumption(params):
        vessel_id = params.get('vessel_id')
        voyage_id = params.get('voyage_id')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        
        query = """
            SELECT 
                dr.report_datetime,
                ves.name AS vessel_name,
                dr.distance_run_nm,
                dr.avg_speed_knots,
                dr.rob_ifo_mt,
                dr.rob_mgo_mt,
                dr.consumption_ifo_24h_mt,
                dr.consumption_mgo_24h_mt
            FROM daily_reports dr
            JOIN vessels ves ON dr.vessel_id = ves.id
            WHERE 1=1
        """
        params_list = []
        if vessel_id:
            query += " AND dr.vessel_id = ?"
            params_list.append(vessel_id)
        if voyage_id:
            query += " AND dr.voyage_id = ?"
            params_list.append(voyage_id)
        if date_from:
            query += " AND dr.report_datetime >= ?"
            params_list.append(date_from)
        if date_to:
            query += " AND dr.report_datetime <= ?"
            params_list.append(date_to)
        query += " ORDER BY dr.report_datetime DESC"
        rows = db.fetch_all(query, params_list)
        if not rows:
            return {'headers': [], 'data': [], 'message': 'No daily reports found matching the criteria.'}
        
        headers = ['Date/Time', 'Vessel', 'Distance (nm)', 'Speed (kn)', 
                   'ROB IFO (MT)', 'ROB MGO (MT)', 'Cons IFO (MT)', 'Cons MGO (MT)']
        data = []
        total_distance = 0
        total_ifo_cons = 0
        total_mgo_cons = 0
        for r in rows:
            distance = r['distance_run_nm'] or 0
            ifo_cons = r['consumption_ifo_24h_mt'] or 0
            mgo_cons = r['consumption_mgo_24h_mt'] or 0
            data.append([
                r['report_datetime'][:16] if r['report_datetime'] else '',
                r['vessel_name'],
                distance,
                r['avg_speed_knots'] or 0,
                r['rob_ifo_mt'] or 0,
                r['rob_mgo_mt'] or 0,
                ifo_cons,
                mgo_cons,
            ])
            total_distance += distance
            total_ifo_cons += ifo_cons
            total_mgo_cons += mgo_cons
        
        if len(data) > 1:
            data.append([
                'TOTAL', '', total_distance, '', '', '', total_ifo_cons, total_mgo_cons
            ])
        return {'headers': headers, 'data': data, 'message': None}
    
    # ------------------------------------------------------------------
    # Fleet Distance & Speed Report
    # ------------------------------------------------------------------
    @staticmethod
    def _fleet_distance_speed(params):
        vessel_id = params.get('vessel_id')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        
        query = """
            SELECT 
                ves.name AS vessel_name,
                SUM(dr.distance_run_nm) AS total_distance,
                COUNT(dr.id) AS report_count,
                ROUND(AVG(dr.avg_speed_knots), 2) AS avg_speed,
                MAX(dr.avg_speed_knots) AS max_speed,
                MIN(dr.avg_speed_knots) AS min_speed
            FROM daily_reports dr
            JOIN vessels ves ON dr.vessel_id = ves.id
            WHERE 1=1
        """
        params_list = []
        if vessel_id:
            query += " AND dr.vessel_id = ?"
            params_list.append(vessel_id)
        if date_from:
            query += " AND dr.report_datetime >= ?"
            params_list.append(date_from)
        if date_to:
            query += " AND dr.report_datetime <= ?"
            params_list.append(date_to)
        query += " GROUP BY dr.vessel_id ORDER BY ves.name"
        rows = db.fetch_all(query, params_list)
        if not rows:
            return {'headers': [], 'data': [], 'message': 'No data found for the criteria.'}
        
        headers = ['Vessel', 'Total Distance (nm)', '# Reports', 'Avg Speed (kn)', 'Max Speed (kn)', 'Min Speed (kn)']
        data = []
        for r in rows:
            data.append([
                r['vessel_name'],
                r['total_distance'] or 0,
                r['report_count'] or 0,
                r['avg_speed'] or 0,
                r['max_speed'] or 0,
                r['min_speed'] or 0,
            ])
        return {'headers': headers, 'data': data, 'message': None}
    
    # ------------------------------------------------------------------
    # Voyage P&L Report
    # ------------------------------------------------------------------
    @staticmethod
    def _voyage_pnl(params):
        vessel_id = params.get('vessel_id')
        voyage_id = params.get('voyage_id')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        
        query = """
            SELECT 
                v.id AS voyage_id,
                v.voyage_number,
                ves.name AS vessel_name,
                v.start_date,
                v.end_date,
                COALESCE(SUM(CASE WHEN p.transaction_type = 'income' THEN p.rub_amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN p.transaction_type = 'expense' THEN p.rub_amount ELSE 0 END), 0) AS total_expenses,
                (COALESCE(SUM(CASE WHEN p.transaction_type = 'income' THEN p.rub_amount ELSE 0 END), 0) -
                 COALESCE(SUM(CASE WHEN p.transaction_type = 'expense' THEN p.rub_amount ELSE 0 END), 0)) AS net_result
            FROM voyages v
            JOIN vessels ves ON v.vessel_id = ves.id
            LEFT JOIN payments p ON p.voyage_id = v.id
            WHERE 1=1
        """
        params_list = []
        if vessel_id:
            query += " AND v.vessel_id = ?"
            params_list.append(vessel_id)
        if voyage_id:
            query += " AND v.id = ?"
            params_list.append(voyage_id)
        if date_from:
            query += " AND v.start_date >= ?"
            params_list.append(date_from)
        if date_to:
            query += " AND v.end_date <= ?"
            params_list.append(date_to)
        
        query += """
            GROUP BY v.id
            ORDER BY v.start_date DESC
        """
        rows = db.fetch_all(query, params_list)
        if not rows:
            return {'headers': [], 'data': [], 'message': 'No voyages found matching the criteria.'}
        
        headers = ['Voyage #', 'Vessel', 'Start Date', 'End Date', 
                   'Total Income (RUB)', 'Total Expenses (RUB)', 'Net Result (RUB)']
        data = []
        for r in rows:
            data.append([
                r['voyage_number'] or '',
                r['vessel_name'],
                r['start_date'] or '',
                r['end_date'] or '',
                r['total_income'],
                r['total_expenses'],
                r['net_result'],
            ])
        return {'headers': headers, 'data': data, 'message': None}
    
    # ------------------------------------------------------------------
    # TCE Report
    # ------------------------------------------------------------------
    @staticmethod
    def _tce(params):
        vessel_id = params.get('vessel_id')
        voyage_id = params.get('voyage_id')
        date_from = params.get('date_from')
        date_to = params.get('date_to')
        
        query = """
            SELECT 
                v.id AS voyage_id,
                v.voyage_number,
                ves.name AS vessel_name,
                v.start_date,
                v.end_date,
                julianday(v.end_date) - julianday(v.start_date) AS duration_days,
                COALESCE(SUM(CASE WHEN p.transaction_type = 'income' THEN p.rub_amount ELSE 0 END), 0) AS total_income,
                COALESCE(SUM(CASE WHEN p.transaction_type = 'expense' THEN p.rub_amount ELSE 0 END), 0) AS total_expenses,
                (COALESCE(SUM(CASE WHEN p.transaction_type = 'income' THEN p.rub_amount ELSE 0 END), 0) -
                 COALESCE(SUM(CASE WHEN p.transaction_type = 'expense' THEN p.rub_amount ELSE 0 END), 0)) AS net_result
            FROM voyages v
            JOIN vessels ves ON v.vessel_id = ves.id
            LEFT JOIN payments p ON p.voyage_id = v.id
            WHERE 1=1
        """
        params_list = []
        if vessel_id:
            query += " AND v.vessel_id = ?"
            params_list.append(vessel_id)
        if voyage_id:
            query += " AND v.id = ?"
            params_list.append(voyage_id)
        if date_from:
            query += " AND v.start_date >= ?"
            params_list.append(date_from)
        if date_to:
            query += " AND v.end_date <= ?"
            params_list.append(date_to)
        
        query += """
            GROUP BY v.id
            ORDER BY v.start_date DESC
        """
        rows = db.fetch_all(query, params_list)
        if not rows:
            return {'headers': [], 'data': [], 'message': 'No voyages found matching the criteria.'}
        
        headers = ['Voyage #', 'Vessel', 'Start Date', 'End Date', 'Duration (days)', 
                   'Total Income (RUB)', 'Total Expenses (RUB)', 'Net Result (RUB)', 'TCE (RUB/day)']
        data = []
        for r in rows:
            duration = r['duration_days'] or 0
            tce = r['net_result'] / duration if duration > 0 else None
            data.append([
                r['voyage_number'] or '',
                r['vessel_name'],
                r['start_date'] or '',
                r['end_date'] or '',
                duration,
                r['total_income'],
                r['total_expenses'],
                r['net_result'],
                round(tce, 2) if tce is not None else 'N/A',
            ])
        return {'headers': headers, 'data': data, 'message': None}

# -------------------------------------------------------------------
# ReportsManager UI (unchanged)
# -------------------------------------------------------------------
class ReportsManager:
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.frame = ttk.Frame(parent)
        self.param_widgets = {}
        self.report_types = ReportEngine.get_report_types()
        self.vessel_list = []
        self.vessel_map = {}
        self.voyage_combo = None
        
        self.setup_ui()
        self.load_vessels()
    
    def setup_ui(self):
        top_frame = ttk.LabelFrame(self.frame, text="Report Selection", padding=10)
        top_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(top_frame, text="Report Type:").grid(row=0, column=0, padx=5, pady=5, sticky='e')
        self.report_type_var = tk.StringVar()
        self.report_type_combo = ttk.Combobox(top_frame, textvariable=self.report_type_var, state='readonly', width=40)
        self.report_type_combo['values'] = list(self.report_types.values())
        self.report_type_combo.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.report_type_combo.bind('<<ComboboxSelected>>', self.on_report_type_selected)
        
        self.params_frame = ttk.LabelFrame(self.frame, text="Parameters", padding=10)
        self.params_frame.pack(fill='x', padx=10, pady=5)
        
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(btn_frame, text="Generate Report", command=self.generate_report).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Export to Excel", command=self.export_to_excel).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh).pack(side='left', padx=5)
        
        result_frame = ttk.LabelFrame(self.frame, text="Results", padding=5)
        result_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.tree = ttk.Treeview(result_frame, show='headings')
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar = ttk.Scrollbar(result_frame, orient='vertical', command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.status_label = ttk.Label(self.frame, text="Ready", anchor='w')
        self.status_label.pack(fill='x', padx=10, pady=2)
    
    def load_vessels(self):
        vessels = db.fetch_all("SELECT id, name FROM vessels WHERE is_active = 1 ORDER BY name")
        self.vessel_list = [f"{v['id']} - {v['name']}" for v in vessels]
        self.vessel_map = {f"{v['id']} - {v['name']}": v['id'] for v in vessels}
    
    def on_report_type_selected(self, event=None):
        for widget in self.params_frame.winfo_children():
            widget.destroy()
        self.param_widgets = {}
        self.voyage_combo = None
        
        selected_display = self.report_type_var.get()
        report_type = None
        for key, display in self.report_types.items():
            if display == selected_display:
                report_type = key
                break
        if not report_type:
            return
        
        params = ReportEngine.get_parameters(report_type)
        row = 0
        for label_text, var_name, param_type in params:
            ttk.Label(self.params_frame, text=label_text).grid(row=row, column=0, padx=5, pady=5, sticky='e')
            if param_type == 'vessel':
                widget = ttk.Combobox(self.params_frame, state='readonly', width=40)
                widget['values'] = [''] + self.vessel_list
                widget.set('')
                widget.bind('<<ComboboxSelected>>', self.on_vessel_selected_for_voyages)
                self.param_widgets[var_name] = widget
                widget.grid(row=row, column=1, padx=5, pady=5, sticky='w')
            elif param_type == 'voyage':
                widget = ttk.Combobox(self.params_frame, state='readonly', width=40)
                widget['values'] = ['']
                widget.set('')
                self.param_widgets[var_name] = widget
                self.voyage_combo = widget
                widget.grid(row=row, column=1, padx=5, pady=5, sticky='w')
            elif param_type == 'date':
                widget = ttk.Entry(self.params_frame, width=20)
                if var_name == 'date_from':
                    widget.insert(0, (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
                elif var_name == 'date_to':
                    widget.insert(0, datetime.now().strftime('%Y-%m-%d'))
                self.param_widgets[var_name] = widget
                widget.grid(row=row, column=1, padx=5, pady=5, sticky='w')
            row += 1
    
    def on_vessel_selected_for_voyages(self, event=None):
        vessel_widget = self.param_widgets.get('vessel_id')
        if not vessel_widget:
            return
        vessel_sel = vessel_widget.get()
        if not vessel_sel or vessel_sel not in self.vessel_map:
            if self.voyage_combo:
                self.voyage_combo['values'] = ['']
                self.voyage_combo.set('')
            return
        vessel_id = self.vessel_map[vessel_sel]
        voyages = db.fetch_all("SELECT id, voyage_number FROM voyages WHERE vessel_id = ? ORDER BY start_date DESC", (vessel_id,))
        voyage_list = [f"{v['id']} - {v['voyage_number']}" for v in voyages]
        if self.voyage_combo:
            self.voyage_combo['values'] = [''] + voyage_list
            self.voyage_combo.set('')
    
    def get_param_values(self):
        params = {}
        for key, widget in self.param_widgets.items():
            value = widget.get().strip()
            if value:
                if key == 'vessel_id' and value in self.vessel_map:
                    params[key] = self.vessel_map[value]
                elif key == 'voyage_id':
                    try:
                        vid = int(value.split(' - ')[0])
                        params[key] = vid
                    except:
                        pass
                else:
                    params[key] = value
        return params
    
    def generate_report(self):
        selected_display = self.report_type_var.get()
        if not selected_display:
            messagebox.showwarning("Warning", "Please select a report type.")
            return
        
        report_type = None
        for key, display in self.report_types.items():
            if display == selected_display:
                report_type = key
                break
        if not report_type:
            return
        
        params = self.get_param_values()
        self.status_label.config(text="Generating report...")
        self.frame.update_idletasks()
        
        try:
            result = ReportEngine.generate_report(report_type, params)
            if result is None:
                messagebox.showerror("Error", "Report generation failed.")
                return
            if result.get('message'):
                messagebox.showinfo("No Data", result['message'])
                self.clear_tree()
                self.status_label.config(text=result['message'])
                return
            headers = result.get('headers', [])
            data = result.get('data', [])
            self.display_results(headers, data)
            self.status_label.config(text=f"Report generated: {len(data)} rows.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to generate report: {str(e)}")
            self.status_label.config(text="Error generating report.")
    
    def display_results(self, headers, data):
        self.clear_tree()
        if not headers or not data:
            return
        self.tree['columns'] = list(range(len(headers)))
        self.tree['show'] = 'headings'
        for i, h in enumerate(headers):
            self.tree.heading(i, text=h)
            width = min(max(len(h) * 10, 80), 250)
            self.tree.column(i, width=width, anchor='w')
        for row in data:
            self.tree.insert('', 'end', values=[str(cell) if cell is not None else '' for cell in row])
    
    def clear_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
    
    def export_to_excel(self):
        if not self.tree.get_children():
            messagebox.showinfo("Export", "No data to export.")
            return
        headers = [self.tree.heading(col)['text'] for col in self.tree['columns']]
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            data.append([str(v) for v in values])
        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        excel_exporter.export_report(data, filename, "ShipMan Report", headers)
        messagebox.showinfo("Export", f"Report exported to {filename}")
    
    def refresh(self):
        self.load_vessels()
        self.clear_tree()
        self.status_label.config(text="Ready")