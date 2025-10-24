"""Mock serial implementations for comprehensive testing."""

import asyncio
from typing import Dict, List, Optional
from unittest.mock import AsyncMock

from bioexperiment_tools_async.core.types import PortName


class MockSerialDevice:
    """Mock serial device with realistic behavior."""
    
    def __init__(self, port: PortName, device_type: str):
        """Initialize mock serial device.
        
        Args:
            port: The port name this device is on
            device_type: Type of device ('pump' or 'spectrophotometer')
        """
        self.port = port
        self.device_type = device_type
        self.is_connected = False
        self.command_history: List[List[int]] = []
        
        # Device state
        self.pump_calibration_volume = 1.0
        self.spectro_temperature = 25.5
        self.spectro_optical_density = 1.234
    
    async def connect(self) -> None:
        """Simulate connection."""
        await asyncio.sleep(0.01)  # Small delay to simulate real connection
        self.is_connected = True
    
    async def disconnect(self) -> None:
        """Simulate disconnection."""
        self.is_connected = False
    
    async def write(self, data: List[int]) -> None:
        """Simulate writing data."""
        if not self.is_connected:
            raise ConnectionError("Device not connected")
        
        self.command_history.append(data)
        await asyncio.sleep(0.001)  # Simulate write delay
    
    async def read(self, num_bytes: int) -> bytes:
        """Simulate reading data with realistic responses."""
        if not self.is_connected:
            raise ConnectionError("Device not connected")
        
        await asyncio.sleep(0.005)  # Simulate read delay
        
        # Get the last command to determine appropriate response
        if not self.command_history:
            return bytes([0x00] * num_bytes)
        
        last_command = self.command_history[-1]
        return self._generate_response(last_command, num_bytes)
    
    def _generate_response(self, command: List[int], num_bytes: int) -> bytes:
        """Generate realistic response based on command."""
        if self.device_type == "pump":
            return self._generate_pump_response(command, num_bytes)
        elif self.device_type == "spectrophotometer":
            return self._generate_spectro_response(command, num_bytes)
        else:
            return bytes([0x00] * num_bytes)
    
    def _generate_pump_response(self, command: List[int], num_bytes: int) -> bytes:
        """Generate pump-specific responses."""
        # Pump identification command: [1, 2, 3, 4, 181]
        if len(command) >= 5 and command[:5] == [1, 2, 3, 4, 181]:
            # Return identification response with calibration data
            calibration_bytes = int(self.pump_calibration_volume * 10**5).to_bytes(3, 'big')
            return bytes([10] + list(calibration_bytes))
        
        # Other pump commands typically don't return responses
        return bytes([0x00] * num_bytes) if num_bytes > 0 else b""
    
    def _generate_spectro_response(self, command: List[int], num_bytes: int) -> bytes:
        """Generate spectrophotometer-specific responses."""
        # Spectrophotometer identification command: [1, 2, 3, 4, 0]
        if len(command) >= 5 and command[:5] == [1, 2, 3, 4, 0]:
            return bytes([70, 0x01, 0x02, 0x03])
        
        # Temperature request: [76, 0, 0, 0, 0]
        elif len(command) >= 5 and command[:5] == [76, 0, 0, 0, 0]:
            temp_int = int(self.spectro_temperature)
            temp_frac = int((self.spectro_temperature - temp_int) * 100)
            return bytes([0x01, 0x02, temp_int, temp_frac])
        
        # Optical density result request: [79, 4, 0, 0, 0]
        elif len(command) >= 5 and command[:5] == [79, 4, 0, 0, 0]:
            od_int = int(self.spectro_optical_density)
            od_frac = int((self.spectro_optical_density - od_int) * 100)
            return bytes([0x01, 0x02, od_int, od_frac])
        
        # Other commands return generic response
        return bytes([0x00] * num_bytes) if num_bytes > 0 else b""


class MockSerialRegistry:
    """Registry of mock serial devices for testing."""
    
    def __init__(self):
        """Initialize the mock serial registry."""
        self.devices: Dict[PortName, MockSerialDevice] = {}
        self.setup_default_devices()
    
    def setup_default_devices(self) -> None:
        """Set up default test devices."""
        # Add some pumps
        self.add_device("COM0", "pump")
        self.add_device("COM2", "pump")
        self.add_device("/dev/ttyUSB0", "pump")
        
        # Add some spectrophotometers
        self.add_device("COM1", "spectrophotometer")
        self.add_device("COM3", "spectrophotometer")
        self.add_device("/dev/ttyUSB1", "spectrophotometer")
        
        # Add some non-device ports (no response)
        self.add_device("COM4", "unknown")
        self.add_device("/dev/ttyUSB2", "unknown")
    
    def add_device(self, port: PortName, device_type: str) -> None:
        """Add a mock device to the registry."""
        self.devices[port] = MockSerialDevice(port, device_type)
    
    def remove_device(self, port: PortName) -> None:
        """Remove a device from the registry."""
        if port in self.devices:
            del self.devices[port]
    
    def get_device(self, port: PortName) -> Optional[MockSerialDevice]:
        """Get a mock device by port name."""
        return self.devices.get(port)
    
    def get_available_ports(self) -> List[PortName]:
        """Get list of available ports."""
        return list(self.devices.keys())
    
    def clear(self) -> None:
        """Clear all devices."""
        self.devices.clear()


# Global registry instance for tests
mock_serial_registry = MockSerialRegistry()
