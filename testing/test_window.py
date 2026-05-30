import tkinter as tk

print("Creating window...")
root = tk.Tk()
root.title("Test Window")
root.geometry("400x300")

label = tk.Label(root, text="If you see this, Tkinter works!", font=('Arial', 14))
label.pack(expand=True)

button = tk.Button(root, text="Close", command=root.destroy)
button.pack(pady=20)

print("Window should appear now. Close it to continue.")
root.mainloop()
print("Window closed.")
