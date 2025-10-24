"""
Bioexperiment Tools Async - Modern async-first device communication library.

This package provides async interfaces for biological experiment devices including
pumps and spectrophotometers, with proper async context management and concurrent operations.

Example usage:
    ```python
    import asyncio
    from bioexperiment_tools_async import discover_devices, Direction
    
    async def main():
        # Discover all connected devices
        pumps, spectrophotometers = await discover_devices()
        
        # Use a pump with context manager
        if pumps:
            async with pumps[0] as pump:
                await pump.set_default_flow_rate(5.0)
                await pump.pour_volume(10.0, direction=Direction.LEFT)
        
        # Use a spectrophotometer
        if spectrophotometers:
            async with spectrophotometers[0] as spectro:
                temperature = await spectro.get_temperature()
                optical_density = await spectro.measure_optical_density()
    
    asyncio.run(main())
    ```
"""

from .core.types import DeviceType, Direction
from .core.config import get_config
from .devices import AsyncPump, AsyncSpectrophotometer
from .discovery import discover_devices, DeviceScanner
from .utils.logging import setup_logging

# Initialize logging when package is imported
setup_logging()

__version__ = "0.1.0"
__all__ = [
    "AsyncPump",
    "AsyncSpectrophotometer", 
    "DeviceType",
    "Direction",
    "discover_devices",
    "DeviceScanner",
    "get_config",
    "setup_logging",
]
