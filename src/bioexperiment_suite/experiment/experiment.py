import inspect
import os
import time
from collections import defaultdict
from datetime import datetime, timedelta
from threading import Event, Thread
from typing import Any, Callable, get_type_hints

from bioexperiment_suite.loader import logger
from bioexperiment_suite.experiment import Condition


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


class ConditionalAction:
    """Class to define action to be executed based on a condition."""

    def __init__(self, action: Action, condition: Condition):
        """Initialize the conditional action with the condition and the action to be executed

        :param condition: The condition to evaluate
        :param action: The action to execute if the condition is met
        """
        self.action = action
        self.condition = condition
        logger.debug(f"Conditional action created: {self.condition} -> {self.action}")

    def get_action(self) -> Action | None:
        """Return the action to be executed if the
        condition is met, otherwise return None."""
        if self.condition.check_condition():
            return self.action
        return None


class Experiment:
    """Class to define an experiment with actions and measurements to be executed in sequence.

    The experiment can be run with the `run` method, which will execute each action in sequence.
    The experiment keeps track of the time each action was executed and the measurements taken.
    """

    def __init__(self, output_dir: os.PathLike | None = None):
        """Initialize the experiment with an empty list of actions and measurements"""
        self.actions: list[Action | WaitAction | ConditionalAction] = []
        self.measurements: dict[str, list[tuple[datetime, Any]]] = defaultdict(list)
        self.current_time: datetime | None = (
            None  # Time to keep track of the experiment progress. Initializes on start.
        )
        self.output_dir = output_dir
        self._thread: Thread | None = None
        self._stop_event = Event()
        logger.debug("Experiment created")

    def specify_output_dir(self, output_dir: os.PathLike):
        """Specify the output directory to write measurements to CSV files.

        :param output_dir: The directory to write measurements to
        """
        self.output_dir = output_dir
        logger.debug(f"Output directory specified: {output_dir}")

    def add_action(self, func: Callable, condition: Condition | None = None, *args: Any, **kwargs: Any):
        """Add an action to the experiment.

        The action will be executed in sequence when the experiment is run.

        :param func: The function to be executed
        :param condition: The condition to evaluate before executing the action
        :param args: The positional arguments to be passed to the function
        :param kwargs: The keyword arguments to be passed to the function
        """
        self._validate_types(func, *args, **kwargs)
        action = Action(func, *args, **kwargs)
        if condition is not None:
            self.actions.append(ConditionalAction(action, condition))
            logger.debug(f"Conditional action added to experiment: {func.__name__} with condition: {condition}")
            return

        self.actions.append(action)
        logger.debug(f"Action added to experiment: {func.__name__}")

    def add_measurement(
        self, func: Callable, measurement_name: str, condition: Condition | None = None, *args: Any, **kwargs: Any
    ):
        """Add a measurement to the experiment.

        The measurement will be executed in sequence when the experiment is run, and the result will be stored.

        :param func: The function to be executed
        :param measurement_name: The name of the measured value
        :param condition: The condition to evaluate before executing the action
        :param args: The positional arguments to be passed to the function
        :param kwargs: The keyword arguments to be passed to the function
        """
        self._validate_types(func, *args, **kwargs)
        measurement = Measurement(func, measurement_name, *args, **kwargs)
        if condition is not None:
            self.actions.append(ConditionalAction(measurement, condition))
            logger.debug(f"Conditional measurement added to experiment: {func.__name__} with condition: {condition}")
            return

        self.actions.append(measurement)
        logger.debug(f"Measurement added to experiment: {func.__name__}")

    def add_wait(self, seconds: float, condition: Condition | None = None):
        """Add a wait action to the experiment.

        The wait action will pause the execution of the experiment for the given amount of time.

        :param seconds: The number of seconds to wait
        :param condition: The condition to evaluate before executing the action
        """
        wait_action = WaitAction(seconds)
        if condition is not None:
            self.actions.append(ConditionalAction(wait_action, condition))
            logger.debug(f"Conditional wait added to experiment: {seconds} seconds with condition: {condition}")
            return

        self.actions.append(wait_action)
        logger.debug(f"Wait action added to experiment: {seconds} seconds")

    def _perform_action(self, action: Action | WaitAction | ConditionalAction, step: int) -> bool:
        """Perform the action by executing it or waiting for the specified time.

        :param action: The action to perform
        """
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

            if datetime.now() > wait_until:
                logger.warning(f"Wait time exceeded on step {step + 1} by {datetime.now() - wait_until}")

            while datetime.now() < wait_until:
                if self._stop_event.is_set():
                    logger.debug("Experiment stopped")
                    return False
                time.sleep(0.1)

            self.current_time += action.wait_time

        elif isinstance(action, ConditionalAction):
            action_to_execute = action.get_action()
            if action_to_execute is not None:
                self._perform_action(action_to_execute, step)
            else:
                logger.debug("Condition not met, skipping action")

        else:
            logger.error(f"Unknown action type: {type(action)}")
            raise ValueError(f"Unknown action type: {type(action)}")

        return True

    def _run(self):
        """Run the experiment by executing each action in sequence."""
        self.current_time = datetime.now()
        logger.debug(f"Experiment started. Start time: {self.current_time}")
        for step, action in enumerate(self.actions):
            if not self._perform_action(action, step):
                return

    def start(self, start_in_background: bool = True):
        """Start the experiment by running it in idle mode or in a separate thread depending on the `start_in_background` flag.

        :param start_in_background: If True, start the experiment in a separate thread.
        If False, run the experiment in the current thread. Be careful with this option,
        as it will block the current thread until the experiment is finished!
        """
        if self._thread is not None:
            logger.warning("Experiment is already running")
            return

        self._stop_event.clear()
        if start_in_background:
            self._thread = Thread(target=self._run)
            self._thread.start()
        else:
            self._run()

    def stop(self):
        """Stop the experiment by setting the stop event."""
        if self._thread is None:
            logger.warning("Experiment is not running")
            return
        self._stop_event.set()
        logger.info("Experiment stop signal sent")

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

    def reset_experiment(self):
        """Reset the experiment by clearing the actions, measurements and current time."""
        logger.debug("Experiment reset")
        if self._thread is not None:
            logger.warning("Experiment is running. Stop it before resetting.")
            return

        self.actions.clear()
        self.measurements.clear()
        self.current_time = None

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
