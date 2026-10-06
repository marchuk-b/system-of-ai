import tkinter as tk

from app import App

if __name__ == "__main__":
    root = tk.Tk()
    root.state("zoomed")
    root.resizable(False, False)
    App(root)
    root.mainloop()