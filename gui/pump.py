from tkinter import DoubleVar, StringVar, simpledialog

import ttkbootstrap as ttk
from bioexperiment_suite.interfaces import Pump
from ttkbootstrap.constants import DANGER


class PumpWidget(ttk.Frame):
    instance_count = 0  # Class variable to keep track of the number of instances

    def __init__(self, parent: ttk.Window, pump: Pump):
        super().__init__(parent)
        PumpWidget.instance_count += 1

        self.pump = pump
        self.title = StringVar(value=f"Pump {PumpWidget.instance_count}")
        self.flow_rate = DoubleVar(value=3.0)
        self.volume = DoubleVar(value=0.0)
        self.direction = StringVar(value="right")

        self.on_flow_rate_change()
        self.flow_rate.trace_add("write", self.on_flow_rate_change)

        # Create widgets
        self.create_widgets()
        self.grid_widgets()

    def create_widgets(self):
        self.title_label = ttk.Label(self, textvariable=self.title, font=("Helvetica", 16, "bold"))

        self.rename_button = ttk.Button(self, text="Rename", command=self.rename_pump)

        self.flow_rate_label = ttk.Label(self, text="Flow rate (mL/min):")
        self.flow_rate_entry = ttk.Entry(self, textvariable=self.flow_rate)
        self.set_flow_rate_button = ttk.Button(self, text="Set", command=self.set_flow_rate)

        self.port_name_label = ttk.Label(self, text="Port:")
        self.port_name_info = ttk.Label(self, textvariable=self.pump.port)

        self.baudrate_label = ttk.Label(self, text="Baudrate:")
        self.baudrate_info = ttk.Label(self, textvariable=self.pump.baudrate)

        self.rotate_right_button = ttk.Button(
            self, text="Rotate right", command=lambda: self.pump.start_continuous_rotation(direction="right")
        )
        self.stop_button = ttk.Button(self, text="Stop", bootstyle=DANGER, command=self.pump.stop_continuous_rotation)
        self.rotate_left_button = ttk.Button(
            self, text="Rotate Left", command=lambda: self.pump.start_continuous_rotation(direction="left")
        )

        self.volume_label = ttk.Label(self, text="Volume (mL):")
        self.volume_entry = ttk.Entry(self, textvariable=self.volume)

        self.right_radio = ttk.Radiobutton(self, text="Right", variable=self.direction, value="right")
        self.left_radio = ttk.Radiobutton(self, text="Left", variable=self.direction, value="left")

        self.pump_button = ttk.Button(
            self,
            text="Pump",
            command=lambda: self.pump.pour_in_volume(self.volume.get(), direction=self.direction.get()),
        )

    def grid_widgets(self):
        self.title_label.grid(row=0, column=0, columnspan=3, padx=5, pady=5)
        self.rename_button.grid(row=0, column=3, padx=5, pady=5)

        self.flow_rate_label.grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.flow_rate_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.port_name_label.grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.port_name_info.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        self.baudrate_label.grid(row=3, column=0, padx=5, pady=5, sticky="e")
        self.baudrate_info.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        self.rotate_right_button.grid(row=4, column=0, padx=5, pady=5)
        self.stop_button.grid(row=4, column=1, padx=5, pady=5)
        self.rotate_left_button.grid(row=4, column=2, padx=5, pady=5)

        self.volume_label.grid(row=5, column=0, padx=5, pady=5, sticky="e")
        self.volume_entry.grid(row=5, column=1, padx=5, pady=5, sticky="w")

        self.right_radio.grid(row=6, column=0, padx=5, pady=5)
        self.left_radio.grid(row=6, column=1, padx=5, pady=5)

        self.pump_button.grid(row=6, column=2, padx=5, pady=5)

    def rename_pump(self):
        new_name = simpledialog.askstring("Rename pump", "Enter new name:", initialvalue=self.title.get())
        if new_name:
            self.title.set(new_name)

    def set_flow_rate(self):
        flow_rate = self.flow_rate.get()
        self.pump.set_default_flow_rate(flow_rate)
        print(f"Flow rate set to {flow_rate} mL/min")


if __name__ == "__main__":
    root = ttk.Window(themename="cosmo")
    root.title("Pump Control Interface")

    from tools import get_connected_devices

    pumps, _ = get_connected_devices()

    for pump in pumps:
        pump_widget = PumpWidget(root, pump=pump)
        pump_widget.grid(padx=10, pady=10, sticky="nsew")

    root.mainloop()
