import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from database.db_manager import db
from utils.language_manager import lang
from utils.excel_exporter import excel_exporter

class BunkerManager:
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.frame = ttk.Frame(parent)
        self.current_bunker_id = None

        self.setup_ui()
        self.load_bunkers()

    def setup_ui(self):
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill='x', padx=5, pady=5)
        ttk.Button(toolbar, text="Add Bunker", command=self.add_bunker).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Edit Bunker", command=self.edit_bunker).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Delete Bunker", command=self.delete_bunker).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Export to Excel", command=self.export_to_excel).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Refresh", command=self.load_bunkers).pack(side='left', padx=2)

        filter_frame = ttk.LabelFrame(self.frame, text="Filters", padding=5)
        filter_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(filter_frame, text="Vessel:").grid(row=0, column=0, padx=5, pady=2)
        self.vessel_filter = ttk.Combobox(filter_frame, state='readonly', width=20)
        self.vessel_filter.grid(row=0, column=1, padx=5, pady=2)
        self.vessel_filter.bind('<<ComboboxSelected>>', lambda e: self.load_bunkers())

        vessels = db.fetch_all("SELECT id, name FROM vessels WHERE is_active = 1 ORDER BY name")
        vessel_list = [f"{v['id']} - {v['name']}" for v in vessels]
        self.vessel_filter['values'] = [''] + vessel_list
        self.vessel_map = {f"{v['id']} - {v['name']}": v['id'] for v in vessels}
        self.vessel_filter.set('')

        columns = ('id', 'date', 'vessel', 'port', 'grade', 'ifo', 'mgo', 'ifo_price', 'mgo_price', 'total_cost', 'supplier')
        self.tree = ttk.Treeview(self.frame, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            self.tree.column(col, width=100)
        self.tree.column('port', width=120)
        self.tree.column('supplier', width=150)
        self.tree.column('total_cost', width=120)
        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y', pady=5)
        self.tree.bind('<Double-1>', lambda e: self.edit_bunker())

    def load_bunkers(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        query = """
            SELECT b.id, b.replenishment_datetime, v.name, b.port_name, b.fuel_grade,
                   b.ifo_amount_mt, b.mgo_amount_mt,
                   b.ifo_price_per_mt, b.mgo_price_per_mt,
                   b.cost_original, b.supplier
            FROM bunker_replenishments b
            JOIN vessels v ON b.vessel_id = v.id
            WHERE 1=1
        """
        params = []
        vessel_sel = self.vessel_filter.get()
        if vessel_sel and vessel_sel in self.vessel_map:
            query += " AND b.vessel_id = ?"
            params.append(self.vessel_map[vessel_sel])

        query += " ORDER BY b.replenishment_datetime DESC"
        rows = db.fetch_all(query, params)

        for r in rows:
            total_cost = r['cost_original'] or 0
            self.tree.insert('', 'end', iid=str(r['id']), values=(
                r['id'],
                r['replenishment_datetime'][:16] if r['replenishment_datetime'] else '',
                r['name'],
                r['port_name'] or '',
                r['fuel_grade'],
                r['ifo_amount_mt'] or '',
                r['mgo_amount_mt'] or '',
                r['ifo_price_per_mt'] or '',
                r['mgo_price_per_mt'] or '',
                f"{total_cost:.2f}",
                r['supplier'] or ''
            ))

    def add_bunker(self):
        BunkerDialog(self.frame, self.current_user, on_save=self.load_bunkers)

    def edit_bunker(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a bunker event to edit")
            return
        bunker_id = int(sel[0])
        BunkerDialog(self.frame, self.current_user, bunker_id, self.load_bunkers)

    def delete_bunker(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a bunker event to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this bunker event? This may affect consumption calculations."):
            bunker_id = int(sel[0])
            db.delete('bunker_replenishments', bunker_id)
            self.load_bunkers()

    def export_to_excel(self):
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            data.append([str(v) for v in values])
        headers = [self.tree.heading(col)['text'] for col in self.tree['columns']]
        filename = f"bunker_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        excel_exporter.export_report(data, filename, "Bunker Replenishments", headers)
        messagebox.showinfo("Export", f"Exported to {filename}")


class BunkerDialog:
    def __init__(self, parent, current_user, bunker_id=None, on_save=None):
        self.parent = parent
        self.current_user = current_user
        self.bunker_id = bunker_id
        self.on_save = on_save

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Bunker Replenishment" + (" - Edit" if bunker_id else " - Add"))
        self.dialog.geometry("600x780")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.vessel_map = {}
        self.setup_ui()
        if bunker_id:
            self.load_data()

    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        row = 0
        # Vessel
        tk.Label(main_frame, text="Vessel:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.vessel_combo = ttk.Combobox(main_frame, state='readonly', width=30)
        self.vessel_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.load_vessels()
        row += 1

        # Date/time
        tk.Label(main_frame, text="Replenishment Date/Time (YYYY-MM-DD HH:MM):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.datetime_entry = tk.Entry(main_frame, width=30)
        self.datetime_entry.insert(0, datetime.now().strftime('%Y-%m-%d %H:%M:00'))
        self.datetime_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Port
        tk.Label(main_frame, text="Port:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.port_entry = tk.Entry(main_frame, width=30)
        self.port_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Fuel grade
        tk.Label(main_frame, text="Fuel Grade:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.grade_var = tk.StringVar(value="both")
        grade_frame = ttk.Frame(main_frame)
        grade_frame.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        ttk.Radiobutton(grade_frame, text="IFO only", variable=self.grade_var, value="IFO").pack(side='left')
        ttk.Radiobutton(grade_frame, text="MGO only", variable=self.grade_var, value="MGO").pack(side='left', padx=10)
        ttk.Radiobutton(grade_frame, text="Both", variable=self.grade_var, value="both").pack(side='left')
        self.grade_var.trace('w', self.update_total_cost)
        row += 1

        # IFO amount
        tk.Label(main_frame, text="IFO Amount (MT):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.ifo_entry = tk.Entry(main_frame, width=30)
        self.ifo_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.ifo_entry.bind('<KeyRelease>', self.update_total_cost)
        row += 1

        # IFO Price per MT
        tk.Label(main_frame, text="IFO Price (per MT, RUB):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.ifo_price_entry = tk.Entry(main_frame, width=30)
        self.ifo_price_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.ifo_price_entry.bind('<KeyRelease>', self.update_total_cost)
        row += 1

        # MGO amount
        tk.Label(main_frame, text="MGO Amount (MT):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.mgo_entry = tk.Entry(main_frame, width=30)
        self.mgo_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.mgo_entry.bind('<KeyRelease>', self.update_total_cost)
        row += 1

        # MGO Price per MT
        tk.Label(main_frame, text="MGO Price (per MT, RUB):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.mgo_price_entry = tk.Entry(main_frame, width=30)
        self.mgo_price_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.mgo_price_entry.bind('<KeyRelease>', self.update_total_cost)
        row += 1

        # Total Cost (read-only, auto-calculated)
        tk.Label(main_frame, text="Total Cost (RUB):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.total_cost_entry = tk.Entry(main_frame, width=30, state='readonly')
        self.total_cost_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Supplier
        tk.Label(main_frame, text="Supplier:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.supplier_entry = tk.Entry(main_frame, width=30)
        self.supplier_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Delivery Receipt Number
        tk.Label(main_frame, text="Delivery Receipt #:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.receipt_entry = tk.Entry(main_frame, width=30)
        self.receipt_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Invoice Number
        tk.Label(main_frame, text="Invoice #:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.invoice_entry = tk.Entry(main_frame, width=30)
        self.invoice_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Payment Terms
        tk.Label(main_frame, text="Payment Terms:").grid(row=row, column=0, sticky='ne', padx=5, pady=5)
        self.payment_text = tk.Text(main_frame, width=40, height=3)
        self.payment_text.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Notes
        tk.Label(main_frame, text="Notes:").grid(row=row, column=0, sticky='ne', padx=5, pady=5)
        self.notes_text = tk.Text(main_frame, width=40, height=3)
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

    def update_total_cost(self, *args):
        """Calculate total cost from quantities and prices."""
        try:
            ifo_qty = float(self.ifo_entry.get().strip()) if self.ifo_entry.get().strip() else 0
        except ValueError:
            ifo_qty = 0
        try:
            ifo_price = float(self.ifo_price_entry.get().strip()) if self.ifo_price_entry.get().strip() else 0
        except ValueError:
            ifo_price = 0
        try:
            mgo_qty = float(self.mgo_entry.get().strip()) if self.mgo_entry.get().strip() else 0
        except ValueError:
            mgo_qty = 0
        try:
            mgo_price = float(self.mgo_price_entry.get().strip()) if self.mgo_price_entry.get().strip() else 0
        except ValueError:
            mgo_price = 0

        total = ifo_qty * ifo_price + mgo_qty * mgo_price
        self.total_cost_entry.config(state='normal')
        self.total_cost_entry.delete(0, tk.END)
        self.total_cost_entry.insert(0, f"{total:.2f}" if total else "")
        self.total_cost_entry.config(state='readonly')

    def load_data(self):
        bunker = db.fetch_one("SELECT * FROM bunker_replenishments WHERE id = ?", (self.bunker_id,))
        if not bunker:
            return
        # Vessel
        vessel = db.fetch_one("SELECT id, name FROM vessels WHERE id = ?", (bunker['vessel_id'],))
        if vessel:
            self.vessel_combo.set(f"{vessel['id']} - {vessel['name']}")

        # Clear and load date/time
        self.datetime_entry.delete(0, tk.END)
        if bunker['replenishment_datetime']:
            # Store only first 16 characters (YYYY-MM-DD HH:MM)
            dt_str = bunker['replenishment_datetime'][:16]
            self.datetime_entry.insert(0, dt_str)

        # Clear and load other fields
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, bunker['port_name'] or '')

        self.grade_var.set(bunker['fuel_grade'] or 'both')

        self.ifo_entry.delete(0, tk.END)
        if bunker['ifo_amount_mt']:
            self.ifo_entry.insert(0, str(bunker['ifo_amount_mt']))

        self.mgo_entry.delete(0, tk.END)
        if bunker['mgo_amount_mt']:
            self.mgo_entry.insert(0, str(bunker['mgo_amount_mt']))

        self.ifo_price_entry.delete(0, tk.END)
        if bunker['ifo_price_per_mt']:
            self.ifo_price_entry.insert(0, str(bunker['ifo_price_per_mt']))

        self.mgo_price_entry.delete(0, tk.END)
        if bunker['mgo_price_per_mt']:
            self.mgo_price_entry.insert(0, str(bunker['mgo_price_per_mt']))

        # Update total cost (this will also clear and recompute)
        self.update_total_cost()

        self.supplier_entry.delete(0, tk.END)
        self.supplier_entry.insert(0, bunker['supplier'] or '')

        self.receipt_entry.delete(0, tk.END)
        self.receipt_entry.insert(0, bunker['delivery_receipt_number'] or '')

        self.invoice_entry.delete(0, tk.END)
        self.invoice_entry.insert(0, bunker['invoice_number'] or '')

        self.payment_text.delete('1.0', tk.END)
        self.payment_text.insert('1.0', bunker['payment_terms'] or '')

        self.notes_text.delete('1.0', tk.END)
        self.notes_text.insert('1.0', bunker['notes'] or '')
        
    def save(self):
        vessel_sel = self.vessel_combo.get()
        if not vessel_sel or vessel_sel not in self.vessel_map:
            messagebox.showerror("Error", "Please select a vessel")
            return
        vessel_id = self.vessel_map[vessel_sel]

        datetime_str = self.datetime_entry.get().strip()
        if not datetime_str:
            messagebox.showerror("Error", "Replenishment date/time is required")
            return
        try:
            dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                dt = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M')
            except:
                messagebox.showerror("Error", "Invalid date/time format. Use YYYY-MM-DD HH:MM")
                return

        fuel_grade = self.grade_var.get()
        ifo_amount = None
        mgo_amount = None
        if fuel_grade in ('IFO', 'both'):
            try:
                ifo_amount = float(self.ifo_entry.get().strip()) if self.ifo_entry.get().strip() else None
            except:
                pass
        if fuel_grade in ('MGO', 'both'):
            try:
                mgo_amount = float(self.mgo_entry.get().strip()) if self.mgo_entry.get().strip() else None
            except:
                pass

        # Prices
        ifo_price = None
        mgo_price = None
        try:
            ifo_price = float(self.ifo_price_entry.get().strip()) if self.ifo_price_entry.get().strip() else None
        except:
            pass
        try:
            mgo_price = float(self.mgo_price_entry.get().strip()) if self.mgo_price_entry.get().strip() else None
        except:
            pass

        # Total cost (computed from prices & quantities; if user entered manual cost we could override)
        total_cost = None
        total_str = self.total_cost_entry.get().strip()
        if total_str:
            try:
                total_cost = float(total_str)
            except:
                pass

        # If total cost is empty, try to compute from ifo_price and mgo_price and quantities
        if total_cost is None:
            if ifo_amount and ifo_price:
                total_cost = ifo_amount * ifo_price
            if mgo_amount and mgo_price:
                if total_cost is None:
                    total_cost = mgo_amount * mgo_price
                else:
                    total_cost += mgo_amount * mgo_price

        data = {
            'vessel_id': vessel_id,
            'replenishment_datetime': dt.strftime('%Y-%m-%d %H:%M:%S'),
            'port_name': self.port_entry.get().strip() or None,
            'fuel_grade': fuel_grade,
            'ifo_amount_mt': ifo_amount,
            'mgo_amount_mt': mgo_amount,
            'ifo_price_per_mt': ifo_price,
            'mgo_price_per_mt': mgo_price,
            'cost_original': total_cost,
            'cost_currency': 'RUB',
            'cost_rub': total_cost,
            'supplier': self.supplier_entry.get().strip() or None,
            'delivery_receipt_number': self.receipt_entry.get().strip() or None,
            'invoice_number': self.invoice_entry.get().strip() or None,
            'payment_terms': self.payment_text.get('1.0', tk.END).strip() or None,
            'notes': self.notes_text.get('1.0', tk.END).strip() or None,
            'created_by': self.current_user['username']
        }

        if self.bunker_id:
            db.update('bunker_replenishments', self.bunker_id, data)
            messagebox.showinfo("Success", "Bunker event updated")
        else:
            db.insert('bunker_replenishments', data)
            messagebox.showinfo("Success", "Bunker event added")

        self.dialog.destroy()
        if self.on_save:
            self.on_save()