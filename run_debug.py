#!/usr/bin/env python3
import sys
import os
import tkinter as tk

sys.path.insert(0, '/home/mike-pi/Documents/coding/projects/shipman')

print("Step 1: Importing modules...")
from database.db_manager import db
print("  ✓ Database")

from modules.login import LoginWindow
print("  ✓ LoginWindow")

from modules.main_window import MainWindow
print("  ✓ MainWindow")

print("\nStep 2: Creating root window...")
root = tk.Tk()
root.withdraw()
print("  ✓ Root created")

print("\nStep 3: Setting up login...")
def on_login(user):
    print(f"  ✓ Login success: {user['username']}")
    root.destroy()
    print("\nStep 5: Starting main window...")
    mw = MainWindow(user)
    mw.run()

print("\nStep 4: Showing login window...")
login = LoginWindow(root, on_login)
print("  ✓ Login window should be visible now")

print("\nEntering main loop...")
root.mainloop()
print("Application finished")