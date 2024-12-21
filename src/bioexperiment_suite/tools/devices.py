from bioexperiment_suite.interfaces import Pump, SerialConnection, Spectrophotometer
from bioexperiment_suite.loader import device_interfaces, logger
from bioexperiment_suite.tools.serial_port import get_serial_ports
from bioexperiment_suite.settings import settings


def identify_device(port: str) -> str | None:
    """Identifies the device connected to the specified serial port.

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
    """Identifies the devices connected to the serial ports on the system.

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


if settings.EMULATE_DEVICES:
    # Overwrite the function if EMULATE_DEVICES is True
    def identify_device(port: str) -> str | None:
        """Identifies the device connected to the specified serial port.

        :param port: The serial port name to identify the device connected to

        :returns: The device name of the device connected to the specified serial port, None otherwise
        """
        device_names = ["pump", "spectrophotometer"]
        port_number = int(port[-1])
        return device_names[port_number % 2]
    
    def get_connected_devices(n_pumps_n_spectrophotometers: tuple[int, int]) -> tuple[list[Pump], list[Spectrophotometer]]:
        """\"Identifies\" the EMULATED devices connected to the FAKE serial ports on the system.

        :param n_pumps_n_spectrophotometers: A tuple containing the number of FAKE pumps and spectrophotometers to find

        :returns: A tuple containing the list of connected pumps and spectrophotometers
        """
        serial_ports = get_serial_ports(n_pumps_n_spectrophotometers)
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
