import tkinter as tk

from app import App

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1320x820")
    root.minsize(1150, 700)
    App(root)
    root.mainloop()