"""Device communication protocols with validation and error recovery."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Generic, TypeVar

from loguru import logger

from ..core.config import get_config
from ..core.exceptions import DeviceCommunicationError
from ..core.protocols import AsyncConnection
from ..core.types import DeviceType, Direction, FlowRate, OpticalDensity, Temperature, Volume
from ..utils.serial_utils import bytes_to_int
from .commands import DeviceCommand, PumpCommand, SpectrophotometerCommand

T = TypeVar("T", bound=DeviceCommand)


class DeviceProtocol(ABC, Generic[T]):
    """Abstract base class for device communication protocols."""

    def __init__(self, connection: AsyncConnection, device_type: DeviceType) -> None:
        """Initialize the device protocol.

        Args:
            connection: The async connection to use for communication
            device_type: The type of device this protocol handles
        """
        self._connection = connection
        self._device_type = device_type
        self._config = self._load_device_config(device_type)

        logger.debug(f"Initialized {device_type.value} protocol for {connection.port}")

    @property
    def device_type(self) -> DeviceType:
        """The device type this protocol handles."""
        return self._device_type

    @property
    def connection(self) -> AsyncConnection:
        """The connection used by this protocol."""
        return self._connection

    def _load_device_config(self, device_type: DeviceType) -> dict[str, Any]:
        """Load device configuration from JSON file."""
        config_path = Path(__file__).parent.parent / "device_configs.json"

        try:
            with config_path.open() as f:
                configs = json.load(f)
                return configs[device_type.value]
        except (FileNotFoundError, KeyError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load config for {device_type.value}: {e}")
            raise DeviceCommunicationError(
                f"Failed to load device configuration for {device_type.value}",
                context={"device_type": device_type.value, "error": str(e)},
            )

    async def execute_command(self, command: T) -> bytes | None:
        """Execute a device command and return response if expected.

        Args:
            command: The command to execute

        Returns:
            Response bytes if command expects a response, None otherwise
        """
        logger.debug(f"Executing command: {command}")

        try:
            if command.response_length > 0:
                response = await self._connection.communicate(command.data, command.response_length)
                logger.debug(f"Command response: {list(response)}")
                return response
            else:
                await self._connection.write(command.data)
                logger.debug("Command executed (no response expected)")
                return None

        except Exception as e:
            raise DeviceCommunicationError(
                f"Failed to execute command: {command.description}",
                device_id=self._connection.port,
                context={"command_data": command.data},
                command=command.data,
            ) from e

    @abstractmethod
    async def identify_device(self) -> bool:
        """Identify if the connected device matches this protocol."""


class PumpProtocol(DeviceProtocol[PumpCommand]):
    """Protocol for pump device communication."""

    def __init__(self, connection: AsyncConnection) -> None:
        super().__init__(connection, DeviceType.PUMP)
        self._calibration_volume: float | None = None

    async def identify_device(self) -> bool:
        """Identify if the connected device is a pump."""
        try:
            command = PumpCommand.identification()
            response = await self.execute_command(command)

            if not response or len(response) != self._config["identification_response_len"]:
                return False

            expected_first_byte = self._config["first_identification_response_byte"]
            return response[0] == expected_first_byte

        except Exception as e:
            logger.debug(f"Pump identification failed: {e}")
            return False

    async def get_calibration_volume(self) -> float:
        """Get the pump calibration volume."""
        if self._calibration_volume is None:
            if get_config().emulate_devices:
                self._calibration_volume = 1.0
                logger.debug("Using mock calibration volume: 1.0")
            else:
                command = PumpCommand.identification()
                response = await self.execute_command(command)
                if response and len(response) >= 4:
                    self._calibration_volume = bytes_to_int(response[1:]) / 10**5
                    logger.debug(f"Calibration volume: {self._calibration_volume:.5f}")
                else:
                    raise DeviceCommunicationError(
                        "Failed to get pump calibration volume",
                        device_id=self._connection.port,
                    )

        return self._calibration_volume

    async def set_flow_rate(self, flow_rate: FlowRate) -> None:
        """Set the pump flow rate."""
        command = PumpCommand.set_flow_rate(flow_rate)
        await self.execute_command(command)

    async def pour_volume(self, volume: Volume, direction: Direction) -> None:
        """Pour a specific volume in the given direction."""
        calibration_volume = await self.get_calibration_volume()
        command = PumpCommand.pour_volume(volume, direction, calibration_volume)
        await self.execute_command(command)

    async def start_continuous_rotation(self, flow_rate: FlowRate, direction: Direction) -> None:
        """Start continuous pump rotation."""
        command = PumpCommand.start_continuous_rotation(flow_rate, direction)
        await self.execute_command(command)

    async def stop_rotation(self) -> None:
        """Stop pump rotation."""
        command = PumpCommand.stop_rotation()
        await self.execute_command(command)


class SpectrophotometerProtocol(DeviceProtocol[SpectrophotometerCommand]):
    """Protocol for spectrophotometer device communication."""

    def __init__(self, connection: AsyncConnection) -> None:
        super().__init__(connection, DeviceType.SPECTROPHOTOMETER)

    async def identify_device(self) -> bool:
        """Identify if the connected device is a spectrophotometer."""
        try:
            command = SpectrophotometerCommand.identification()
            response = await self.execute_command(command)

            if not response or len(response) != self._config["identification_response_len"]:
                return False

            expected_first_byte = self._config["first_identification_response_byte"]
            return response[0] == expected_first_byte

        except Exception as e:
            logger.debug(f"Spectrophotometer identification failed: {e}")
            return False

    async def get_temperature(self) -> Temperature:
        """Get the current temperature."""
        if get_config().emulate_devices:
            import random

            temperature = random.uniform(20.0, 30.0)
            logger.debug(f"Mock temperature: {temperature:.2f}°C")
            return temperature

        command = SpectrophotometerCommand.get_temperature()
        response = await self.execute_command(command)

        if not response or len(response) < 4:
            raise DeviceCommunicationError(
                "Invalid temperature response",
                device_id=self._connection.port,
                response=response,
            )

        integer_part, fractional_part = response[2], response[3]
        temperature = integer_part + (fractional_part / 100)
        logger.debug(f"Temperature: {temperature:.2f}°C")
        return temperature

    async def measure_optical_density(self, *, timeout: float | None = None) -> OpticalDensity:
        """Measure optical density."""
        if get_config().emulate_devices:
            import random

            optical_density = random.uniform(0.0, 2.0)
            logger.debug(f"Mock optical density: {optical_density:.5f}")
            return optical_density

        # Start measurement
        start_command = SpectrophotometerCommand.start_measurement()
        await self.execute_command(start_command)

        # Wait for measurement to complete (device-specific timing)
        import asyncio

        await asyncio.sleep(3.0)  # Standard measurement time

        # Get result
        result_command = SpectrophotometerCommand.get_measurement_result()
        response = await self.execute_command(result_command)

        if not response or len(response) < 4:
            raise DeviceCommunicationError(
                "Invalid optical density response",
                device_id=self._connection.port,
                response=response,
            )

        integer_part, fractional_part = response[2], response[3]
        optical_density = integer_part + (fractional_part / 100)
        logger.debug(f"Optical density: {optical_density:.5f}")
        return optical_density
