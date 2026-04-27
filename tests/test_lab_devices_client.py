"""LabDevicesClient HTTP behaviour, exercised through httpx.MockTransport."""
from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import parse_qsl

import httpx
import pytest

from bioexperiment_suite.interfaces.lab_devices_client import (
    LabDevicesClient,
    DeviceBusy,
    DeviceIOFailed,
    DeviceIdentityChanged,
    DeviceNotFound,
    DeviceUnreachable,
    DiscoveryFailed,
    DiscoveryInProgress,
    InvalidRequest,
    TransportError,
)


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> LabDevicesClient:
    """Build a LabDevicesClient whose transport is an in-memory MockTransport."""
    client = LabDevicesClient(port=9001)
    client._http.close()
    client._http = httpx.Client(
        base_url="http://chisel:9001",
        timeout=5.0,
        transport=httpx.MockTransport(handler),
    )
    return client


def test_constructor_uses_chisel_default_host():
    client = LabDevicesClient(port=9001)
    assert str(client._http.base_url) == "http://chisel:9001"
    client.close()


def test_constructor_overrides_host():
    client = LabDevicesClient(host="localhost", port=8080)
    assert str(client._http.base_url) == "http://localhost:8080"
    client.close()


def test_context_manager_closes_http_client():
    with LabDevicesClient(port=9001) as client:
        assert client._http.is_closed is False
    assert client._http.is_closed is True


def test_send_command_happy_path_and_query_omits_optional_params():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        captured["query"] = dict(parse_qsl(request.url.query.decode()))
        return httpx.Response(200, json={"response": [10, 1, 2, 3]})

    with _make_client(handler) as client:
        result = client.send_command(
            "pump_1",
            command=[1, 2, 3, 4, 0],
            wait_for_response=True,
            expected_response_bytes=4,
        )

    assert result == [10, 1, 2, 3]
    assert "/devices/pump_1/command" in captured["url"]
    assert captured["body"] == {"command": [1, 2, 3, 4, 0]}
    assert captured["query"] == {"wait_for_response": "true", "expected_response_bytes": "4"}


def test_send_command_omits_expected_response_bytes_when_no_wait():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(parse_qsl(request.url.query.decode()))
        return httpx.Response(200, json={"response": []})

    with _make_client(handler) as client:
        result = client.send_command("pump_1", command=[16, 0, 0, 1, 0], wait_for_response=False)

    assert result == []
    assert captured["query"] == {"wait_for_response": "false"}
    assert "expected_response_bytes" not in captured["query"]


def test_send_command_passes_optional_timeout_overrides():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(parse_qsl(request.url.query.decode()))
        return httpx.Response(200, json={"response": [10, 0, 0, 0]})

    with _make_client(handler) as client:
        client.send_command(
            "pump_1",
            command=[1, 2, 3, 4, 0],
            wait_for_response=True,
            expected_response_bytes=4,
            timeout_ms=2000,
            inter_byte_ms=75,
        )

    assert captured["query"]["timeout_ms"] == "2000"
    assert captured["query"]["inter_byte_ms"] == "75"


@pytest.mark.parametrize(
    "status, code, exc_cls",
    [
        (400, "invalid request body", InvalidRequest),
        (400, "invalid query param", InvalidRequest),
        (404, "device not found", DeviceNotFound),
        (409, "device busy", DeviceBusy),
        (409, "discovery in progress", DiscoveryInProgress),
        (500, "discovery failed", DiscoveryFailed),
        (503, "device unreachable", DeviceUnreachable),
        (503, "device i/o failed", DeviceIOFailed),
        (503, "device identity changed", DeviceIdentityChanged),
    ],
)
def test_send_command_maps_http_errors_to_exceptions(status, code, exc_cls):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": code, "detail": "details here"})

    with _make_client(handler) as client:
        with pytest.raises(exc_cls) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.status == status
    assert exc_info.value.code == code
    assert exc_info.value.detail == "details here"


def test_send_command_translates_connect_error_to_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with _make_client(handler) as client:
        with pytest.raises(TransportError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.status == 0
    assert exc_info.value.code == "connection error"


def test_send_command_translates_read_timeout_to_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out")

    with _make_client(handler) as client:
        with pytest.raises(TransportError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.code == "read timeout"


def test_send_command_translates_connect_timeout_to_connection_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connect timed out")

    with _make_client(handler) as client:
        with pytest.raises(TransportError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.code == "connection error"


def test_send_command_translates_write_timeout_to_read_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.WriteTimeout("write timed out")

    with _make_client(handler) as client:
        with pytest.raises(TransportError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.code == "read timeout"


def test_send_command_translates_invalid_json_to_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all")

    with _make_client(handler) as client:
        with pytest.raises(TransportError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.code == "invalid response"


def test_unknown_error_status_raises_lab_devices_error():
    """A status the server shouldn't ever return still raises a typed error."""
    from bioexperiment_suite.interfaces.lab_devices_client import LabDevicesError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(418, json={"error": "i'm a teapot", "detail": ""})

    with _make_client(handler) as client:
        with pytest.raises(LabDevicesError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.status == 418
