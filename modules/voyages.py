import tkinter as tk
from tkinter import ttk, messagebox
from database.db_manager import db
from utils.language_manager import lang

class VoyageManager:
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.frame = ttk.Frame(parent)
        self.current_charter_id = None
        self.current_voyage_id = None

        self.setup_ui()
        self.load_charters()

    def setup_ui(self):
        # Top: charter party selector
        top_frame = ttk.LabelFrame(self.frame, text="Select Charter Party", padding=10)
        top_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(top_frame, text="Charter Party:").pack(side='left', padx=5)
        self.charter_combo = ttk.Combobox(top_frame, state='readonly', width=50)
        self.charter_combo.pack(side='left', padx=5)
        self.charter_combo.bind('<<ComboboxSelected>>', self.on_charter_selected)

        ttk.Button(top_frame, text="Add Voyage", command=self.add_voyage).pack(side='left', padx=20)
        ttk.Button(top_frame, text="Refresh", command=self.load_voyages).pack(side='left', padx=5)

        # Treeview for voyages
        columns = ('id', 'number', 'load_port', 'discharge_port', 'start_date', 'end_date', 'cargo', 'quantity', 'laden')
        self.tree = ttk.Treeview(self.frame, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            self.tree.column(col, width=100)
        self.tree.column('number', width=120)
        self.tree.column('load_port', width=120)
        self.tree.column('discharge_port', width=120)
        self.tree.column('cargo', width=120)

        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=10, pady=5)
        scrollbar.pack(side='right', fill='y', pady=5)

        self.tree.bind('<Double-1>', lambda e: self.edit_voyage())

        # Buttons for edit/delete
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(fill='x', padx=10, pady=5)
        ttk.Button(btn_frame, text="Edit Voyage", command=self.edit_voyage).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Delete Voyage", command=self.delete_voyage).pack(side='left', padx=5)

    def load_charters(self):
        """Populate charter party dropdown"""
        charters = db.fetch_all("""
            SELECT c.id, v.name as vessel_name, c.charterer_name, c.charter_type
            FROM charter_parties c
            JOIN vessels v ON c.vessel_id = v.id
            WHERE c.is_active = 1
            ORDER BY c.charter_date DESC
        """)
        charter_list = [f"{c['id']} - {c['vessel_name']} / {c['charterer_name']} ({c['charter_type']})" for c in charters]
        self.charter_combo['values'] = charter_list
        self.charter_map = {item: c['id'] for item, c in zip(charter_list, charters)}

    def on_charter_selected(self, event=None):
        selection = self.charter_combo.get()
        if selection and selection in self.charter_map:
            self.current_charter_id = self.charter_map[selection]
            self.load_voyages()

    def load_voyages(self):
        if not self.current_charter_id:
            self.tree.delete(*self.tree.get_children())
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        voyages = db.fetch_all("""
            SELECT id, voyage_number, load_port, discharge_port,
                   start_date, end_date, cargo_name, cargo_quantity_loaded, is_laden
            FROM voyages
            WHERE charter_party_id = ?
            ORDER BY start_date DESC
        """, (self.current_charter_id,))

        for v in voyages:
            laden = "Yes" if v['is_laden'] else "No"
            self.tree.insert('', 'end', iid=str(v['id']), values=(
                v['id'], v['voyage_number'] or '', v['load_port'] or '', v['discharge_port'] or '',
                v['start_date'] or '', v['end_date'] or '', v['cargo_name'] or '',
                v['cargo_quantity_loaded'] or '', laden
            ))

    def add_voyage(self):
        if not self.current_charter_id:
            messagebox.showwarning("Warning", "Please select a charter party first")
            return
        VoyageDialog(self.frame, self.current_charter_id, on_save=self.load_voyages)

    def edit_voyage(self):
        if not self.current_charter_id:
            messagebox.showwarning("Warning", "Please select a charter party first")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a voyage to edit")
            return
        voyage_id = int(selected[0])
        VoyageDialog(self.frame, self.current_charter_id, voyage_id, self.load_voyages)

    def delete_voyage(self):
        if not self.current_charter_id:
            messagebox.showwarning("Warning", "Please select a charter party first")
            return
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a voyage to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this voyage? All linked daily reports will be disassociated."):
            voyage_id = int(selected[0])
            # Optionally set daily_reports.voyage_id = NULL for those linked
            db.execute_query("UPDATE daily_reports SET voyage_id = NULL WHERE voyage_id = ?", (voyage_id,))
            db.delete('voyages', voyage_id)
            self.load_voyages()


