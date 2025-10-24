"""Async pump implementation with proper flow control and timing."""

import asyncio
from typing import Any

from loguru import logger

from ..core.exceptions import DeviceOperationError, InvalidDeviceParameterError
from ..core.types import DeviceType, Direction, FlowRate, PortName, Volume
from ..protocol.device_protocol import PumpProtocol
from .base import AsyncBaseDevice


class AsyncPump(AsyncBaseDevice):
    """Async pump device implementation."""
    
    def __init__(self, port: PortName) -> None:
        """Initialize the async pump.
        
        Args:
            port: The serial port name to connect to
        """
        super().__init__(port)
        self._protocol: PumpProtocol | None = None
        self._default_flow_rate: FlowRate | None = None
        self._unaccounted_time_sec = 1.0  # Buffer time for operations
        
        logger.debug(f"Created AsyncPump for port {port}")
    
    @property
    def device_type(self) -> DeviceType:
        """The type of this device."""
        return DeviceType.PUMP
    
    @property
    def default_flow_rate(self) -> FlowRate | None:
        """The default flow rate for this pump."""
        return self._default_flow_rate
    
    async def _ensure_protocol(self) -> PumpProtocol:
        """Ensure protocol is initialized and return it."""
        connection = await self._ensure_connected()
        
        if self._protocol is None:
            self._protocol = PumpProtocol(connection)
        
        return self._protocol
    
    def _validate_flow_rate(self, flow_rate: FlowRate | None) -> FlowRate:
        """Validate and return a flow rate, using default if needed."""
        if flow_rate is not None:
            if flow_rate <= 0:
                raise InvalidDeviceParameterError(
                    f"Flow rate must be positive, got {flow_rate}",
                    device_id=self.device_id,
                    context={"flow_rate": flow_rate},
                )
            return flow_rate
        
        if self._default_flow_rate is not None:
            return self._default_flow_rate
        
        raise InvalidDeviceParameterError(
            "No flow rate specified and no default flow rate set",
            device_id=self.device_id,
        )
    
    def _validate_volume(self, volume: Volume) -> None:
        """Validate volume parameter."""
        if volume < 0:
            raise InvalidDeviceParameterError(
                f"Volume must be non-negative, got {volume}",
                device_id=self.device_id,
                context={"volume": volume},
            )
    
    def _validate_direction(self, direction: Direction) -> None:
        """Validate direction parameter."""
        if not isinstance(direction, Direction):
            raise InvalidDeviceParameterError(
                f"Invalid direction: {direction}. Must be Direction.LEFT or Direction.RIGHT",
                device_id=self.device_id,
                context={"direction": direction},
            )
    
    async def set_default_flow_rate(self, flow_rate: FlowRate) -> None:
        """Set the default flow rate for this pump.
        
        Args:
            flow_rate: The flow rate in mL/min
        """
        async def _set_default_flow_rate() -> None:
            validated_flow_rate = self._validate_flow_rate(flow_rate)
            self._default_flow_rate = validated_flow_rate
            logger.info(f"Set default flow rate to {validated_flow_rate} mL/min for {self.device_id}")
        
        await self._execute_operation("set_default_flow_rate", _set_default_flow_rate)
    
    async def pour_volume(
        self,
        volume: Volume,
        *,
        flow_rate: FlowRate | None = None,
        direction: Direction = Direction.LEFT,
        timeout: float | None = None,
    ) -> None:
        """Pour a specific volume.
        
        Args:
            volume: The volume to pour in mL
            flow_rate: The flow rate in mL/min (uses default if not specified)
            direction: The pump direction (left or right)
            timeout: Optional timeout for the operation
        """
        async def _pour_volume() -> None:
            self._validate_volume(volume)
            self._validate_direction(direction)
            validated_flow_rate = self._validate_flow_rate(flow_rate)
            
            protocol = await self._ensure_protocol()
            
            # Set flow rate first
            await protocol.set_flow_rate(validated_flow_rate)
            
            # Calculate expected duration
            expected_duration = (volume / validated_flow_rate) * 60 + self._unaccounted_time_sec
            
            # Apply timeout if specified
            operation_timeout = timeout if timeout is not None else expected_duration * 2
            
            logger.info(f"Pouring {volume} mL at {validated_flow_rate} mL/min in direction {direction.value}")
            
            # Start the pour operation
            await protocol.pour_volume(volume, direction)
            
            # Wait for completion if volume > 0 (blocking mode)
            if volume > 0:
                try:
                    await asyncio.wait_for(
                        asyncio.sleep(expected_duration),
                        timeout=operation_timeout,
                    )
                    logger.info(f"Completed pouring {volume} mL")
                except asyncio.TimeoutError:
                    logger.warning(f"Pour operation timed out after {operation_timeout}s")
                    raise DeviceOperationError(
                        f"Pour operation timed out after {operation_timeout}s",
                        device_id=self.device_id,
                        operation="pour_volume",
                        context={
                            "volume": volume,
                            "flow_rate": validated_flow_rate,
                            "direction": direction.value,
                            "timeout": operation_timeout,
                        },
                    )
        
        await self._execute_operation("pour_volume", _pour_volume)
    
    async def start_continuous_rotation(
        self,
        *,
        flow_rate: FlowRate | None = None,
        direction: Direction = Direction.LEFT,
    ) -> None:
        """Start continuous pump rotation.
        
        Args:
            flow_rate: The flow rate in mL/min (uses default if not specified)
            direction: The pump direction (left or right)
        """
        async def _start_continuous_rotation() -> None:
            self._validate_direction(direction)
            validated_flow_rate = self._validate_flow_rate(flow_rate)
            
            protocol = await self._ensure_protocol()
            await protocol.start_continuous_rotation(validated_flow_rate, direction)
            
            logger.info(f"Started continuous rotation at {validated_flow_rate} mL/min in direction {direction.value}")
        
        await self._execute_operation("start_continuous_rotation", _start_continuous_rotation)
    
    async def stop_continuous_rotation(self) -> None:
        """Stop continuous pump rotation."""
        async def _stop_continuous_rotation() -> None:
            protocol = await self._ensure_protocol()
            await protocol.stop_rotation()
            
            logger.info(f"Stopped continuous rotation for {self.device_id}")
        
        await self._execute_operation("stop_continuous_rotation", _stop_continuous_rotation)
    
    async def disconnect(self) -> None:
        """Disconnect from the pump and clean up protocol."""
        self._protocol = None
        await super().disconnect()
