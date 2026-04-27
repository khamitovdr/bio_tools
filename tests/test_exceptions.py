"""Exception hierarchy for the lab_devices HTTP client."""
import pickle

import pytest

from bioexperiment_suite.interfaces.lab_devices_client import (
    LabDevicesError,
    InvalidRequest,
    DeviceNotFound,
    DeviceBusy,
    DiscoveryInProgress,
    DiscoveryFailed,
    DeviceUnreachable,
    DeviceIOFailed,
    DeviceIdentityChanged,
    TransportError,
)


@pytest.mark.parametrize(
    "exc_cls",
    [
        InvalidRequest,
        DeviceNotFound,
        DeviceBusy,
        DiscoveryInProgress,
        DiscoveryFailed,
        DeviceUnreachable,
        DeviceIOFailed,
        DeviceIdentityChanged,
        TransportError,
    ],
)
def test_subclasses_lab_devices_error(exc_cls):
    assert issubclass(exc_cls, LabDevicesError)
    assert issubclass(exc_cls, Exception)
    instance = exc_cls(status=0, code="x", detail="")
    assert isinstance(instance, LabDevicesError)


def test_attributes_are_set():
    err = DeviceBusy(status=409, code="device busy", detail="locked by another caller")
    assert err.status == 409
    assert err.code == "device busy"
    assert err.detail == "locked by another caller"


def test_str_includes_status_and_code():
    err = DeviceNotFound(status=404, code="device not found", detail="")
    s = str(err)
    assert "404" in s
    assert "device not found" in s


def test_str_includes_detail_when_present():
    err = DeviceBusy(status=409, code="device busy", detail="locked by another caller")
    s = str(err)
    assert "409" in s
    assert "device busy" in s
    assert "locked by another caller" in s


def test_pickle_roundtrip_preserves_attributes():
    err = DeviceBusy(status=409, code="device busy", detail="locked by another caller")
    restored = pickle.loads(pickle.dumps(err))
    assert isinstance(restored, DeviceBusy)
    assert restored.status == 409
    assert restored.code == "device busy"
    assert restored.detail == "locked by another caller"
    assert str(restored) == str(err)
