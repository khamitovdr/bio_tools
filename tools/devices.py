from typing import Optional

from loguru import logger

from interfaces import Pump, SerialConnection, Spectrophotometer
from loader import device_interfaces
from tools.serial_port import get_serial_ports


def identify_device(port: str) -> Optional[str]:
    """Identifies the device connected to the specified serial port

    :param port: The serial port name to identify the device connected to

    :returns: The device name of the device connected to the specified serial port, None otherwise
    """
    serial_connection = SerialConnection(port)
    for device_name, device_interface in device_interfaces.items():
        logger.debug(f'Checking for device "{device_interface.type}" on port {port}')
        logger.debug(f"Identification signal: {device_interface.identification_signal}")
        response = serial_connection.communicate_with_serial_port(
            device_interface.identification_signal, device_interface.identification_response_len
        )

        if len(response) == device_interface.identification_response_len and list(response)[0] == int(
            device_interface.first_identification_response_byte
        ):
            logger.success(f'Device "{device_interface.type}" identified on port {port}')
            return device_name

    logger.warning(f"No device identified on port {port}")
    return None


def get_connected_devices() -> tuple[list[Pump], list[Spectrophotometer]]:
    """Identifies the devices connected to the serial ports on the system

    :returns: A tuple containing the list of connected pumps and spectrophotometers
    """
    serial_ports = get_serial_ports()
    pump_list = []
    spectrophotometer_list = []
    for port in serial_ports:
        device = identify_device(port)

        match device:
            case "pump":
                pump = Pump(port)
                pump_list.append(pump)
            case "spectrophotometer":
                spectrophotometer = Spectrophotometer(port)
                spectrophotometer_list.append(spectrophotometer)

    return pump_list, spectrophotometer_list
