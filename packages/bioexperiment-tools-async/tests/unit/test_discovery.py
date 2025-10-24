"""Unit tests for device discovery functionality."""

import asyncio
from datetime import datetime, timedelta
import pytest
from unittest.mock import AsyncMock, Mock, patch

from bioexperiment_tools_async.core.types import DeviceType
from bioexperiment_tools_async.devices import AsyncPump, AsyncSpectrophotometer
from bioexperiment_tools_async.discovery import DeviceScanner, discover_devices
from bioexperiment_tools_async.discovery.identifier import DeviceIdentifier, IdentificationResult


class TestIdentificationResult:
    """Tests for IdentificationResult dataclass."""

    def test_identification_result_creation(self):
        """Test creating identification result."""
        result = IdentificationResult(
            port="COM0",
            device_type=DeviceType.PUMP,
            success=True,
        )
        
        assert result.port == "COM0"
        assert result.device_type == DeviceType.PUMP
        assert result.success is True
        assert result.error is None
        assert isinstance(result.timestamp, datetime)

    def test_identification_result_with_error(self):
        """Test creating identification result with error."""
        result = IdentificationResult(
            port="COM0",
            device_type=None,
            success=False,
            error="Connection timeout",
        )
        
        assert result.port == "COM0"
        assert result.device_type is None
        assert result.success is False
        assert result.error == "Connection timeout"


class TestDeviceIdentifier:
    """Tests for DeviceIdentifier."""

    @pytest.fixture
    def identifier(self):
        """Create device identifier instance."""
        return DeviceIdentifier()

    def test_identifier_initialization(self, identifier):
        """Test identifier initialization."""
        assert isinstance(identifier._cache, dict)
        assert len(identifier._cache) == 0

    @pytest.mark.asyncio
    async def test_identify_pump_device(self, identifier, monkeypatch):
        """Test identifying pump device."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        
        result = await identifier.identify_device("COM0")  # Even port = pump
        
        assert result.port == "COM0"
        assert result.device_type == DeviceType.PUMP
        assert result.success is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_identify_spectrophotometer_device(self, identifier, monkeypatch):
        """Test identifying spectrophotometer device."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        
        result = await identifier.identify_device("COM1")  # Odd port = spectro
        
        assert result.port == "COM1"
        assert result.device_type == DeviceType.SPECTROPHOTOMETER
        assert result.success is True
        assert result.error is None

    @pytest.mark.asyncio
    async def test_identify_device_caching(self, identifier, monkeypatch):
        """Test that identification results are cached."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        
        # First identification
        result1 = await identifier.identify_device("COM0")
        assert result1.success is True
        
        # Second identification should use cache
        result2 = await identifier.identify_device("COM0", use_cache=True)
        assert result2.success is True
        assert result2.timestamp == result1.timestamp  # Same cached result

    @pytest.mark.asyncio
    async def test_identify_device_skip_cache(self, identifier, monkeypatch):
        """Test identifying device without using cache."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        
        # First identification
        result1 = await identifier.identify_device("COM0")
        
        # Wait a bit to ensure different timestamps
        await asyncio.sleep(0.01)
        
        # Second identification bypassing cache
        result2 = await identifier.identify_device("COM0", use_cache=False)
        assert result2.timestamp > result1.timestamp

    def test_cache_expiry(self, identifier):
        """Test that cache entries expire after TTL."""
        # Create an old result
        old_result = IdentificationResult(
            port="COM0",
            device_type=DeviceType.PUMP,
            success=True,
            timestamp=datetime.now() - timedelta(seconds=120),  # 2 minutes ago
        )
        
        identifier._cache["COM0"] = old_result
        
        # Should not return expired result
        cached = identifier.get_cached_result("COM0")
        assert cached is None
        assert "COM0" not in identifier._cache  # Should be removed

    def test_cache_management(self, identifier):
        """Test cache management operations."""
        # Add some results
        result1 = IdentificationResult("COM0", DeviceType.PUMP, True)
        result2 = IdentificationResult("COM1", DeviceType.SPECTROPHOTOMETER, True)
        
        identifier.cache_result(result1)
        identifier.cache_result(result2)
        
        assert len(identifier._cache) == 2
        
        # Clear specific port
        identifier.clear_cache("COM0")
        assert len(identifier._cache) == 1
        assert "COM1" in identifier._cache
        
        # Clear all
        identifier.clear_cache()
        assert len(identifier._cache) == 0

    def test_cache_stats(self, identifier):
        """Test cache statistics."""
        # Add valid result
        result1 = IdentificationResult("COM0", DeviceType.PUMP, True)
        identifier.cache_result(result1)
        
        # Add expired result
        expired_result = IdentificationResult(
            "COM1", DeviceType.PUMP, True,
            timestamp=datetime.now() - timedelta(seconds=120)
        )
        identifier._cache["COM1"] = expired_result
        
        stats = identifier.get_cache_stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 1
        assert stats["expired_entries"] == 1
        assert stats["cache_ttl_seconds"] > 0


