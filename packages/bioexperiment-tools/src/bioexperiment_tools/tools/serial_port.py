import glob
import sys

import serial

from bioexperiment_tools.loader import logger
from bioexperiment_tools.settings import get_settings


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
        raise OSError("Unsupported platform")

    if get_settings().EMULATE_DEVICES:
        logger.info("Emulating devices")
        pumps_port_numbers = [i * 2 for i in range(get_settings().N_VIRTUAL_PUMPS)]
        spectrophotometers_port_numbers = [i * 2 + 1 for i in range(get_settings().N_VIRTUAL_SPECTROPHOTOMETERS)]
        result = [f"COM{i}" for i in sorted(pumps_port_numbers + spectrophotometers_port_numbers)]
        logger.debug(f"Fake serial ports found: {result}")
        return result

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass

    return result
