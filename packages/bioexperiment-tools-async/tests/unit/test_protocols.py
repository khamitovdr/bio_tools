"""Unit tests for device protocols and commands."""

import pytest
from unittest.mock import AsyncMock, Mock

from bioexperiment_tools_async.core.exceptions import DeviceCommunicationError
from bioexperiment_tools_async.core.types import DeviceType, Direction
from bioexperiment_tools_async.protocol.commands import PumpCommand, SpectrophotometerCommand
from bioexperiment_tools_async.protocol.device_protocol import PumpProtocol, SpectrophotometerProtocol


class TestPumpCommand:
    """Tests for PumpCommand."""

    def test_identification_command(self):
        """Test pump identification command generation."""
        cmd = PumpCommand.identification()
        
        assert cmd.data == [1, 2, 3, 4, 181]
        assert cmd.response_length == 4
        assert "identification" in cmd.description.lower()

    def test_set_flow_rate_command(self):
        """Test set flow rate command generation."""
        flow_rate = 5.0
        cmd = PumpCommand.set_flow_rate(flow_rate)
        
        expected_speed_param = int(29 / flow_rate)
        assert cmd.data == [10, 0, 1, expected_speed_param, 0]
        assert cmd.response_length == 0
        assert "5.0" in cmd.description

    def test_pour_volume_command(self):
        """Test pour volume command generation."""
        volume = 10.0
        direction = Direction.LEFT
        calibration_volume = 1.0
        
        cmd = PumpCommand.pour_volume(volume, direction, calibration_volume)
        
        assert cmd.data[0] == 16  # Left direction byte
        assert cmd.response_length == 0
        assert "10.0" in cmd.description
        assert "left" in cmd.description.lower()

    def test_pour_volume_command_right_direction(self):
        """Test pour volume command with right direction."""
        volume = 5.0
        direction = Direction.RIGHT
        calibration_volume = 1.0
        
        cmd = PumpCommand.pour_volume(volume, direction, calibration_volume)
        
        assert cmd.data[0] == 17  # Right direction byte
        assert "right" in cmd.description.lower()

    def test_continuous_rotation_command(self):
        """Test continuous rotation command generation."""
        flow_rate = 8.0
        direction = Direction.LEFT
        
        cmd = PumpCommand.start_continuous_rotation(flow_rate, direction)
        
        assert cmd.data[0] == 11  # Left continuous rotation byte
        assert cmd.data[1] == 111
        assert cmd.response_length == 0
        assert "8.0" in cmd.description

    def test_stop_rotation_command(self):
        """Test stop rotation command generation."""
        cmd = PumpCommand.stop_rotation()
        
        # Should be a pour volume command with 0 volume
        assert cmd.data[0] == 16  # Left direction (default)
        assert cmd.response_length == 0


class TestSpectrophotometerCommand:
    """Tests for SpectrophotometerCommand."""

    def test_identification_command(self):
        """Test spectrophotometer identification command generation."""
        cmd = SpectrophotometerCommand.identification()
        
        assert cmd.data == [1, 2, 3, 4, 0]
        assert cmd.response_length == 4
        assert "identification" in cmd.description.lower()

    def test_get_temperature_command(self):
        """Test get temperature command generation."""
        cmd = SpectrophotometerCommand.get_temperature()
        
        assert cmd.data == [76, 0, 0, 0, 0]
        assert cmd.response_length == 4
        assert "temperature" in cmd.description.lower()

    def test_start_measurement_command(self):
        """Test start measurement command generation."""
        cmd = SpectrophotometerCommand.start_measurement()
        
        assert cmd.data == [78, 4, 0, 0, 0]
        assert cmd.response_length == 0
        assert "measurement" in cmd.description.lower()

    def test_get_measurement_result_command(self):
        """Test get measurement result command generation."""
        cmd = SpectrophotometerCommand.get_measurement_result()
        
        assert cmd.data == [79, 4, 0, 0, 0]
        assert cmd.response_length == 4
        assert "result" in cmd.description.lower()


