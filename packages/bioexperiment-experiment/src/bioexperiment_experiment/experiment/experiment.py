from __future__ import annotations

import asyncio
import inspect
import json
import os
import time
from collections import defaultdict
from datetime import datetime
from threading import Event, Thread
from typing import Any, Callable, get_type_hints

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    websockets = None
    WebSocketServerProtocol = None

from bioexperiment_experiment.loader import logger

from .actions import Action, WaitAction, Measurement
from .collections import Statistic, RelationFunction


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

    def __init__(self, output_dir: os.PathLike | None = None, output_socket_port: int | None = None):
        """Initialize the experiment with an empty list of actions and measurements"""
        self.actions: list[Action | WaitAction | ConditionalAction] = []
        self.measurements: dict[str, list[tuple[datetime, Any]]] = defaultdict(list)
        self.current_time: datetime | None = (
            None  # Time to keep track of the experiment progress. Initializes on start.
        )
        self.output_dir = output_dir
        self.output_socket_port = output_socket_port
        self._thread: Thread | None = None
        self._stop_event = Event()
        self._websocket_clients: set[WebSocketServerProtocol] = set()
        self._websocket_server = None
        self._websocket_thread: Thread | None = None
        self._websocket_loop: asyncio.AbstractEventLoop | None = None
        logger.debug("Experiment created")

    def create_metric(self, measurement_name: str, statistic: Statistic | None = Statistic.LAST()) -> Metric:
        """Create a metric object to be used in the experiment for making dynamic decisions.

        :param measurement_name: The name of the measurement in the experiment to use for the metric calculation
        :param statistic: The statistic to apply to the measurement values

        :return: The metric object
        """
        return Metric(self, measurement_name, statistic)

    def specify_output_dir(self, output_dir: os.PathLike):
        """Specify the output directory to write measurements to CSV files.

        :param output_dir: The directory to write measurements to
        """
        self.output_dir = output_dir
        logger.debug(f"Output directory specified: {output_dir}")

    def specify_output_socket_port(self, port: int):
        """Specify the output socket port to stream measurements via websocket.

        :param port: The port number to use for the websocket server
        """
        self.output_socket_port = port
        logger.debug(f"Output socket port specified: {port}")

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
            self.write_measurements_to_socket(action.measurement_name)
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
        
        # Start websocket server if port is specified
        if self.output_socket_port is not None:
            self._websocket_thread = Thread(target=self._start_websocket_server, daemon=True)
            self._websocket_thread.start()
            # Give the websocket server a moment to start
            time.sleep(0.5)
        
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
        
        # Stop websocket server
        if self.output_socket_port is not None:
            self._stop_websocket_server()

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

    def write_measurements_to_socket(self, measurement_name: str):
        """Write all acquired measurements to a websocket.

        :param measurement_name: The name of the measurement to write to a websocket
        """
        if self.output_socket_port is None:
            return

        if not self._websocket_clients:
            return

        # Format measurements as requested: {measurement_name: [[timestamp, value], ...]}
        measurements_data = {
            measurement_name: [
                [int(timestamp.timestamp() * 1000), value]
                for timestamp, value in self.measurements[measurement_name]
            ]
        }
        
        message = json.dumps(measurements_data)
        
        # Send to all connected clients
        if self._websocket_loop is not None:
            asyncio.run_coroutine_threadsafe(
                self._broadcast_message(message),
                self._websocket_loop
            )
        
        logger.debug(f"Measurement '{measurement_name}' sent to {len(self._websocket_clients)} websocket clients")

    async def _broadcast_message(self, message: str):
        """Broadcast a message to all connected websocket clients.
        
        :param message: The message to broadcast
        """
        if self._websocket_clients:
            disconnected_clients = set()
            for client in self._websocket_clients:
                try:
                    await client.send(message)
                except Exception as e:
                    logger.warning(f"Failed to send message to client: {e}")
                    disconnected_clients.add(client)
            
            # Remove disconnected clients
            self._websocket_clients -= disconnected_clients

    async def _handle_websocket_client(self, websocket: WebSocketServerProtocol):
        """Handle a websocket client connection.
        
        :param websocket: The websocket connection
        """
        self._websocket_clients.add(websocket)
        logger.info(f"Websocket client connected. Total clients: {len(self._websocket_clients)}")
        
        try:
            # Send all current measurements to the new client
            all_measurements = {
                name: [
                    [timestamp.isoformat(), value]
                    for timestamp, value in measurements
                ]
                for name, measurements in self.measurements.items()
            }
            if all_measurements:
                await websocket.send(json.dumps(all_measurements))
            
            # Keep connection alive and handle incoming messages
            async for message in websocket:
                logger.debug(f"Received message from client: {message}")
        except Exception as e:
            logger.warning(f"Websocket client error: {e}")
        finally:
            self._websocket_clients.discard(websocket)
            logger.info(f"Websocket client disconnected. Total clients: {len(self._websocket_clients)}")

    def _start_websocket_server(self):
        """Start the websocket server in a separate event loop."""
        async def run_server():
            self._websocket_server = await websockets.serve(
                self._handle_websocket_client,
                "localhost",
                self.output_socket_port
            )
            logger.info(f"Websocket server started on port {self.output_socket_port}")
            if self._websocket_server is not None:
                await self._websocket_server.wait_closed()
            logger.info("Websocket server stopped")

        self._websocket_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._websocket_loop)
        self._websocket_loop.run_until_complete(run_server())

    def _stop_websocket_server(self):
        """Stop the websocket server."""
        if self._websocket_server is not None and self._websocket_loop is not None:
            asyncio.run_coroutine_threadsafe(
                self._websocket_server.close(),
                self._websocket_loop
            )
            self._websocket_loop.call_soon_threadsafe(self._websocket_loop.stop)
            if self._websocket_thread is not None:
                self._websocket_thread.join(timeout=5)
            self._websocket_thread = None
            self._websocket_loop = None
            self._websocket_server = None
            logger.debug("Websocket server stopped")

    def reset_experiment(self):
        """Reset the experiment by clearing the actions, measurements and current time."""
        logger.debug("Experiment reset")
        if self._thread is not None:
            logger.warning("Experiment is running. Stop it before resetting.")
            return

        # Stop websocket server if running
        if self.output_socket_port is not None:
            self._stop_websocket_server()

        self.actions.clear()
        self.measurements.clear()
        self.current_time = None
        self._websocket_clients.clear()

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
