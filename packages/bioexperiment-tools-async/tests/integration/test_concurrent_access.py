"""Integration tests for concurrent device access and thread safety."""

import asyncio
import pytest
from concurrent.futures import ThreadPoolExecutor

from bioexperiment_tools_async import discover_devices, DeviceType, Direction


class TestConcurrentDeviceAccess:
    """Tests for concurrent access to devices."""

    @pytest.mark.asyncio
    async def test_single_device_concurrent_operations(self, monkeypatch):
        """Test that concurrent operations on a single device are properly serialized."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "1")
        
        pumps, _ = await discover_devices(device_type=DeviceType.PUMP)
        pump = pumps[0]
        
        # Track operation order
        operation_log = []
        
        async def operation_with_delay(op_id: str, delay: float):
            """Perform an operation with artificial delay."""
            async with pump:
                await pump.set_default_flow_rate(5.0)
                operation_log.append(f"{op_id}_start")
                await asyncio.sleep(delay)
                await pump.pour_volume(0.1)
                operation_log.append(f"{op_id}_end")
                return op_id
        
        # Start multiple operations concurrently
        tasks = [
            operation_with_delay("op1", 0.1),
            operation_with_delay("op2", 0.05),
            operation_with_delay("op3", 0.02),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All operations should complete
        assert len(results) == 3
        assert set(results) == {"op1", "op2", "op3"}
        
        # Operations should be serialized (start-end pairs should not interleave)
        assert len(operation_log) == 6
        for i in range(0, 6, 2):
            start_op = operation_log[i].split("_")[0]
            end_op = operation_log[i + 1].split("_")[0]
            assert start_op == end_op  # Each start should be followed by its corresponding end

    @pytest.mark.asyncio
    async def test_multiple_devices_concurrent_operations(self, monkeypatch):
        """Test that operations on different devices can run concurrently."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "3")
        
        pumps, _ = await discover_devices(device_type=DeviceType.PUMP)
        assert len(pumps) == 3
        
        # Track timing to ensure concurrent execution
        start_times = {}
        end_times = {}
        
        async def timed_operation(pump, pump_id: str):
            """Perform timed operation on a pump."""
            start_times[pump_id] = asyncio.get_event_loop().time()
            
            async with pump:
                await pump.set_default_flow_rate(5.0)
                await asyncio.sleep(0.1)  # Simulate work
                await pump.pour_volume(0.5)
            
            end_times[pump_id] = asyncio.get_event_loop().time()
            return pump_id
        
        # Run operations on all pumps concurrently
        tasks = [
            timed_operation(pumps[0], "pump1"),
            timed_operation(pumps[1], "pump2"), 
            timed_operation(pumps[2], "pump3"),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All operations should complete
        assert len(results) == 3
        
        # Operations should overlap in time (concurrent execution)
        total_time = max(end_times.values()) - min(start_times.values())
        # If run sequentially, would take ~0.3s, concurrently should be ~0.1s
        assert total_time < 0.2  # Allow some overhead

    @pytest.mark.asyncio
    async def test_mixed_device_concurrent_operations(self, monkeypatch):
        """Test concurrent operations on different device types."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "2")
        
        pumps, spectrophotometers = await discover_devices()
        
        results = []
        
        async def pump_operation(pump, pump_id: str):
            """Perform pump operations."""
            async with pump:
                await pump.set_default_flow_rate(8.0)
                await pump.pour_volume(1.0, direction=Direction.LEFT)
                await pump.pour_volume(0.5, direction=Direction.RIGHT)
                return f"pump_{pump_id}_complete"
        
        async def spectro_operation(spectro, spectro_id: str):
            """Perform spectrophotometer operations."""
            async with spectro:
                temperature = await spectro.get_temperature()
                optical_density = await spectro.measure_optical_density()
                return {
                    'id': f"spectro_{spectro_id}",
                    'temperature': temperature,
                    'optical_density': optical_density,
                }
        
        # Run all operations concurrently
        tasks = []
        tasks.extend([pump_operation(pumps[i], f"p{i}") for i in range(2)])
        tasks.extend([spectro_operation(spectrophotometers[i], f"s{i}") for i in range(2)])
        
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        assert len(results) == 4
        
        pump_results = [r for r in results if isinstance(r, str)]
        spectro_results = [r for r in results if isinstance(r, dict)]
        
        assert len(pump_results) == 2
        assert len(spectro_results) == 2

    @pytest.mark.asyncio
    async def test_device_connection_sharing(self, monkeypatch):
        """Test that device connections are properly managed across concurrent operations."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "1")
        
        pumps, _ = await discover_devices(device_type=DeviceType.PUMP)
        pump = pumps[0]
        
        connection_states = []
        
        async def check_connection_operation(op_id: str):
            """Operation that checks connection state."""
            connection_states.append(f"{op_id}_before_{pump.is_connected}")
            
            async with pump:
                connection_states.append(f"{op_id}_inside_{pump.is_connected}")
                await pump.set_default_flow_rate(5.0)
                await asyncio.sleep(0.01)  # Brief delay
            
            connection_states.append(f"{op_id}_after_{pump.is_connected}")
            return op_id
        
        # Run concurrent operations
        tasks = [
            check_connection_operation("op1"),
            check_connection_operation("op2"),
            check_connection_operation("op3"),
        ]
        
        await asyncio.gather(*tasks)
        
        # Analyze connection states
        # Device should be connected during operations, disconnected before/after
        for state in connection_states:
            if "_inside_" in state:
                assert state.endswith("_True")  # Should be connected inside context
            else:
                assert state.endswith("_False")  # Should be disconnected outside context

    @pytest.mark.asyncio
    async def test_discovery_cache_concurrent_access(self, monkeypatch):
        """Test that device discovery cache handles concurrent access properly."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        monkeypatch.setenv("N_VIRTUAL_SPECTROPHOTOMETERS", "1")
        
        from bioexperiment_tools_async.discovery import DeviceScanner
        
        scanner = DeviceScanner()
        
        # Run multiple concurrent discoveries with caching
        tasks = [
            scanner.discover_devices(),
            scanner.discover_devices(),
            scanner.discover_devices(device_type=DeviceType.PUMP),
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All discoveries should return consistent results
        (pumps1, spectros1), (pumps2, spectros2), (pumps3, spectros3) = results
        
        assert len(pumps1) == len(pumps2) == 2
        assert len(spectros1) == len(spectros2) == 1
        assert len(pumps3) == 2
        assert len(spectros3) == 0
        
        # Device IDs should be consistent
        pump_ids1 = {p.device_id for p in pumps1}
        pump_ids2 = {p.device_id for p in pumps2}
        pump_ids3 = {p.device_id for p in pumps3}
        
        assert pump_ids1 == pump_ids2 == pump_ids3

    @pytest.mark.asyncio
    async def test_error_propagation_in_concurrent_operations(self, monkeypatch):
        """Test that errors in concurrent operations are properly propagated."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "2")
        
        pumps, _ = await discover_devices(device_type=DeviceType.PUMP)
        
        async def failing_operation(pump, should_fail: bool):
            """Operation that may fail."""
            async with pump:
                await pump.set_default_flow_rate(5.0)
                
                if should_fail:
                    # Trigger an error
                    await pump.pour_volume(-1.0)  # Invalid volume
                else:
                    await pump.pour_volume(1.0)
                
                return "success"
        
        # Run mix of successful and failing operations
        tasks = [
            failing_operation(pumps[0], False),  # Should succeed
            failing_operation(pumps[1], True),   # Should fail
        ]
        
        # Use return_exceptions to capture both results and exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        assert len(results) == 2
        assert results[0] == "success"  # First operation succeeded
        assert isinstance(results[1], Exception)  # Second operation failed

    @pytest.mark.asyncio
    async def test_concurrent_device_lifecycle(self, monkeypatch):
        """Test concurrent device lifecycle operations (connect/disconnect)."""
        monkeypatch.setenv("EMULATE_DEVICES", "true")
        monkeypatch.setenv("N_VIRTUAL_PUMPS", "1")
        
        pumps, _ = await discover_devices(device_type=DeviceType.PUMP)
        pump = pumps[0]
        
        lifecycle_events = []
        
        async def lifecycle_operation(op_id: str, cycles: int):
            """Perform multiple connect/disconnect cycles."""
            for i in range(cycles):
                await pump.connect()
                lifecycle_events.append(f"{op_id}_connect_{i}")
                await asyncio.sleep(0.01)  # Brief operation time
                await pump.disconnect()
                lifecycle_events.append(f"{op_id}_disconnect_{i}")
            return op_id
        
        # Run concurrent lifecycle operations
        tasks = [
            lifecycle_operation("op1", 3),
            lifecycle_operation("op2", 2),
        ]
        
        results = await asyncio.gather(*tasks)
        assert len(results) == 2
        
        # All operations should complete successfully
        # Events should be properly serialized due to connection lock
        assert len([e for e in lifecycle_events if "_connect_" in e]) == 5
        assert len([e for e in lifecycle_events if "_disconnect_" in e]) == 5
