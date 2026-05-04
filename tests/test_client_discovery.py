"""Bridge-level client lookup behaviour for LabDevicesClient."""
from __future__ import annotations

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
