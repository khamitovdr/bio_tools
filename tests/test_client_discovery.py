"""Bridge-level client lookup behaviour for LabDevicesClient."""
from __future__ import annotations

from typing import Callable

import httpx
import pytest

from bioexperiment_suite.interfaces import lab_devices_client as ldc_mod
from bioexperiment_suite.interfaces.lab_devices_client import (
    ClientLookupEndpointError,
    ClientLookupEndpointUnreachable,
    ClientLookupError,
    LabDevicesClient,
    UnknownLabClient,
)


def test_exception_hierarchy_uses_separate_base():
    assert issubclass(ClientLookupEndpointUnreachable, ClientLookupError)
    assert issubclass(ClientLookupEndpointError, ClientLookupError)
    assert issubclass(UnknownLabClient, ClientLookupError)
    assert issubclass(ClientLookupError, Exception)


def test_unknown_lab_client_message_lists_available_names():
    exc = UnknownLabClient(name="khamit_desktp", available=["another_lab", "khamit_desktop"])
    assert exc.name == "khamit_desktp"
    assert exc.available == ["another_lab", "khamit_desktop"]
    text = str(exc)
    assert "khamit_desktp" in text
    assert "another_lab" in text
    assert "khamit_desktop" in text


@pytest.fixture
def mock_discovery(monkeypatch):
    """Patch _build_discovery_client to use httpx.MockTransport.

    Returns a setter: call set_handler(callable) to install the request handler
    used for subsequent _fetch_roster calls.
    """
    state: dict[str, Callable[[httpx.Request], httpx.Response]] = {
        "handler": lambda req: httpx.Response(200, json={}),
    }

    def factory(timeout: float) -> httpx.Client:
        return httpx.Client(
            transport=httpx.MockTransport(state["handler"]),
            timeout=timeout,
        )

    monkeypatch.setattr(ldc_mod, "_build_discovery_client", factory)

    def set_handler(handler: Callable[[httpx.Request], httpx.Response]) -> None:
        state["handler"] = handler

    return set_handler


def test_fetch_roster_returns_parsed_body(mock_discovery):
    roster = {
        "khamit_desktop": {"host": "chisel", "port": 8089},
        "another_lab": {"host": "chisel", "port": 8090},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "http://siteapp:8000/api/clients/"
        return httpx.Response(200, json=roster)

    mock_discovery(handler)

    result = ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)
    assert result == roster


def test_fetch_roster_connection_error_raises_unreachable(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused")

    mock_discovery(handler)

    with pytest.raises(ldc_mod.ClientLookupEndpointUnreachable) as info:
        ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)
    assert "siteapp" in str(info.value)


def test_fetch_roster_connect_timeout_raises_unreachable(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connect timed out")

    mock_discovery(handler)

    with pytest.raises(ldc_mod.ClientLookupEndpointUnreachable):
        ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)


def test_fetch_roster_read_timeout_raises_unreachable(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out")

    mock_discovery(handler)

    with pytest.raises(ldc_mod.ClientLookupEndpointUnreachable):
        ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)


def test_fetch_roster_5xx_raises_endpoint_error(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    mock_discovery(handler)

    with pytest.raises(ldc_mod.ClientLookupEndpointError) as info:
        ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)
    assert "500" in str(info.value)


