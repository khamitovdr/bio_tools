import glob
import json
import sys
from functools import wraps
from time import sleep
from typing import Callable, Optional

import serial

DEVICE_INTERFACES_PATH = "./device_interfaces.json"
with open(DEVICE_INTERFACES_PATH, "r") as file:
    DEVICE_INTERFACES = json.load(file)


def get_serial_ports() -> list[str]:
    """Lists serial port names on the system

    :returns: A list of the serial ports available on the system
    :raises EnvironmentError: On unsupported or unknown platforms
    """
    if sys.platform.startswith("win"):
        ports = [f"COM{i + 1}" for i in range(256)]
    elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):
        # this excludes your current terminal "/dev/tty"
        ports = glob.glob("/dev/tty[A-Za-z]*")
    elif sys.platform.startswith("darwin"):
        ports = glob.glob("/dev/tty.*")
    else:
        raise EnvironmentError("Unsupported platform")

    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass

    return result


class SerialConnection:
    """Class to handle serial communication with a device connected to a serial port


    :param port: The serial port name to connect to
    :param baudrate: The baudrate of the serial connection
    :param timeout_sec: The timeout for the serial connection in seconds

    :raises serial.SerialException: If the serial connection cannot be established
    """

    def __init__(self, port: str, baudrate: int = 9600, timeout_sec: float = 1.0):
        self.port = port
        self.baudrate = baudrate
        self.timeout_sec = timeout_sec
        self.create_serial_connection()

    def create_serial_connection(self):
        """Creates a serial connection with the specified parameters"""
        self.serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout_sec)
        sleep(3)

    @staticmethod
    def _restore_connection(method: Callable) -> Callable:
        """Decorator to restore the serial connection if it is lost during communication"""

        @wraps(method)
        def wrapper(self, *args, **kwargs):
            try:
                return method(self, *args, **kwargs)
            except serial.SerialException:
                print("Serial connection lost. Restoring connection...")
                self.create_serial_connection()
                return method(self, *args, **kwargs)

        return wrapper

    @_restore_connection
    def write_to_serial_port(self, data_to_send: list[int]) -> None:
        """Writes data to the serial port

        :param data_to_send: The data to send to the serial port
        """
        bytes_to_send = bytes(data_to_send)
        self.serial.write(bytes_to_send)
        print("Bytes sent successfully.")

    @_restore_connection
    def read_from_serial_port(self, response_bytes: int) -> bytes:
        """Reads data from the serial port

        :param response_bytes: The number of bytes to read from the serial port

        :returns: The response from the serial port
        """
        response = self.serial.read(response_bytes)
        return response

    def communicate_with_serial_port(self, data_to_send: list[int], response_bytes: int) -> bytes:
        """Communicates with the serial port by sending data and receiving a response

        :param data_to_send: The data to send to the serial port
        :param response_bytes: The number of bytes to read from the serial port as a response

        :returns: The response from the serial port
        """
        self.write_to_serial_port(data_to_send)
        response = self.read_from_serial_port(response_bytes)
        return response

    def __del__(self):
        self.serial.close()


def identify_device(port: str) -> Optional[SerialConnection]:
    """Identifies the device connected to the specified serial port

    :param port: The serial port name to identify the device connected to

    :returns: The device interface of the device connected to the specified serial port, None otherwise
    """
    RESPONSE_LENGTH = 4
    serial_connection = SerialConnection(port)
    for device_interface in DEVICE_INTERFACES:
        identification_sequence = [int(i) for i in device_interface["identification_signal"]]
        print(f"Identifying device interface: {device_interface['type']}")
        print(f"Identification sequence: {identification_sequence}")
        response = serial_connection.communicate_with_serial_port(identification_sequence, RESPONSE_LENGTH)
        print(f"Response received: {response!r}")
        print(f"Response received: {list(response)}")

        if len(response) == RESPONSE_LENGTH and list(response)[0] == int(
            device_interface["first_identification_response_byte"]
        ):
            print(f"Device interface found: {device_interface['type']}")
            return serial_connection

    return None
