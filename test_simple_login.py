import tkinter as tk
from tkinter import ttk, messagebox

class SimpleLoginWindow:
    def __init__(self, parent, on_success):
        self.parent = parent
        self.on_success = on_success
        
        self.window = tk.Toplevel(parent)
        self.window.title("ShipMan Login")
        self.window.geometry("400x300")
        self.window.transient(parent)
        self.window.grab_set()
        
        # Make it visible
        self.window.lift()
        self.window.focus_force()
        
        # Main frame
        main_frame = tk.Frame(self.window, padx=30, pady=30)
        main_frame.pack(expand=True, fill='both')
        
        # Title
        title_label = tk.Label(main_frame, text="ShipMan", font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 30))
        
        # Username
        tk.Label(main_frame, text="Username").pack(anchor='w')
        self.username_entry = tk.Entry(main_frame, font=('Arial', 11), width=30)
        self.username_entry.pack(pady=(0, 15))
        
        # Password
        tk.Label(main_frame, text="Password").pack(anchor='w')
        self.password_entry = tk.Entry(main_frame, show='*', font=('Arial', 11), width=30)
        self.password_entry.pack(pady=(0, 20))
        
        # Login button
        self.login_btn = tk.Button(main_frame, text="Login", command=self.login,
                                    bg='#0078d4', fg='white', padx=20, pady=5)
        self.login_btn.pack()
        
        # Status
        self.status_label = tk.Label(main_frame, text="", fg='red')
        self.status_label.pack(pady=10)
        
        self.username_entry.focus()
    
    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        # Hardcoded for test
        if username == "admin" and password == "admin123":
            self.status_label.config(text="Login successful!", fg='green')
            self.window.after(1000, lambda: self.on_success({"username": username}))
        else:
            self.status_label.config(text="Invalid credentials", fg='red')

# Test
root = tk.Tk()
root.withdraw()

def on_success(user):
    print(f"Login successful: {user}")
    root.quit()

login = SimpleLoginWindow(root, on_success)
root.mainloop()
print("Test complete")
