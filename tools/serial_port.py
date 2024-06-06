import glob
import sys

import serial
from loguru import logger


def get_serial_ports() -> list[str]:
    """Lists serial port names on the system

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

    logger.debug(f"Serial ports found: {result}")
    return result
