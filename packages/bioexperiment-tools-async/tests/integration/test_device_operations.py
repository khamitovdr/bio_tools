"""Integration tests for complete device operations."""

import asyncio
import pytest

from bioexperiment_tools_async import discover_devices, DeviceType, Direction
from bioexperiment_tools_async.devices import AsyncPump, AsyncSpectrophotometer


class TestPumpIntegration:
    """Integration tests for pump operations."""

    @pytest.mark.asyncio
    async def test_pump_complete_workflow(self, monkeypatch):
        """Test complete pump workflow from discovery to operation."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "1")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "0")
        
        # Discover pumps
        pumps, spectrophotometers = await discover_devices(device_type=DeviceType.PUMP)
        
        assert len(pumps) == 1
        assert len(spectrophotometers) == 0
        
        pump = pumps[0]
        assert isinstance(pump, AsyncPump)
        
        # Test complete workflow
        async with pump:
            # Set default flow rate
            await pump.set_default_flow_rate(5.0)
            assert pump.default_flow_rate == 5.0
            
            # Pour some volumes
            await pump.pour_volume(1.0, direction=Direction.LEFT)
            await pump.pour_volume(0.5, flow_rate=8.0, direction=Direction.RIGHT)
            
            # Test continuous operation
            await pump.start_continuous_rotation(flow_rate=3.0, direction=Direction.LEFT)
            await asyncio.sleep(0.1)  # Let it run briefly
            await pump.stop_continuous_rotation()

    @pytest.mark.asyncio
    async def test_multiple_pumps_concurrent(self, monkeypatch):
        """Test operating multiple pumps concurrently."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "3")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "0")
        
        # Discover pumps
        pumps, _ = await discover_devices(device_type=DeviceType.PUMP)
        assert len(pumps) == 3
        
        async def operate_pump(pump, flow_rate):
            """Operate a single pump."""
            async with pump:
                await pump.set_default_flow_rate(flow_rate)
                await pump.pour_volume(0.5, direction=Direction.LEFT)
                return pump.device_id
        
        # Operate all pumps concurrently
        tasks = [
            operate_pump(pumps[0], 5.0),
            operate_pump(pumps[1], 7.0),
            operate_pump(pumps[2], 3.0),
        ]
        
        results = await asyncio.gather(*tasks)
        assert len(results) == 3
        assert all(isinstance(device_id, str) for device_id in results)

    @pytest.mark.asyncio
    async def test_pump_error_handling(self, monkeypatch):
        """Test pump error handling in realistic scenarios."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "1")
        
        pumps, _ = await discover_devices(device_type=DeviceType.PUMP)
        pump = pumps[0]
        
        # Test operations on disconnected pump
        with pytest.raises(Exception):  # Should raise connection error
            await pump.pour_volume(1.0, flow_rate=5.0)
        
        # Connect and test invalid parameters
        async with pump:
            with pytest.raises(Exception):  # Invalid flow rate
                await pump.set_default_flow_rate(-1.0)
            
            with pytest.raises(Exception):  # Invalid volume
                await pump.pour_volume(-1.0, flow_rate=5.0)


class TestSpectrophotometerIntegration:
    """Integration tests for spectrophotometer operations."""

    @pytest.mark.asyncio
    async def test_spectrophotometer_complete_workflow(self, monkeypatch):
        """Test complete spectrophotometer workflow."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "0")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "1")
        
        # Discover spectrophotometers
        pumps, spectrophotometers = await discover_devices(
            device_type=DeviceType.SPECTROPHOTOMETER
        )
        
        assert len(pumps) == 0
        assert len(spectrophotometers) == 1
        
        spectro = spectrophotometers[0]
        assert isinstance(spectro, AsyncSpectrophotometer)
        
        # Test complete workflow
        async with spectro:
            # Get temperature
            temperature = await spectro.get_temperature()
            assert isinstance(temperature, float)
            assert 0.0 <= temperature <= 100.0
            
            # Measure optical density
            optical_density = await spectro.measure_optical_density()
            assert isinstance(optical_density, float)
            assert 0.0 <= optical_density <= 10.0
            
            # Measure with custom timeout
            optical_density2 = await spectro.measure_optical_density(timeout=5.0)
            assert isinstance(optical_density2, float)

    @pytest.mark.asyncio
    async def test_multiple_spectrophotometers_concurrent(self, monkeypatch):
        """Test operating multiple spectrophotometers concurrently."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "0")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "2")
        
        # Discover spectrophotometers
        _, spectrophotometers = await discover_devices(
            device_type=DeviceType.SPECTROPHOTOMETER
        )
        assert len(spectrophotometers) == 2
        
        async def measure_spectro(spectro):
            """Take measurements from a spectrophotometer."""
            async with spectro:
                temperature = await spectro.get_temperature()
                optical_density = await spectro.measure_optical_density()
                return {
                    'device_id': spectro.device_id,
                    'temperature': temperature,
                    'optical_density': optical_density,
                }
        
        # Measure from both spectrophotometers concurrently
        tasks = [
            measure_spectro(spectrophotometers[0]),
            measure_spectro(spectrophotometers[1]),
        ]
        
        results = await asyncio.gather(*tasks)
        assert len(results) == 2
        
        for result in results:
            assert 'device_id' in result
            assert 'temperature' in result
            assert 'optical_density' in result
            assert isinstance(result['temperature'], float)
            assert isinstance(result['optical_density'], float)


class TestMixedDeviceIntegration:
    """Integration tests with multiple device types."""

    @pytest.mark.asyncio
    async def test_mixed_device_discovery(self, monkeypatch):
        """Test discovering mixed device types."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "3")
        
        # Discover all devices
        pumps, spectrophotometers = await discover_devices()
        
        assert len(pumps) == 2
        assert len(spectrophotometers) == 3
        assert all(isinstance(p, AsyncPump) for p in pumps)
        assert all(isinstance(s, AsyncSpectrophotometer) for s in spectrophotometers)
        
        # Verify unique device IDs
        all_device_ids = [p.device_id for p in pumps] + [s.device_id for s in spectrophotometers]
        assert len(all_device_ids) == len(set(all_device_ids))  # All unique

    @pytest.mark.asyncio
    async def test_complex_experiment_workflow(self, monkeypatch):
        """Test a complex experiment workflow with multiple devices."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "1")
        
        # Discover devices
        pumps, spectrophotometers = await discover_devices()
        assert len(pumps) == 2
        assert len(spectrophotometers) == 1
        
        pump1, pump2 = pumps
        spectro = spectrophotometers[0]
        
        # Complex workflow: prepare solutions, mix, and measure
        async with pump1, pump2, spectro:
            # Setup pumps
            await pump1.set_default_flow_rate(5.0)
            await pump2.set_default_flow_rate(3.0)
            
            # Simulate adding reagents
            await asyncio.gather(
                pump1.pour_volume(2.0, direction=Direction.LEFT),
                pump2.pour_volume(1.5, direction=Direction.LEFT),
            )
            
            # Wait for mixing (simulated)
            await asyncio.sleep(0.1)
            
            # Take measurements
            initial_temp = await spectro.get_temperature()
            initial_od = await spectro.measure_optical_density()
            
            # Add more reagent
            await pump1.pour_volume(0.5, direction=Direction.RIGHT)
            
            # Final measurements
            final_temp = await spectro.get_temperature()
            final_od = await spectro.measure_optical_density()
            
            # Verify we got reasonable measurements
            assert isinstance(initial_temp, float)
            assert isinstance(final_temp, float)
            assert isinstance(initial_od, float)
            assert isinstance(final_od, float)

    @pytest.mark.asyncio
    async def test_device_context_manager_exception_handling(self, monkeypatch):
        """Test proper cleanup when exceptions occur in device context managers."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "1")
        
        pumps, _ = await discover_devices(device_type=DeviceType.PUMP)
        pump = pumps[0]
        
        # Test that device is properly disconnected even if exception occurs
        with pytest.raises(ValueError):
            async with pump:
                assert pump.is_connected
                await pump.set_default_flow_rate(5.0)
                # Simulate an exception during operation
                raise ValueError("Simulated error")
        
        # Device should be disconnected after exception
        assert not pump.is_connected

    @pytest.mark.asyncio
    async def test_concurrent_discovery_operations(self, monkeypatch):
        """Test that discovery can be called concurrently."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "1")
        
        # Run multiple discovery operations concurrently
        tasks = [
            discover_devices(),
            discover_devices(device_type=DeviceType.PUMP),
            discover_devices(device_type=DeviceType.SPECTROPHOTOMETER),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All discovery should return consistent results
        all_pumps, all_spectros = results[0]
        pump_only_pumps, pump_only_spectros = results[1] 
        spectro_only_pumps, spectro_only_spectros = results[2]
        
        assert len(all_pumps) == 2
        assert len(all_spectros) == 1
        assert len(pump_only_pumps) == 2
        assert len(pump_only_spectros) == 0
        assert len(spectro_only_pumps) == 0
        assert len(spectro_only_spectros) == 1
