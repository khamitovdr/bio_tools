"""Abstract base device class with common async patterns."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger

from ..connection import MockConnection, SerialConnection
from ..core.config import get_config
from ..core.exceptions import DeviceConnectionError, DeviceOperationError
from ..core.protocols import AsyncConnection
from ..core.types import DeviceType, PortName


class AsyncBaseDevice(ABC):
    """Abstract base class for async device implementations."""
    
    def __init__(self, port: PortName) -> None:
        """Initialize the base device.
        
        Args:
            port: The serial port name to connect to
        """
        self._port = port
        self._device_id = self._generate_device_id(port)
        self._connection: AsyncConnection | None = None
        self._connection_lock = asyncio.Lock()
        self._operation_lock = asyncio.Lock()
        
        logger.debug(f"Initialized {self.__class__.__name__} for port {port}")
    
    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """The type of this device."""
        pass
    
    @property
    def port(self) -> PortName:
        """The port this device is connected to."""
        return self._port
    
    @property
    def device_id(self) -> str:
        """Unique identifier for this device."""
        return self._device_id
    
    @property
    def is_connected(self) -> bool:
        """Whether the device is currently connected."""
        return self._connection is not None and self._connection.is_connected
    
    def _generate_device_id(self, port: str) -> str:
        """Generate a unique device ID from the port name."""
        # Clean up port name for use as ID
        port_clean = port.replace("/dev/", "").replace("/", "_")
        return f"{self.device_type.value}_{port_clean}"
    
    def _create_connection(self) -> AsyncConnection:
        """Create the appropriate connection type based on configuration."""
        config = get_config()
        
        if config.emulate_devices:
            logger.debug(f"Creating mock connection for {self._port}")
            return MockConnection(self._port)
        else:
            logger.debug(f"Creating serial connection for {self._port}")
            return SerialConnection(self._port, config=config.connection)
    
    async def connect(self) -> None:
        """Connect to the device."""
        async with self._connection_lock:
            if self.is_connected:
                logger.debug(f"Device {self.device_id} already connected")
                return
            
            try:
                if self._connection is None:
                    self._connection = self._create_connection()
                
                await self._connection.connect()
                logger.info(f"Connected to device {self.device_id}")
                
            except Exception as e:
                self._connection = None
                raise DeviceConnectionError(
                    f"Failed to connect to device {self.device_id}",
                    device_id=self.device_id,
                    context={"port": self._port},
                ) from e
    
    async def disconnect(self) -> None:
        """Disconnect from the device."""
        async with self._connection_lock:
            if not self.is_connected or self._connection is None:
                logger.debug(f"Device {self.device_id} already disconnected")
                return
            
            try:
                await self._connection.disconnect()
                logger.info(f"Disconnected from device {self.device_id}")
                
            except Exception as e:
                logger.warning(f"Error during disconnect of {self.device_id}: {e}")
            finally:
                self._connection = None
    
    async def _ensure_connected(self) -> AsyncConnection:
        """Ensure device is connected and return the connection."""
        if not self.is_connected:
            await self.connect()
        
        if self._connection is None:
            raise DeviceConnectionError(
                f"Device {self.device_id} is not connected",
                device_id=self.device_id,
            )
        
        return self._connection
    
    async def _execute_operation(self, operation_name: str, operation_func, *args, **kwargs) -> Any:
        """Execute a device operation with proper error handling and locking.
        
        Args:
            operation_name: Name of the operation for logging/error reporting
            operation_func: The async function to execute
            *args: Arguments to pass to the operation function
            **kwargs: Keyword arguments to pass to the operation function
        
        Returns:
            Result of the operation function
        """
        async with self._operation_lock:
            try:
                logger.debug(f"Executing {operation_name} on {self.device_id}")
                result = await operation_func(*args, **kwargs)
                logger.debug(f"Completed {operation_name} on {self.device_id}")
                return result
                
            except Exception as e:
                logger.error(f"Failed to execute {operation_name} on {self.device_id}: {e}")
                
                if isinstance(e, (DeviceConnectionError, DeviceOperationError)):
                    raise
                
                raise DeviceOperationError(
                    f"Operation '{operation_name}' failed on device {self.device_id}",
                    device_id=self.device_id,
                    operation=operation_name,
                    context={"args": args, "kwargs": kwargs},
                ) from e
    
    async def __aenter__(self) -> "AsyncBaseDevice":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
