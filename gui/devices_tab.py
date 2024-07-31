import threading

import ttkbootstrap as ttk
from bioexperiment_suite.tools import get_connected_devices
from device_widgets import PumpWidget, SpectrophotometerWidget
from ttkbootstrap import constants as c


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
            child.device.__del__()
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
