"""Async spectrophotometer implementation with measurement workflows."""

import asyncio

from loguru import logger

from bioexperiment_tools_async.core.exceptions import DeviceOperationError
from bioexperiment_tools_async.core.types import (
    DeviceType,
    OpticalDensity,
    PortName,
    Temperature,
)
from bioexperiment_tools_async.protocol.device_protocol import (
    SpectrophotometerProtocol,
)

from .base import AsyncBaseDevice


class AsyncSpectrophotometer(AsyncBaseDevice):
    """Async spectrophotometer device implementation."""

    def __init__(self, port: PortName) -> None:
        """Initialize the async spectrophotometer.

        Args:
            port: The serial port name to connect to
        """
        super().__init__(port)
        self._protocol: SpectrophotometerProtocol | None = None
        self._default_measurement_timeout = 30.0  # Default timeout for measurements

        logger.debug(f"Created AsyncSpectrophotometer for port {port}")

    @property
    def device_type(self) -> DeviceType:
        """The type of this device."""
        return DeviceType.SPECTROPHOTOMETER

    async def _ensure_protocol(self) -> SpectrophotometerProtocol:
        """Ensure protocol is initialized and return it."""
        connection = await self._ensure_connected()

        if self._protocol is None:
            self._protocol = SpectrophotometerProtocol(connection)

        return self._protocol

    async def get_temperature(self) -> Temperature:
        """Get the current temperature.

        Returns:
            The temperature in degrees Celsius
        """

        async def _get_temperature() -> Temperature:
            protocol = await self._ensure_protocol()
            temperature = await protocol.get_temperature()

            logger.info(f"Temperature reading: {temperature:.2f}°C from {self.device_id}")
            return temperature

        return await self._execute_operation("get_temperature", _get_temperature)

    async def measure_optical_density(self, *, timeout: float | None = None) -> OpticalDensity:
        """Measure optical density.

        Args:
            timeout: Optional timeout for the measurement operation

        Returns:
            The optical density value
        """

        async def _measure_optical_density() -> OpticalDensity:
            protocol = await self._ensure_protocol()
            measurement_timeout = timeout or self._default_measurement_timeout

            logger.info(f"Starting optical density measurement on {self.device_id}")

            try:
                optical_density = await asyncio.wait_for(
                    protocol.measure_optical_density(),
                    timeout=measurement_timeout,
                )

                logger.info(f"Optical density measurement: {optical_density:.5f} from {self.device_id}")
                return optical_density

            except TimeoutError:
                logger.error(f"Optical density measurement timed out after {measurement_timeout}s")
                raise DeviceOperationError(
                    f"Optical density measurement timed out after {measurement_timeout}s",
                    device_id=self.device_id,
                    operation="measure_optical_density",
                    context={"timeout": measurement_timeout},
                )

        return await self._execute_operation("measure_optical_density", _measure_optical_density)

    async def disconnect(self) -> None:
        """Disconnect from the spectrophotometer and clean up protocol."""
        self._protocol = None
        await super().disconnect()
