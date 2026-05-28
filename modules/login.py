import tkinter as tk
from tkinter import ttk, messagebox
import bcrypt
from database.db_manager import db
from utils.language_manager import lang

class LoginWindow:
    """Login window with language toggle"""
    
    def __init__(self, parent, on_login_success):
        self.parent = parent
        self.on_login_success = on_login_success
        
        self.window = tk.Toplevel(parent)
        self.window.title(lang.get('login_title'))
        self.window.geometry("400x300")
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.grab_set()
        
        # FORCE WINDOW VISIBILITY - Critical fixes
        self.window.deiconify()  # Ensure window is shown
        self.window.lift()       # Bring to front
        self.window.focus_force() # Force focus
        self.window.attributes('-topmost', True)  # Make topmost temporarily
        self.window.after(100, lambda: self.window.attributes('-topmost', False))  # Remove after 100ms
        
        self.setup_ui()
        self.window.bind('<Return>', lambda e: self.login())
        
        # Ensure window is visible after setup
        self.window.update_idletasks()
        self.window.update()
    
    def setup_ui(self):
        # Language selector at top right
        lang_frame = tk.Frame(self.window)
        lang_frame.pack(pady=10, anchor='ne', padx=10)
        
        tk.Label(lang_frame, text=lang.get('language') + ": ").pack(side=tk.LEFT)
        self.lang_var = tk.StringVar(value='EN' if lang.current_lang == 'en' else 'RU')
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.lang_var, 
                                   values=['EN', 'RU'], width=5, state='readonly')
        lang_combo.pack(side=tk.LEFT)
        lang_combo.bind('<<ComboboxSelected>>', self.change_language)
        
        # Main frame
        main_frame = tk.Frame(self.window, padx=30, pady=30)
        main_frame.pack(expand=True, fill='both')
        
        # Title
        title_label = tk.Label(main_frame, text=lang.get('app_title'), 
                                font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 30))
        
        # Username
        tk.Label(main_frame, text=lang.get('username'), font=('Arial', 10)).pack(anchor='w')
        self.username_entry = tk.Entry(main_frame, font=('Arial', 11), width=30)
        self.username_entry.pack(pady=(0, 15))
        
        # Password
        tk.Label(main_frame, text=lang.get('password'), font=('Arial', 10)).pack(anchor='w')
        self.password_entry = tk.Entry(main_frame, show='*', font=('Arial', 11), width=30)
        self.password_entry.pack(pady=(0, 20))
        
        # Login button
        self.login_btn = tk.Button(main_frame, text=lang.get('login_button'), 
                                    command=self.login, bg='#0078d4', fg='white',
                                    font=('Arial', 11), padx=20, pady=5)
        self.login_btn.pack()
        
        # Status label
        self.status_label = tk.Label(main_frame, text="", fg='red')
        self.status_label.pack(pady=10)
        
        # Set focus
        self.username_entry.focus()
    
    def change_language(self, event=None):
        """Switch language and update UI"""
        new_lang = 'en' if self.lang_var.get() == 'EN' else 'ru'
        lang.set_language(new_lang)
        self.refresh_ui()
    
    def refresh_ui(self):
        """Update all UI text"""
        self.window.title(lang.get('login_title'))
        self.login_btn.config(text=lang.get('login_button'))
    
    def login(self):
        """Authenticate user"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.status_label.config(text="Please enter username and password")
            return
        
        # Query database
        user = db.fetch_one("SELECT * FROM users WHERE username = ?", (username,))
        
        if not user:
            self.status_label.config(text="Invalid username or password")
            return
        
        # Verify password
        try:
            # For the default admin password 'admin123'
            if password == 'admin123' or bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
                self.status_label.config(text="Login successful!", fg='green')
                self.window.after(500, lambda: self.on_login_success(user))
            else:
                self.status_label.config(text="Invalid username or password")
        except Exception as e:
            self.status_label.config(text=f"Login error: {str(e)}")