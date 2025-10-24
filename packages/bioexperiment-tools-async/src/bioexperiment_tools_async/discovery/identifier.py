"""Device identification logic with caching and retry mechanisms."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from loguru import logger

from ..connection import MockConnection, SerialConnection
from ..core.config import get_config
from ..core.exceptions import DeviceConnectionError
from ..core.types import DeviceType, PortName
from ..protocol.device_protocol import PumpProtocol, SpectrophotometerProtocol


@dataclass
class IdentificationResult:
    """Result of device identification attempt."""
    
    port: PortName
    device_type: DeviceType | None
    success: bool
    error: str | None = None
    timestamp: datetime = None
    
    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now()


class DeviceIdentifier:
    """Handles device identification with caching and retry logic."""
    
    def __init__(self) -> None:
        """Initialize the device identifier."""
        self._cache: dict[PortName, IdentificationResult] = {}
        self._config = get_config()
        self._cache_ttl = timedelta(seconds=self._config.device_cache_ttl)
        
        logger.debug("Initialized DeviceIdentifier")
    
    def _is_cache_valid(self, result: IdentificationResult) -> bool:
        """Check if cached result is still valid."""
        return datetime.now() - result.timestamp < self._cache_ttl
    
    def get_cached_result(self, port: PortName) -> IdentificationResult | None:
        """Get cached identification result if valid."""
        if port in self._cache:
            result = self._cache[port]
            if self._is_cache_valid(result):
                logger.debug(f"Using cached identification for {port}: {result.device_type}")
                return result
            else:
                logger.debug(f"Cache expired for {port}, removing")
                del self._cache[port]
        
        return None
    
    def cache_result(self, result: IdentificationResult) -> None:
        """Cache an identification result."""
        self._cache[result.port] = result
        logger.debug(f"Cached identification result for {result.port}: {result.device_type}")
    
    async def identify_device(self, port: PortName, *, use_cache: bool = True) -> IdentificationResult:
        """Identify a device on the specified port.
        
        Args:
            port: The port to check
            use_cache: Whether to use cached results
            
        Returns:
            IdentificationResult with device type and success status
        """
        # Check cache first
        if use_cache:
            cached_result = self.get_cached_result(port)
            if cached_result is not None:
                return cached_result
        
        logger.debug(f"Identifying device on port {port}")
        
        # Try to identify the device
        result = await self._perform_identification(port)
        
        # Cache the result
        self.cache_result(result)
        
        return result
    
    async def _perform_identification(self, port: PortName) -> IdentificationResult:
        """Perform the actual device identification."""
        connection = None
        
        try:
            # Create connection
            if self._config.emulate_devices:
                connection = MockConnection(port)
            else:
                connection = SerialConnection(port, config=self._config.connection)
            
            # Connect with timeout
            await asyncio.wait_for(
                connection.connect(),
                timeout=self._config.connection.timeout,
            )
            
            # Try pump identification first
            pump_protocol = PumpProtocol(connection)
            if await pump_protocol.identify_device():
                logger.debug(f"Identified pump on {port}")
                return IdentificationResult(
                    port=port,
                    device_type=DeviceType.PUMP,
                    success=True,
                )
            
            # Try spectrophotometer identification
            spectro_protocol = SpectrophotometerProtocol(connection)
            if await spectro_protocol.identify_device():
                logger.debug(f"Identified spectrophotometer on {port}")
                return IdentificationResult(
                    port=port,
                    device_type=DeviceType.SPECTROPHOTOMETER,
                    success=True,
                )
            
            # No device identified
            logger.debug(f"No device identified on {port}")
            return IdentificationResult(
                port=port,
                device_type=None,
                success=False,
                error="No recognized device found",
            )
            
        except asyncio.TimeoutError:
            logger.debug(f"Timeout identifying device on {port}")
            return IdentificationResult(
                port=port,
                device_type=None,
                success=False,
                error="Connection timeout",
            )
        except Exception as e:
            logger.debug(f"Error identifying device on {port}: {e}")
            return IdentificationResult(
                port=port,
                device_type=None,
                success=False,
                error=str(e),
            )
        finally:
            # Clean up connection
            if connection is not None:
                try:
                    await connection.disconnect()
                except Exception as e:
                    logger.debug(f"Error disconnecting from {port}: {e}")
    
    def clear_cache(self, port: PortName | None = None) -> None:
        """Clear identification cache.
        
        Args:
            port: Specific port to clear, or None to clear all
        """
        if port is not None:
            if port in self._cache:
                del self._cache[port]
                logger.debug(f"Cleared cache for {port}")
        else:
            self._cache.clear()
            logger.debug("Cleared all identification cache")
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics for monitoring."""
        valid_entries = 0
        expired_entries = 0
        
        for result in self._cache.values():
            if self._is_cache_valid(result):
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_ttl_seconds": self._cache_ttl.total_seconds(),
        }
