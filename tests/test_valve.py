"""Valve placeholder."""
from __future__ import annotations

from bioexperiment_suite.interfaces.valve import Valve
from tests.conftest import FakeLabDevicesClient


def test_init_stores_identifiers_and_does_not_call_server():
    client = FakeLabDevicesClient()
    valve = Valve(client, "valve_1", "COM4")

    assert valve.client is client
    assert valve.device_id == "valve_1"
    assert valve.port == "COM4"
    assert client.calls == []


def test_valve_has_no_protocol_methods_yet():
    """Sanity check: until the wire protocol is documented, Valve must not pretend to support commands."""
    client = FakeLabDevicesClient()
    valve = Valve(client, "valve_1", "COM4")

    public_methods = [name for name in dir(valve) if not name.startswith("_") and callable(getattr(valve, name))]
    # The class itself should expose nothing callable beyond what's inherited from `object`.
    assert public_methods == []
