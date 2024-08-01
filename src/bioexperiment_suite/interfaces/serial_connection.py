# from functools import wraps
from time import sleep

# from typing import Callable
# import serial
from bioexperiment_suite.loader import logger


class SerialConnection:
    """Class to handle serial communication with a device connected to a serial port."""

    def __init__(self, port: str, baudrate: int = 9600, timeout_sec: float = 1.0):
        """Initializes the serial connection object.

        :param port: The serial port to connect to
        :param baudrate: The baudrate of the serial connection. Defaults to 9600
        :param timeout_sec: The timeout of the serial connection to respond in seconds. Defaults to 1.0

        :raises serial.SerialException: If the serial connection cannot be established
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout_sec = timeout_sec
        self._create_serial_connection()

    def _create_serial_connection(self):
        """Creates a serial connection with the specified parameters."""
        # self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout_sec)
        logger.info(f"FAKE serial connection established with {self.port}")
        sleep(1)

        # @staticmethod
        # def _restore_connection(method: Callable) -> Callable:
        # """Decorator to restore the serial connection if it is lost during communication.

        # :param method: The method to decorate

        # :returns: The decorated method
        # """

        # @wraps(method)
        # def wrapper(self, *args, **kwargs):
        #     try:
        #         return method(self, *args, **kwargs)
        #     except serial.SerialException:
        #         logger.warning(f"Serial connection lost on port {self.port}. Restoring connection...")
        #         self._create_serial_connection()
        #         return method(self, *args, **kwargs)

        # return wrapper

    # @_restore_connection
    def write_to_serial_port(self, data_to_send: list[int]) -> None:
        """Writes data to the serial port.

        :param data_to_send: The data to send to the serial port
        """
        # bytes_to_send = bytes(data_to_send)
        # self.serial.write(bytes_to_send)
        logger.debug(f"Data sent to FAKE serial port: {data_to_send}")

    # @_restore_connection
    def read_from_serial_port(self, response_bytes: int) -> bytes:
        """Reads data from the serial port.

        :param response_bytes: The number of bytes to read from the serial port

        :returns: The response from the serial port
        """
        # response = self.serial.read(response_bytes)
        response = bytes([0x00] * response_bytes)
        logger.debug(f"Data received from serial port: {list(response)}")
        return response

    def communicate_with_serial_port(self, data_to_send: list[int], response_bytes: int) -> bytes:
        """Communicates with the serial port by sending data and receiving a response.

        :param data_to_send: The data to send to the serial port
        :param response_bytes: The number of bytes to read from the serial port as a response

        :returns: The response from the serial port
        """
        self.write_to_serial_port(data_to_send)
        response = self.read_from_serial_port(response_bytes)
        return response

    def _bytes_to_int(self, bytes_: bytes) -> int:
        """Converts a byte array to an integer.

        :param bytes_: The byte array to convert to an integer

        :returns: The integer representation of the byte array
        """
        return int.from_bytes(bytes_, byteorder="big")

    def _int_to_bytes(self, integer: int, n_bytes: int | None = None) -> list[int]:
        """Converts an integer to a byte array.

        :param integer: The integer to convert to a byte array
        :param n_bytes: The number of bytes to represent the integer. Defaults to None.

        :returns: The byte array representation of the integer
        """
        if n_bytes is None:
            n_bytes = (integer.bit_length() + 7) // 8

        byte_representation = integer.to_bytes(n_bytes, byteorder="big")
        return list(byte_representation)

    def __del__(self):
        """Closes the serial connection when the object is deleted."""
        logger.debug(f"Closing FAKE serial connection with {self.port}")
        # self.serial.close()
