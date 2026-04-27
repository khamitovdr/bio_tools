"""Densitometer device behaviour."""
from __future__ import annotations

from unittest.mock import patch

from bioexperiment_suite.interfaces.densitometer import Densitometer
from tests.conftest import FakeLabDevicesClient


def test_init_does_not_call_server():
    client = FakeLabDevicesClient()
    densitometer = Densitometer(client, "densitometer_1", "COM7")

    assert densitometer.device_id == "densitometer_1"
    assert densitometer.port == "COM7"
    assert client.calls == []


def test_get_temperature_decodes_two_byte_payload():
    # Temperature payload format from device_interfaces.json: [_, _, integer, fractional]
    client = FakeLabDevicesClient(responses=[[0, 0, 25, 30]])
    densitometer = Densitometer(client, "densitometer_1", "COM7")

    temperature = densitometer.get_temperature()

    assert temperature == 25 + 30 / 100
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call.device_id == "densitometer_1"
    assert call.command == [76, 0, 0, 0, 0]
    assert call.wait_for_response is True
    assert call.expected_response_bytes == 4


def test_measure_optical_density_starts_then_reads_after_sleep():
    client = FakeLabDevicesClient(
        responses=[
            [],                  # response to start_measurement (wait_for_response=False)
            [0, 0, 0, 42],       # response to get_measurement_result
        ]
    )
    densitometer = Densitometer(client, "densitometer_1", "COM7")

    with patch("bioexperiment_suite.interfaces.densitometer.sleep") as fake_sleep:
        optical_density = densitometer.measure_optical_density()

    assert optical_density == 0 + 42 / 100
    fake_sleep.assert_called_once_with(3)

    assert len(client.calls) == 2
    start_call, read_call = client.calls
    assert start_call.command == [78, 4, 0, 0, 0]
    assert start_call.wait_for_response is False
    assert start_call.expected_response_bytes is None
    assert read_call.command == [79, 4, 0, 0, 0]
    assert read_call.wait_for_response is True
    assert read_call.expected_response_bytes == 4


def test_measure_optical_density_raises_on_empty_read():
    import pytest

    client = FakeLabDevicesClient(responses=[[], []])
    densitometer = Densitometer(client, "densitometer_1", "COM7")

    with patch("bioexperiment_suite.interfaces.densitometer.sleep"):
        with pytest.raises(Exception):
            densitometer.measure_optical_density()
