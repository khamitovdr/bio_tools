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
