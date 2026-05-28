#!/usr/bin/env python3
"""
ShipMan - Small Fleet Operations Manager
Main entry point
"""

import sys
import os
import tkinter as tk

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    print("=" * 50)
    print("ShipMan Starting...")
    print("=" * 50)
    
    # Create backups directory
    os.makedirs("backups", exist_ok=True)
    
    # Import database
    try:
        from database.db_manager import db
        print("✓ Database loaded")
    except Exception as e:
        print(f"✗ Database error: {e}")
        return
    
    # Import modules
    try:
        from modules.login import LoginWindow
        print("✓ Login module loaded")
        from modules.main_window import MainWindow
        print("✓ MainWindow module loaded")
    except Exception as e:
        print(f"✗ Module import error: {e}")
        return
    
    # Create root window
    root = tk.Tk()
    root.withdraw()
    
    # Force Tkinter to initialize properly
    root.update_idletasks()
    
    def on_login_success(user):
        print(f"✓ Login successful: {user['username']}")
        root.quit()  # Exit the current mainloop
        root.destroy()  # Destroy the hidden root
        
        # Start main application in a new Tk instance
        print("Opening main application...")
        main_window = MainWindow(user)
        main_window.run()
    
    # Show login window
    print("\nShowing login window...")
    login = LoginWindow(root, on_login_success)
    
    # Force the login window to appear
    login.window.update_idletasks()
    login.window.deiconify()
    login.window.lift()
    login.window.focus_force()
    
    print("Login window should be visible now.")
    print("Enter credentials and click Login, or close the window to exit.")
    
    root.mainloop()
    print("Application finished")

if __name__ == "__main__":
    main()