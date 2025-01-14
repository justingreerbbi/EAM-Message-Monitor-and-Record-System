import tkinter as tk
from tkinter import messagebox
from radio import Radio

class RadioControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Radio Control")

        self.is_radio_on = False

        self.start_button = tk.Button(root, text="Start Radio", command=self.start_radio)
        self.start_button.pack(pady=10)

        self.stop_button = tk.Button(root, text="Stop Radio", command=self.stop_radio)
        self.stop_button.pack(pady=10)

        self.radio = Radio()

    def start_radio(self):
        if not self.is_radio_on:
            self.is_radio_on = True
            self.radio.play()
        else:
            messagebox.showwarning("Radio Control", "Radio is already running.")

    def stop_radio(self):
        if self.is_radio_on:
            self.is_radio_on = False
            self.radio.stop()
        else:
            messagebox.showwarning("Radio Control", "Radio is not running.")

if __name__ == "__main__":
    root = tk.Tk()
    app = RadioControlApp(root)
    root.mainloop()