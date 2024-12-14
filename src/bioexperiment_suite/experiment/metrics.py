from typing import Callable, SupportsIndex, Optional
from statistics import median

from bioexperiment_suite.experiment import Experiment


class Statistic:
    """A class that provides common statistical functions."""

    @staticmethod
    def LAST() -> Callable[[SupportsIndex], float]:
        return lambda measurement: measurement[-1]

    @staticmethod
    def COUNT() -> Callable[[SupportsIndex], int]:
        return len

    @staticmethod
    def SUM(window_size: Optional[int] = None) -> Callable[[SupportsIndex], float]:
        return lambda measurement: sum(measurement[-window_size:]) if window_size else sum(measurement)

    @staticmethod
    def MEAN(window_size: Optional[int] = None) -> Callable[[SupportsIndex], float]:
        return lambda measurement: (
            sum(measurement[-window_size:]) / window_size if window_size else sum(measurement) / len(measurement)
        )

    @staticmethod
    def MEDIAN(window_size: Optional[int] = None) -> Callable[[SupportsIndex], float]:
        return lambda measurement: median(measurement[-window_size:]) if window_size else median(measurement)

    @staticmethod
    def MAX(window_size: Optional[int] = None) -> Callable[[SupportsIndex], float]:
        return lambda measurement: max(measurement[-window_size:]) if window_size else max(measurement)

    @staticmethod
    def MIN(window_size: Optional[int] = None) -> Callable[[SupportsIndex], float]:
        return lambda measurement: min(measurement[-window_size:]) if window_size else min(measurement)


class Metric:
    """Class to define a metric to be used during the experiment run to make dynamic decisions"""

    def __init__(self, experiment: Experiment, measurement_name: str, statistic: Statistic | None = Statistic.LAST()):
        """Initialize the metric to be used in the experiment

        :param experiment: The experiment object
        :param measurement_name: The name of the measurement in the experiment to use for the metric calculation
        :param statistic: The statistic to apply to the measurement values
        """
        self.measurements = experiment.measurements
        self.measurement_name = measurement_name
        self.statistic = statistic

    def _measurement_values(self) -> tuple[float]:
        return tuple(zip(*self.measurements[self.measurement_name]))[1]

    def get_value(self) -> int | float:
        return self.statistic(self._measurement_values())
