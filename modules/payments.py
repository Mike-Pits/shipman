import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from database.db_manager import db
from utils.language_manager import lang
from utils.excel_exporter import excel_exporter

class PaymentManager:
    def __init__(self, parent, current_user):
        self.parent = parent
        self.current_user = current_user
        self.frame = ttk.Frame(parent)
        self.current_payment_id = None

        self.setup_ui()
        self.load_payments()

    def setup_ui(self):
        # Toolbar
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill='x', padx=5, pady=5)
        ttk.Button(toolbar, text="Add Payment", command=self.add_payment).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Edit Payment", command=self.edit_payment).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Delete Payment", command=self.delete_payment).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Export to Excel", command=self.export_to_excel).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Refresh", command=self.load_payments).pack(side='left', padx=2)

        # Filter frame
        filter_frame = ttk.LabelFrame(self.frame, text="Filters", padding=5)
        filter_frame.pack(fill='x', padx=10, pady=5)

        ttk.Label(filter_frame, text="Vessel:").grid(row=0, column=0, padx=5, pady=2)
        self.vessel_filter = ttk.Combobox(filter_frame, state='readonly', width=20)
        self.vessel_filter.grid(row=0, column=1, padx=5, pady=2)
        self.vessel_filter.bind('<<ComboboxSelected>>', lambda e: self.load_payments())

        ttk.Label(filter_frame, text="Status:").grid(row=0, column=2, padx=5, pady=2)
        self.status_filter = ttk.Combobox(filter_frame, values=['', 'draft', 'pending', 'partial', 'paid', 'overdue', 'cancelled'], state='readonly', width=12)
        self.status_filter.grid(row=0, column=3, padx=5, pady=2)
        self.status_filter.bind('<<ComboboxSelected>>', lambda e: self.load_payments())

        ttk.Label(filter_frame, text="Type:").grid(row=0, column=4, padx=5, pady=2)
        self.type_filter = ttk.Combobox(filter_frame, values=['', 'income', 'expense'], state='readonly', width=10)
        self.type_filter.grid(row=0, column=5, padx=5, pady=2)
        self.type_filter.bind('<<ComboboxSelected>>', lambda e: self.load_payments())

        # Load vessel list for filter
        vessels = db.fetch_all("SELECT id, name FROM vessels WHERE is_active = 1 ORDER BY name")
        vessel_list = [f"{v['id']} - {v['name']}" for v in vessels]
        self.vessel_filter['values'] = [''] + vessel_list
        self.vessel_map = {f"{v['id']} - {v['name']}": v['id'] for v in vessels}
        self.vessel_filter.set('')

        # Treeview
        columns = ('id', 'date', 'type', 'cost_type', 'vendor', 'amount', 'status', 'vessel', 'voyage')
        self.tree = ttk.Treeview(self.frame, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col.replace('_', ' ').title())
            self.tree.column(col, width=100)
        self.tree.column('cost_type', width=150)
        self.tree.column('vendor', width=150)
        scrollbar = ttk.Scrollbar(self.frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y', pady=5)
        self.tree.bind('<Double-1>', lambda e: self.edit_payment())

    def load_payments(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        query = """
            SELECT p.id, p.invoice_date, ct.category, ct.name, v.legal_name,
                   p.rub_amount, p.status,
                   ves.name as vessel_name, vo.voyage_number
            FROM payments p
            JOIN cost_types ct ON p.cost_type_id = ct.id
            LEFT JOIN vessels ves ON p.vessel_id = ves.id
            LEFT JOIN voyages vo ON p.voyage_id = vo.id
            LEFT JOIN vendors v ON p.vendor_id = v.id
            WHERE 1=1
        """
        params = []
        vessel_sel = self.vessel_filter.get()
        if vessel_sel and vessel_sel in self.vessel_map:
            query += " AND p.vessel_id = ?"
            params.append(self.vessel_map[vessel_sel])
        status_sel = self.status_filter.get()
        if status_sel:
            query += " AND p.status = ?"
            params.append(status_sel)
        type_sel = self.type_filter.get()
        if type_sel:
            query += " AND ct.category = ?"
            params.append(type_sel)

        query += " ORDER BY p.invoice_date DESC"
        rows = db.fetch_all(query, params)

        for r in rows:
            self.tree.insert('', 'end', iid=str(r['id']), values=(
                r['id'],
                r['invoice_date'][:10] if r['invoice_date'] else '',
                r['category'],
                r['name'],
                r['legal_name'] or '',
                r['rub_amount'],
                r['status'],
                r['vessel_name'] or '',
                r['voyage_number'] or ''
            ))

    def add_payment(self):
        PaymentDialog(self.frame, self.current_user, on_save=self.load_payments)

    def edit_payment(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a payment to edit")
            return
        payment_id = int(sel[0])
        PaymentDialog(self.frame, self.current_user, payment_id, self.load_payments)

    def delete_payment(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Warning", "Please select a payment to delete")
            return
        if messagebox.askyesno("Confirm", "Delete this payment?"):
            payment_id = int(sel[0])
            db.delete('payments', payment_id)
            self.load_payments()

    def export_to_excel(self):
        data = []
        for item in self.tree.get_children():
            values = self.tree.item(item)['values']
            data.append([str(v) for v in values])
        headers = [self.tree.heading(col)['text'] for col in self.tree['columns']]
        filename = f"payments_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        excel_exporter.export_report(data, filename, "Payments List", headers)
        messagebox.showinfo("Export", f"Exported to {filename}")


class PaymentDialog:
    def __init__(self, parent, current_user, payment_id=None, on_save=None):
        self.parent = parent
        self.current_user = current_user
        self.payment_id = payment_id
        self.on_save = on_save

        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Payment" + (" - Edit" if payment_id else " - Add"))
        self.dialog.geometry("500x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()

        self.vessel_map = {}
        self.voyage_map = {}
        self.charter_map = {}
        self.vendor_map = {}
        self.cost_type_map = {}

        self.setup_ui()
        if payment_id:
            self.load_data()

    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill='both', expand=True)

        row = 0
        # Transaction Type
        tk.Label(main_frame, text="Transaction Type:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.type_var = tk.StringVar()
        self.type_combo = ttk.Combobox(main_frame, textvariable=self.type_var, values=['income', 'expense'], state='readonly', width=27)
        self.type_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.type_combo.bind('<<ComboboxSelected>>', self.on_type_change)
        row += 1

        # Cost Type
        tk.Label(main_frame, text="Cost Type:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.cost_type_combo = ttk.Combobox(main_frame, state='readonly', width=27)
        self.cost_type_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Vendor (only for expenses)
        self.vendor_label = tk.Label(main_frame, text="Vendor:")
        self.vendor_label.grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.vendor_combo = ttk.Combobox(main_frame, state='readonly', width=27)
        self.vendor_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.load_vendors()
        self.vendor_label.grid_remove()
        self.vendor_combo.grid_remove()
        row += 1

        # Vessel
        tk.Label(main_frame, text="Vessel:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.vessel_combo = ttk.Combobox(main_frame, state='readonly', width=27)
        self.vessel_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.load_vessels()
        self.vessel_combo.bind('<<ComboboxSelected>>', self.on_vessel_selected)
        row += 1

        # Voyage
        tk.Label(main_frame, text="Voyage:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.voyage_combo = ttk.Combobox(main_frame, state='readonly', width=27)
        self.voyage_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Charter Party
        tk.Label(main_frame, text="Charter Party:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.charter_combo = ttk.Combobox(main_frame, state='readonly', width=27)
        self.charter_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        self.load_charters()
        row += 1

        # Amount (RUB only for now)
        tk.Label(main_frame, text="Amount (RUB):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.amount_entry = tk.Entry(main_frame, width=30)
        self.amount_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Invoice Date
        tk.Label(main_frame, text="Invoice Date (YYYY-MM-DD):").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.invoice_date_entry = tk.Entry(main_frame, width=30)
        self.invoice_date_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Due Date
        tk.Label(main_frame, text="Due Date:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.due_date_entry = tk.Entry(main_frame, width=30)
        self.due_date_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Payment Date
        tk.Label(main_frame, text="Payment Date:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.payment_date_entry = tk.Entry(main_frame, width=30)
        self.payment_date_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Status
        tk.Label(main_frame, text="Status:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.status_combo = ttk.Combobox(main_frame, values=['draft', 'pending', 'partial', 'paid', 'overdue', 'cancelled'], state='readonly', width=27)
        self.status_combo.set('draft')
        self.status_combo.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Document Number
        tk.Label(main_frame, text="Document Number:").grid(row=row, column=0, sticky='e', padx=5, pady=5)
        self.doc_entry = tk.Entry(main_frame, width=30)
        self.doc_entry.grid(row=row, column=1, sticky='w', padx=5, pady=5)
        row += 1

        # Description
        tk.Label(main_frame, text="Description:").grid(row=row, column=0, sticky='ne', padx=5, pady=5)
        self.desc_text = tk.Text(main_frame, width=40, height=4)
        self.desc_text.grid(row=row, column=1, sticky='w', padx=5, pady=5)
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

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def load_vessels(self):
        vessels = db.fetch_all("SELECT id, name FROM vessels WHERE is_active = 1 ORDER BY name")
        vessel_list = [f"{v['id']} - {v['name']}" for v in vessels]
        self.vessel_combo['values'] = vessel_list
        self.vessel_map = {f"{v['id']} - {v['name']}": v['id'] for v in vessels}

    def load_vendors(self):
        vendors = db.fetch_all("SELECT id, legal_name FROM vendors ORDER BY legal_name")
        vendor_list = [f"{v['id']} - {v['legal_name']}" for v in vendors]
        self.vendor_combo['values'] = vendor_list
        self.vendor_map = {f"{v['id']} - {v['legal_name']}": v['id'] for v in vendors}

    def load_charters(self):
        charters = db.fetch_all("SELECT id, charterer_name FROM charter_parties WHERE is_active = 1 ORDER BY charter_date DESC")
        charter_list = [f"{c['id']} - {c['charterer_name']}" for c in charters]
        self.charter_combo['values'] = charter_list
        self.charter_map = {f"{c['id']} - {c['charterer_name']}": c['id'] for c in charters}

    def on_vessel_selected(self, event=None):
        vessel_sel = self.vessel_combo.get()
        if vessel_sel and vessel_sel in self.vessel_map:
            vessel_id = self.vessel_map[vessel_sel]
            voyages = db.fetch_all("SELECT id, voyage_number FROM voyages WHERE vessel_id = ? ORDER BY start_date DESC", (vessel_id,))
            voyage_list = [f"{v['id']} - {v['voyage_number']}" for v in voyages]
            self.voyage_combo['values'] = voyage_list
            self.voyage_map = {f"{v['id']} - {v['voyage_number']}": v['id'] for v in voyages}
        else:
            self.voyage_combo['values'] = []
            self.voyage_map = {}

    def on_type_change(self, event=None):
        ttype = self.type_var.get()
        if ttype == 'expense':
            self.vendor_label.grid()
            self.vendor_combo.grid()
        else:
            self.vendor_label.grid_remove()
            self.vendor_combo.grid_remove()

        # Update cost type dropdown
        cost_types = db.fetch_all("SELECT id, name FROM cost_types WHERE category = ? ORDER BY name", (ttype,))
        cost_list = [f"{c['id']} - {c['name']}" for c in cost_types]
        self.cost_type_combo['values'] = cost_list
        self.cost_type_map = {f"{c['id']} - {c['name']}": c['id'] for c in cost_types}

    def load_data(self):
        payment = db.fetch_one("SELECT * FROM payments WHERE id = ?", (self.payment_id,))
        if not payment:
            return
        # Type
        self.type_var.set(payment['transaction_type'])
        self.on_type_change()
        # Cost type
        cost = db.fetch_one("SELECT id, name FROM cost_types WHERE id = ?", (payment['cost_type_id'],))
        if cost:
            self.cost_type_combo.set(f"{cost['id']} - {cost['name']}")
        # Vendor
        if payment['vendor_id']:
            vendor = db.fetch_one("SELECT id, legal_name FROM vendors WHERE id = ?", (payment['vendor_id'],))
            if vendor:
                self.vendor_combo.set(f"{vendor['id']} - {vendor['legal_name']}")
        # Vessel
        if payment['vessel_id']:
            vessel = db.fetch_one("SELECT id, name FROM vessels WHERE id = ?", (payment['vessel_id'],))
            if vessel:
                self.vessel_combo.set(f"{vessel['id']} - {vessel['name']}")
                self.on_vessel_selected()
        # Voyage
        if payment['voyage_id']:
            voyage = db.fetch_one("SELECT id, voyage_number FROM voyages WHERE id = ?", (payment['voyage_id'],))
            if voyage:
                self.voyage_combo.set(f"{voyage['id']} - {voyage['voyage_number']}")
        # Charter
        if payment['charter_party_id']:
            charter = db.fetch_one("SELECT id, charterer_name FROM charter_parties WHERE id = ?", (payment['charter_party_id'],))
            if charter:
                self.charter_combo.set(f"{charter['id']} - {charter['charterer_name']}")
        # Amount
        self.amount_entry.insert(0, str(payment['rub_amount']))
        # Dates
        self.invoice_date_entry.insert(0, payment['invoice_date'] or '')
        self.due_date_entry.insert(0, payment['due_date'] or '')
        self.payment_date_entry.insert(0, payment['payment_date'] or '')
        # Status
        self.status_combo.set(payment['status'])
        # Document
        self.doc_entry.insert(0, payment['document_number'] or '')
        # Description/Notes
        self.desc_text.insert('1.0', payment['description'] or '')
        self.notes_text.insert('1.0', payment['notes'] or '')

    def save(self):
        try:
            ttype = self.type_var.get()
            if not ttype:
                messagebox.showerror("Error", "Transaction type is required")
                return

            cost_sel = self.cost_type_combo.get()
            if not cost_sel:
                messagebox.showerror("Error", "Cost type is required")
                return
            cost_type_id = self.cost_type_map.get(cost_sel)
            if not cost_type_id:
                messagebox.showerror("Error", "Invalid cost type selection")
                return

            amount_str = self.amount_entry.get().strip()
            if not amount_str:
                messagebox.showerror("Error", "Amount is required")
                return
            try:
                rub_amount = float(amount_str)
            except ValueError:
                messagebox.showerror("Error", "Amount must be number")
                return

            vessel_id = self.vessel_map.get(self.vessel_combo.get())
            voyage_id = self.voyage_map.get(self.voyage_combo.get())
            charter_id = self.charter_map.get(self.charter_combo.get())
            vendor_id = None
            if ttype == 'expense':
                vendor_id = self.vendor_map.get(self.vendor_combo.get())

            data = {
                'vessel_id': vessel_id,
                'voyage_id': voyage_id,
                'charter_party_id': charter_id,
                'vendor_id': vendor_id,
                'cost_type_id': cost_type_id,
                'transaction_type': ttype,   # THIS LINE IS CRITICAL
                'original_currency': 'RUB',
                'original_amount': rub_amount,
                'rub_amount': rub_amount,
                'exchange_rate_used': 1.0,
                'exchange_rate_date': datetime.now().date().isoformat(),
                'invoice_date': self.invoice_date_entry.get().strip() or None,
                'due_date': self.due_date_entry.get().strip() or None,
                'payment_date': self.payment_date_entry.get().strip() or None,
                'status': self.status_combo.get(),
                'document_number': self.doc_entry.get().strip() or None,
                'description': self.desc_text.get('1.0', tk.END).strip() or None,
                'notes': self.notes_text.get('1.0', tk.END).strip() or None,
                'created_by': self.current_user['username']
            }

            if self.payment_id:
                db.update('payments', self.payment_id, data)
                messagebox.showinfo("Success", "Payment updated")
            else:
                db.insert('payments', data)
                messagebox.showinfo("Success", "Payment added")

            self.dialog.destroy()
            if self.on_save:
                self.on_save()
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to save payment: {str(e)}")