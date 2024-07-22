from time import sleep

from loguru import logger

from interfaces.serial_connection import SerialConnection
from loader import device_interfaces


class Spectrophotometer(SerialConnection):
    """Class to handle communication with a spectrophotometer connected to a serial port."""

    def __init__(self, port: str, baudrate: int = 9600, timeout_sec: int | float = 1.0):
        """Initializes the spectrophotometer object.

        :param port: The serial port to connect to
        :param baudrate: The baudrate of the serial connection. Defaults to 9600
        :param timeout_sec: The timeout of the serial connection to respond in seconds. Defaults to 1.0
        """
        self.interface = device_interfaces.spectrophotometer
        super(Spectrophotometer, self).__init__(port, baudrate, timeout_sec)

    def get_temperature(self) -> float:
        """Gets the temperature of the spectrophotometer

        :returns: The temperature in degrees Celsius
        """
        logger.debug("Getting temperature")
        temperature_response = self.communicate_with_serial_port(
            self.interface.commands.get_temperature.request,
            self.interface.commands.get_temperature.response_len,
        )
        logger.debug(f"Temperature response: {list(temperature_response)}")
        integer, fractional = temperature_response[2:]
        temperature = integer + (fractional / 100)
        return temperature

    def _send_start_measurement_command(self):
        """Sends the command to start the measurement."""
        self.write_to_serial_port(self.interface.commands.start_measurement.request)
        logger.debug("Start measurement command sent")

    def _get_absorbance(self) -> float | None:
        """Gets the absorbance of the sample.

        :returns: The absorbance of the sample
        """
        logger.debug("Getting absorbance")
        absorbance_response = self.communicate_with_serial_port(
            self.interface.commands.get_measurement_result.request,
            self.interface.commands.get_measurement_result.response_len,
        )
        logger.debug(f"Absorbance response: {list(absorbance_response)}")
        if not absorbance_response:
            return None
        integer, fractional = absorbance_response[2:]
        absorbance = integer + (fractional / 100)
        logger.debug(f"Absorbance: {absorbance}")
        return absorbance

    def measure_absorbance(self) -> float:
        """Measures the absorbance of the sample.

        :returns: The absorbance of the sample
        """
        logger.debug("Measuring absorbance")
        self._send_start_measurement_command()
        logger.debug("Absorbance not ready yet, waiting...")
        sleep(4)
        absorbance = self._get_absorbance()
        if absorbance is None:
            logger.error("Absorbance could not be measured")
            raise Exception("Absorbance could not be measured")

        return absorbance
