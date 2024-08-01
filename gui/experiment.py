from pathlib import Path
from tkinter import DoubleVar, Event, IntVar, StringVar, filedialog

import ttkbootstrap as ttk
from bioexperiment_suite.interfaces import Pump, Spectrophotometer
from store import Store
from ttkbootstrap import constants as c


class ExperimentWidget(ttk.Frame):
    FRAME_PADDING = 5
    PADX = 5
    PADY = 5

    def __init__(self, master: ttk.Frame, store: Store):
        super().__init__(master)

        self.store = store

        self.infuse_pump: Pump | None = None
        self.pour_out_pump: Pump | None = None
        self.spectrophotometer: Spectrophotometer | None = None

        self.output_directory_path = StringVar(value="Didn't selected (No CSV output)")
        self.experiment_duration_hours = IntVar(value=24)
        self.solution_refresh_interval_minutes = IntVar(value=60)
        self.measurement_interval_minutes = IntVar(value=5)
        self.poured_out_volume_ml = DoubleVar(value=2.0)
        self.infused_volume_ml = DoubleVar(value=1.0)
        self.flow_rate_ml_per_minute = DoubleVar(value=3.0)

        self.create_widgets()

    def ask_for_output_directory(self):
        self.output_directory_path.set(filedialog.askdirectory(initialdir=".", title="Select results output directory"))
        if not self.output_directory_path.get():
            self.output_directory_path.set("Didn't selected (No CSV output)")
            return
        output_directory_path = Path(self.output_directory_path.get())
        self.store.experiment.specify_output_dir(output_directory_path)

    def create_output_directory_widget(self) -> ttk.Labelframe:
        frame = ttk.Labelframe(self, bootstyle=c.PRIMARY, text="CSV Output", padding=self.FRAME_PADDING)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        output_dir_label = ttk.Label(frame, text="Output Directory:")
        output_dir_label.grid(row=0, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        output_dir_button = ttk.Button(frame, text="Select", command=self.ask_for_output_directory)
        output_dir_button.grid(row=0, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        output_dir_entry = ttk.Label(frame, textvariable=self.output_directory_path, style="info.TLabel")
        output_dir_entry.grid(row=1, column=0, columnspan=2, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        return frame

    def create_experiment_setup_widget(self) -> ttk.Labelframe:
        frame = ttk.Labelframe(self, bootstyle=c.PRIMARY, text="Experiment Parameters", padding=self.FRAME_PADDING)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        duration_label = ttk.Label(frame, text="Total duration (hours):")
        duration_label.grid(row=0, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        duration_entry = ttk.Entry(frame, textvariable=self.experiment_duration_hours)
        duration_entry.grid(row=0, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        refresh_interval_label = ttk.Label(frame, text="Solution refresh interval (minutes):")
        refresh_interval_label.grid(row=1, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        refresh_interval_entry = ttk.Entry(frame, textvariable=self.solution_refresh_interval_minutes)
        refresh_interval_entry.grid(row=1, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        measurement_interval_label = ttk.Label(frame, text="Measurement interval (minutes):")
        measurement_interval_label.grid(row=2, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        measurement_interval_entry = ttk.Entry(frame, textvariable=self.measurement_interval_minutes)
        measurement_interval_entry.grid(row=2, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        poured_out_volume_label = ttk.Label(frame, text="Poured out volume (mL):")
        poured_out_volume_label.grid(row=3, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        poured_out_volume_entry = ttk.Entry(frame, textvariable=self.poured_out_volume_ml)
        poured_out_volume_entry.grid(row=3, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        infused_volume_label = ttk.Label(frame, text="Infused volume (mL):")
        infused_volume_label.grid(row=4, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        infused_volume_entry = ttk.Entry(frame, textvariable=self.infused_volume_ml)
        infused_volume_entry.grid(row=4, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        flow_rate_label = ttk.Label(frame, text="Flow rate (mL/min):")
        flow_rate_label.grid(row=5, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        flow_rate_entry = ttk.Entry(frame, textvariable=self.flow_rate_ml_per_minute)
        flow_rate_entry.grid(row=5, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        return frame

    def create_devices_choice_widget(self) -> ttk.Labelframe:
        frame = ttk.Labelframe(self, bootstyle=c.PRIMARY, text="Devices", padding=self.FRAME_PADDING)
        frame.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        infused_pump_label = ttk.Label(frame, text="Infuse Pump:")
        infused_pump_label.grid(row=0, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        poured_out_pump_label = ttk.Label(frame, text="Pour Out Pump:")
        poured_out_pump_label.grid(row=1, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        spectrophotometer_label = ttk.Label(frame, text="Spectrophotometer:")
        spectrophotometer_label.grid(row=2, column=0, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        def handle_infuse_pump_choice(event: Event) -> None:
            self.infuse_pump = self.store.pump_widgets[event.widget.get()].pump

        def handle_pour_out_pump_choice(event: Event) -> None:
            self.pour_out_pump = self.store.pump_widgets[event.widget.get()].pump

        def handle_spectrophotometer_choice(event: Event) -> None:
            self.spectrophotometer = self.store.spectrophotometer_widgets[event.widget.get()].spectrophotometer

        def render_choices():
            infuse_pump_choice = ttk.Combobox(
                frame,
                values=list(self.store.pump_widgets.keys()),
                state="readonly",
            )
            infuse_pump_choice.grid(row=0, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)
            infuse_pump_choice.bind("<<ComboboxSelected>>", handle_infuse_pump_choice)

            pour_out_pump_choice = ttk.Combobox(
                frame,
                values=list(self.store.pump_widgets.keys()),
                state="readonly",
            )
            pour_out_pump_choice.grid(row=1, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)
            pour_out_pump_choice.bind("<<ComboboxSelected>>", handle_pour_out_pump_choice)

            spectrophotometer_choice = ttk.Combobox(
                frame,
                values=list(self.store.spectrophotometer_widgets.keys()),
                state="readonly",
            )
            spectrophotometer_choice.grid(row=2, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)
            spectrophotometer_choice.bind("<<ComboboxSelected>>", handle_spectrophotometer_choice)

        render_choices()

        update_button = ttk.Button(frame, text="Update", command=render_choices)
        update_button.grid(row=3, column=0, columnspan=2, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        return frame

    def create_widgets(self):
        output_directory_widget = self.create_output_directory_widget()
        output_directory_widget.grid(row=0, column=0, sticky=c.NSEW)

        devices_choice_widget = self.create_devices_choice_widget()
        devices_choice_widget.grid(row=1, column=0, sticky=c.NSEW)

        experiment_setup_widget = self.create_experiment_setup_widget()
        experiment_setup_widget.grid(row=2, column=0, sticky=c.NSEW)
