import tkinter as tk
from tkinter import ttk, messagebox
from database.db_manager import db
from utils.language_manager import lang

class VesselManager:
    """Vessel management module"""
    
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.frame = ttk.Frame(parent)
        
        self.setup_ui()
        self.load_vessels()
    
    def setup_ui(self):
        # Toolbar
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
        
        # Treeview
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
        
        vessels = db.fetch_all("SELECT id, name, imo_number, vessel_type, deadweight_mt FROM vessels WHERE is_active = 1 ORDER BY name")
        
        for v in vessels:
            self.tree.insert('', 'end', values=(
                v['id'], v['name'], v['imo_number'],
                v['vessel_type'], v['deadweight_mt']
            ))
    
    def add_vessel(self):
        VesselDialog(self.frame, on_save=self.load_vessels)
    
    def edit_vessel(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning(lang.get('warning'), "Please select a vessel to edit")
            return
        vessel_id = self.tree.item(selected[0])['values'][0]
        VesselDialog(self.frame, vessel_id, self.load_vessels)
    
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
    def __init__(self, parent, vessel_id=None, on_save=None):
        self.parent = parent
        self.vessel_id = vessel_id
        self.on_save = on_save
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(lang.get('add_vessel') if not vessel_id else lang.get('edit_vessel'))
        self.dialog.geometry("400x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        
        if vessel_id:
            self.load_data()
    
    def setup_ui(self):
        main_frame = tk.Frame(self.dialog, padx=20, pady=20)
        main_frame.pack(fill='both', expand=True)
        
        fields = [
            ('vessel_name', 'name'),
            ('imo_number', 'imo_number'),
            ('year_built', 'year_built'),
            ('flag', 'flag'),
            ('vessel_type', 'vessel_type'),
            ('deadweight_mt', 'deadweight_mt'),
        ]
        
        self.entries = {}
        
        for i, (label_key, field) in enumerate(fields):
            tk.Label(main_frame, text=lang.get(label_key)).grid(row=i, column=0, sticky='e', padx=5, pady=5)
            entry = tk.Entry(main_frame, width=30)
            entry.grid(row=i, column=1, sticky='w', padx=5, pady=5)
            self.entries[field] = entry
        
        # Buttons
        btn_frame = tk.Frame(main_frame)
        btn_frame.grid(row=len(fields), column=0, columnspan=2, pady=20)
        
        tk.Button(btn_frame, text=lang.get('save'), command=self.save).pack(side='left', padx=5)
        tk.Button(btn_frame, text=lang.get('cancel'), command=self.dialog.destroy).pack(side='left', padx=5)
    
    def load_data(self):
        vessel = db.fetch_one("SELECT * FROM vessels WHERE id = ?", (self.vessel_id,))
        if vessel:
            for field, entry in self.entries.items():
                if vessel.get(field):
                    entry.delete(0, tk.END)
                    entry.insert(0, str(vessel[field]))
    
    def save(self):
        data = {field: entry.get().strip() for field, entry in self.entries.items()}
        data['is_active'] = 1
        
        # Convert numeric fields
        if data.get('year_built'):
            try:
                data['year_built'] = int(data['year_built'])
            except ValueError:
                data['year_built'] = None
        
        if data.get('deadweight_mt'):
            try:
                data['deadweight_mt'] = float(data['deadweight_mt'])
            except ValueError:
                data['deadweight_mt'] = None
        
        if self.vessel_id:
            db.update('vessels', self.vessel_id, data)
            messagebox.showinfo(lang.get('success'), "Vessel updated")
        else:
            db.insert('vessels', data)
            messagebox.showinfo(lang.get('success'), "Vessel added")
        
        self.dialog.destroy()
        if self.on_save:
            self.on_save()