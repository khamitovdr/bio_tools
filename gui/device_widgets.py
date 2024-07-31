import threading
from abc import ABC
from datetime import datetime
from tkinter import DoubleVar, StringVar, simpledialog
from typing import Callable

import ttkbootstrap as ttk
from bioexperiment_suite.interfaces import Pump, SerialConnection, Spectrophotometer
from bioexperiment_suite.tools import get_connected_devices
from ttkbootstrap import constants as c


class DeviceWidget(ttk.Labelframe, ABC):
    instance_count = 0  # Class variable to keep track of the number of instances
    DEVICE_TYPE = ""
    FRAME_PADDING = 5
    PADX = 5
    PADY = 5

    def __init__(self, parent: ttk.Frame, device: SerialConnection):
        super().__init__(parent, padding=self.FRAME_PADDING, bootstyle=c.PRIMARY, text=self.DEVICE_TYPE)
        self.device = device
        self.title = StringVar(value=f"{self.DEVICE_TYPE} {self.instance_count}")

    def crate_title_frame(self) -> ttk.Frame:
        frame = ttk.Frame(self, padding=self.FRAME_PADDING)

        label = ttk.Label(frame, textvariable=self.title, font=("Helvetica", 16, "bold"))
        label.pack(side=c.LEFT, padx=self.PADX, pady=self.PADY)

        rename_button = ttk.Button(frame, text="Rename", command=self.rename, bootstyle=c.SECONDARY)
        rename_button.pack(side=c.RIGHT, padx=self.PADX, pady=self.PADY)

        return frame

    def rename(self):
        new_name = simpledialog.askstring(
            f"Rename {self.DEVICE_TYPE}",
            "Enter new name:",
            initialvalue=self.title.get(),
        )
        if new_name:
            self.title.set(new_name)

    def create_info_section(self) -> ttk.Labelframe:
        frame = ttk.Labelframe(self, bootstyle=c.INFO, text="Info", padding=self.FRAME_PADDING)
        frame.columnconfigure(0, weight=1, minsize=110)
        frame.columnconfigure(1, weight=1, minsize=40)

        port_name_label = ttk.Label(frame, text="Port:")
        port_name_label.grid(row=0, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        port_name_info = ttk.Label(frame, text=self.device.port)
        port_name_info.grid(row=0, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        baudrate_label = ttk.Label(frame, text="Baudrate:")
        baudrate_label.grid(row=1, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        baudrate_info = ttk.Label(frame, text=self.device.baudrate)
        baudrate_info.grid(row=1, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        return frame


class PumpWidget(DeviceWidget):
    DEVICE_TYPE = "Pump"

    def __init__(self, parent: ttk.Frame, pump: Pump):
        PumpWidget.instance_count += 1
        super().__init__(parent, pump)

        self.pump = pump
        self.flow_rate = DoubleVar(value=3.0)
        self.volume = DoubleVar(value=0.0)
        self.direction = StringVar(value="right")

        self.set_flow_rate()
        self.create_widgets()

    def create_flow_rate_control(self) -> ttk.Labelframe:
        frame = ttk.Labelframe(self, bootstyle=c.PRIMARY, text="Flow rate control", padding=self.FRAME_PADDING)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        label = ttk.Label(frame, text="Flow rate (mL/min):")
        label.grid(row=0, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        entry = ttk.Entry(frame, textvariable=self.flow_rate, bootstyle=c.PRIMARY, width=label.winfo_width())
        entry.grid(row=0, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        set_button = ttk.Button(frame, text="Set", command=self.set_flow_rate, bootstyle=c.PRIMARY)
        set_button.grid(row=1, column=0, sticky="ew", columnspan=2, padx=self.PADX, pady=self.PADY)

        return frame

    def create_continuous_rotation_control(self) -> ttk.Labelframe:
        frame = ttk.Labelframe(
            self, bootstyle=c.PRIMARY, text="Continuous rotation control", padding=self.FRAME_PADDING
        )
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(2, weight=1)

        rotate_right_button = ttk.Button(
            frame,
            text="Rotate right",
            command=lambda: self.pump.start_continuous_rotation(direction="right"),
            bootstyle=c.SUCCESS,
        )
        rotate_right_button.grid(row=0, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        stop_button = ttk.Button(frame, text="Stop", bootstyle=c.DANGER, command=self.pump.stop_continuous_rotation)
        stop_button.grid(row=0, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        rotate_left_button = ttk.Button(
            frame,
            text="Rotate Left",
            command=lambda: self.pump.start_continuous_rotation(direction="left"),
            bootstyle=c.SUCCESS,
        )
        rotate_left_button.grid(row=0, column=2, sticky="ew", padx=self.PADX, pady=self.PADY)

        return frame

    def create_volume_pouring_control(self) -> ttk.Labelframe:
        frame = ttk.Labelframe(self, bootstyle=c.PRIMARY, text="Volume pouring control", padding=self.FRAME_PADDING)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        volume_label = ttk.Label(frame, text="Volume (mL):")
        volume_label.grid(row=0, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        volume_entry = ttk.Entry(frame, textvariable=self.volume, bootstyle=c.PRIMARY, width=volume_label.winfo_width())
        volume_entry.grid(row=0, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        direction_frame = ttk.Frame(frame, padding=0)
        direction_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        direction_frame.columnconfigure(0, weight=1)
        direction_frame.columnconfigure(1, weight=1)
        right_radio = ttk.Radiobutton(
            direction_frame, text="Right", variable=self.direction, value="right", bootstyle=("toolbutton", c.PRIMARY)
        )
        right_radio.grid(row=0, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        left_radio = ttk.Radiobutton(
            direction_frame, text="Left", variable=self.direction, value="left", bootstyle=("toolbutton", c.PRIMARY)
        )
        left_radio.grid(row=0, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        pump_button = ttk.Button(
            frame,
            text="Pump",
            command=lambda: self.pump.pour_in_volume(self.volume.get(), direction=self.direction.get()),
            bootstyle=c.SUCCESS,
        )
        pump_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=self.PADX, pady=self.PADY)

        return frame

    def create_widgets(self):
        title_frame = self.crate_title_frame()
        title_frame.pack(fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

        info_section = self.create_info_section()
        info_section.pack(fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

        flow_rate_control = self.create_flow_rate_control()
        flow_rate_control.pack(fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

        continuous_rotation_control = self.create_continuous_rotation_control()
        continuous_rotation_control.pack(fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

        volume_pouring_control = self.create_volume_pouring_control()
        volume_pouring_control.pack(fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

    def set_flow_rate(self):
        flow_rate = self.flow_rate.get()
        self.pump.set_default_flow_rate(flow_rate)
        print(f"Flow rate set to {flow_rate} mL/min")


class SpectrophotometerWidget(DeviceWidget):
    DEVICE_TYPE = "Spectrophotometer"

    def __init__(self, parent: ttk.Frame, spectrophotometer: Spectrophotometer):
        SpectrophotometerWidget.instance_count += 1
        super().__init__(parent, spectrophotometer)

        self.spectrophotometer = spectrophotometer

        self.temperature = DoubleVar()
        self.temperature_updated = StringVar(value="-")

        self.absorbance = DoubleVar()
        self.absorbance_updated = StringVar(value="-")

        self.create_widgets()

    def create_measurement_display(
        self, title: str, value_var: DoubleVar, updated_var: StringVar, update_function: Callable
    ) -> ttk.Labelframe:
        frame = ttk.Labelframe(self, bootstyle=c.PRIMARY, text=title, padding=self.FRAME_PADDING)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        label = ttk.Label(frame, text=f"{title}:")
        label.grid(row=0, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        value = ttk.Label(frame, textvariable=value_var)
        value.grid(row=0, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        time_label = ttk.Label(frame, text="Last updated:")
        time_label.grid(row=1, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        time_value = ttk.Label(frame, textvariable=updated_var)
        time_value.grid(row=1, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        measure_button = ttk.Button(frame, text="Measure", command=update_function, bootstyle=c.PRIMARY)
        measure_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=self.PADX, pady=self.PADY)

        return frame

    def create_widgets(self):
        title_frame = self.crate_title_frame()
        title_frame.pack(fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

        info_section = self.create_info_section()
        info_section.pack(fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

        temperature_display = self.create_measurement_display(
            "Temperature, °C", self.temperature, self.temperature_updated, self.measure_temperature
        )
        temperature_display.pack(fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

        absorbance_display = self.create_measurement_display(
            "Absorbance", self.absorbance, self.absorbance_updated, self.measure_absorbance
        )
        absorbance_display.pack(fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

    def measure_temperature(self):
        temperature = self.spectrophotometer.get_temperature()
        self.temperature_updated.set(datetime.now().strftime("%H:%M:%S"))
        self.temperature.set(round(temperature, 2))

    def measure_absorbance(self):
        absorbance = self.spectrophotometer.measure_absorbance()
        self.absorbance_updated.set(datetime.now().strftime("%H:%M:%S"))
        self.absorbance.set(round(absorbance, 5))


class ConnectedDevicesWidget(ttk.Frame):
    FRAME_PADDING = 5
    PADX = 5
    PADY = 5

    def __init__(self, parent):
        super().__init__(parent, padding=5)

        self.pumps = []
        self.spectrophotometers = []
        self.create_widgets()

    def discover_devices(self):
        for child in self.devices_frame.winfo_children():
            child.destroy()

        progress = ttk.Progressbar(self.devices_frame, mode="determinate", bootstyle=c.STRIPED)
        progress.pack(fill=c.X, expand=c.YES, padx=self.PADX, pady=self.PADY)
        self.master.update()

        for class_ in (PumpWidget, SpectrophotometerWidget):
            class_.instance_count = 0  # type: ignore

        def find_connected_devices():
            self.pumps, self.spectrophotometers = get_connected_devices()

        t = threading.Thread(target=find_connected_devices)

        t.start()
        while t.is_alive():
            progress.step(1)
            self.master.update()
            t.join(0.1)

        progress.destroy()

        for pump in self.pumps:
            PumpWidget(self.devices_frame, pump).pack(
                side=c.LEFT, fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY
            )

        for spec in self.spectrophotometers:
            SpectrophotometerWidget(self.devices_frame, spec).pack(
                side=c.LEFT, fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY
            )

    def create_widgets(self):
        discover_button = ttk.Button(self, text="Discover devices", command=self.discover_devices, bootstyle=c.PRIMARY)
        discover_button.pack(fill=c.NONE, expand=c.NO, padx=self.PADX, pady=self.PADY)

        self.devices_frame = ttk.Frame(self, padding=5)
        self.devices_frame.pack(fill=c.X, expand=c.YES, padx=self.PADX, pady=self.PADY)


def main():
    root = ttk.Window(minsize=(1000, 600), themename="litera")
    app = ConnectedDevicesWidget(root)
    app.pack(fill=c.BOTH, expand=c.YES)
    root.mainloop()


if __name__ == "__main__":
    main()
