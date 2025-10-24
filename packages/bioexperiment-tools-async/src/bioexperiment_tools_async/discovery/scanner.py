"""Async device discovery with concurrent scanning."""

import asyncio
from typing import Any

from loguru import logger

from ..core.config import get_config
from ..core.types import DeviceType
from ..devices import AsyncPump, AsyncSpectrophotometer
from ..utils.serial_utils import get_available_ports
from .identifier import DeviceIdentifier, IdentificationResult


class DeviceScanner:
    """Concurrent device scanner with smart identification."""
    
    def __init__(self) -> None:
        """Initialize the device scanner."""
        self._identifier = DeviceIdentifier()
        self._config = get_config()
        self._semaphore = asyncio.Semaphore(self._config.discovery_concurrent_limit)
        
        logger.debug("Initialized DeviceScanner")
    
    async def scan_ports(
        self, 
        ports: list[str] | None = None,
        *,
        use_cache: bool = True,
        timeout: float | None = None,
    ) -> list[IdentificationResult]:
        """Scan ports for devices concurrently.
        
        Args:
            ports: List of ports to scan (discovers all if None)
            use_cache: Whether to use cached identification results
            timeout: Overall timeout for the scan operation
            
        Returns:
            List of identification results for all scanned ports
        """
        scan_timeout = timeout or self._config.discovery_timeout
        
        try:
            if ports is None:
                logger.info("Discovering available serial ports...")
                ports = await get_available_ports()
                logger.info(f"Found {len(ports)} available ports")
            
            if not ports:
                logger.info("No ports to scan")
                return []
            
            logger.info(f"Scanning {len(ports)} ports for devices...")
            
            # Create identification tasks with semaphore limiting
            tasks = [
                self._scan_port_with_semaphore(port, use_cache=use_cache)
                for port in ports
            ]
            
            # Execute all tasks concurrently with timeout
            results = await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=scan_timeout,
            )
            
            # Process results and handle exceptions
            identification_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.warning(f"Error scanning port {ports[i]}: {result}")
                    identification_results.append(
                        IdentificationResult(
                            port=ports[i],
                            device_type=None,
                            success=False,
                            error=str(result),
                        )
                    )
                else:
                    identification_results.append(result)
            
            # Log summary
            successful = sum(1 for r in identification_results if r.success)
            device_types = {}
            for result in identification_results:
                if result.success and result.device_type:
                    device_types[result.device_type] = device_types.get(result.device_type, 0) + 1
            
            logger.info(f"Scan complete: {successful}/{len(ports)} devices identified")
            for device_type, count in device_types.items():
                logger.info(f"  - {device_type.value}: {count}")
            
            return identification_results
            
        except asyncio.TimeoutError:
            logger.error(f"Device scan timed out after {scan_timeout}s")
            raise
        except Exception as e:
            logger.error(f"Error during device scan: {e}")
            raise
    
    async def _scan_port_with_semaphore(self, port: str, *, use_cache: bool) -> IdentificationResult:
        """Scan a single port with semaphore limiting."""
        async with self._semaphore:
            return await self._identifier.identify_device(port, use_cache=use_cache)
    
    async def discover_devices(
        self,
        *,
        device_type: DeviceType | None = None,
        timeout: float | None = None,
    ) -> tuple[list[AsyncPump], list[AsyncSpectrophotometer]]:
        """Discover connected devices and create device instances.
        
        Args:
            device_type: Filter to specific device type (None for all)
            timeout: Timeout for the discovery operation
            
        Returns:
            Tuple of (pumps, spectrophotometers)
        """
        logger.info("Starting device discovery...")
        
        # Scan all ports
        identification_results = await self.scan_ports(timeout=timeout)
        
        # Filter successful identifications
        successful_results = [r for r in identification_results if r.success and r.device_type]
        
        # Filter by device type if specified
        if device_type is not None:
            successful_results = [r for r in successful_results if r.device_type == device_type]
        
        # Create device instances
        pumps = []
        spectrophotometers = []
        
        for result in successful_results:
            try:
                if result.device_type == DeviceType.PUMP:
                    pump = AsyncPump(result.port)
                    pumps.append(pump)
                    logger.debug(f"Created pump instance for {result.port}")
                    
                elif result.device_type == DeviceType.SPECTROPHOTOMETER:
                    spectrophotometer = AsyncSpectrophotometer(result.port)
                    spectrophotometers.append(spectrophotometer)
                    logger.debug(f"Created spectrophotometer instance for {result.port}")
                    
            except Exception as e:
                logger.error(f"Failed to create device instance for {result.port}: {e}")
        
        logger.info(f"Discovery complete: {len(pumps)} pumps, {len(spectrophotometers)} spectrophotometers")
        return pumps, spectrophotometers
    
    def clear_cache(self, port: str | None = None) -> None:
        """Clear identification cache."""
        self._identifier.clear_cache(port)
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        return self._identifier.get_cache_stats()


# Convenience function for simple device discovery
async def discover_devices(
    *,
    device_type: DeviceType | None = None,
    timeout: float | None = None,
) -> tuple[list[AsyncPump], list[AsyncSpectrophotometer]]:
    """Discover connected devices.
    
    Args:
        device_type: Filter to specific device type (None for all)
        timeout: Timeout for the discovery operation
        
    Returns:
        Tuple of (pumps, spectrophotometers)
    """
    scanner = DeviceScanner()
    return await scanner.discover_devices(device_type=device_type, timeout=timeout)
