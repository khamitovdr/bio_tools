"""HTTP client for the lab_devices_client Go service."""
from __future__ import annotations


class LabDevicesError(Exception):
    """Base for every error raised by the lab_devices HTTP client."""

    def __init__(self, status: int, code: str, detail: str):
        self.status = status
        self.code = code
        self.detail = detail
        super().__init__(f"[{status}] {code}: {detail}" if detail else f"[{status}] {code}")

    def __reduce__(self):
        return (self.__class__, (self.status, self.code, self.detail))


class InvalidRequest(LabDevicesError):
    """400 — invalid request body or query parameter.

    Server `error` codes: ``"invalid request body"``, ``"invalid query param"``.
    """


class DeviceNotFound(LabDevicesError):
    """404 — the requested device id is not in the registry.

    Server `error` code: ``"device not found"``.
    """


class DeviceBusy(LabDevicesError):
    """409 — another caller currently holds the device's mutex.

    Server `error` code: ``"device busy"``.
    """


class DiscoveryInProgress(LabDevicesError):
    """409 — a discovery pass is already running.

    Server `error` code: ``"discovery in progress"``.
    """


class DiscoveryFailed(LabDevicesError):
    """500 — the service could not enumerate ports.

    Server `error` code: ``"discovery failed"``.
    """


class DeviceUnreachable(LabDevicesError):
    """503 — the service could not re-open the device's serial port.

    Server `error` code: ``"device unreachable"``.
    """


class DeviceIOFailed(LabDevicesError):
    """503 — generic device I/O failure that the server could not recover from.

    Server `error` code: ``"device i/o failed"``.
    """


class DeviceIdentityChanged(LabDevicesError):
    """503 — the device's identity changed on the wire; it has been removed from the registry.

    Server `error` code: ``"device identity changed"``.
    """


class TransportError(LabDevicesError):
    """Network-level failure (connection refused, timeout, malformed response).

    `status` is 0 because no HTTP response was completed. `code` is one of
    "connection error", "read timeout", "invalid response".
    """
