"""Device registry for managing connected devices."""

import asyncio
from typing import ClassVar, Literal, Union

from bioexperiment_tools import Pump, Spectrophotometer, get_connected_devices
from loguru import logger

from .models import Device, DeviceType


DeviceInstance = Union[Pump, Spectrophotometer]
DeviceTypeStr = Literal["pump", "spectrophotometer"]


class DeviceRegistry:
    """Singleton registry for managing connected devices."""
    
    _instance: ClassVar["DeviceRegistry | None"] = None
    
    def __new__(cls) -> "DeviceRegistry":
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self) -> None:
        """Initialize the registry."""
        self._devices: dict[str, tuple[DeviceTypeStr, DeviceInstance]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._initialized = False
    
    def _device_id_from_port(self, port: str) -> str:
        """Generate a stable device ID from port."""
        # Sanitize port path to create a stable ID
        return port.replace("/", "_").replace("\\", "_").replace(":", "_")
    
    async def scan(self) -> dict[str, list[str]]:
        """Scan for connected devices and update registry.
        
        Returns:
            Dictionary with 'added' and 'removed' device IDs
        """
        logger.info("Scanning for connected devices...")
        
        try:
            # Get current devices from hardware
            pumps, spectrophotometers = get_connected_devices()
            
            # Create mapping of new devices
            new_devices: dict[str, tuple[DeviceTypeStr, DeviceInstance]] = {}
            
            # Add pumps
            for pump in pumps:
                device_id = self._device_id_from_port(pump.port)
                new_devices[device_id] = ("pump", pump)
            
            # Add spectrophotometers
            for spectro in spectrophotometers:
                device_id = self._device_id_from_port(spectro.port)
                new_devices[device_id] = ("spectrophotometer", spectro)
            
            # Find added and removed devices
            old_device_ids = set(self._devices.keys())
            new_device_ids = set(new_devices.keys())
            
            added = list(new_device_ids - old_device_ids)
            removed = list(old_device_ids - new_device_ids)
            
            # Close removed devices
            for device_id in removed:
                if device_id in self._devices:
                    _, device = self._devices[device_id]
                    try:
                        # Clean up the device connection
                        if hasattr(device, '__del__'):
                            device.__del__()
                    except Exception as e:
                        logger.warning(f"Error closing device {device_id}: {e}")
                    
                    # Remove lock
                    if device_id in self._locks:
                        del self._locks[device_id]
            
            # Update devices registry
            self._devices = new_devices
            
            # Create locks for new devices
            for device_id in added:
                if device_id not in self._locks:
                    self._locks[device_id] = asyncio.Lock()
            
            # Ensure all current devices have locks
            for device_id in self._devices:
                if device_id not in self._locks:
                    self._locks[device_id] = asyncio.Lock()
            
            logger.info(f"Device scan complete. Added: {added}, Removed: {removed}")
            self._initialized = True
            
            return {"added": added, "removed": removed}
            
        except Exception as e:
            logger.error(f"Error during device scan: {e}")
            raise
    
    def get(self, device_id: str) -> tuple[DeviceTypeStr, DeviceInstance]:
        """Get device by ID.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Tuple of (device_type, device_instance)
            
        Raises:
            KeyError: If device not found
        """
        if device_id not in self._devices:
            raise KeyError(f"Device {device_id} not found")
        
        return self._devices[device_id]
    
    def list_devices(self) -> list[Device]:
        """List all registered devices.
        
        Returns:
            List of Device models
        """
        devices = []
        for device_id, (device_type, device_instance) in self._devices.items():
            # Map internal type to enum
            device_type_enum = DeviceType.PUMP if device_type == "pump" else DeviceType.SPECTROPHOTOMETER
            
            devices.append(Device(
                device_id=device_id,
                type=device_type_enum,
                port=device_instance.port,
                is_available=True  # All registered devices are considered available
            ))
        
        return devices
    
    def get_device_details(self, device_id: str) -> Device:
        """Get details for a specific device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Device model
            
        Raises:
            KeyError: If device not found
        """
        device_type, device_instance = self.get(device_id)
        device_type_enum = DeviceType.PUMP if device_type == "pump" else DeviceType.SPECTROPHOTOMETER
        
        return Device(
            device_id=device_id,
            type=device_type_enum,
            port=device_instance.port,
            is_available=True
        )
    
    def lock(self, device_id: str) -> asyncio.Lock:
        """Get lock for device.
        
        Args:
            device_id: Device identifier
            
        Returns:
            Asyncio lock for the device
            
        Raises:
            KeyError: If device not found
        """
        if device_id not in self._locks:
            raise KeyError(f"Device {device_id} not found")
        
        return self._locks[device_id]
    
    def is_initialized(self) -> bool:
        """Check if registry has been initialized."""
        return self._initialized
    
    async def shutdown(self) -> None:
        """Shutdown registry and close all device connections."""
        logger.info("Shutting down device registry...")
        
        for device_id, (_, device) in self._devices.items():
            try:
                if hasattr(device, '__del__'):
                    device.__del__()
            except Exception as e:
                logger.warning(f"Error closing device {device_id}: {e}")
        
        self._devices.clear()
        self._locks.clear()
        self._initialized = False
        
        logger.info("Device registry shutdown complete")
