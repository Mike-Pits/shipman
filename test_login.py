#!/usr/bin/env python3
import sys
import os

sys.path.insert(0, '/home/mike-pi/Documents/coding/projects/shipman')

print("Starting ShipMan test...")

from database.db_manager import db
print("✓ Database loaded")

from modules.login import LoginWindow
print("✓ Login module loaded")

import tkinter as tk
print("✓ Tkinter loaded")

root = tk.Tk()
root.withdraw()
print("✓ Root window created")

def on_success(user):
    print(f"✓ User logged in: {user['username']}")
    root.quit()

login = LoginWindow(root, on_success)
print("✓ Login window created - you should see it now")
print("If no window appears, check DISPLAY variable")

root.mainloop()
print("Mainloop ended")