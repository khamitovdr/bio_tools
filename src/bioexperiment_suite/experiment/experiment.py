import inspect
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Callable, get_type_hints

from bioexperiment_suite.loader import logger


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


class Experiment:
    """Class to define an experiment with actions and measurements to be executed in sequence.

    The experiment can be run with the `run` method, which will execute each action in sequence.
    The experiment keeps track of the time each action was executed and the measurements taken.
    """

    def __init__(self, output_dir: os.PathLike | None = None):
        """Initialize the experiment with an empty list of actions and measurements"""
        self.actions: list[Action | WaitAction] = []
        self.measurements: dict[str, list[tuple[datetime, Any]]] = defaultdict(list)
        self.current_time: datetime | None = (
            None  # Time to keep track of the experiment progress. Initializes on start.
        )
        self.output_dir = output_dir
        logger.debug("Experiment created")

    def add_action(self, func: Callable, *args: Any, **kwargs: Any):
        """Add an action to the experiment.

        The action will be executed in sequence when the experiment is run.

        :param func: The function to be executed
        :param args: The positional arguments to be passed to the function
        :param kwargs: The keyword arguments to be passed to the function
        """
        self._validate_types(func, *args, **kwargs)
        self.actions.append(Action(func, *args, **kwargs))
        logger.debug(f"Action added to experiment: {func.__name__}")

    def add_measurement(self, func: Callable, measurement_name: str, *args: Any, **kwargs: Any):
        """Add a measurement to the experiment.

        The measurement will be executed in sequence when the experiment is run, and the result will be stored.

        :param func: The function to be executed
        :param measurement_name: The name of the measured value
        :param args: The positional arguments to be passed to the function
        :param kwargs: The keyword arguments to be passed to the function
        """
        self._validate_types(func, *args, **kwargs)
        self.actions.append(Measurement(func, measurement_name, *args, **kwargs))
        logger.debug(f"Measurement added to experiment: {func.__name__}")

    def add_wait(self, seconds: float):
        """Add a wait action to the experiment.

        The wait action will pause the execution of the experiment for the given amount of time.

        :param seconds: The number of seconds to wait
        """
        self.actions.append(WaitAction(seconds))
        logger.debug(f"Wait action added to experiment: {seconds} seconds")

    def run(self):
        """Run the experiment by executing each action in sequence."""
        self.current_time = datetime.now()
        logger.debug(f"Experiment started. Start time: {self.current_time}")
        for step, action in enumerate(self.actions):
            logger.debug(f"Step {step + 1} from {len(self.actions)}")
            if isinstance(action, Measurement):
                logger.debug(f"Executing measurement: {action.func.__name__}")
                action.execute()
                self.measurements[action.measurement_name].append((datetime.now(), action.measured_value))
                self.write_measurement_to_csv(action.measurement_name)
            elif isinstance(action, Action):
                logger.debug(f"Executing action: {action.func.__name__}")
                action.execute()
            elif isinstance(action, WaitAction):
                wait_until = self.current_time + action.wait_time
                logger.debug(f"Waiting for {action.wait_time.total_seconds()} seconds from {self.current_time}")
                if datetime.now() <= wait_until:
                    time.sleep((wait_until - datetime.now()).total_seconds())
                else:
                    logger.warning(f"Wait time exceeded on step {step + 1} by {datetime.now() - wait_until}")

                self.current_time += action.wait_time

            else:
                logger.error(f"Unknown action type: {type(action)}")
                raise ValueError(f"Unknown action type: {type(action)}")

    def write_measurement_to_csv(self, measurement_name: str):
        """Write last acquired measurement to a CSV file.

        :param measurement_name: The name of the measurement to write to a CSV file
        """
        if self.output_dir is None:
            return

        if measurement_name not in self.measurements:
            raise ValueError(f"Measurement '{measurement_name}' not found")

        output_file = os.path.join(self.output_dir, f"{measurement_name}.csv")
        with open(output_file, "a") as f:
            timestamp, value = self.measurements[measurement_name][-1]
            f.write(f"{timestamp},{value}\n")

        logger.debug(f"Measurement '{measurement_name}' written to {output_file}")

    def _validate_types(self, func: Callable, *args: Any, **kwargs: Any):
        """Validate that the arguments passed to the function are of the correct type.

        :param func: The function to validate the arguments for
        :param args: The positional arguments to validate
        :param kwargs: The keyword arguments to validate

        :raises TypeError: If any argument is not of the expected type according to the type hints of the function
        """
        type_hints = get_type_hints(func)
        sig = inspect.signature(func)
        bound_arguments = sig.bind_partial(*args, **kwargs).arguments

        for name, value in bound_arguments.items():
            expected_type = type_hints.get(name)
            if expected_type and not isinstance(value, expected_type):
                msg = f"Argument '{name}' is expected to be of type {expected_type}, but got {type(value)}"
                raise TypeError(msg)
