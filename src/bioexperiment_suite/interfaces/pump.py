from time import sleep

from bioexperiment_suite.loader import device_interfaces, logger
from bioexperiment_suite.settings import settings

from .serial_connection import SerialConnection


class Pump(SerialConnection):
    """Class to handle communication with a pump connected to a serial port."""

    def __init__(self, port: str, baudrate: int = 9600, timeout_sec: int | float = 1.0):
        """Initializes the pump object.

        :param port: The serial port to connect to
        :param baudrate: The baudrate of the serial connection. Defaults to 9600
        :param timeout_sec: The timeout of the serial connection to respond in seconds. Defaults to 1.0
        """
        self.interface = device_interfaces.pump
        self.default_flow_rate: int | float | None = None
        super(Pump, self).__init__(port, baudrate, timeout_sec)
        self._compute_calibration_volume()

    def _compute_calibration_volume(self) -> None:
        """Computes the calibration volume of the pump."""

        if settings.EMULATE_DEVICES:
            self._calibration_volume = 1.0
            logger.debug(f"FAKE calibration volume computed: {self._calibration_volume:.3f}")
            return

        identification_response = self.communicate_with_serial_port(
            self.interface.identification_signal,
            self.interface.identification_response_len,
        )
        self._calibration_volume = self._bytes_to_int(identification_response[1:]) / 10**5
        logger.debug(f"Calibration volume computed: {self._calibration_volume:.3f}")

    def _compute_speed_param_from_flow(self, flow: int | float) -> int:
        """Computes the speed parameter from the real speed of the pump.

        :param flow: The real flow rate of the pump in mL/min

        :returns: The speed parameter to send to the pump
        """

        speed_param = int(29 / flow)
        return speed_param

    def _compute_step_volume_bytes(self, volume: int | float) -> list[int]:
        """Computes the step volume in bytes to send to the pump.

        :param volume: The volume to set in mL

        :returns: The byte representation of the volume
        """
        step_volume = int((volume * 10**4) / self._calibration_volume)
        step_volume_bytes = self._int_to_bytes(step_volume, 4)
        return step_volume_bytes

    def set_default_flow_rate(self, flow_rate: int | float):
        """Sets the default flow rate of the pump.

        :param flow_rate: The flow rate to set in mL/min
        """
        self.default_flow_rate = flow_rate

    def _set_flow_rate(self, flow_rate: int | float):
        """Sets the flow rate of the pump before pouring in volume.

        :param flow_rate: The flow rate to set in mL/min
        """
        logger.debug(f"Setting flow rate to {flow_rate:.3f} mL/min")
        speed_param = self._compute_speed_param_from_flow(flow_rate)
        data_to_send = [10, 0, 1, speed_param, 0]
        self.write_to_serial_port(data_to_send)

    def pour_in_volume(
        self,
        volume: int | float,
        flow_rate: int | float | None = None,
        direction: str = "left",
        blocking_mode: bool = True,
    ):
        """Pours in the specified volume of liquid.

        :param volume: The volume to pour in mL
        :param flow_rate: The flow rate of the pump in mL/min
        :param direction: The direction of the pump, either "left" or "right". Defaults to "left"
        :param blocking_mode: Whether to wait for the pump to finish pouring in the volume. Defaults to True
        """

        assert direction in ["left", "right"], "Invalid direction. Must be either 'left' or 'right'"
        direction_byte = 16 if direction == "left" else 17

        if flow_rate is None and self.default_flow_rate is None:
            raise ValueError("Flow rate must be set before pouring in volume or passed as an argument")

        flow_rate = flow_rate or self.default_flow_rate
        self._set_flow_rate(flow_rate)  # type: ignore

        logger.debug(f"Pouring in {volume:.3f} mL at flow rate {flow_rate:.3f} mL/min")

        data_to_send = [direction_byte] + self._compute_step_volume_bytes(volume)
        self.write_to_serial_port(data_to_send)

        if blocking_mode:
            sleep_time = (volume / flow_rate) * 60
            sleep(sleep_time)

    def start_continuous_rotation(self, flow_rate: int | float | None = None, direction: str = "left"):
        """Starts the continuous rotation of the pump.

        :param flow_rate: The flow rate of the pump in mL/min
        :param direction: The direction of the pump, either "left" or "right". Defaults to "left"
        """

        assert direction in ["left", "right"], "Invalid direction. Must be either 'left' or 'right'"
        direction_byte = 11 if direction == "left" else 12

        if flow_rate is None and self.default_flow_rate is None:
            raise ValueError("Flow rate must be set before starting continuous rotation or passed as an argument")

        flow_rate = flow_rate or self.default_flow_rate

        logger.debug(f"Starting continuous rotation at flow rate {flow_rate:.3f} mL/min")
        speed_param = self._compute_speed_param_from_flow(flow_rate)  # type: ignore

        data_to_send = [direction_byte, 111, 1, speed_param, 0]
        self.write_to_serial_port(data_to_send)

    def stop_continuous_rotation(self):
        """Stops the continuous rotation of the pump"""
        logger.debug("Stopping continuous rotation")
        self.pour_in_volume(0)
