import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from database.db_manager import db
from utils.language_manager import lang

class CharterPartyManager:
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.frame = ttk.Frame(parent)
        self.current_charter_id = None
        
        self.setup_ui()
        self.load_charters()
    
    def setup_ui(self):
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill='x', padx=5, pady=5)
        ttk.Button(toolbar, text="Add Charter", command=self.add_charter).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Edit Charter", command=self.edit_charter).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Delete Charter", command=self.delete_charter).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Refresh", command=self.load_charters).pack(side='left', padx=2)
        
        columns = ('id', 'vessel', 'charter_type', 'charterer', 'currency', 'date')
        self.tree = ttk.Treeview(self.frame, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col.capitalize())
            self.tree.column(col, width=120)
        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y', pady=5)
        self.tree.bind('<Double-1>', lambda e: self.edit_charter())
    
    def load_charters(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        rows = db.fetch_all("""
            SELECT c.id, v.name as vessel_name, c.charter_type, c.charterer_name, c.contract_currency, c.charter_date
            FROM charter_parties c
            JOIN vessels v ON c.vessel_id = v.id
            WHERE c.is_active = 1
            ORDER BY c.charter_date DESC
        """)
        for r in rows:
            self.tree.insert('', 'end', iid=str(r['id']), values=(
                r['id'], r['vessel_name'], r['charter_type'], r['charterer_name'], r['contract_currency'], r['charter_date']
            ))
    
    def add_charter(self):
        CharterDialog(self.frame, self.current_user, on_save=self.load_charters)
    
    def edit_charter(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a charter to edit")
            return
        charter_id = int(sel[0])
        CharterDialog(self.frame, self.current_user, charter_id, self.load_charters)
    
    def delete_charter(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a charter to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this charter party?"):
            charter_id = int(sel[0])
            db.update('charter_parties', charter_id, {'is_active': 0})
            self.load_charters()


class CharterDialog:
    def __init__(self, parent, current_user, charter_id=None, on_save=None):
        self.parent = parent
        self.current_user = current_user
        self.charter_id = charter_id
        self.on_save = on_save
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Charter Party" + (" - Edit" if charter_id else " - Add"))
        self.dialog.geometry("800x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        if charter_id:
            self.load_data()
    
    def setup_ui(self):
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Basic Info (includes charter type specific fields)
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="Basic Info")
        self.setup_basic_tab(basic_frame)
        
        # Tab 2: Laytime & Demurrage
        laytime_frame = ttk.Frame(notebook)
        notebook.add(laytime_frame, text="Laytime & Demurrage")
        self.setup_laytime_tab(laytime_frame)
        
        # Tab 3: Other
        other_frame = ttk.Frame(notebook)
        notebook.add(other_frame, text="Other")
        self.setup_other_tab(other_frame)
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side='right', padx=5)
    
    def setup_basic_tab(self, parent):
        # Row 0: Vessel
        tk.Label(parent, text="Vessel:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
        self.vessel_combo = ttk.Combobox(parent, state='readonly', width=30)
        self.vessel_combo.grid(row=0, column=1, sticky='w', padx=5, pady=5)
        self.load_vessels()
        
        # Row 1: Charter Type
        tk.Label(parent, text="Charter Type:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(parent, textvariable=self.type_var, values=['time', 'voyage', 'bareboat'], state='readonly', width=27)
        self.type_combo.grid(row=1, column=1, sticky='w', padx=5, pady=5)
        self.type_combo.bind('<<ComboboxSelected>>', self.on_type_change)
        
        # Row 2: Charterer
        tk.Label(parent, text="Charterer Name:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.charterer_entry = tk.Entry(parent, width=30)
        self.charterer_entry.grid(row=2, column=1, sticky='w', padx=5, pady=5)
        
        # Row 3: Charter Date
        tk.Label(parent, text="Charter Date:").grid(row=3, column=0, sticky='e', padx=5, pady=5)
        self.date_entry = tk.Entry(parent, width=30)
        self.date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
        self.date_entry.grid(row=3, column=1, sticky='w', padx=5, pady=5)
        
        # Row 4: Contract Currency
        tk.Label(parent, text="Contract Currency:").grid(row=4, column=0, sticky='e', padx=5, pady=5)
        self.currency_var = tk.StringVar(value="RUB")
        self.currency_combo = ttk.Combobox(parent, textvariable=self.currency_var, values=['RUB', 'USD'], state='readonly', width=27)
        self.currency_combo.grid(row=4, column=1, sticky='w', padx=5, pady=5)
        
        # Dynamic frame for charter-specific fields
        self.dynamic_frame = ttk.LabelFrame(parent, text="Charter Specific Details", padding=5)
        self.dynamic_frame.grid(row=5, column=0, columnspan=2, sticky='ew', padx=5, pady=10)
        self.dynamic_entries = {}
        
        # Make grid expandable
        parent.columnconfigure(1, weight=1)
    
    def load_vessels(self):
        vessels = db.fetch_all("SELECT id, name FROM vessels WHERE is_active = 1 ORDER BY name")
        vessel_list = [f"{v['id']} - {v['name']}" for v in vessels]
        self.vessel_combo['values'] = vessel_list
        self.vessel_map = {f"{v['id']} - {v['name']}": v['id'] for v in vessels}
    
    def on_type_change(self, event=None):
        for widget in self.dynamic_frame.winfo_children():
            widget.destroy()
        self.dynamic_entries.clear()
        
        charter_type = self.type_var.get()
        if charter_type == 'time':
            self.setup_time_fields()
        elif charter_type == 'voyage':
            self.setup_voyage_fields()
        # bareboat: no additional fields
    
    def setup_time_fields(self):
        row = 0
        tk.Label(self.dynamic_frame, text="Hire Rate (per day):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        entry = tk.Entry(self.dynamic_frame, width=20)
        entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.dynamic_entries['hire_rate_original'] = entry
        row += 1
        
        tk.Label(self.dynamic_frame, text="Payment Terms:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        entry = tk.Entry(self.dynamic_frame, width=40)
        entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.dynamic_entries['payment_terms'] = entry
    
    def setup_voyage_fields(self):
        row = 0
        tk.Label(self.dynamic_frame, text="Cargo Name:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        entry = tk.Entry(self.dynamic_frame, width=30)
        entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.dynamic_entries['cargo_name'] = entry
        row += 1
        
        tk.Label(self.dynamic_frame, text="Cargo Quantity Fixed (MT):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        entry = tk.Entry(self.dynamic_frame, width=20)
        entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.dynamic_entries['cargo_quantity_fixed'] = entry
        row += 1
        
        tk.Label(self.dynamic_frame, text="Freight Rate (per MT):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        entry_rate = tk.Entry(self.dynamic_frame, width=20)
        entry_rate.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.dynamic_entries['freight_rate_original'] = entry_rate
        row += 1
        
        tk.Label(self.dynamic_frame, text="Freight Lumpsum (total):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        entry_lump = tk.Entry(self.dynamic_frame, width=20)
        entry_lump.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.dynamic_entries['freight_lumpsum_original'] = entry_lump
        row += 1
        
        tk.Label(self.dynamic_frame, text="Payment Terms:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        entry = tk.Entry(self.dynamic_frame, width=40)
        entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.dynamic_entries['payment_terms'] = entry
    
    def setup_laytime_tab(self, parent):
        fields = [
            ('laytime_allowed', 'Laytime Allowed (e.g., 5 days):'),
            ('laytime_basis', 'Laytime Basis (SHINC/SSHEX):'),
            ('demurrage_rate_original', 'Demurrage Rate (per day):'),
            ('despatch_rate_original', 'Despatch Rate (per day):'),
            ('nor_clauses', 'NOR Clauses:'),
        ]
        self.laytime_entries = {}
        for i, (field, label) in enumerate(fields):
            tk.Label(parent, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=5)
            entry = tk.Entry(parent, width=40)
            entry.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            self.laytime_entries[field] = entry
        parent.columnconfigure(1, weight=1)
    
    def setup_other_tab(self, parent):
        fields = [
            ('port_rotation', 'Port Rotation (comma separated):'),
            ('agents_name', 'Agent Name:'),
            ('remarks', 'Remarks:'),
        ]
        self.other_entries = {}
        for i, (field, label) in enumerate(fields):
            tk.Label(parent, text=label).grid(row=i, column=0, sticky='ne', padx=5, pady=5)
            if field == 'remarks':
                entry = tk.Text(parent, width=50, height=5)
                entry.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            else:
                entry = tk.Entry(parent, width=50)
                entry.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            self.other_entries[field] = entry
        parent.columnconfigure(1, weight=1)
    
    def load_data(self):
        charter = db.fetch_one("SELECT * FROM charter_parties WHERE id = ?", (self.charter_id,))
        if not charter:
            return
        
        # Basic info
        vessel_name = db.fetch_one("SELECT name FROM vessels WHERE id = ?", (charter['vessel_id'],))['name']
        vessel_text = f"{charter['vessel_id']} - {vessel_name}"
        self.vessel_combo.set(vessel_text)
        self.type_combo.set(charter['charter_type'])
        self.charterer_entry.insert(0, charter['charterer_name'] or '')
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, charter['charter_date'] or '')
        self.currency_combo.set(charter['contract_currency'] or 'RUB')
        
        # Trigger dynamic fields based on type
        self.on_type_change()
        
        # Fill dynamic fields
        for key, entry in self.dynamic_entries.items():
            value = charter.get(key)
            if value is not None:
                entry.delete(0, tk.END)
                entry.insert(0, str(value))
        
        # Laytime fields
        for key, entry in self.laytime_entries.items():
            value = charter.get(key)
            if value is not None:
                entry.delete(0, tk.END)
                entry.insert(0, str(value))
        
        # Other fields
        for key, entry in self.other_entries.items():
            value = charter.get(key)
            if value is not None:
                if isinstance(entry, tk.Text):
                    entry.delete('1.0', tk.END)
                    entry.insert('1.0', str(value))
                else:
                    entry.delete(0, tk.END)
                    entry.insert(0, str(value))
    
    def save(self):
        # Collect basic data
        vessel_sel = self.vessel_combo.get()
        if not vessel_sel or vessel_sel not in self.vessel_map:
            messagebox.showerror("Error", "Please select a vessel")
            return
        vessel_id = self.vessel_map[vessel_sel]
        
        charter_type = self.type_var.get()
        if not charter_type:
            messagebox.showerror("Error", "Please select charter type")
            return
        
        charterer = self.charterer_entry.get().strip()
        if not charterer:
            messagebox.showerror("Error", "Charterer name is required")
            return
        
        charter_date = self.date_entry.get().strip()
        contract_currency = self.currency_var.get()
        
        data = {
            'vessel_id': vessel_id,
            'charter_type': charter_type,
            'charterer_name': charterer,
            'charter_date': charter_date,
            'contract_currency': contract_currency,
            'is_active': 1,
        }
        
        # Get exchange rate if USD
        if contract_currency == 'USD':
            rate_row = db.fetch_one("SELECT usd_to_rub_rate FROM exchange_rates WHERE rate_date = ?", (charter_date,))
            if rate_row:
                rate = rate_row['usd_to_rub_rate']
            else:
                rate_row = db.fetch_one("SELECT usd_to_rub_rate FROM exchange_rates ORDER BY rate_date DESC LIMIT 1")
                rate = rate_row['usd_to_rub_rate'] if rate_row else 92.50
            data['exchange_rate_used'] = rate
        else:
            data['exchange_rate_used'] = 1.0
        
        # Dynamic fields
        for key, entry in self.dynamic_entries.items():
            val = entry.get().strip()
            if key.endswith('_original') or key in ('cargo_quantity_fixed',):
                try:
                    data[key] = float(val) if val else None
                except:
                    data[key] = None
            else:
                data[key] = val if val else None
        
        # Laytime fields
        for key, entry in self.laytime_entries.items():
            val = entry.get().strip()
            if key.endswith('_original'):
                try:
                    data[key] = float(val) if val else None
                except:
                    data[key] = None
            else:
                data[key] = val if val else None
        
        # Other fields
        for key, entry in self.other_entries.items():
            if isinstance(entry, tk.Text):
                val = entry.get('1.0', tk.END).strip()
                data[key] = val if val else None
            else:
                val = entry.get().strip()
                data[key] = val if val else None
        
        if self.charter_id:
            db.update('charter_parties', self.charter_id, data)
            messagebox.showinfo("Success", "Charter party updated")
        else:
            db.insert('charter_parties', data)
            messagebox.showinfo("Success", "Charter party added")
        
        self.dialog.destroy()
        if self.on_save:
            self.on_save()