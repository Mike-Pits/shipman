import tkinter as tk
from tkinter import ttk, messagebox
from modules.vessels import VesselManager
from modules.daily_reports import DailyReportManager
from utils.language_manager import lang
from database.db_manager import db

class MainWindow:
    """Main application window with tabs"""
    
    def __init__(self, current_user):
        self.current_user = current_user
        self.root = tk.Tk()
        self.root.title(lang.get('app_title'))
        self.root.geometry("1200x700")
        
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
        """Create toolbar with language controls"""
        toolbar = ttk.Frame(self.root)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        # Language toggle
        ttk.Label(toolbar, text="Language:").pack(side='left', padx=(10, 5))
        self.lang_var = tk.StringVar(value="EN" if lang.current_lang == 'en' else "RU")
        lang_combo = ttk.Combobox(toolbar, textvariable=self.lang_var,
                                   values=["EN", "RU"], width=5, state='readonly')
        lang_combo.pack(side='left', padx=5)
        lang_combo.bind('<<ComboboxSelected>>', self.change_language)
        
        # User info (right side)
        user_label = ttk.Label(toolbar, text=f"User: {self.current_user['username']} ({self.current_user['role']})")
        user_label.pack(side='right', padx=10)
    
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
        
        # Tab 4: Charter Parties (placeholder)
        charter_frame = ttk.Frame(self.notebook)
        self.notebook.add(charter_frame, text=lang.get('charter_parties_title'))
        tk.Label(charter_frame, text="Charter Parties Module - Coming Soon", 
                 font=('Arial', 14)).pack(expand=True)
        
        # Tab 5: Payments (placeholder)
        payments_frame = ttk.Frame(self.notebook)
        self.notebook.add(payments_frame, text=lang.get('payments_title'))
        tk.Label(payments_frame, text="Payments Module - Coming Soon", 
                 font=('Arial', 14)).pack(expand=True)
        
        # Tab 6: Reports (placeholder)
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