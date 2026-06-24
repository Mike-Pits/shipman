import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
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

        # Idle voyage management
        idle_frame = ttk.Frame(top_frame)
        idle_frame.pack(side='left', padx=20)
        ttk.Button(idle_frame, text="Start Idle Voyage", command=self.start_idle_voyage).pack(side='left', padx=2)
        ttk.Button(idle_frame, text="Close Idle Voyage", command=self.close_idle_voyage).pack(side='left', padx=2)

        # Treeview for voyages
        columns = ('id', 'number', 'load_port', 'discharge_port', 'start_date', 'end_date', 'cargo', 'quantity', 'laden', 'idle')
        self.tree = ttk.Treeview(self.frame, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            self.tree.column(col, width=100)
        self.tree.column('number', width=120)
        self.tree.column('load_port', width=120)
        self.tree.column('discharge_port', width=120)
        self.tree.column('cargo', width=120)
        self.tree.column('idle', width=60)

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
        charters = db.fetch_all("""
            SELECT c.id, v.name as vessel_name, c.charterer_name, c.charter_type
            FROM charter_parties c
            JOIN vessels v ON c.vessel_id = v.id
            WHERE c.is_active = 1
            ORDER BY c.charter_date DESC
        """)
        charter_list = [f"{c['id']} - {c['vessel_name']} / {c['charterer_name']} ({c['charter_type']})" for c in charters]
        # Add an entry for "Idle voyages" – this will show voyages without a charter party
        charter_list.append("0 - Idle Voyages")
        self.charter_combo['values'] = charter_list
        self.charter_map = {}
        for item, c in zip(charter_list[:-1], charters):
            self.charter_map[item] = c['id']
        self.charter_map["0 - Idle Voyages"] = 0  # 0 means "idle"

    def on_charter_selected(self, event=None):
        selection = self.charter_combo.get()
        if selection and selection in self.charter_map:
            self.current_charter_id = self.charter_map[selection]
            self.load_voyages()

    def load_voyages(self):
        if self.current_charter_id is None:
            self.tree.delete(*self.tree.get_children())
            return

        if self.current_charter_id == 0:
            # Show idle voyages (charter_party_id IS NULL)
            voyages = db.fetch_all("""
                SELECT id, voyage_number, load_port, discharge_port,
                       start_date, end_date, cargo_name, cargo_quantity_loaded, is_laden, is_idle
                FROM voyages
                WHERE charter_party_id IS NULL AND is_idle = 1
                ORDER BY start_date DESC
            """)
        else:
            voyages = db.fetch_all("""
                SELECT id, voyage_number, load_port, discharge_port,
                       start_date, end_date, cargo_name, cargo_quantity_loaded, is_laden, is_idle
                FROM voyages
                WHERE charter_party_id = ?
                ORDER BY start_date DESC
            """, (self.current_charter_id,))

        for item in self.tree.get_children():
            self.tree.delete(item)

        for v in voyages:
            laden = "Yes" if v['is_laden'] else "No"
            idle = "Yes" if v['is_idle'] else "No"
            self.tree.insert('', 'end', iid=str(v['id']), values=(
                v['id'], v['voyage_number'] or '', v['load_port'] or '', v['discharge_port'] or '',
                v['start_date'] or '', v['end_date'] or '', v['cargo_name'] or '',
                v['cargo_quantity_loaded'] or '', laden, idle
            ))

    def add_voyage(self):
        if self.current_charter_id is None:
            messagebox.showwarning("Warning", "Please select a charter party first (or 'Idle Voyages')")
            return
        # If "Idle Voyages" is selected, allow creating a voyage without charter party
        if self.current_charter_id == 0:
            charter_id = None
        else:
            charter_id = self.current_charter_id
        VoyageDialog(self.frame, charter_id, on_save=self.load_voyages)

    def edit_voyage(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a voyage to edit")
            return
        voyage_id = int(selected[0])
        voyage = db.fetch_one("SELECT * FROM voyages WHERE id = ?", (voyage_id,))
        if not voyage:
            return
        # Pass the charter_party_id (may be None)
        VoyageDialog(self.frame, voyage['charter_party_id'], voyage_id, self.load_voyages)

    def delete_voyage(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a voyage to delete")
            return
        voyage_id = int(selected[0])
        voyage = db.fetch_one("SELECT is_idle FROM voyages WHERE id = ?", (voyage_id,))
        if voyage and voyage.get('is_idle'):
            # Allow deletion of idle voyages (but prompt confirmation)
            if not messagebox.askyesno("Confirm", "Delete this idle voyage? All linked daily reports will be disassociated."):
                return
        else:
            if not messagebox.askyesno("Confirm", "Delete this voyage? All linked daily reports will be disassociated."):
                return
        db.execute_query("UPDATE daily_reports SET voyage_id = NULL WHERE voyage_id = ?", (voyage_id,))
        db.delete('voyages', voyage_id)
        self.load_voyages()

    def start_idle_voyage(self):
        """Create a new idle voyage for the selected vessel (if a vessel is selected)."""
        # We need to know which vessel. We can get it from the charter selection.
        if self.current_charter_id is None:
            messagebox.showwarning("Warning", "Please select a charter party or 'Idle Voyages' first.")
            return
        # Get vessel_id from charter or from an existing voyage?
        vessel_id = None
        if self.current_charter_id == 0:
            # For idle voyages, we need to ask the user which vessel.
            # We'll show a dialog to select vessel.
            vessel_id = self.ask_vessel()
            if not vessel_id:
                return
        else:
            # Get vessel from charter
            charter = db.fetch_one("SELECT vessel_id FROM charter_parties WHERE id = ?", (self.current_charter_id,))
            if charter:
                vessel_id = charter['vessel_id']
            else:
                messagebox.showerror("Error", "Could not find vessel for this charter.")
                return

        # Check if there is already an open idle voyage for this vessel (without end_date)
        open_idle = db.fetch_one("""
            SELECT id FROM voyages
            WHERE vessel_id = ? AND is_idle = 1 AND end_date IS NULL
        """, (vessel_id,))
        if open_idle:
            messagebox.showwarning("Warning", "There is already an open idle voyage for this vessel. Please close it first.")
            return

        # Generate a voyage number
        today = datetime.now().strftime('%Y%m%d')
        number = f"IDLE-{today}"
        # Optionally add a suffix if multiple idle periods start on same day (unlikely)
        data = {
            'vessel_id': vessel_id,
            'voyage_number': number,
            'load_port': 'Idle',
            'discharge_port': 'Idle',
            'start_date': datetime.now().strftime('%Y-%m-%d'),
            'end_date': None,
            'cargo_name': None,
            'cargo_quantity_loaded': None,
            'is_laden': 0,
            'is_idle': 1,
            'charter_party_id': None if self.current_charter_id == 0 else self.current_charter_id,
            'voyage_notes': 'Idle period'
        }
        db.insert('voyages', data)
        messagebox.showinfo("Success", f"Idle voyage {number} started.")
        self.load_voyages()

    def close_idle_voyage(self):
        """Close the currently open idle voyage for the selected vessel."""
        if self.current_charter_id is None:
            messagebox.showwarning("Warning", "Please select a charter party or 'Idle Voyages' first.")
            return
        vessel_id = None
        if self.current_charter_id == 0:
            # Ask for vessel
            vessel_id = self.ask_vessel()
            if not vessel_id:
                return
        else:
            charter = db.fetch_one("SELECT vessel_id FROM charter_parties WHERE id = ?", (self.current_charter_id,))
            if charter:
                vessel_id = charter['vessel_id']
            else:
                messagebox.showerror("Error", "Could not find vessel for this charter.")
                return

        open_idle = db.fetch_one("""
            SELECT id FROM voyages
            WHERE vessel_id = ? AND is_idle = 1 AND end_date IS NULL
        """, (vessel_id,))
        if not open_idle:
            messagebox.showwarning("Warning", "No open idle voyage found for this vessel.")
            return

        if messagebox.askyesno("Confirm", "Close idle voyage? It will be ended today."):
            db.update('voyages', open_idle['id'], {'end_date': datetime.now().strftime('%Y-%m-%d')})
            messagebox.showinfo("Success", "Idle voyage closed.")
            self.load_voyages()

    def ask_vessel(self):
        """Simple dialog to select a vessel (used for idle voyages)."""
        vessels = db.fetch_all("SELECT id, name FROM vessels WHERE is_active = 1 ORDER BY name")
        vessel_list = [f"{v['id']} - {v['name']}" for v in vessels]
        if not vessel_list:
            messagebox.showerror("Error", "No active vessels found.")
            return None
        dialog = tk.Toplevel(self.frame)
        dialog.title("Select Vessel")
        dialog.geometry("300x150")
        dialog.transient(self.frame)
        dialog.grab_set()
        tk.Label(dialog, text="Select Vessel:").pack(pady=5)
        var = tk.StringVar()
        combo = ttk.Combobox(dialog, textvariable=var, values=vessel_list, state='readonly', width=30)
        combo.pack(pady=5)
        combo.set(vessel_list[0])
        result = None
        def on_ok():
            nonlocal result
            sel = var.get()
            if sel:
                vessel_id = int(sel.split(' - ')[0])
                result = vessel_id
            dialog.destroy()
        tk.Button(dialog, text="OK", command=on_ok).pack(pady=10)
        dialog.wait_window()
        return result


class VoyageDialog:
    def __init__(self, parent, charter_party_id, voyage_id=None, on_save=None):
        self.parent = parent
        self.charter_party_id = charter_party_id  # may be None for idle voyages
        self.voyage_id = voyage_id
        self.on_save = on_save

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Voyage" + (" - Edit" if voyage_id else " - Add"))
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.vessel_map = {}
        self.setup_ui()
        if voyage_id:
            self.load_data()

    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        row = 0
        # Idle voyage checkbox
        self.idle_var = tk.BooleanVar(value=False)
        self.idle_cb = ttk.Checkbutton(main_frame, text="Idle Voyage (no charter)", variable=self.idle_var, command=self.toggle_idle)
        self.idle_cb.grid(row=row, column=0, columnspan=2, sticky='w', padx=5, pady=5)
        row += 1

        # If this is an idle voyage (charter_party_id is None), we need vessel selection
        if self.charter_party_id is None:
            # Show vessel dropdown
            tk.Label(main_frame, text="Vessel:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
            self.vessel_combo = ttk.Combobox(main_frame, state='readonly', width=27)
            self.vessel_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
            self.load_vessels()
            row += 1
        else:
            self.vessel_combo = None

        # Voyage number
        tk.Label(main_frame, text="Voyage Number:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.number_entry = tk.Entry(main_frame, width=30)
        self.number_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Load port
        tk.Label(main_frame, text="Load Port:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.load_port_entry = tk.Entry(main_frame, width=30)
        self.load_port_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Discharge port
        tk.Label(main_frame, text="Discharge Port:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.discharge_port_entry = tk.Entry(main_frame, width=30)
        self.discharge_port_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Start date
        tk.Label(main_frame, text="Start Date (YYYY-MM-DD):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.start_date_entry = tk.Entry(main_frame, width=30)
        self.start_date_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # End date
        tk.Label(main_frame, text="End Date (YYYY-MM-DD):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.end_date_entry = tk.Entry(main_frame, width=30)
        self.end_date_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Cargo name
        tk.Label(main_frame, text="Cargo Name:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.cargo_entry = tk.Entry(main_frame, width=30)
        self.cargo_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Cargo quantity
        tk.Label(main_frame, text="Cargo Quantity (MT):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.qty_entry = tk.Entry(main_frame, width=30)
        self.qty_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Laden / Ballast
        tk.Label(main_frame, text="Laden / Ballast:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.laden_var = tk.StringVar(value="Yes")
        self.laden_combo = ttk.Combobox(main_frame, textvariable=self.laden_var, values=['Yes', 'No'], state='readonly', width=27)
        self.laden_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Notes
        tk.Label(main_frame, text="Notes:").grid(row=row, column=0, sticky='ne', padx=5, pady=5)
        self.notes_text = tk.Text(main_frame, width=40, height=4)
        self.notes_text.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        ttk.Button(btn_frame, text="Save", command=self.save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.dialog.destroy).pack(side='left', padx=5)

    def load_vessels(self):
        vessels = db.fetch_all("SELECT id, name FROM vessels WHERE is_active = 1 ORDER BY name")
        vessel_list = [f"{v['id']} - {v['name']}" for v in vessels]
        self.vessel_combo['values'] = vessel_list
        self.vessel_map = {f"{v['id']} - {v['name']}": v['id'] for v in vessels}

    def toggle_idle(self):
        if self.idle_var.get():
            # Pre-fill fields for idle
            self.number_entry.delete(0, tk.END)
            self.number_entry.insert(0, "IDLE-" + datetime.now().strftime('%Y%m%d'))
            self.load_port_entry.delete(0, tk.END)
            self.load_port_entry.insert(0, "Idle")
            self.load_port_entry.config(state='readonly')
            self.discharge_port_entry.delete(0, tk.END)
            self.discharge_port_entry.insert(0, "Idle")
            self.discharge_port_entry.config(state='readonly')
            # Start date to today if empty
            if not self.start_date_entry.get():
                self.start_date_entry.insert(0, datetime.now().strftime('%Y-%m-%d'))
            # Set end date empty
            self.end_date_entry.delete(0, tk.END)
            self.cargo_entry.delete(0, tk.END)
            self.cargo_entry.config(state='readonly')
            self.qty_entry.delete(0, tk.END)
            self.qty_entry.config(state='readonly')
            self.laden_combo.set('No')
            self.laden_combo.config(state='disabled')
        else:
            self.load_port_entry.config(state='normal')
            self.discharge_port_entry.config(state='normal')
            self.cargo_entry.config(state='normal')
            self.qty_entry.config(state='normal')
            self.laden_combo.config(state='normal')

    def load_data(self):
        voyage = db.fetch_one("SELECT * FROM voyages WHERE id = ?", (self.voyage_id,))
        if not voyage:
            return

        is_idle = voyage.get('is_idle', 0)
        self.idle_var.set(bool(is_idle))
        self.toggle_idle()

        # Set fields
        self.number_entry.delete(0, tk.END)
        self.number_entry.insert(0, voyage['voyage_number'] or '')
        self.load_port_entry.delete(0, tk.END)
        self.load_port_entry.insert(0, voyage['load_port'] or '')
        self.discharge_port_entry.delete(0, tk.END)
        self.discharge_port_entry.insert(0, voyage['discharge_port'] or '')
        self.start_date_entry.delete(0, tk.END)
        self.start_date_entry.insert(0, voyage['start_date'] or '')
        self.end_date_entry.delete(0, tk.END)
        self.end_date_entry.insert(0, voyage['end_date'] or '')
        self.cargo_entry.delete(0, tk.END)
        self.cargo_entry.insert(0, voyage['cargo_name'] or '')
        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, str(voyage['cargo_quantity_loaded']) if voyage['cargo_quantity_loaded'] is not None else '')
        self.laden_var.set('Yes' if voyage['is_laden'] else 'No')
        self.notes_text.delete('1.0', tk.END)
        self.notes_text.insert('1.0', voyage['voyage_notes'] or '')

        if self.vessel_combo:
            # If idle, set vessel dropdown
            if voyage['vessel_id']:
                vessel = db.fetch_one("SELECT id, name FROM vessels WHERE id = ?", (voyage['vessel_id'],))
                if vessel:
                    self.vessel_combo.set(f"{vessel['id']} - {vessel['name']}")

    def save(self):
        # Get vessel_id if idle (charter_party_id is None)
        vessel_id = None
        if self.charter_party_id is None:
            if not self.vessel_combo:
                messagebox.showerror("Error", "Vessel selection is required for idle voyages.")
                return
            vessel_sel = self.vessel_combo.get()
            if vessel_sel not in self.vessel_map:
                messagebox.showerror("Error", "Please select a vessel.")
                return
            vessel_id = self.vessel_map[vessel_sel]
        else:
            # Get vessel from charter (optional, but we can set it)
            charter = db.fetch_one("SELECT vessel_id FROM charter_parties WHERE id = ?", (self.charter_party_id,))
            if charter:
                vessel_id = charter['vessel_id']

        data = {}
        data['charter_party_id'] = self.charter_party_id
        data['vessel_id'] = vessel_id
        data['voyage_number'] = self.number_entry.get().strip() or None
        data['load_port'] = self.load_port_entry.get().strip() or None
        data['discharge_port'] = self.discharge_port_entry.get().strip() or None
        data['start_date'] = self.start_date_entry.get().strip() or None
        data['end_date'] = self.end_date_entry.get().strip() or None
        data['cargo_name'] = self.cargo_entry.get().strip() or None
        qty_str = self.qty_entry.get().strip()
        data['cargo_quantity_loaded'] = float(qty_str) if qty_str else None
        data['is_laden'] = 1 if self.laden_var.get() == 'Yes' else 0
        data['is_idle'] = 1 if self.idle_var.get() else 0
        data['voyage_notes'] = self.notes_text.get('1.0', tk.END).strip() or None

        # If idle, force some fields
        if data['is_idle']:
            data['load_port'] = 'Idle'
            data['discharge_port'] = 'Idle'
            data['cargo_name'] = None
            data['cargo_quantity_loaded'] = None
            data['is_laden'] = 0
            if not data['voyage_number']:
                data['voyage_number'] = 'IDLE-' + datetime.now().strftime('%Y%m%d')

        if self.voyage_id:
            db.update('voyages', self.voyage_id, data)
            messagebox.showinfo("Success", "Voyage updated")
        else:
            db.insert('voyages', data)
            messagebox.showinfo("Success", "Voyage added")

        self.dialog.destroy()
        if self.on_save:
            self.on_save()