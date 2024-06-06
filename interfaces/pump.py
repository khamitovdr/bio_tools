from loguru import logger

from interfaces.serial_connection import SerialConnection
from loader import device_interfaces


class Pump(SerialConnection):
    """Class to handle communication with a pump connected to a serial port"""

    def __init__(self, port: str, baudrate: int = 9600, timeout_sec: float = 1.0):
        self.interface = device_interfaces.pump
        super(Pump, self).__init__(port, baudrate, timeout_sec)
        self._compute_calibration_volume()

    def _compute_calibration_volume(self):
        identification_response = self.communicate_with_serial_port(
            self.interface.identification_signal,
            self.interface.identification_response_len,
        )
        self._calibration_volume = self._bytes_to_int(identification_response[1:]) / 10**5
        logger.debug(f"Calibration volume computed: {self._calibration_volume:.3f}")

    def _compute_speed_param_from_flow(self, flow: float) -> int:
        """Computes the speed parameter from the real speed of the pump

        :param flow: The real flow rate of the pump in mL/min

        :returns: The speed parameter to send to the pump
        """

        speed_param = int(29 / flow)
        return speed_param

    def _compute_step_volume_bytes(self, volume: float) -> list[int]:
        """Computes the step volume in bytes to send to the pump

        :param volume: The volume to set in mL

        :returns: The byte representation of the volume
        """
        step_volume = int((volume * 10**4) / self._calibration_volume)
        step_volume_bytes = self._int_to_bytes(step_volume, 4)
        return step_volume_bytes

    def _set_flow_rate(self, flow_rate: float):
        """Sets the flow rate of the pump

        :param flow_rate: The flow rate to set in mL/min
        """
        logger.debug(f"Setting flow rate to {flow_rate:.3f} mL/min")
        speed_param = self._compute_speed_param_from_flow(flow_rate)
        data_to_send = [10, 0, 1, speed_param, 0]
        self.write_to_serial_port(data_to_send)

    def pour_in_volume(self, volume: float, flow_rate: float, direction: str = "left"):
        """Pours in the specified volume of liquid

        :param volume: The volume to pour in mL
        :param flow_rate: The flow rate of the pump in mL/min
        :param direction: The direction of the pump, either "left" or "right". Defaults to "left"
        """

        assert direction in ["left", "right"], "Invalid direction. Must be either 'left' or 'right'"
        direction_byte = 16 if direction == "left" else 17

        logger.debug(f"Pouring in {volume:.3f} mL at flow rate {flow_rate:.3f} mL/min")

        self._set_flow_rate(flow_rate)

        data_to_send = [direction_byte] + self._compute_step_volume_bytes(volume)
        self.write_to_serial_port(data_to_send)

    def start_continuous_rotation(self, flow_rate: float, direction: str = "left"):
        """Starts the continuous rotation of the pump

        :param flow_rate: The flow rate of the pump in mL/min
        :param direction: The direction of the pump, either "left" or "right". Defaults to "left"
        """

        assert direction in ["left", "right"], "Invalid direction. Must be either 'left' or 'right'"
        direction_byte = 11 if direction == "left" else 12

        logger.debug(f"Starting continuous rotation at flow rate {flow_rate:.3f} mL/min")

        speed_param = self._compute_speed_param_from_flow(flow_rate)

        data_to_send = [direction_byte, 111, 1, speed_param, 0]
        self.write_to_serial_port(data_to_send)

    def stop_continuous_rotation(self):
        """Stops the continuous rotation of the pump"""
        logger.debug("Stopping continuous rotation")
        self.pour_in_volume(0, 1)
