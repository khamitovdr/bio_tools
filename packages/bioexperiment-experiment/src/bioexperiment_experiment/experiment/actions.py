from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

from bioexperiment_experiment.loader import logger


class Action:
    """Class to define an action to be executed in an experiment.

    The action can be executed with the `execute` method, which will call the function with the provided arguments.
    The action keeps track of the time it was started and completed.
    """

    def __init__(self, func: Callable, *args: Any, **kwargs: Any) -> None:
        """Initialize the action with the function to be executed and the arguments to be passed to it.

        :param func: The function to be executed
        :param args: The positional arguments to be passed to the function
        :param kwargs: The keyword arguments to be passed to the function
        """
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None
        logger.debug(f"Action created: {self.func.__name__} with args: {args} and kwargs: {kwargs}")

    def execute(self) -> None:
        """Execute the action by calling the function with the provided arguments and tracking the start and end time."""
        self.start_time = datetime.now()
        logger.debug(f"Executing action: {self.func.__name__}")
        self.func(*self.args, **self.kwargs)
        self.end_time = datetime.now()
        logger.debug(f"Action completed: {self.func.__name__}")

    def is_completed(self) -> bool:
        """Check if the action has been completed.

        :return: True if the action has been completed, False otherwise
        """
        return self.end_time is not None and self.start_time is not None

    def duration(self) -> timedelta:
        """Get the duration of the action.

        :return: The duration of the action as a timedelta

        :raises ValueError: If the action has not been completed yet
        """
        if not self.is_completed():
            raise ValueError("Action did not complete yet")

        return self.end_time - self.start_time  # type: ignore


class Measurement(Action):
    """Class to define a measurement to be executed in an experiment.

    The measurement is a special type of action that also stores the measured value name and the measurement result.
    """

    def __init__(self, func: Callable, measurement_name: str, *args: Any, **kwargs: Any):
        """Initialize the measurement with the function to be executed, the measured value name, and the arguments.

        :param func: The function to be executed
        :param measurement_name: The name of the measured value
        :param args: The positional arguments to be passed to the function
        :param kwargs: The keyword arguments to be passed to the function
        """
        super().__init__(func, *args, **kwargs)
        self.measurement_name = measurement_name
        self.measured_value = None
        logger.debug(f"Measurement created: {self.func.__name__} with args: {args} and kwargs: {kwargs}")

    def execute(self) -> Any:
        """Execute the measurement by calling the function with the provided arguments and tracking the start and end time.

        :return: The result of the measurement
        """
        assert self.start_time is None, "Measurement already executed"
        self.start_time = datetime.now()
        logger.debug(f"Executing measurement: {self.func.__name__}")
        result = self.func(*self.args, **self.kwargs)
        self.end_time = datetime.now()
        self.measured_value = result
        logger.debug(f"Measurement completed: {self.func.__name__}")
        return result


class WaitAction:
    """Class to define a wait action to be executed in an experiment.

    The wait action is a special type of action that pauses the execution of the experiment for a given amount of time.
    If some action takes time to be executed, the wait time should be not less than the time taken by the action.
    """

    def __init__(self, seconds: float):
        """Initialize the wait action with the number of seconds to wait.

        :param seconds: The number of seconds to wait
        """
        self.wait_time: timedelta = timedelta(seconds=seconds)
        logger.debug(f"Wait action created: {seconds} seconds")
