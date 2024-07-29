import random
import threading
import time
import tkinter as tk
import warnings

import ttkbootstrap as ttk
from ttkbootstrap.constants import INFO, PRIMARY, SUCCESS

warnings.filterwarnings("ignore", message="invalid escape sequence '\\$'", category=SyntaxWarning)


class MeasurementApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Measurement Interface")

        # Create buttons
        self.find_pump_button = ttk.Button(root, text="Find Pump", command=self.find_pump, bootstyle=SUCCESS)
        self.find_pump_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")

        self.find_spec_button = ttk.Button(
            root, text="Find Spectrophotometer", command=self.find_spectrophotometer, bootstyle=SUCCESS
        )
        self.find_spec_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        self.start_meas_button = ttk.Button(
            root, text="Start Measurement", command=self.start_measurement, bootstyle=PRIMARY
        )
        self.start_meas_button.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

        # Create input field for measurement interval
        self.interval_label = ttk.Label(root, text="Measurement Interval (s):")
        self.interval_label.grid(row=1, column=0, padx=10, pady=10, sticky="e")

        self.interval_entry = ttk.Entry(root)
        self.interval_entry.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Create info area displaying table with measurements
        self.tree = ttk.Treeview(root, columns=("Measurement", "Value"), show="headings", bootstyle=INFO)
        self.tree.heading("Measurement", text="Measurement")
        self.tree.heading("Value", text="Value")
        self.tree.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")

        # Add vertical scrollbar to the treeview
        self.scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=self.tree.yview, bootstyle=INFO)
        self.tree.configure(yscroll=self.scrollbar.set)
        self.scrollbar.grid(row=2, column=3, sticky="ns")

        # Make the grid layout responsive
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.columnconfigure(2, weight=1)
        root.columnconfigure(3, weight=0)
        root.rowconfigure(2, weight=1)

        self.measurement_running = False

    def find_pump(self):
        print("Finding pump...")

    def find_spectrophotometer(self):
        print("Finding spectrophotometer...")

    def start_measurement(self):
        if self.measurement_running:
            return
        try:
            interval = float(self.interval_entry.get())
        except ValueError:
            print("Please enter a valid number for the interval.")
            return

        self.measurement_running = True
        threading.Thread(target=self.measurement_thread, args=(interval,), daemon=True).start()

    def measurement_thread(self, interval):
        while self.measurement_running:
            self.add_measurement(random.random())
            time.sleep(interval)

    def add_measurement(self, value):
        self.tree.insert("", "end", values=("Measurement", value))
        self.tree.yview_moveto(1)  # Scroll to the end to show the most recent measurement
        print(f"Measurement taken: {value}")

    def stop_measurement(self):
        self.measurement_running = False
        self.root.quit()  # Ensure the application exits properly


def main():
    root = ttk.Window(themename="superhero")
    app = MeasurementApp(root)
    root.protocol("WM_DELETE_WINDOW", app.stop_measurement)  # Handle window close event
    root.mainloop()


if __name__ == "__main__":
    main()
