# from loguru import logger

from interfaces.serial_connection import SerialConnection
from loader import device_interfaces


class Spectrophotometer(SerialConnection):
    """Class to handle communication with a spectrophotometer connected to a serial port"""

    def __init__(self, port: str, baudrate: int = 9600, timeout_sec: float = 1.0):
        self.interface = device_interfaces.spectrophotometer
        super(Spectrophotometer, self).__init__(port, baudrate, timeout_sec)

    def spectrophotometer_read(self) -> float:
        raise NotImplementedError("Method not implemented")
