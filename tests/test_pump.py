"""Pump device behaviour."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from bioexperiment_suite.interfaces.pump import Pump
from tests.conftest import FakeLabDevicesClient


def _make_pump(calibration_response: list[int] | None = None) -> tuple[Pump, FakeLabDevicesClient]:
    """Construct a Pump bound to a FakeLabDevicesClient.

    The FakeLabDevicesClient is pre-loaded with the calibration probe response
    that Pump.__init__ will consume.
    """
    client = FakeLabDevicesClient(responses=[calibration_response or [10, 0, 0, 100]])
    pump = Pump(client, "pump_1", "COM3")
    return pump, client


def test_init_runs_calibration_probe_and_stores_volume():
    pump, client = _make_pump(calibration_response=[10, 0, 0, 100])

    assert pump.device_id == "pump_1"
    assert pump.port == "COM3"
    assert pump._calibration_volume == pytest.approx(100 / 10**5)

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call.device_id == "pump_1"
    assert call.command == [1, 2, 3, 4, 0]
    assert call.wait_for_response is True
    assert call.expected_response_bytes == 4


def test_set_default_flow_rate_does_not_call_server():
    pump, client = _make_pump()
    initial = len(client.calls)

    pump.set_default_flow_rate(3.0)

    assert pump.default_flow_rate == 3.0
    assert len(client.calls) == initial  # no extra send_command


def test_pour_in_volume_left_emits_correct_command_and_does_not_wait_for_response():
    pump, client = _make_pump(calibration_response=[10, 0, 0, 100])
    pump.set_default_flow_rate(60.0)  # to make the post-pour sleep negligible
    client.calls.clear()

    with patch("bioexperiment_suite.interfaces.pump.sleep") as fake_sleep:
        pump.pour_in_volume(volume=0.0, direction="left")

    # Two send_command calls expected: _set_flow_rate, then the volume write.
    assert len(client.calls) == 2
    set_speed_call, volume_call = client.calls

    assert set_speed_call.command[0] == 10           # set-speed prefix
    assert set_speed_call.wait_for_response is False
    assert set_speed_call.expected_response_bytes is None

    assert volume_call.command[0] == 16              # left direction byte
    assert volume_call.wait_for_response is False
    assert volume_call.expected_response_bytes is None
    fake_sleep.assert_called_once()                  # blocking-mode wait happened


def test_pour_in_volume_right_uses_direction_byte_17():
    pump, client = _make_pump()
    pump.set_default_flow_rate(60.0)
    client.calls.clear()

    with patch("bioexperiment_suite.interfaces.pump.sleep"):
        pump.pour_in_volume(volume=0.0, direction="right")

    _, volume_call = client.calls
    assert volume_call.command[0] == 17


def test_pour_in_volume_requires_flow_rate():
    pump, _ = _make_pump()
    with pytest.raises(ValueError):
        pump.pour_in_volume(volume=1.0)


def test_start_continuous_rotation_left():
    pump, client = _make_pump()
    client.calls.clear()

    pump.start_continuous_rotation(flow_rate=3.0, direction="left")

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call.command[0] == 11
    assert call.wait_for_response is False
    assert call.expected_response_bytes is None


def test_start_continuous_rotation_right_uses_direction_byte_12():
    pump, client = _make_pump()
    client.calls.clear()

    pump.start_continuous_rotation(flow_rate=3.0, direction="right")

    assert client.calls[0].command[0] == 12


def test_stop_continuous_rotation_delegates_to_pour_in_volume_zero():
    pump, client = _make_pump()
    pump.set_default_flow_rate(60.0)
    client.calls.clear()

    with patch("bioexperiment_suite.interfaces.pump.sleep"):
        pump.stop_continuous_rotation()

    # Same shape as pour_in_volume(0): set-speed + direction byte.
    assert len(client.calls) == 2
    assert client.calls[0].command[0] == 10
    assert client.calls[1].command[0] == 16  # default direction is "left"
