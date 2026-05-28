import sys
import os
import tkinter as tk

sys.path.insert(0, '/home/mike-pi/Documents/coding/projects/shipman')

print("Testing login module directly...")

from modules.login import LoginWindow

def on_success(user):
    print(f"Login success: {user}")
    root.quit()

root = tk.Tk()
root.title("Direct Login Test")
root.geometry("800x600")

# Put a label to show it's working
label = tk.Label(root, text="ShipMan Login Test\nIf you see this, Tkinter works.\nLogin window will appear in 2 seconds...", 
                 font=('Arial', 14))
label.pack(expand=True)

root.update()

# Show login after 2 seconds
def show_login():
    print("Creating login window...")
    login = LoginWindow(root, on_success)
    print("Login window created")

root.after(2000, show_login)
root.mainloop()
