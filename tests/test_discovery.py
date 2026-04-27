"""Discovery factory: POST /discover and GET /devices."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import httpx
import pytest

from bioexperiment_suite.interfaces.lab_devices_client import (
    LabDevicesClient,
    DiscoveredDevices,
    DiscoveryInProgress,
    DiscoveryFailed,
)


_DEVICES_RESPONSE = {
    "devices": [
        {"id": "pump_1", "type": "pump", "type_code": 10, "port": "COM3"},
        {"id": "valve_1", "type": "valve", "type_code": 30, "port": "COM4"},
        {"id": "densitometer_1", "type": "densitometer", "type_code": 70, "port": "COM7"},
    ],
    "discovered_at": "2026-04-26T12:34:56Z",
}


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> LabDevicesClient:
    client = LabDevicesClient(port=9001)
    client._http.close()
    client._http = httpx.Client(
        base_url="http://chisel:9001",
        transport=httpx.MockTransport(handler),
        timeout=5.0,
    )
    return client


def _discovery_handler(devices_response: dict, command_response: dict) -> Callable:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in ("/discover", "/devices"):
            return httpx.Response(200, json=devices_response)
        if path.endswith("/command"):
            return httpx.Response(200, json=command_response)
        return httpx.Response(404, json={"error": "not found", "detail": ""})

    return handler


def test_discover_returns_categorized_devices_and_parses_timestamp():
    handler = _discovery_handler(_DEVICES_RESPONSE, {"response": [10, 0, 0, 100]})
    with _make_client(handler) as client:
        result = client.discover()

    assert isinstance(result, DiscoveredDevices)
    assert len(result.pumps) == 1
    assert len(result.densitometers) == 1
    assert len(result.valves) == 1
    assert result.pumps[0].device_id == "pump_1"
    assert result.pumps[0].port == "COM3"
    assert result.densitometers[0].device_id == "densitometer_1"
    assert result.valves[0].device_id == "valve_1"
    assert result.discovered_at == datetime(2026, 4, 26, 12, 34, 56, tzinfo=timezone.utc)


def test_list_devices_handles_null_discovered_at():
    handler = _discovery_handler(
        {"devices": [], "discovered_at": None},
        {"response": []},
    )
    with _make_client(handler) as client:
        result = client.list_devices()

    assert result.pumps == []
    assert result.densitometers == []
    assert result.valves == []
    assert result.discovered_at is None


def test_unknown_device_type_is_skipped():
    response = {
        "devices": [
            {"id": "pump_1", "type": "pump", "type_code": 10, "port": "COM3"},
            {"id": "thing_1", "type": "thing", "type_code": 99, "port": "COM9"},
        ],
        "discovered_at": "2026-04-26T12:34:56Z",
    }
    handler = _discovery_handler(response, {"response": [10, 0, 0, 100]})
    with _make_client(handler) as client:
        result = client.discover()

    assert len(result.pumps) == 1
    assert len(result.densitometers) == 0
    assert len(result.valves) == 0


def test_discover_raises_discovery_in_progress():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "discovery in progress", "detail": ""})

    with _make_client(handler) as client:
        with pytest.raises(DiscoveryInProgress):
            client.discover()


def test_discover_raises_discovery_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "discovery failed", "detail": "USB enum error"})

    with _make_client(handler) as client:
        with pytest.raises(DiscoveryFailed) as exc_info:
            client.discover()

    assert exc_info.value.detail == "USB enum error"
