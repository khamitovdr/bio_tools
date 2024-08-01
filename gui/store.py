from dataclasses import dataclass, field

from bioexperiment_suite.experiment import Experiment
from device_widgets import PumpWidget, SpectrophotometerWidget


@dataclass
class Store:
    pump_widgets: dict[str, PumpWidget] = field(default_factory=dict)
    spectrophotometer_widgets: dict[str, SpectrophotometerWidget] = field(default_factory=dict)
    experiment: Experiment = field(default_factory=Experiment)
