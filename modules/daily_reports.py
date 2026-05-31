import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from database.db_manager import db
from utils.language_manager import lang
from utils.disp_parser import disp_parser

class DailyReportManager:
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.frame = ttk.Frame(parent)
        self.current_vessel_id = None
        self.current_report_id = None
        
        self.setup_ui()
        self.load_vessels()
    
    def setup_ui(self):
        top_frame = ttk.LabelFrame(self.frame, text=lang.get('select_vessel'), padding=10)
        top_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(top_frame, text=lang.get('vessel_name')).pack(side='left', padx=5)
        self.vessel_combo = ttk.Combobox(top_frame, state='readonly', width=30)
        self.vessel_combo.pack(side='left', padx=5)
        self.vessel_combo.bind('<<ComboboxSelected>>', self.on_vessel_selected)
        
        ttk.Button(top_frame, text=lang.get('new_report'), command=self.new_report).pack(side='left', padx=20)
        ttk.Button(top_frame, text=lang.get('refresh'), command=self.load_reports).pack(side='left', padx=5)
        
        paned = ttk.PanedWindow(self.frame, orient='horizontal')
        paned.pack(fill='both', expand=True, padx=10, pady=5)
        
        list_frame = ttk.LabelFrame(paned, text=lang.get('reports_list'), padding=5)
        paned.add(list_frame, weight=1)
        self.setup_reports_list(list_frame)
        
        entry_frame = ttk.LabelFrame(paned, text=lang.get('report_entry'), padding=5)
        paned.add(entry_frame, weight=2)
        self.setup_entry_form(entry_frame)
        
        bottom_frame = ttk.Frame(self.frame)
        bottom_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Button(bottom_frame, text=lang.get('parse_disp'), command=self.open_parser_dialog).pack(side='left', padx=5)
        ttk.Button(bottom_frame, text=lang.get('save_report'), command=self.save_report).pack(side='right', padx=5)
        ttk.Button(bottom_frame, text=lang.get('approve_report'), command=self.approve_report).pack(side='right', padx=5)
        ttk.Button(bottom_frame, text=lang.get('delete_report'), command=self.delete_report).pack(side='right', padx=5)
    
    def setup_reports_list(self, parent):
        columns = ('date', 'distance', 'ifo_consumption', 'mgo_consumption', 'status')
        self.reports_tree = ttk.Treeview(parent, columns=columns, show='headings', height=15)
        
        self.reports_tree.heading('date', text=lang.get('date'))
        self.reports_tree.heading('distance', text=lang.get('distance_nm'))
        self.reports_tree.heading('ifo_consumption', text='IFO (MT)')
        self.reports_tree.heading('mgo_consumption', text='MGO (MT)')
        self.reports_tree.heading('status', text=lang.get('status'))
        
        self.reports_tree.column('date', width=120)
        self.reports_tree.column('distance', width=100)
        self.reports_tree.column('ifo_consumption', width=100)
        self.reports_tree.column('mgo_consumption', width=100)
        self.reports_tree.column('status', width=80)
        
        scrollbar = ttk.Scrollbar(parent, orient='vertical', command=self.reports_tree.yview)
        self.reports_tree.configure(yscrollcommand=scrollbar.set)
        
        self.reports_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.reports_tree.bind('<<TreeviewSelect>>', self.on_report_selected)
    
    def setup_entry_form(self, parent):
        self.entries = {}
        fields = [
            ('report_datetime', 'Date/Time'),
            ('distance_run_nm', 'Distance (nm)'),
            ('avg_speed_knots', 'Speed (knots)'),
            ('rob_ifo_mt', 'ROB IFO (MT)'),
            ('rob_mgo_mt', 'ROB MGO (MT)'),
            ('consumption_ifo_24h_mt', 'IFO Cons (MT/24h)'),
            ('consumption_mgo_24h_mt', 'MGO Cons (MT/24h)'),
            ('next_port_name', 'Next Port'),
            ('free_text', 'Remarks'),
        ]
        for i, (field, label) in enumerate(fields):
            tk.Label(parent, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=5)
            if field == 'free_text':
                widget = tk.Text(parent, width=40, height=4)
                widget.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            else:
                widget = tk.Entry(parent, width=30)
                widget.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            self.entries[field] = widget
    
    def load_vessels(self):
        if self.current_user['role'] == 'master':
            vessels = db.fetch_all(
                "SELECT id, name FROM vessels WHERE id = ? AND is_active = 1",
                (self.current_user['vessel_id'],)
            )
        else:
            vessels = db.fetch_all("SELECT id, name FROM vessels WHERE is_active = 1 ORDER BY name")
        vessel_list = [f"{v['id']} - {v['name']}" for v in vessels]
        self.vessel_combo['values'] = vessel_list
        self.vessel_map = {f"{v['id']} - {v['name']}": v['id'] for v in vessels}
    
    def on_vessel_selected(self, event=None):
        selection = self.vessel_combo.get()
        if selection and selection in self.vessel_map:
            self.current_vessel_id = self.vessel_map[selection]
            self.load_reports()
    
    def load_reports(self):
        if not self.current_vessel_id:
            return
        for item in self.reports_tree.get_children():
            self.reports_tree.delete(item)
        reports = db.fetch_all("""
            SELECT id, report_datetime, distance_run_nm,
                   consumption_ifo_24h_mt, consumption_mgo_24h_mt, is_approved
            FROM daily_reports 
            WHERE vessel_id = ? 
            ORDER BY report_datetime DESC
        """, (self.current_vessel_id,))
        for r in reports:
            status = lang.get('approved') if r['is_approved'] else lang.get('pending')
            self.reports_tree.insert('', 'end', iid=str(r['id']), values=(
                r['report_datetime'][:16] if r['report_datetime'] else '',
                r['distance_run_nm'] or '',
                r['consumption_ifo_24h_mt'] or '',
                r['consumption_mgo_24h_mt'] or '',
                status
            ))
    
    def on_report_selected(self, event=None):
        selection = self.reports_tree.selection()
        if not selection:
            return
        self.current_report_id = int(selection[0])
        report = db.fetch_one("SELECT * FROM daily_reports WHERE id = ?", (self.current_report_id,))
        if report:
            self.load_report_to_form(report)
    
    def load_report_to_form(self, report):
        for field, widget in self.entries.items():
            value = report.get(field)
            if value is not None:
                if isinstance(widget, tk.Entry):
                    widget.delete(0, tk.END)
                    widget.insert(0, str(value))
                elif isinstance(widget, tk.Text):
                    widget.delete('1.0', tk.END)
                    widget.insert('1.0', str(value))
    
    def new_report(self):
        self.current_report_id = None
        for widget in self.entries.values():
            if isinstance(widget, tk.Entry):
                widget.delete(0, tk.END)
            elif isinstance(widget, tk.Text):
                widget.delete('1.0', tk.END)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.entries['report_datetime'].delete(0, tk.END)
        self.entries['report_datetime'].insert(0, now)
    
    def open_parser_dialog(self):
        dialog = tk.Toplevel(self.frame)
        dialog.title("Parse DISP-01")
        dialog.geometry("700x500")
        dialog.transient(self.frame)
        dialog.grab_set()
        tk.Label(dialog, text=lang.get('paste_disp_text'), font=('Arial', 10, 'bold')).pack(pady=10)
        text_area = tk.Text(dialog, height=15, width=80)
        text_area.pack(padx=10, pady=5)
        
        def parse_and_fill():
            raw_text = text_area.get('1.0', tk.END).strip()
            if not raw_text:
                messagebox.showwarning(lang.get('warning'), lang.get('enter_disp_text'))
                return
            parsed = disp_parser.parse(raw_text)
            if parsed['report_datetime']:
                self.entries['report_datetime'].delete(0, tk.END)
                self.entries['report_datetime'].insert(0, parsed['report_datetime'].strftime('%Y-%m-%d %H:%M:%S'))
            if parsed['distance_run_nm']:
                self.entries['distance_run_nm'].delete(0, tk.END)
                self.entries['distance_run_nm'].insert(0, str(parsed['distance_run_nm']))
            if parsed['avg_speed_knots']:
                self.entries['avg_speed_knots'].delete(0, tk.END)
                self.entries['avg_speed_knots'].insert(0, str(parsed['avg_speed_knots']))
            if parsed['rob_ifo_mt']:
                self.entries['rob_ifo_mt'].delete(0, tk.END)
                self.entries['rob_ifo_mt'].insert(0, str(parsed['rob_ifo_mt']))
            if parsed['rob_mgo_mt']:
                self.entries['rob_mgo_mt'].delete(0, tk.END)
                self.entries['rob_mgo_mt'].insert(0, str(parsed['rob_mgo_mt']))
            if parsed['next_port_name']:
                self.entries['next_port_name'].delete(0, tk.END)
                self.entries['next_port_name'].insert(0, parsed['next_port_name'])
            if parsed['free_text']:
                self.entries['free_text'].delete('1.0', tk.END)
                self.entries['free_text'].insert('1.0', parsed['free_text'])
            messagebox.showinfo("Success", "DISP-01 parsed and fields populated")
            dialog.destroy()
        
        tk.Button(dialog, text="Parse & Fill", command=parse_and_fill, bg='#0078d4', fg='white').pack(pady=10)
    
    # -----------------------------------------------------------------
    # Auto‑recalculation of consumption for all reports of a vessel
    # -----------------------------------------------------------------
    def recalc_vessel_consumptions(self, vessel_id):
        """Recalculate IFO and MGO consumption for all reports of a vessel
        based on chronological order of report_datetime and ROB values.
        Consumption for a report = ROB of previous report - ROB of this report.
        If no previous report, consumption set to NULL.
        """
        # Get all reports with ROB values, ordered by datetime
        reports = db.fetch_all("""
            SELECT id, report_datetime, rob_ifo_mt, rob_mgo_mt
            FROM daily_reports
            WHERE vessel_id = ? AND rob_ifo_mt IS NOT NULL AND rob_mgo_mt IS NOT NULL
            ORDER BY report_datetime ASC
        """, (vessel_id,))
        
        if len(reports) < 2:
            # If only one report (or none), set its consumption to NULL
            for r in reports:
                db.update('daily_reports', r['id'], {
                    'consumption_ifo_24h_mt': None,
                    'consumption_mgo_24h_mt': None
                })
            return
        
        # For the oldest report, consumption = NULL
        oldest = reports[0]
        db.update('daily_reports', oldest['id'], {
            'consumption_ifo_24h_mt': None,
            'consumption_mgo_24h_mt': None
        })
        
        # For each subsequent report, calculate consumption from previous
        for i in range(1, len(reports)):
            prev = reports[i-1]
            curr = reports[i]
            ifo_cons = round(prev['rob_ifo_mt'] - curr['rob_ifo_mt'], 2)
            mgo_cons = round(prev['rob_mgo_mt'] - curr['rob_mgo_mt'], 2)
            # If consumption negative, set to 0 (bunkering occurred – handled later)
            if ifo_cons < 0:
                ifo_cons = 0
            if mgo_cons < 0:
                mgo_cons = 0
            db.update('daily_reports', curr['id'], {
                'consumption_ifo_24h_mt': ifo_cons,
                'consumption_mgo_24h_mt': mgo_cons
            })
    
    # -----------------------------------------------------------------
    # Save, Approve, Delete with auto‑recalc
    # -----------------------------------------------------------------
    def save_report(self):
        if not self.current_vessel_id:
            messagebox.showwarning(lang.get('warning'), "Please select a vessel first")
            return
        
        data = {}
        for field, widget in self.entries.items():
            if isinstance(widget, tk.Entry):
                value = widget.get().strip()
                if field in ('distance_run_nm', 'avg_speed_knots', 'rob_ifo_mt', 'rob_mgo_mt',
                             'consumption_ifo_24h_mt', 'consumption_mgo_24h_mt'):
                    try:
                        data[field] = float(value) if value else None
                    except ValueError:
                        data[field] = None
                else:
                    data[field] = value if value else None
            elif isinstance(widget, tk.Text):
                value = widget.get('1.0', tk.END).strip()
                data[field] = value if value else None
        
        data['vessel_id'] = self.current_vessel_id
        data['is_approved'] = 0
        
        if self.current_report_id:
            db.update('daily_reports', self.current_report_id, data)
            messagebox.showinfo(lang.get('success'), "Report updated")
        else:
            new_id = db.insert('daily_reports', data)
            self.current_report_id = new_id
            messagebox.showinfo(lang.get('success'), "Report saved")
        
        # Recalculate all consumptions for this vessel (handles out-of-order entries)
        self.recalc_vessel_consumptions(self.current_vessel_id)
        self.load_reports()
        self.new_report()
    
    def approve_report(self):
        if not self.current_report_id:
            messagebox.showwarning(lang.get('warning'), "Please select a report to approve")
            return
        db.update('daily_reports', self.current_report_id, {'is_approved': 1})
        messagebox.showinfo(lang.get('success'), "Report approved")
        # Recalc after approval (though approval alone doesn't change ROB, it's safe)
        self.recalc_vessel_consumptions(self.current_vessel_id)
        self.load_reports()
    
    def delete_report(self):
        if not self.current_report_id:
            messagebox.showwarning(lang.get('warning'), "Please select a report to delete")
            return
        if messagebox.askyesno(lang.get('confirm_delete'), "Delete this report?"):
            db.delete('daily_reports', self.current_report_id)
            messagebox.showinfo(lang.get('success'), "Report deleted")
            self.current_report_id = None
            self.new_report()
            # Recalculate consumptions after deletion
            self.recalc_vessel_consumptions(self.current_vessel_id)
            self.load_reports()