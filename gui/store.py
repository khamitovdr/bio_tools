from dataclasses import dataclass, field

from bioexperiment_suite.experiment import Experiment
from device_widgets import PumpWidget, SpectrophotometerWidget


@dataclass
class Store:
    experiment: Experiment = field(default_factory=Experiment)

    pump_widgets: list[PumpWidget] = field(default_factory=list)

    @property
    def pump_names(self) -> list[str]:
        return [widget.title.get() for widget in self.pump_widgets]

    def get_pump_by_name(self, pump_name: str):
        for widget in self.pump_widgets:
            if widget.title.get() == pump_name:
                return widget.device

    spectrophotometer_widgets: list[SpectrophotometerWidget] = field(default_factory=list)

    @property
    def spectrophotometer_names(self) -> list[str]:
        return [widget.title.get() for widget in self.spectrophotometer_widgets]

    def get_spectrophotometer_by_name(self, spectrophotometer_name: str):
        for widget in self.spectrophotometer_widgets:
            if widget.title.get() == spectrophotometer_name:
                return widget.device
