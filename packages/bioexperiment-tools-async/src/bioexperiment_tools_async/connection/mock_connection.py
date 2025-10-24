"""Mock connection implementation for testing and device emulation."""

import asyncio
from typing import Any

from loguru import logger

from ..core.config import get_config
from ..core.exceptions import DeviceConnectionError, DeviceCommunicationError
from ..core.protocols import AsyncConnection
from ..core.types import PortName


class MockConnection:
    """Mock connection for testing and device emulation."""
    
    def __init__(self, port: PortName) -> None:
        """Initialize the mock connection.
        
        Args:
            port: The port name to simulate
        """
        self._port = port
        self._is_connected = False
        self._connection_delay = 0.1  # Simulate connection time
        self._response_delay = 0.05   # Simulate communication delay
        
        # Determine device type from port for realistic responses
        self._device_type = self._determine_device_type(port)
        
        logger.debug(f"Created MockConnection for port {port} (type: {self._device_type})")
    
    @property
    def port(self) -> PortName:
        """The port name this connection is bound to."""
        return self._port
    
    @property
    def is_connected(self) -> bool:
        """Whether the connection is currently active."""
        return self._is_connected
    
    def _determine_device_type(self, port: str) -> str:
        """Determine device type from port name for emulation."""
        config = get_config()
        
        if not config.emulate_devices:
            return "unknown"
        
        # For emulated devices, use port number to determine type
        try:
            if "COM" in port:
                port_num = int(port.replace("COM", ""))
                return "pump" if port_num % 2 == 0 else "spectrophotometer"
            else:
                # Unix-style port names
                return "pump" if port.endswith("0") or port.endswith("2") else "spectrophotometer"
        except (ValueError, AttributeError):
            return "pump"  # Default to pump
    
    async def connect(self) -> None:
        """Simulate establishing a connection."""
        if self._is_connected:
            logger.debug(f"Already connected to mock {self._port}")
            return
        
        logger.debug(f"Connecting to mock {self._port}")
        await asyncio.sleep(self._connection_delay)
        self._is_connected = True
        logger.info(f"Connected to mock {self._port}")
    
    async def disconnect(self) -> None:
        """Simulate closing the connection."""
        if not self._is_connected:
            logger.debug(f"Already disconnected from mock {self._port}")
            return
        
        self._is_connected = False
        logger.info(f"Disconnected from mock {self._port}")
    
    async def write(self, data: list[int]) -> None:
        """Simulate writing data."""
        if not self._is_connected:
            raise DeviceConnectionError(
                f"Cannot write to disconnected mock port {self._port}",
                context={"port": self._port},
            )
        
        logger.debug(f"Mock write to {self._port}: {data}")
        await asyncio.sleep(self._response_delay / 2)
    
    async def read(self, num_bytes: int) -> bytes:
        """Simulate reading data with realistic device responses."""
        if not self._is_connected:
            raise DeviceConnectionError(
                f"Cannot read from disconnected mock port {self._port}",
                context={"port": self._port},
            )
        
        await asyncio.sleep(self._response_delay)
        
        # Generate realistic mock responses based on device type and request size
        mock_data = self._generate_mock_response(num_bytes)
        
        logger.debug(f"Mock read from {self._port}: {list(mock_data)}")
        return mock_data
    
    def _generate_mock_response(self, num_bytes: int) -> bytes:
        """Generate realistic mock response based on device type."""
        if self._device_type == "pump":
            if num_bytes == 4:
                # Pump identification response: [10, a, b, c]
                return bytes([10, 0x01, 0x02, 0x03])
            else:
                # Generic pump response
                return bytes([0x00] * num_bytes)
        
        elif self._device_type == "spectrophotometer":
            if num_bytes == 4:
                # Could be identification or measurement response
                # Identification: [70, a, b, c]
                # Temperature: [a1, a2, temp_int, temp_frac]
                # Optical density: [a1, a2, od_int, od_frac]
                return bytes([70, 0x01, 25, 50])  # 25.50°C or similar
            else:
                # Generic spectrophotometer response  
                return bytes([0x00] * num_bytes)
        
        else:
            # Unknown device type
            return bytes([0x00] * num_bytes)
    
    async def communicate(self, data: list[int], response_bytes: int) -> bytes:
        """Send data and read response in one operation."""
        await self.write(data)
        return await self.read(response_bytes)
    
    async def __aenter__(self) -> "MockConnection":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