class TestDeviceScanner:
    """Tests for DeviceScanner."""

    @pytest.fixture
    def scanner(self):
        """Create device scanner instance."""
        return DeviceScanner()

    def test_scanner_initialization(self, scanner):
        """Test scanner initialization."""
        assert isinstance(scanner._identifier, DeviceIdentifier)
        assert scanner._semaphore._value > 0  # Has concurrency limit

    @pytest.mark.asyncio
    async def test_scan_ports_with_emulation(self, scanner, monkeypatch):
        """Test scanning ports with device emulation."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "1")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "1")
        
        ports = ["COM0", "COM1"]
        results = await scanner.scan_ports(ports)
        
        assert len(results) == 2
        assert any(r.device_type == DeviceType.PUMP for r in results)
        assert any(r.device_type == DeviceType.SPECTROPHOTOMETER for r in results)

    @pytest.mark.asyncio
    async def test_scan_ports_auto_discovery(self, scanner, monkeypatch):
        """Test scanning with automatic port discovery."""
        monkeypatch.setenv("EMULATE_DEVICES", "true") 
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "1")
        
        results = await scanner.scan_ports(ports=None)  # Auto-discover
        
        # Should find the virtual devices
        assert len(results) >= 3
        successful_results = [r for r in results if r.success]
        assert len(successful_results) >= 3

    @pytest.mark.asyncio
    async def test_scan_ports_timeout(self, scanner):
        """Test scan ports with timeout."""
        with patch('bioexperiment_tools_async.utils.serial_utils.get_available_ports') as mock_ports:
            # Return a port that will cause slow identification
            mock_ports.return_value = ["SLOW_PORT"]
            
            with patch.object(scanner._identifier, 'identify_device') as mock_identify:
                # Make identification hang
                mock_identify.side_effect = asyncio.sleep(10)
                
                with pytest.raises(asyncio.TimeoutError):
                    await scanner.scan_ports(timeout=0.1)

    @pytest.mark.asyncio
    async def test_scan_empty_ports(self, scanner):
        """Test scanning empty port list."""
        results = await scanner.scan_ports([])
        assert results == []

    @pytest.mark.asyncio
    async def test_discover_devices(self, scanner, monkeypatch):
        """Test device discovery returning device instances."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "1")
        
        pumps, spectrophotometers = await scanner.discover_devices()
        
        assert len(pumps) == 2
        assert len(spectrophotometers) == 1
        assert all(isinstance(p, AsyncPump) for p in pumps)
        assert all(isinstance(s, AsyncSpectrophotometer) for s in spectrophotometers)

    @pytest.mark.asyncio
    async def test_discover_devices_filter_by_type(self, scanner, monkeypatch):
        """Test device discovery with device type filter."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "1")
        
        # Filter for pumps only
        pumps, spectrophotometers = await scanner.discover_devices(
            device_type=DeviceType.PUMP
        )
        
        assert len(pumps) == 2
        assert len(spectrophotometers) == 0

    def test_scanner_cache_operations(self, scanner):
        """Test scanner cache management operations."""
        # Add some cached data via identifier
        result = IdentificationResult("COM0", DeviceType.PUMP, True)
        scanner._identifier.cache_result(result)
        
        stats = scanner.get_cache_stats()
        assert stats["total_entries"] == 1
        
        # Clear cache
        scanner.clear_cache("COM0")
        stats = scanner.get_cache_stats()
        assert stats["total_entries"] == 0


class TestDiscoverDevicesFunction:
    """Tests for the convenience discover_devices function."""

    @pytest.mark.asyncio
    async def test_discover_devices_function(self, monkeypatch):
        """Test the standalone discover_devices function."""
        from bioexperiment_tools_async.core.config import clear_config
        
        monkeypatch.setenv("BIOEXPERIMENT_EMULATE_DEVICES", "true")
        monkeypatch.setenv("BIOEXPERIMENT_N_VIRTUAL_PUMPS", "1")
        monkeypatch.setenv("BIOEXPERIMENT_N_VIRTUAL_SPECTROPHOTOMETERS", "1")
        clear_config()  # Clear cache to pick up new env vars
        
        pumps, spectrophotometers = await discover_devices()
        
        assert len(pumps) == 1
        assert len(spectrophotometers) == 1
        assert isinstance(pumps[0], AsyncPump)
        assert isinstance(spectrophotometers[0], AsyncSpectrophotometer)

    @pytest.mark.asyncio
    async def test_discover_devices_function_with_filter(self, monkeypatch):
        """Test discover_devices function with device type filter."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "2")
        
        # Test spectrophotometer filter
        pumps, spectrophotometers = await discover_devices(
            device_type=DeviceType.SPECTROPHOTOMETER
        )
        
        assert len(pumps) == 0
        assert len(spectrophotometers) == 2

    @pytest.mark.asyncio
    async def test_discover_devices_function_with_timeout(self, monkeypatch):
        """Test discover_devices function with timeout."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "1")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "0")
        
        pumps, spectrophotometers = await discover_devices(timeout=5.0)
        
        assert len(pumps) == 1
        assert len(spectrophotometers) == 0