def test_fetch_roster_non_200_raises_endpoint_error(mock_discovery):
    """The contract says 200 or 500. Anything else is a contract violation."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="not found")

    mock_discovery(handler)

    with pytest.raises(ldc_mod.ClientLookupEndpointError):
        ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)


def test_fetch_roster_invalid_json_raises_endpoint_error(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all")

    mock_discovery(handler)

    with pytest.raises(ldc_mod.ClientLookupEndpointError):
        ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)


def test_fetch_roster_non_object_body_raises_endpoint_error(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=["not", "a", "dict"])

    mock_discovery(handler)

    with pytest.raises(ldc_mod.ClientLookupEndpointError):
        ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)


def test_fetch_roster_malformed_entry_raises_endpoint_error(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"khamit_desktop": {"host": "chisel"}},  # missing port
        )

    mock_discovery(handler)

    with pytest.raises(ldc_mod.ClientLookupEndpointError) as info:
        ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)
    assert "khamit_desktop" in str(info.value)


def test_fetch_roster_wrong_typed_entry_raises_endpoint_error(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"khamit_desktop": {"host": "chisel", "port": "8089"}},  # port as str
        )

    mock_discovery(handler)

    with pytest.raises(ldc_mod.ClientLookupEndpointError):
        ldc_mod._fetch_roster("http://siteapp:8000/api/clients/", request_timeout_sec=5.0)


def test_resolve_discovery_url_returns_default_when_unset(monkeypatch):
    monkeypatch.delenv(ldc_mod.DISCOVERY_URL_ENV_VAR, raising=False)
    assert ldc_mod._resolve_discovery_url(None) == ldc_mod.DEFAULT_DISCOVERY_URL


def test_resolve_discovery_url_uses_env_var(monkeypatch):
    monkeypatch.setenv(ldc_mod.DISCOVERY_URL_ENV_VAR, "http://override.example/api/")
    assert ldc_mod._resolve_discovery_url(None) == "http://override.example/api/"


def test_resolve_discovery_url_explicit_arg_wins_over_env(monkeypatch):
    monkeypatch.setenv(ldc_mod.DISCOVERY_URL_ENV_VAR, "http://env.example/api/")
    assert (
        ldc_mod._resolve_discovery_url("http://arg.example/api/")
        == "http://arg.example/api/"
    )


def test_default_discovery_url_constant():
    assert ldc_mod.DEFAULT_DISCOVERY_URL == "http://siteapp:8000/api/clients/"


def test_discovery_url_env_var_constant():
    assert ldc_mod.DISCOVERY_URL_ENV_VAR == "LAB_DEVICES_DISCOVERY_URL"


def test_constructor_with_user_resolves_via_bridge(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "khamit_desktop": {"host": "chisel", "port": 8089},
                "another_lab": {"host": "chisel", "port": 8090},
            },
        )

    mock_discovery(handler)

    client = LabDevicesClient(user="khamit_desktop")
    try:
        assert client.host == "chisel"
        assert client.port == 8089
        assert str(client._http.base_url) == "http://chisel:8089"
    finally:
        client.close()


def test_constructor_with_user_passes_explicit_discovery_url(mock_discovery):
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json={"x": {"host": "chisel", "port": 1}})

    mock_discovery(handler)

    LabDevicesClient(
        user="x", discovery_url="http://custom.example/api/clients/"
    ).close()
    assert seen_urls == ["http://custom.example/api/clients/"]


def test_constructor_with_user_unknown_raises(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"another_lab": {"host": "chisel", "port": 8090}},
        )

    mock_discovery(handler)

    with pytest.raises(UnknownLabClient) as info:
        LabDevicesClient(user="khamit_desktp")
    assert info.value.name == "khamit_desktp"
    assert info.value.available == ["another_lab"]


def test_constructor_with_port_path_unaffected():
    """The original construction path keeps working without touching the bridge."""
    client = LabDevicesClient(port=9001)
    try:
        assert client.host == "chisel"
        assert client.port == 9001
        assert str(client._http.base_url) == "http://chisel:9001"
    finally:
        client.close()


def test_constructor_user_and_port_are_mutually_exclusive():
    with pytest.raises(TypeError, match="mutually exclusive"):
        LabDevicesClient(user="x", port=9001)


def test_constructor_requires_user_or_port():
    with pytest.raises(TypeError, match="either user= or port="):
        LabDevicesClient()


def test_constructor_host_cannot_combine_with_user():
    with pytest.raises(TypeError, match="host= cannot be combined with user="):
        LabDevicesClient(user="x", host="other")


def test_constructor_discovery_url_cannot_combine_with_port():
    with pytest.raises(TypeError, match="discovery_url= cannot be combined with port="):
        LabDevicesClient(port=9001, discovery_url="http://example/")


def test_constructor_rejects_positional_port():
    """The signature is keyword-only; positional args should be rejected."""
    with pytest.raises(TypeError):
        LabDevicesClient(9001)  # type: ignore[misc]


def test_list_registered_users_returns_sorted_keys(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "zeta_lab": {"host": "chisel", "port": 8091},
                "alpha_lab": {"host": "chisel", "port": 8089},
                "mid_lab": {"host": "chisel", "port": 8090},
            },
        )

    mock_discovery(handler)

    assert LabDevicesClient.list_registered_users() == ["alpha_lab", "mid_lab", "zeta_lab"]


def test_list_registered_users_empty_roster(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    mock_discovery(handler)

    assert LabDevicesClient.list_registered_users() == []


def test_list_registered_users_propagates_bridge_unreachable(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    mock_discovery(handler)

    with pytest.raises(ClientLookupEndpointUnreachable):
        LabDevicesClient.list_registered_users()


def test_list_registered_users_uses_explicit_discovery_url(mock_discovery):
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json={})

    mock_discovery(handler)

    LabDevicesClient.list_registered_users(discovery_url="http://custom.example/api/")
    assert seen_urls == ["http://custom.example/api/"]


@pytest.fixture
def mock_probes(monkeypatch):
    """Patch _build_probe_client to use httpx.MockTransport per (host, port).

    Returns a setter: call set_handler(host, port, callable) to install a
    handler for that target. Unregistered targets behave as connection-refused.
    """
    handlers: dict[tuple[str, int], Callable[[httpx.Request], httpx.Response]] = {}

    def factory(host: str, port: int, timeout: float) -> httpx.Client:
        handler = handlers.get((host, port))
        if handler is None:
            def refused(_req: httpx.Request) -> httpx.Response:
                raise httpx.ConnectError("refused")
            handler = refused
        return httpx.Client(
            base_url=f"http://{host}:{port}",
            transport=httpx.MockTransport(handler),
            timeout=timeout,
        )

    monkeypatch.setattr(ldc_mod, "_build_probe_client", factory)

    def set_handler(host: str, port: int, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        handlers[(host, port)] = handler

    return set_handler


def _devices_ok_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/devices"
    return httpx.Response(200, json={"devices": [], "discovered_at": None})


def test_list_active_users_returns_only_responsive(mock_discovery, mock_probes):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "alive_lab": {"host": "chisel", "port": 8089},
                "refused_lab": {"host": "chisel", "port": 8090},
                "timeout_lab": {"host": "chisel", "port": 8091},
            },
        )

    mock_discovery(discovery_handler)
    mock_probes("chisel", 8089, _devices_ok_handler)
    # 8090 and 8091 are unregistered → default connection-refused behavior.
    # For timeout, override explicitly to make the intent obvious.

    def timeout_handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connect timed out")

    mock_probes("chisel", 8091, timeout_handler)

    active = LabDevicesClient.list_active_users()
    assert active == ["alive_lab"]


def test_list_active_users_treats_5xx_response_as_active(mock_discovery, mock_probes):
    """Any HTTP response (even 500) means the service is up."""

    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"unhappy_lab": {"host": "chisel", "port": 8089}}
        )

    def probe_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    mock_discovery(discovery_handler)
    mock_probes("chisel", 8089, probe_500)

    assert LabDevicesClient.list_active_users() == ["unhappy_lab"]


def test_list_active_users_treats_4xx_response_as_active(mock_discovery, mock_probes):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"weird_lab": {"host": "chisel", "port": 8089}}
        )

    def probe_404(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    mock_discovery(discovery_handler)
    mock_probes("chisel", 8089, probe_404)

    assert LabDevicesClient.list_active_users() == ["weird_lab"]


def test_list_active_users_returns_sorted(mock_discovery, mock_probes):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "zeta_lab": {"host": "chisel", "port": 8091},
                "alpha_lab": {"host": "chisel", "port": 8089},
            },
        )

    mock_discovery(discovery_handler)
    mock_probes("chisel", 8089, _devices_ok_handler)
    mock_probes("chisel", 8091, _devices_ok_handler)

    assert LabDevicesClient.list_active_users() == ["alpha_lab", "zeta_lab"]


def test_list_active_users_empty_roster(mock_discovery):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    mock_discovery(discovery_handler)
    assert LabDevicesClient.list_active_users() == []


def test_list_active_users_propagates_bridge_unreachable(mock_discovery):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    mock_discovery(discovery_handler)
    with pytest.raises(ClientLookupEndpointUnreachable):
        LabDevicesClient.list_active_users()


def test_list_active_users_propagates_bridge_500(mock_discovery):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    mock_discovery(discovery_handler)
    with pytest.raises(ClientLookupEndpointError):
        LabDevicesClient.list_active_users()
