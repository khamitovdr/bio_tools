from typing import Callable, SupportsIndex, Optional, TypeAlias
from statistics import median

RelationFunction: TypeAlias = Callable[[float], bool]


class Relation:
    """Class to define common relations for conditional actions."""

    @staticmethod
    def EQUALS_TO(value: float) -> RelationFunction:
        """Returns a relation checking if a metric equals the given value."""
        return lambda x: x == value

    @staticmethod
    def GREATER_THAN(value: float) -> RelationFunction:
        """Returns a relation checking if a metric is greater than the given value."""
        return lambda x: x > value

    @staticmethod
    def LESS_THAN(value: float) -> RelationFunction:
        """Returns a relation checking if a metric is less than the given value."""
        return lambda x: x < value

    @staticmethod
    def GREATER_THAN_OR_EQUALS_TO(value: float) -> RelationFunction:
        """Returns a relation checking if a metric is greater than or equal to the given value."""
        return lambda x: x >= value

    @staticmethod
    def LESS_THAN_OR_EQUALS_TO(value: float) -> RelationFunction:
        """Returns a relation checking if a metric is less than or equal to the given value."""
        return lambda x: x <= value

    @staticmethod
    def NOT_EQUALS_TO(value: float) -> RelationFunction:
        """Returns a relation checking if a metric does not equal the given value."""
        return lambda x: x != value


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
