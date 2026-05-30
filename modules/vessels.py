import tkinter as tk
from tkinter import ttk, messagebox
from database.db_manager import db
from utils.language_manager import lang
from utils.validators import validators
from utils.audit import audit

class VesselManager:
    # ... (keep as is, no changes)
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.frame = ttk.Frame(parent)
        
        self.setup_ui()
        self.load_vessels()
    
    def setup_ui(self):
        # ... unchanged ...
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text=lang.get('add_vessel'),
                   command=self.add_vessel).pack(side='left', padx=2)
        ttk.Button(toolbar, text=lang.get('edit_vessel'),
                   command=self.edit_vessel).pack(side='left', padx=2)
        ttk.Button(toolbar, text=lang.get('delete_vessel'),
                   command=self.delete_vessel).pack(side='left', padx=2)
        ttk.Button(toolbar, text=lang.get('refresh'),
                   command=self.load_vessels).pack(side='left', padx=2)
        
        columns = ('id', 'name', 'imo', 'type', 'deadweight')
        self.tree = ttk.Treeview(self.frame, columns=columns, show='headings', height=20)
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text=lang.get('vessel_name'))
        self.tree.heading('imo', text=lang.get('imo_number'))
        self.tree.heading('type', text='Type')
        self.tree.heading('deadweight', text='DWT (MT)')
        self.tree.column('id', width=50)
        self.tree.column('name', width=200)
        self.tree.column('imo', width=100)
        self.tree.column('type', width=100)
        self.tree.column('deadweight', width=100)
        
        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y', pady=5)
        self.tree.bind('<Double-1>', lambda e: self.edit_vessel())
    
    def load_vessels(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        vessels = db.fetch_all("""
            SELECT id, name, imo_number, vessel_type, deadweight_mt 
            FROM vessels WHERE is_active = 1 ORDER BY name
        """)
        for v in vessels:
            self.tree.insert('', 'end', values=(
                v['id'], v['name'], v['imo_number'],
                v['vessel_type'], v['deadweight_mt']
            ))
    
    def add_vessel(self):
        VesselDialog(self.frame, self.current_user, on_save=self.load_vessels)
    
    def edit_vessel(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(lang.get('warning'), "Please select a vessel to edit")
            return
        vessel_id = self.tree.item(selected[0])['values'][0]
        VesselDialog(self.frame, self.current_user, vessel_id, self.load_vessels)
    
    def delete_vessel(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(lang.get('warning'), "Please select a vessel to delete")
            return
        if messagebox.askyesno(lang.get('confirm_delete'), lang.get('confirm_delete')):
            vessel_id = self.tree.item(selected[0])['values'][0]
            db.update('vessels', vessel_id, {'is_active': 0})
            self.load_vessels()


class VesselDialog:
    """Dialog for adding/editing vessels with all technical fields"""
    
    def __init__(self, parent, current_user, vessel_id=None, on_save=None):
        self.parent = parent
        self.current_user = current_user
        self.vessel_id = vessel_id
        self.on_save = on_save
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(lang.get('add_vessel') if not vessel_id else lang.get('edit_vessel'))
        self.dialog.geometry("800x700")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        
        if vessel_id:
            self.load_vessel_data()
    
    def setup_ui(self):
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Tab 1: Basic Information
        basic_frame = ttk.Frame(notebook)
        notebook.add(basic_frame, text="Basic Info")
        self.setup_basic_tab(basic_frame)
        
        # Tab 2: Performance (Laden)
        laden_frame = ttk.Frame(notebook)
        notebook.add(laden_frame, text="Laden Performance")
        self.setup_laden_tab(laden_frame)
        
        # Tab 3: Performance (Ballast)
        ballast_frame = ttk.Frame(notebook)
        notebook.add(ballast_frame, text="Ballast Performance")
        self.setup_ballast_tab(ballast_frame)
        
        # Tab 4: Other Consumption
        other_frame = ttk.Frame(notebook)
        notebook.add(other_frame, text="Other Consumption")
        self.setup_other_tab(other_frame)
        
        # Buttons
        btn_frame = ttk.Frame(self.dialog)
        btn_frame.pack(fill='x', padx=10, pady=10)
        ttk.Button(btn_frame, text=lang.get('save'), command=self.save).pack(side='right', padx=5)
        ttk.Button(btn_frame, text=lang.get('cancel'), command=self.dialog.destroy).pack(side='right', padx=5)
    
    def setup_basic_tab(self, parent):
        fields = [
            ('vessel_name', 'name', 'entry'),
            ('imo_number', 'imo_number', 'entry'),
            ('year_built', 'year_built', 'entry'),
            ('flag', 'flag', 'entry'),
            ('vessel_type', 'vessel_type', 'combobox', ['tanker', 'dry-cargo', 'tug']),
            ('deadweight_mt', 'deadweight_mt', 'entry'),
            ('loa', 'loa', 'entry'),
            ('beam', 'beam', 'entry'),
            ('me_power', 'me_power', 'entry'),
        ]
        self.basic_entries = {}
        for i, (label_key, field_name, widget_type, *args) in enumerate(fields):
            tk.Label(parent, text=lang.get(label_key)).grid(row=i, column=0, sticky='e', padx=5, pady=5)
            if widget_type == 'entry':
                entry = tk.Entry(parent, width=30)
                entry.grid(row=i, column=1, sticky='w', padx=5, pady=5)
                self.basic_entries[field_name] = entry
            elif widget_type == 'combobox':
                combo = ttk.Combobox(parent, values=args[0], width=27, state='readonly')
                combo.grid(row=i, column=1, sticky='w', padx=5, pady=5)
                self.basic_entries[field_name] = combo
    
    def setup_laden_tab(self, parent):
        # speed laden, IFO under way, MGO under way
        fields = [
            ('speed_laden', 'speed_laden', 'Speed (knots)'),
            ('IFO_under_way', 'IFO_under_way', 'IFO Consumption (MT/day)'),
            ('MGO_under_way', 'MGO_under_way', 'MGO Consumption (MT/day)'),
        ]
        self.laden_entries = {}
        for i, (field_name, db_field, label) in enumerate(fields):
            tk.Label(parent, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=5)
            entry = tk.Entry(parent, width=30)
            entry.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            self.laden_entries[db_field] = entry
    
    def setup_ballast_tab(self, parent):
        fields = [
            ('speed_ballast', 'speed_ballast', 'Speed (knots)'),
            ('IFO_ballast', 'IFO_ballast', 'IFO Consumption (MT/day)'),
            ('MGO_ballast', 'MGO_ballast', 'MGO Consumption (MT/day)'),
        ]
        self.ballast_entries = {}
        for i, (db_field, key, label) in enumerate(fields):
            tk.Label(parent, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=5)
            entry = tk.Entry(parent, width=30)
            entry.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            self.ballast_entries[db_field] = entry
    
    def setup_other_tab(self, parent):
        fields = [
            ('IFO_idle', 'IFO_idle', 'IFO Idle (MT/day)'),
            ('IFO_boiler', 'IFO_boiler', 'IFO Boiler (MT/day)'),
            ('MGO_idle', 'MGO_idle', 'MGO Idle (MT/day)'),
            ('MGO_discharging', 'MGO_discharging', 'MGO Discharging (MT/day)'),
            ('MGO_IGS', 'MGO_IGS', 'MGO IGS (MT/day)'),
        ]
        self.other_entries = {}
        for i, (db_field, key, label) in enumerate(fields):
            tk.Label(parent, text=label).grid(row=i, column=0, sticky='e', padx=5, pady=5)
            entry = tk.Entry(parent, width=30)
            entry.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            self.other_entries[db_field] = entry
    
    def load_vessel_data(self):
        vessel = db.fetch_one("SELECT * FROM vessels WHERE id = ?", (self.vessel_id,))
        if not vessel:
            return
        
        # Basic fields
        for field, entry in self.basic_entries.items():
            if field in vessel and vessel[field] is not None:
                if isinstance(entry, tk.Entry):
                    entry.delete(0, tk.END)
                    entry.insert(0, str(vessel[field]))
                elif isinstance(entry, ttk.Combobox):
                    entry.set(vessel[field])
        
        # Laden fields
        for db_field, entry in self.laden_entries.items():
            if db_field in vessel and vessel[db_field] is not None:
                entry.delete(0, tk.END)
                entry.insert(0, str(vessel[db_field]))
        
        # Ballast fields
        for db_field, entry in self.ballast_entries.items():
            if db_field in vessel and vessel[db_field] is not None:
                entry.delete(0, tk.END)
                entry.insert(0, str(vessel[db_field]))
        
        # Other fields
        for db_field, entry in self.other_entries.items():
            if db_field in vessel and vessel[db_field] is not None:
                entry.delete(0, tk.END)
                entry.insert(0, str(vessel[db_field]))
    
    def save(self):
        data = {}
        
        # Collect basic entries
        for field, entry in self.basic_entries.items():
            value = entry.get().strip()
            if value:
                if field in ['year_built', 'deadweight_mt', 'loa', 'beam', 'me_power']:
                    try:
                        data[field] = float(value) if '.' in value else int(value)
                    except ValueError:
                        data[field] = None
                else:
                    data[field] = value
            else:
                data[field] = None
        
        # Collect laden entries
        for db_field, entry in self.laden_entries.items():
            value = entry.get().strip()
            if value:
                try:
                    data[db_field] = float(value)
                except ValueError:
                    data[db_field] = None
            else:
                data[db_field] = None
        
        # Collect ballast entries
        for db_field, entry in self.ballast_entries.items():
            value = entry.get().strip()
            if value:
                try:
                    data[db_field] = float(value)
                except ValueError:
                    data[db_field] = None
            else:
                data[db_field] = None
        
        # Collect other entries
        for db_field, entry in self.other_entries.items():
            value = entry.get().strip()
            if value:
                try:
                    data[db_field] = float(value)
                except ValueError:
                    data[db_field] = None
            else:
                data[db_field] = None
        
        data['is_active'] = 1
        
        if self.vessel_id:
            db.update('vessels', self.vessel_id, data)
            messagebox.showinfo(lang.get('success'), "Vessel updated")
        else:
            db.insert('vessels', data)
            messagebox.showinfo(lang.get('success'), "Vessel added")
        
        self.dialog.destroy()
        if self.on_save:
            self.on_save()