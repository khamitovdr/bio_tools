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
