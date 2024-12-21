from random import random
from time import sleep

from bioexperiment_suite.loader import device_interfaces, logger
from bioexperiment_suite.settings import settings

from .serial_connection import SerialConnection


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

        if settings.EMULATE_DEVICES:
            logger.debug("Getting FAKE temperature")
            temperature = random() * 10 + 20
            logger.debug(f"FAKE temperature: {temperature:.2f}")
            return temperature

        logger.debug("Getting temperature")
        temperature_response = self.communicate_with_serial_port(
            self.interface.commands.get_temperature.request,
            self.interface.commands.get_temperature.response_len,
        )
        logger.debug(f"Temperature response: {list(temperature_response)}")
        integer, fractional = temperature_response[2:]
        temperature = integer + (fractional / 100)
        logger.debug(f"Temperature: {temperature:.2f}")
        return temperature

    def _send_start_measurement_command(self):
        """Sends the command to start the measurement."""
        self.write_to_serial_port(self.interface.commands.start_measurement.request)
        logger.debug("Start measurement command sent")

    def _get_optical_density(self) -> float | None:
        """Gets the optical density of the sample.

        :returns: The optical density of the sample
        """

        if settings.EMULATE_DEVICES:
            logger.debug("Getting FAKE optical density")
            optical_density = random()
            logger.debug(f"Fake optical density: {optical_density:.5f}")
            return optical_density

        optical_density_response = self.communicate_with_serial_port(
            self.interface.commands.get_measurement_result.request,
            self.interface.commands.get_measurement_result.response_len,
        )
        logger.debug(f"Optical density response: {list(optical_density_response)}")
        if not optical_density_response:
            return None
        integer, fractional = optical_density_response[2:]
        optical_density = integer + (fractional / 100)
        logger.debug(f"Optical density: {optical_density:.5f}")
        return optical_density

    def measure_optical_density(self) -> float:
        """Measures the optical density of the sample.

        :returns: The optical density of the sample
        """
        logger.debug("Measuring optical density")
        self._send_start_measurement_command()
        logger.debug("Optical density not ready yet, waiting...")
        sleep(4 if not settings.EMULATE_DEVICES else 1)
        optical_density = self._get_optical_density()
        if optical_density is None:
            logger.error("Optical density could not be measured")
            raise Exception("Optical density could not be measured")

        return optical_density
