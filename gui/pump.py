from tkinter import DoubleVar, StringVar, simpledialog

import ttkbootstrap as ttk
from bioexperiment_suite.interfaces import Pump
from ttkbootstrap import constants as c


class PumpWidget(ttk.Labelframe):
    instance_count = 0  # Class variable to keep track of the number of instances
    FRAME_PADDING = 5
    PADX = 5
    PADY = 5

    def __init__(self, parent: ttk.Frame, pump: Pump):
        super().__init__(parent, padding=self.FRAME_PADDING, bootstyle=c.PRIMARY, text="Pump")
        PumpWidget.instance_count += 1

        self.pump = pump
        self.title = StringVar(value=f"Pump {PumpWidget.instance_count}")
        self.flow_rate = DoubleVar(value=3.0)
        self.volume = DoubleVar(value=0.0)
        self.direction = StringVar(value="right")

        self.create_widgets()

    def crate_title_frame(self) -> ttk.Frame:
        frame = ttk.Frame(self, padding=self.FRAME_PADDING)

        label = ttk.Label(frame, textvariable=self.title, font=("Helvetica", 16, "bold"))
        label.pack(side=c.LEFT, padx=self.PADX, pady=self.PADY)

        rename_button = ttk.Button(frame, text="Rename", command=self.rename_pump, bootstyle=c.SECONDARY)
        rename_button.pack(side=c.RIGHT, padx=self.PADX, pady=self.PADY)

        return frame

    def create_info_section(self) -> ttk.Labelframe:
        frame = ttk.Labelframe(self, bootstyle=c.INFO, text="Info", padding=self.FRAME_PADDING)
        frame.columnconfigure(0, weight=1, minsize=110)
        frame.columnconfigure(1, weight=1, minsize=40)

        port_name_label = ttk.Label(frame, text="Port:")
        port_name_label.grid(row=0, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        port_name_info = ttk.Label(frame, text=self.pump.port)
        port_name_info.grid(row=0, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        baudrate_label = ttk.Label(frame, text="Baudrate:")
        baudrate_label.grid(row=1, column=0, sticky="ew", padx=self.PADX, pady=self.PADY)

        baudrate_info = ttk.Label(frame, text=self.pump.baudrate)
        baudrate_info.grid(row=1, column=1, sticky="ew", padx=self.PADX, pady=self.PADY)

        return frame

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

    def rename_pump(self):
        new_name = simpledialog.askstring("Rename pump", "Enter new name:", initialvalue=self.title.get())
        if new_name:
            self.title.set(new_name)

    def set_flow_rate(self):
        flow_rate = self.flow_rate.get()
        self.pump.set_default_flow_rate(flow_rate)
        print(f"Flow rate set to {flow_rate} mL/min")
