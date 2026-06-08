import tkinter as tk
from tkinter import ttk, messagebox
from modules.vessels import VesselManager
from modules.daily_reports import DailyReportManager
from modules.charter_parties import CharterPartyManager
from modules.voyages import VoyageManager
from modules.payments import PaymentManager 
from utils.language_manager import lang
from database.db_manager import db

class MainWindow:
    """Main application window with tabs"""
    
    def __init__(self, current_user):
        self.current_user = current_user
        self.root = tk.Tk()
        self.root.title(lang.get('app_title'))
        self.root.geometry("1200x700")
        
        # For exchange rate
        self.current_rate = 92.50
        
        # Make sure window is visible
        self.root.lift()
        self.root.focus_force()
        
        self.setup_menu()
        self.setup_toolbar()
        self.setup_tabs()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def setup_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Backup Database", command=self.backup_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def setup_toolbar(self):
        """Create toolbar with currency, exchange rate, and language controls"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        # Currency Selector
        ttk.Label(toolbar, text="Currency:").pack(side='left', padx=(10, 5))
        self.currency_var = tk.StringVar(value="RUB")
        currency_combo = ttk.Combobox(toolbar, textvariable=self.currency_var,
                                       values=["RUB", "USD"], width=8, state='readonly')
        currency_combo.pack(side='left', padx=5)
        currency_combo.bind('<<ComboboxSelected>>', self.change_currency)
        
        # Exchange Rate Display & Update Button
        self.rate_label = ttk.Label(toolbar, text="USD/RUB: --")
        self.rate_label.pack(side='left', padx=10)
        
        self.update_rate_btn = ttk.Button(toolbar, text="Update Rate", 
                                           command=self.update_exchange_rate)
        self.update_rate_btn.pack(side='left', padx=5)
        
        # Language Toggle
        ttk.Label(toolbar, text="Language:").pack(side='left', padx=(20, 5))
        self.lang_var = tk.StringVar(value="EN" if lang.current_lang == 'en' else "RU")
        lang_combo = ttk.Combobox(toolbar, textvariable=self.lang_var,
                                   values=["EN", "RU"], width=5, state='readonly')
        lang_combo.pack(side='left', padx=5)
        lang_combo.bind('<<ComboboxSelected>>', self.change_language)
        
        # User info (right side)
        user_label = ttk.Label(toolbar, text=f"User: {self.current_user['username']} ({self.current_user['role']})")
        user_label.pack(side='right', padx=10)
        
        # Load current exchange rate
        self.load_exchange_rate()
    
    def load_exchange_rate(self):
        """Load the latest USD/RUB rate from database"""
        try:
            rate_row = db.fetch_one("SELECT usd_to_rub_rate FROM exchange_rates ORDER BY rate_date DESC LIMIT 1")
            if rate_row:
                self.current_rate = rate_row['usd_to_rub_rate']
                self.rate_label.config(text=f"USD/RUB: {self.current_rate:.2f}")
            else:
                self.current_rate = 92.50
                self.rate_label.config(text=f"USD/RUB: {self.current_rate:.2f} (default)")
        except Exception as e:
            print(f"Error loading exchange rate: {e}")
            self.current_rate = 92.50
            self.rate_label.config(text="USD/RUB: --")
    
    def change_currency(self, event=None):
        """Handle currency display toggle"""
        selected = self.currency_var.get()
        print(f"Currency changed to: {selected}")
        # For now just show a message - full implementation later
        messagebox.showinfo("Currency", f"Display currency set to {selected}\n(Full implementation coming with payment modules)")
    
    def update_exchange_rate(self):
        """Open dialog to manually update USD/RUB rate"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Update Exchange Rate")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()

        tk.Label(dialog, text="Current USD to RUB rate:", font=('Arial', 10)).pack(pady=10)
        current_rate_label = tk.Label(dialog, text=f"{self.current_rate:.2f}", font=('Arial', 12, 'bold'))
        current_rate_label.pack(pady=5)

        tk.Label(dialog, text="New rate (RUB per 1 USD):").pack(pady=10)
        rate_entry = tk.Entry(dialog, width=15)
        rate_entry.pack(pady=5)
        rate_entry.focus()

        def save_rate():
            try:
                new_rate = float(rate_entry.get())
                if new_rate <= 0:
                    raise ValueError
                from datetime import date
                today = date.today().isoformat()
                db.execute_query("""
                    INSERT OR REPLACE INTO exchange_rates (rate_date, usd_to_rub_rate, source, notes, created_by)
                    VALUES (?, ?, ?, ?, ?)
                """, (today, new_rate, 'manual', 'User update', self.current_user['username']))
                self.current_rate = new_rate
                self.rate_label.config(text=f"USD/RUB: {new_rate:.2f}")
                dialog.destroy()
                messagebox.showinfo("Success", f"Exchange rate updated to {new_rate:.2f} RUB/USD")
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid positive number")

        rate_entry.bind('<Return>', lambda event: save_rate())
        tk.Button(dialog, text="Save", command=save_rate, bg='#0078d4', fg='white').pack(pady=10)
 
    def setup_tabs(self):
        """Create tabbed interface"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)

        # Tab 1: Dashboard (placeholder)
        dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(dashboard_frame, text="Dashboard")
        tk.Label(dashboard_frame, text="ShipMan Dashboard\n\nWelcome!", 
                font=('Arial', 14)).pack(expand=True)

        # Tab 2: Vessels
        try:
            self.vessel_manager = VesselManager(self.notebook, self.current_user)
            self.notebook.add(self.vessel_manager.frame, text=lang.get('vessels_title'))
        except Exception as e:
            print(f"Error loading vessels module: {e}")
            error_frame = ttk.Frame(self.notebook)
            self.notebook.add(error_frame, text="Vessels")
            tk.Label(error_frame, text=f"Error loading vessels: {e}", fg='red').pack(expand=True)

        # Tab 3: Daily Reports
        try:
            self.daily_reports = DailyReportManager(self.notebook, self.current_user)
            self.notebook.add(self.daily_reports.frame, text=lang.get('daily_reports_title'))
        except Exception as e:
            print(f"Error loading daily reports module: {e}")
            error_frame = ttk.Frame(self.notebook)
            self.notebook.add(error_frame, text="Daily Reports")
            tk.Label(error_frame, text=f"Error loading daily reports: {e}", fg='red').pack(expand=True)

        # Tab 4: Charter Parties
        try:
            from modules.charter_parties import CharterPartyManager
            self.charter_manager = CharterPartyManager(self.notebook, self.current_user)
            self.notebook.add(self.charter_manager.frame, text=lang.get('charter_parties_title'))
        except Exception as e:
            print(f"Error loading charter parties module: {e}")
            error_frame = ttk.Frame(self.notebook)
            self.notebook.add(error_frame, text="Charter Parties")
            tk.Label(error_frame, text=f"Error loading charter parties: {e}", fg='red').pack(expand=True)

        # Tab 5: Voyages
        try:
            from modules.voyages import VoyageManager
            self.voyage_manager = VoyageManager(self.notebook, self.current_user)
            self.notebook.add(self.voyage_manager.frame, text=lang.get('voyages_title'))
        except Exception as e:
            print(f"Error loading voyages module: {e}")
            error_frame = ttk.Frame(self.notebook)
            self.notebook.add(error_frame, text="Voyages")
            tk.Label(error_frame, text=f"Error loading voyages: {e}", fg='red').pack(expand=True)

        # Tab 6: Payments (NEW - replacing placeholder)
        try:
            from modules.payments import PaymentManager
            self.payment_manager = PaymentManager(self.notebook, self.current_user)
            self.notebook.add(self.payment_manager.frame, text=lang.get('payments_title'))
        except Exception as e:
            print(f"Error loading payments module: {e}")
            error_frame = ttk.Frame(self.notebook)
            self.notebook.add(error_frame, text="Payments")
            tk.Label(error_frame, text=f"Error loading payments: {e}", fg='red').pack(expand=True)

        # Tab 7: Reports (placeholder)
        reports_frame = ttk.Frame(self.notebook)
        self.notebook.add(reports_frame, text=lang.get('reports_title'))
        tk.Label(reports_frame, text="Reports Module - Coming Soon", 
                font=('Arial', 14)).pack(expand=True)
    
    def change_language(self, event=None):
        """Switch application language"""
        new_lang = 'en' if self.lang_var.get() == 'EN' else 'ru'
        lang.set_language(new_lang)
        
        # Update tab titles
        self.notebook.tab(0, text="Dashboard")
        self.notebook.tab(1, text=lang.get('vessels_title'))
        self.notebook.tab(2, text=lang.get('daily_reports_title'))
        self.notebook.tab(3, text=lang.get('charter_parties_title'))
        self.notebook.tab(4, text=lang.get('payments_title'))
        self.notebook.tab(5, text=lang.get('reports_title'))
        
        self.root.title(lang.get('app_title'))
    
    def backup_database(self):
        """Create database backup"""
        try:
            backup_path = db.backup()
            messagebox.showinfo("Backup", f"Database backed up to:\n{backup_path}")
        except Exception as e:
            messagebox.showerror("Backup Error", f"Failed to backup: {e}")
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
            "ShipMan - Fleet Management System\n"
            "Version 1.0\n\n"
            "For Small Shipping Company\n"
            "Bilingual: English / Russian")
    
    def on_close(self):
        """Handle application shutdown"""
        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.root.quit()
            self.root.destroy()
    
    def run(self):
        """Start the main loop"""
        print("Main window running...")
        self.root.mainloop()