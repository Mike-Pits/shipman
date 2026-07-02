import tkinter as tk
root = tk.Tk()
root.title("Test")
root.geometry("300x200")
label = tk.Label(root, text="Click the button")
label.pack()
def on_click():
    label.config(text="Clicked!")
btn = tk.Button(root, text="Click me", command=on_click)
btn.pack()
root.mainloop()