class VoyageDialog:
    def __init__(self, parent, charter_party_id, voyage_id=None, on_save=None):
        self.parent = parent
        self.charter_party_id = charter_party_id
        self.voyage_id = voyage_id
        self.on_save = on_save

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Voyage" + (" - Edit" if voyage_id else " - Add"))
        self.dialog.geometry("500x550")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.setup_ui()
        if voyage_id:
            self.load_data()

    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        fields = [
            ('voyage_number', 'Voyage Number:'),
            ('load_port', 'Load Port:'),
            ('discharge_port', 'Discharge Port:'),
            ('start_date', 'Start Date (YYYY-MM-DD):'),
            ('end_date', 'End Date (YYYY-MM-DD):'),
            ('cargo_name', 'Cargo Name:'),
            ('cargo_quantity_loaded', 'Cargo Quantity (MT):'),
            ('is_laden', 'Laden / Ballast:'),
            ('voyage_notes', 'Notes:'),
        ]

        self.entries = {}
        row = 0
        for field, label in fields:
            tk.Label(main_frame, text=label).grid(row=row, column=0, sticky='e', padx=5, pady=5)
            if field == 'is_laden':
                self.laden_var = tk.StringVar(value="Yes")
                combo = ttk.Combobox(main_frame, textvariable=self.laden_var, values=['Yes', 'No'], state='readonly', width=27)
                combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
                self.entries[field] = combo
            elif field == 'voyage_notes':
                text = tk.Text(main_frame, width=40, height=4)
                text.grid(row=row, column=1, sticky='w', padx=5, pady=5)
                self.entries[field] = text
            else:
                entry = tk.Entry(main_frame, width=30)
                entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
                self.entries[field] = entry
            row += 1

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side='left', padx=5)

    def load_data(self):
        voyage = db.fetch_one("SELECT * FROM voyages WHERE id = ?", (self.voyage_id,))
        if not voyage:
            return

        for field, widget in self.entries.items():
            value = voyage.get(field)
            if value is not None:
                if isinstance(widget, tk.Entry):
                    widget.delete(0, tk.END)
                    widget.insert(0, str(value))
                elif isinstance(widget, tk.Text):
                    widget.delete('1.0', tk.END)
                    widget.insert('1.0', str(value))
                elif isinstance(widget, ttk.Combobox) and field == 'is_laden':
                    widget.set('Yes' if value else 'No')

    def save(self):
        data = {}
        # Collect values
        for field, widget in self.entries.items():
            if field == 'is_laden':
                val = self.laden_var.get()
                data[field] = 1 if val == 'Yes' else 0
            elif isinstance(widget, tk.Entry):
                val = widget.get().strip()
                if field in ('cargo_quantity_loaded',):
                    try:
                        data[field] = float(val) if val else None
                    except ValueError:
                        data[field] = None
                else:
                    data[field] = val if val else None
            elif isinstance(widget, tk.Text):
                val = widget.get('1.0', tk.END).strip()
                data[field] = val if val else None
            elif isinstance(widget, ttk.Combobox):
                data[field] = widget.get()

        data['charter_party_id'] = self.charter_party_id

        if self.voyage_id:
            db.update('voyages', self.voyage_id, data)
            messagebox.showinfo("Success", "Voyage updated")
        else:
            db.insert('voyages', data)
            messagebox.showinfo("Success", "Voyage added")

        self.dialog.destroy()
        if self.on_save:
            self.on_save()