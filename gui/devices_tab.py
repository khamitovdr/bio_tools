import threading

import ttkbootstrap as ttk
from bioexperiment_suite.interfaces import Pump, Spectrophotometer
from bioexperiment_suite.tools import get_connected_devices
from device_widgets import PumpWidget, SpectrophotometerWidget
from store import Store
from ttkbootstrap import constants as c


class ConnectedDevicesWidget(ttk.Frame):
    FRAME_PADDING = 5
    PADX = 5
    PADY = 5

    def __init__(self, parent: ttk.Frame, store: Store):
        super().__init__(parent, padding=5)

        self.store = store

        self.pumps: list[Pump] = []
        self.spectrophotometers: list[Spectrophotometer] = []

        self.create_widgets()

    def discover_devices(self) -> None:
        for device_widgets in (self.store.pump_widgets, self.store.spectrophotometer_widgets):
            for key in device_widgets:
                widget = device_widgets.pop(key)
                widget.device.__del__()
                widget.destroy()

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

        while self.pumps:
            pump = self.pumps.pop()
            pump_widget = PumpWidget(self.devices_frame, pump)
            self.store.pump_widgets[pump_widget.title.get()] = pump_widget
            pump_widget.pack(side=c.LEFT, fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

        while self.spectrophotometers:
            spec = self.spectrophotometers.pop()
            spec_widget = SpectrophotometerWidget(self.devices_frame, spec)
            self.store.spectrophotometer_widgets[spec_widget.title.get()] = spec_widget
            spec_widget.pack(side=c.LEFT, fill=c.X, expand=c.NO, padx=self.PADX, pady=self.PADY)

    def create_widgets(self) -> None:
        discover_button = ttk.Button(self, text="Discover devices", command=self.discover_devices, bootstyle=c.PRIMARY)
        discover_button.pack(fill=c.NONE, expand=c.NO, padx=self.PADX, pady=self.PADY)

        self.devices_frame = ttk.Frame(self, padding=5)
        self.devices_frame.pack(fill=c.X, expand=c.YES, padx=self.PADX, pady=self.PADY)
