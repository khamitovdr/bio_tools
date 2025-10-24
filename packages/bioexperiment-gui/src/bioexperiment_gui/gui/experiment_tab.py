from pathlib import Path
from tkinter import DoubleVar, Event, IntVar, StringVar, filedialog, messagebox

import ttkbootstrap as ttk
from bioexperiment_tools.interfaces import Pump, Spectrophotometer
from bioexperiment_tools.loader import logger
from ttkbootstrap import constants as c

from .store import Store


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

        self.is_experiment_setup = False
        self.is_experiment_running = False

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
            self.infuse_pump = self.store.get_pump_by_name(event.widget.get())

        def handle_pour_out_pump_choice(event: Event) -> None:
            self.pour_out_pump = self.store.get_pump_by_name(event.widget.get())

        def handle_spectrophotometer_choice(event: Event) -> None:
            self.spectrophotometer = self.store.get_spectrophotometer_by_name(event.widget.get())

        def render_choices():
            infuse_pump_choice = ttk.Combobox(
                frame,
                values=self.store.pump_names,
                state="readonly",
            )
            infuse_pump_choice.grid(row=0, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)
            infuse_pump_choice.bind("<<ComboboxSelected>>", handle_infuse_pump_choice)

            pour_out_pump_choice = ttk.Combobox(
                frame,
                values=self.store.pump_names,
                state="readonly",
            )
            pour_out_pump_choice.grid(row=1, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)
            pour_out_pump_choice.bind("<<ComboboxSelected>>", handle_pour_out_pump_choice)

            spectrophotometer_choice = ttk.Combobox(
                frame,
                values=self.store.spectrophotometer_names,
                state="readonly",
            )
            spectrophotometer_choice.grid(row=2, column=1, sticky=c.EW, padx=self.PADX, pady=self.PADY)
            spectrophotometer_choice.bind("<<ComboboxSelected>>", handle_spectrophotometer_choice)

        render_choices()

        update_button = ttk.Button(frame, text="Update", command=render_choices)
        update_button.grid(row=3, column=0, columnspan=2, sticky=c.EW, padx=self.PADX, pady=self.PADY)

        return frame

    def setup_experiment(self):
        MEASUREMENT_WAIT_TIME_SECONDS = 60
        n_solution_refreshes = self.experiment_duration_hours.get() * 60 // self.solution_refresh_interval_minutes.get()
        n_measurements_per_solution_refresh = (
            self.solution_refresh_interval_minutes.get() // self.measurement_interval_minutes.get()
        )

        for _ in range(n_solution_refreshes):
            for _ in range(n_measurements_per_solution_refresh):
                self.store.experiment.add_measurement(
                    self.spectrophotometer.get_temperature,  # type: ignore
                    measurement_name="Temperature (C)",
                )
                self.store.experiment.add_measurement(
                    self.spectrophotometer.measure_optical_density,  # type: ignore
                    measurement_name="Optical density",
                )
                self.store.experiment.add_wait(self.measurement_interval_minutes.get() * 60)

            self.store.experiment.actions.pop()
            self.store.experiment.add_wait(MEASUREMENT_WAIT_TIME_SECONDS)
            self.store.experiment.add_action(
                self.pour_out_pump.pour_in_volume,  # type: ignore
                volume=self.poured_out_volume_ml.get(),
                flow_rate=self.flow_rate_ml_per_minute.get(),
                direction="left",
            )
            self.store.experiment.add_action(
                self.infuse_pump.pour_in_volume,  # type: ignore
                volume=self.infused_volume_ml.get(),
                flow_rate=self.flow_rate_ml_per_minute.get(),
                direction="right",
            )
            self.store.experiment.add_wait(self.measurement_interval_minutes.get() * 60 - MEASUREMENT_WAIT_TIME_SECONDS)

    def apply_experiment_settings(self):
        if not self.infuse_pump or not self.pour_out_pump or not self.spectrophotometer:
            messagebox.showerror(title="Error", message="Please select all devices")
            return

        try:
            assert self.experiment_duration_hours.get() > 0
            assert self.solution_refresh_interval_minutes.get() > 0
            assert self.measurement_interval_minutes.get() > 0
        except AssertionError:
            messagebox.showerror(title="Error", message="Please enter positive values for durations and intervals")
            return

        self.store.experiment.reset_experiment()
        self.setup_experiment()
        self.is_experiment_setup = True
        logger.info("Experiment is ready to start")

    def start_experiment(self):
        if not self.is_experiment_setup:
            messagebox.showerror(title="Error", message="Please apply experiment settings first")
            return

        self.store.experiment.start()
        self.is_experiment_running = True

    def stop_experiment(self):
        if not self.is_experiment_running:
            messagebox.showerror(title="Error", message="Experiment is not running")
            return

        self.store.experiment.stop()
        self.is_experiment_running = False

    def create_experiment_controls_widget(self) -> ttk.Labelframe:
        frame = ttk.Labelframe(self, bootstyle=c.PRIMARY, text="Experiment Controls", padding=self.FRAME_PADDING)

        apply_settings_button = ttk.Button(
            frame,
            text="Apply Experiment Settings",
            command=self.apply_experiment_settings,
            bootstyle=c.PRIMARY,
        )
        apply_settings_button.pack(fill=c.X, padx=self.PADX, pady=self.PADY)

        start_experiment_button = ttk.Button(
            frame,
            text="Start Experiment",
            command=self.start_experiment,
            bootstyle=c.SUCCESS,
        )
        start_experiment_button.pack(fill=c.X, padx=self.PADX, pady=self.PADY)

        stop_experiment_button = ttk.Button(
            frame,
            text="Stop Experiment",
            command=self.stop_experiment,
            bootstyle=c.DANGER,
        )
        stop_experiment_button.pack(fill=c.X, padx=self.PADX, pady=self.PADY)

        return frame

    def create_widgets(self):
        output_directory_widget = self.create_output_directory_widget()
        output_directory_widget.grid(row=1, column=0, sticky=c.NSEW, padx=self.PADX, pady=self.PADY)

        devices_choice_widget = self.create_devices_choice_widget()
        devices_choice_widget.grid(row=0, column=0, sticky=c.NSEW, padx=self.PADX, pady=self.PADY)

        experiment_setup_widget = self.create_experiment_setup_widget()
        experiment_setup_widget.grid(row=0, column=1, sticky=c.NSEW, padx=self.PADX, pady=self.PADY)

        experiment_controls_widget = self.create_experiment_controls_widget()
        experiment_controls_widget.grid(row=1, column=1, sticky=c.NSEW, padx=self.PADX, pady=self.PADY)
