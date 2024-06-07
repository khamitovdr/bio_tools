import inspect
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, get_type_hints

from loader import logger


class Action:
    def __init__(self, func: Callable, *args: Any, **kwargs: Any):
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        logger.debug(f"Action created: {self.func.__name__} with args: {args} and kwargs: {kwargs}")

    def execute(self) -> Any:
        self.start_time = datetime.now()
        logger.debug(f"Executing action: {self.func.__name__}")
        result = self.func(*self.args, **self.kwargs)
        self.end_time = datetime.now()
        logger.debug(f"Action completed: {self.func.__name__}")
        return result

    def is_completed(self) -> bool:
        return self.end_time is not None and self.start_time is not None

    def duration(self) -> timedelta:
        if not self.is_completed():
            raise ValueError("Action did not complete yet")

        return self.end_time - self.start_time  # type: ignore


class WaitAction:
    def __init__(self, seconds: float):
        self.wait_time: timedelta = timedelta(seconds=seconds)
        logger.debug(f"Wait action created: {seconds} seconds")


class Experiment:
    def __init__(self):
        self.actions: list[Action | WaitAction] = []
        self.current_time: Optional[datetime] = None
        logger.debug("Experiment created")

    def add_action(self, func: Callable, *args: Any, **kwargs: Any):
        self._validate_types(func, *args, **kwargs)
        self.actions.append(Action(func, *args, **kwargs))
        logger.debug(f"Action added to experiment: {func.__name__}")

    def add_wait(self, seconds: float):
        self.actions.append(WaitAction(seconds))
        logger.debug(f"Wait action added to experiment: {seconds} seconds")

    def run(self):
        self.current_time = datetime.now()
        logger.debug(f"Experiment started. Start time: {self.current_time}")
        for step, action in enumerate(self.actions):
            logger.debug(f"Step {step + 1} from {len(self.actions)}")
            if isinstance(action, Action):
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

    def _validate_types(self, func: Callable, *args: Any, **kwargs: Any):
        type_hints = get_type_hints(func)
        sig = inspect.signature(func)
        bound_arguments = sig.bind_partial(*args, **kwargs).arguments

        for name, value in bound_arguments.items():
            expected_type = type_hints.get(name)
            if expected_type and not isinstance(value, expected_type):
                raise TypeError(f"Argument '{name}' is expected to be of type {expected_type}, but got {type(value)}")


# pump1 = Pump("COM1")
# pump2 = Pump("COM2")
# spectrophotometer = Spectrophotometer("COM3")

# experiment = Experiment()
# experiment.add_action(pump1.pour_in_volume, 10.0, 1.0, "left")
# experiment.add_wait(5.0)
# experiment.add_action(pump2.pour_in_volume, 5.0, 0.5, "right")
# experiment.add_wait(5.0)
# experiment.add_action(spectrophotometer.measure_absorbance)

# experiment.run()
