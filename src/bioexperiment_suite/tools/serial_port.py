import glob
import sys

import serial

from bioexperiment_suite.loader import logger
from bioexperiment_suite.settings import settings


def get_serial_ports() -> list[str]:
    """Lists serial port names on the system.

    :returns: A list of the serial ports available on the system

    :raises EnvironmentError: On unsupported or unknown platforms
    """
    if sys.platform.startswith("win"):
        logger.info("Windows platform detected")
        ports = [f"COM{i + 1}" for i in range(256)]
    elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):
        logger.info("Linux platform detected")
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob("/dev/tty[A-Za-z]*")
    elif sys.platform.startswith("darwin"):
        logger.info("MacOS platform detected")
        ports = glob.glob("/dev/tty.*")
    else:
        logger.error(f"Unsupported platform: {sys.platform}")
        raise EnvironmentError("Unsupported platform")

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass


if settings.EMULATE_DEVICES:
    # Overwrite the function if EMULATE_DEVICES is True
    def get_serial_ports(n_pumps_n_spectrophotometers: tuple[int, int]) -> list[str]:
        """Lists serial port names on the system.

        :param n_pumps_n_spectrophotometers: A tuple containing the number of pumps and spectrophotometers to find

        :returns: A list of the serial ports available on the system

        :raises EnvironmentError: On unsupported or unknown platforms
        """
        pumps_port_n, spectrophotometers_port_n = n_pumps_n_spectrophotometers
        pumps_port_numbers = [i * 2 for i in range(pumps_port_n)]
        spectrophotometers_port_numbers = [i * 2 + 1 for i in range(spectrophotometers_port_n)]
        result = [f"COM{i}" for i in sorted(pumps_port_numbers + spectrophotometers_port_numbers)]
        logger.debug(f"Fake serial ports found: {result}")
        return result
