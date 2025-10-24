"""Unit tests for connection implementations."""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch

from bioexperiment_tools_async.connection import MockConnection, SerialConnection
from bioexperiment_tools_async.core.exceptions import DeviceConnectionError, DeviceCommunicationError
from bioexperiment_tools_async.core.config import ConnectionConfig


class TestMockConnection:
    """Tests for MockConnection."""

    @pytest.mark.asyncio
    async def test_mock_connection_lifecycle(self):
        """Test mock connection connect/disconnect lifecycle."""
        connection = MockConnection("COM0")
        
        assert connection.port == "COM0"
        assert not connection.is_connected
        
        # Test connect
        await connection.connect()
        assert connection.is_connected
        
        # Test disconnect
        await connection.disconnect()
        assert not connection.is_connected

    @pytest.mark.asyncio
    async def test_mock_connection_context_manager(self):
        """Test mock connection as async context manager."""
        async with MockConnection("COM0") as connection:
            assert connection.is_connected
            assert connection.port == "COM0"
        
        assert not connection.is_connected

    @pytest.mark.asyncio
    async def test_mock_connection_communication(self):
        """Test mock connection write/read operations."""
        connection = MockConnection("COM0")
        await connection.connect()
        
        # Test write
        test_data = [1, 2, 3, 4, 5]
        await connection.write(test_data)
        
        # Test read
        response = await connection.read(4)
        assert len(response) == 4
        assert isinstance(response, bytes)
        
        # Test communicate
        response = await connection.communicate([1, 2, 3], 2)
        assert len(response) == 2
        
        await connection.disconnect()

    @pytest.mark.asyncio
    async def test_mock_connection_device_type_detection(self):
        """Test that mock connection generates appropriate responses by device type."""
        # Test pump device (even port number)
        pump_connection = MockConnection("COM0")
        await pump_connection.connect()
        
        # Pump identification should return pump-like response
        response = await pump_connection.communicate([1, 2, 3, 4, 181], 4)
        assert response[0] == 10  # Pump identification byte
        
        # Test spectrophotometer device (odd port number)  
        spectro_connection = MockConnection("COM1")
        await spectro_connection.connect()
        
        # Spectrophotometer identification should return spectro-like response
        response = await spectro_connection.communicate([1, 2, 3, 4, 0], 4)
        assert response[0] == 70  # Spectrophotometer identification byte
        
        await pump_connection.disconnect()
        await spectro_connection.disconnect()

    @pytest.mark.asyncio
    async def test_mock_connection_disconnected_operations(self):
        """Test that operations on disconnected connection raise appropriate errors."""
        connection = MockConnection("COM0")
        
        with pytest.raises(DeviceConnectionError):
            await connection.write([1, 2, 3])
        
        with pytest.raises(DeviceConnectionError):
            await connection.read(4)


class TestSerialConnection:
    """Tests for SerialConnection."""

    @pytest.mark.asyncio
    async def test_serial_connection_init(self):
        """Test serial connection initialization."""
        connection = SerialConnection("COM0")
        
        assert connection.port == "COM0"
        assert not connection.is_connected

    @pytest.mark.asyncio
    async def test_serial_connection_with_custom_config(self):
        """Test serial connection with custom configuration."""
        config = ConnectionConfig(
            baudrate=115200,
            timeout=2.0,
            max_retries=5,
            retry_delay=1.0,
        )
        
        connection = SerialConnection("COM0", config=config)
        assert connection._config.baudrate == 115200
        assert connection._config.timeout == 2.0
        assert connection._config.max_retries == 5

    @pytest.mark.asyncio
    async def test_serial_connection_mocked_success(self, mock_serial_asyncio):
        """Test successful serial connection with mocked pyserial-asyncio."""
        mock_reader, mock_writer = mock_serial_asyncio
        
        connection = SerialConnection("COM0")
        await connection.connect()
        
        assert connection.is_connected
        
        await connection.disconnect()
        assert not connection.is_connected

    @pytest.mark.asyncio
    async def test_serial_connection_write_read(self, mock_serial_asyncio):
        """Test serial connection write/read operations."""
        mock_reader, mock_writer = mock_serial_asyncio
        mock_reader.read.return_value = bytes([10, 20, 30, 40])
        
        connection = SerialConnection("COM0")
        await connection.connect()
        
        # Test write
        test_data = [1, 2, 3, 4, 5]
        await connection.write(test_data)
        mock_writer.write.assert_called_once_with(bytes(test_data))
        mock_writer.drain.assert_called_once()
        
        # Test read
        response = await connection.read(4)
        assert response == bytes([10, 20, 30, 40])
        mock_reader.read.assert_called_with(4)
        
        await connection.disconnect()

    @pytest.mark.asyncio
    async def test_serial_connection_communicate(self, mock_serial_asyncio):
        """Test serial connection communicate method."""
        mock_reader, mock_writer = mock_serial_asyncio
        mock_reader.read.return_value = bytes([10, 20])
        
        connection = SerialConnection("COM0")
        await connection.connect()
        
        response = await connection.communicate([1, 2, 3], 2)
        
        # Should have written then read
        mock_writer.write.assert_called_once_with(bytes([1, 2, 3]))
        mock_reader.read.assert_called_once_with(2)
        assert response == bytes([10, 20])
        
        await connection.disconnect()

    @pytest.mark.asyncio
    async def test_serial_connection_retry_mechanism(self):
        """Test serial connection retry mechanism on failure."""
        config = ConnectionConfig(max_retries=3, retry_delay=0.01)
        connection = SerialConnection("COM999", config=config)  # Non-existent port
        
        # Should raise error after retries
        with pytest.raises(DeviceConnectionError) as exc_info:
            await connection.connect()
        
        assert "Failed to connect" in str(exc_info.value)
        assert "COM999" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_serial_connection_disconnected_operations(self):
        """Test operations on disconnected serial connection."""
        connection = SerialConnection("COM0")
        
        with pytest.raises(DeviceConnectionError):
            await connection.write([1, 2, 3])
        
        with pytest.raises(DeviceConnectionError):
            await connection.read(4)

    @pytest.mark.asyncio
    async def test_serial_connection_read_timeout(self, mock_serial_asyncio):
        """Test serial connection read timeout handling."""
        mock_reader, mock_writer = mock_serial_asyncio
        
        # Make read hang to trigger timeout
        mock_reader.read.side_effect = asyncio.TimeoutError()
        
        connection = SerialConnection("COM0")
        await connection.connect()
        
        with pytest.raises(DeviceCommunicationError):
            await connection.read(4)
        
        await connection.disconnect()

    @pytest.mark.asyncio
    async def test_serial_connection_multiple_connect_disconnect(self, mock_serial_asyncio):
        """Test multiple connect/disconnect cycles."""
        connection = SerialConnection("COM0")
        
        # Connect and disconnect multiple times
        for _ in range(3):
            await connection.connect()
            assert connection.is_connected
            
            await connection.disconnect() 
            assert not connection.is_connected