class TestPumpProtocol:
    """Tests for PumpProtocol."""

    @pytest.fixture
    def mock_connection(self):
        """Create mock connection for testing."""
        connection = AsyncMock()
        connection.port = "COM0"
        return connection

    @pytest.fixture
    def pump_protocol(self, mock_connection):
        """Create pump protocol instance."""
        return PumpProtocol(mock_connection)

    @pytest.mark.asyncio
    async def test_pump_protocol_init(self, pump_protocol, mock_connection):
        """Test pump protocol initialization."""
        assert pump_protocol.device_type == DeviceType.PUMP
        assert pump_protocol.connection == mock_connection

    @pytest.mark.asyncio
    async def test_identify_device_success(self, pump_protocol, mock_connection):
        """Test successful pump device identification."""
        # Mock successful identification response
        mock_connection.communicate.return_value = bytes([10, 1, 2, 3])
        
        result = await pump_protocol.identify_device()
        assert result is True
        
        # Verify correct command was sent
        mock_connection.communicate.assert_called_once()
        call_args = mock_connection.communicate.call_args[0]
        assert call_args[0] == [1, 2, 3, 4, 181]
        assert call_args[1] == 4

    @pytest.mark.asyncio
    async def test_identify_device_wrong_response(self, pump_protocol, mock_connection):
        """Test pump identification with wrong response."""
        # Mock wrong identification response
        mock_connection.communicate.return_value = bytes([70, 1, 2, 3])  # Spectro response
        
        result = await pump_protocol.identify_device()
        assert result is False

    @pytest.mark.asyncio
    async def test_identify_device_exception(self, pump_protocol, mock_connection):
        """Test pump identification with communication exception."""
        mock_connection.communicate.side_effect = Exception("Communication error")
        
        result = await pump_protocol.identify_device()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_calibration_volume(self, pump_protocol, mock_connection, monkeypatch):
        """Test getting pump calibration volume."""
        # Mock identification response with calibration data
        calibration_bytes = (123456).to_bytes(3, 'big')
        mock_connection.communicate.return_value = bytes([10]) + calibration_bytes
        
        # Ensure not in emulated mode
        monkeypatch.setenv("BIOEXPERIMENT_EMULATE_DEVICES", "false")
        
        volume = await pump_protocol.get_calibration_volume()
        expected_volume = 123456 / 10**5
        assert volume == expected_volume

    @pytest.mark.asyncio 
    async def test_get_calibration_volume_emulated(self, pump_protocol, mock_connection, monkeypatch):
        """Test getting calibration volume in emulated mode."""
        from bioexperiment_tools_async.core.config import clear_config
        
        monkeypatch.setenv("BIOEXPERIMENT_EMULATE_DEVICES", "true")
        clear_config()  # Clear cache to pick up new env vars
        
        volume = await pump_protocol.get_calibration_volume()
        assert volume == 1.0

    @pytest.mark.asyncio
    async def test_set_flow_rate(self, pump_protocol, mock_connection):
        """Test setting pump flow rate."""
        flow_rate = 7.5
        
        await pump_protocol.set_flow_rate(flow_rate)
        
        # Verify correct command was sent
        mock_connection.write.assert_called_once()
        call_args = mock_connection.write.call_args[0][0]
        expected_speed_param = int(29 / flow_rate)
        assert call_args == [10, 0, 1, expected_speed_param, 0]

    @pytest.mark.asyncio
    async def test_pour_volume(self, pump_protocol, mock_connection):
        """Test pump pour volume operation."""
        # Mock calibration volume response
        pump_protocol._calibration_volume = 1.0
        
        volume = 15.0
        direction = Direction.RIGHT
        
        await pump_protocol.pour_volume(volume, direction)
        
        # Verify correct command was sent
        mock_connection.write.assert_called_once()
        call_args = mock_connection.write.call_args[0][0]
        assert call_args[0] == 17  # Right direction byte


class TestSpectrophotometerProtocol:
    """Tests for SpectrophotometerProtocol."""

    @pytest.fixture
    def mock_connection(self):
        """Create mock connection for testing."""
        connection = AsyncMock()
        connection.port = "COM1"
        return connection

    @pytest.fixture
    def spectro_protocol(self, mock_connection):
        """Create spectrophotometer protocol instance."""
        return SpectrophotometerProtocol(mock_connection)

    @pytest.mark.asyncio
    async def test_spectro_protocol_init(self, spectro_protocol, mock_connection):
        """Test spectrophotometer protocol initialization."""
        assert spectro_protocol.device_type == DeviceType.SPECTROPHOTOMETER
        assert spectro_protocol.connection == mock_connection

    @pytest.mark.asyncio
    async def test_identify_device_success(self, spectro_protocol, mock_connection):
        """Test successful spectrophotometer device identification."""
        # Mock successful identification response
        mock_connection.communicate.return_value = bytes([70, 1, 2, 3])
        
        result = await spectro_protocol.identify_device()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_temperature(self, spectro_protocol, mock_connection, monkeypatch):
        """Test getting temperature from spectrophotometer."""
        monkeypatch.setenv("BIOEXPERIMENT_EMULATE_DEVICES", "false")
        
        # Mock temperature response: 25.75°C
        mock_connection.communicate.return_value = bytes([1, 2, 25, 75])
        
        temperature = await spectro_protocol.get_temperature()
        assert temperature == 25.75

    @pytest.mark.asyncio
    async def test_get_temperature_emulated(self, spectro_protocol, mock_connection, monkeypatch):
        """Test getting temperature in emulated mode."""
        from bioexperiment_tools_async.core.config import clear_config
        
        monkeypatch.setenv("BIOEXPERIMENT_EMULATE_DEVICES", "true")
        clear_config()  # Clear cache to pick up new env vars
        
        temperature = await spectro_protocol.get_temperature()
        assert 20.0 <= temperature <= 30.0  # Random range

    @pytest.mark.asyncio
    async def test_measure_optical_density(self, spectro_protocol, mock_connection, monkeypatch):
        """Test measuring optical density."""
        monkeypatch.setenv("BIOEXPERIMENT_EMULATE_DEVICES", "false")
        
        # Mock start measurement (no response) and result response
        mock_connection.write.return_value = None
        mock_connection.communicate.return_value = bytes([1, 2, 1, 23])  # 1.23
        
        optical_density = await spectro_protocol.measure_optical_density()
        assert optical_density == 1.23
        
        # Verify both start and result commands were sent
        assert mock_connection.write.call_count == 1  # Start measurement
        assert mock_connection.communicate.call_count == 1  # Get result

    @pytest.mark.asyncio
    async def test_measure_optical_density_emulated(self, spectro_protocol, mock_connection, monkeypatch):
        """Test measuring optical density in emulated mode."""
        from bioexperiment_tools_async.core.config import clear_config
        
        monkeypatch.setenv("BIOEXPERIMENT_EMULATE_DEVICES", "true")
        clear_config()  # Clear cache to pick up new env vars
        
        optical_density = await spectro_protocol.measure_optical_density()
        assert 0.0 <= optical_density <= 2.0  # Random range
