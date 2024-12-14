from __future__ import annotations

from typing import Callable, TypeAlias
from bioexperiment_suite.experiment import Metric


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


class Condition:
    """Class to define a condition to determine if an action should be executed."""

    def __init__(self, metric: Metric, relation: RelationFunction):
        """
        Initialize the condition for the action to be executed.

        :param metric: The metric to evaluate.
        :param relation: A callable that takes the metric's value and returns a boolean.
        """
        if not isinstance(metric, Metric):
            raise TypeError("Expected a Metric instance for 'metric'.")
        if not callable(relation):
            raise TypeError("Expected a callable for 'relation'.")

        self.metric = metric
        self.relation = relation

    def check_condition(self) -> bool:
        """
        Check if the condition is met.

        :return: True if the condition is met, False otherwise.
        """
        metric_value = self.metric.get_value()
        return self.relation(metric_value)
    
    @property
    def negation(self) -> Condition:
        """Return a new condition that is the negation of this condition."""
        return Condition(self.metric, lambda x: not self.relation(x))
