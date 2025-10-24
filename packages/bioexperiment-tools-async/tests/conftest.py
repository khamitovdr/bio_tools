"""Pytest fixtures and configuration for bioexperiment-tools-async tests."""

import asyncio
import os
from typing import AsyncGenerator, Any
from unittest.mock import AsyncMock, Mock

import pytest

from bioexperiment_tools_async.connection import MockConnection, SerialConnection
from bioexperiment_tools_async.core.config import GlobalConfig
from bioexperiment_tools_async.devices import AsyncPump, AsyncSpectrophotometer
from bioexperiment_tools_async.discovery import DeviceScanner




@pytest.fixture
def test_config() -> GlobalConfig:
    """Provide test configuration with emulated devices."""
    return GlobalConfig(
        emulate_devices=True,
        n_virtual_pumps=2,
        n_virtual_spectrophotometers=2,
        discovery_timeout=5.0,
        discovery_concurrent_limit=5,
        device_cache_ttl=10.0,
        log_level="DEBUG",
    )


@pytest.fixture
def mock_serial_config() -> GlobalConfig:
    """Provide configuration that forces mocked serial connections."""
    return GlobalConfig(
        emulate_devices=False,  # But we'll mock the actual serial connections
        discovery_timeout=5.0,
        discovery_concurrent_limit=5,
        device_cache_ttl=10.0,
        log_level="DEBUG",
    )


@pytest.fixture
async def mock_connection() -> AsyncGenerator[MockConnection, None]:
    """Provide a mock connection."""
    connection = MockConnection("COM0")
    yield connection
    if connection.is_connected:
        await connection.disconnect()


@pytest.fixture
async def connected_mock_connection(mock_connection: MockConnection) -> MockConnection:
    """Provide a connected mock connection."""
    await mock_connection.connect()
    return mock_connection


@pytest.fixture
async def async_pump() -> AsyncGenerator[AsyncPump, None]:
    """Provide an AsyncPump instance for testing."""
    pump = AsyncPump("COM0")
    yield pump
    if pump.is_connected:
        await pump.disconnect()


@pytest.fixture
async def connected_async_pump(async_pump: AsyncPump, monkeypatch) -> AsyncPump:
    """Provide a connected AsyncPump instance."""
    # Ensure emulated mode for testing
    monkeypatch.setenv("EMULATE_DEVICES", "true")
    await async_pump.connect()
    return async_pump


@pytest.fixture
async def async_spectrophotometer() -> AsyncGenerator[AsyncSpectrophotometer, None]:
    """Provide an AsyncSpectrophotometer instance for testing."""
    spectro = AsyncSpectrophotometer("COM1")
    yield spectro
    if spectro.is_connected:
        await spectro.disconnect()


@pytest.fixture
async def connected_async_spectrophotometer(
    async_spectrophotometer: AsyncSpectrophotometer, 
    monkeypatch
) -> AsyncSpectrophotometer:
    """Provide a connected AsyncSpectrophotometer instance."""
    # Ensure emulated mode for testing
    monkeypatch.setenv("EMULATE_DEVICES", "true")
    await async_spectrophotometer.connect()
    return async_spectrophotometer


@pytest.fixture
def device_scanner() -> DeviceScanner:
    """Provide a DeviceScanner instance for testing."""
    return DeviceScanner()


@pytest.fixture
def mock_serial_ports():
    """Mock list of available serial ports."""
    return ["COM0", "COM1", "COM2", "COM3", "/dev/ttyUSB0", "/dev/ttyUSB1"]


@pytest.fixture
def mock_serial_asyncio(monkeypatch):
    """Mock serial_asyncio for testing without real hardware."""
    mock_reader = AsyncMock()
    mock_writer = AsyncMock()
    
    async def mock_open_serial_connection(*args, **kwargs):
        return mock_reader, mock_writer
    
    import serial_asyncio
    monkeypatch.setattr(serial_asyncio, "open_serial_connection", mock_open_serial_connection)
    
    return mock_reader, mock_writer


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment variables automatically for all tests."""
    # Clear any cached config before setting environment
    from bioexperiment_tools_async.core.config import clear_config
    clear_config()
    
    # Enable emulation by default for tests
    monkeypatch.setenv("BIOEXPERIMENT_EMULATE_DEVICES", "true")
    monkeypatch.setenv("BIOEXPERIMENT_N_VIRTUAL_PUMPS", "2")
    monkeypatch.setenv("BIOEXPERIMENT_N_VIRTUAL_SPECTROPHOTOMETERS", "2")
    monkeypatch.setenv("BIOEXPERIMENT_LOG_LEVEL", "DEBUG")
    
    # Clear config again after setting environment variables
    clear_config()


# Helper functions for tests
def create_mock_identification_response(device_type: str) -> bytes:
    """Create a mock identification response for the given device type."""
    if device_type == "pump":
        return bytes([10, 0x01, 0x02, 0x03])  # Pump identification response
    elif device_type == "spectrophotometer":
        return bytes([70, 0x01, 0x02, 0x03])  # Spectrophotometer identification response
    else:
        return bytes([0x00, 0x00, 0x00, 0x00])


def create_mock_temperature_response(temperature: float = 25.5) -> bytes:
    """Create a mock temperature response."""
    integer_part = int(temperature)
    fractional_part = int((temperature - integer_part) * 100)
    return bytes([0x01, 0x02, integer_part, fractional_part])


def create_mock_optical_density_response(optical_density: float = 1.234) -> bytes:
    """Create a mock optical density response."""
    integer_part = int(optical_density)
    fractional_part = int((optical_density - integer_part) * 100)
    return bytes([0x01, 0x02, integer_part, fractional_part])
