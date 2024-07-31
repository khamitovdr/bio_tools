from dataclasses import dataclass, field

from bioexperiment_suite.experiment import Experiment
from device_widgets import PumpWidget, SpectrophotometerWidget


@dataclass
class Store:
    pump_widgets: list[PumpWidget] = field(default_factory=list)
    spectrophotometer_widgets: list[SpectrophotometerWidget] = field(default_factory=list)
    experiment: Experiment = field(default_factory=Experiment)
