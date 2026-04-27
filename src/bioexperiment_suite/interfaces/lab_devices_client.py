"""HTTP client for the lab_devices_client Go service."""
from __future__ import annotations


class LabDevicesError(Exception):
    """Base for every error raised by the lab_devices HTTP client."""

    def __init__(self, status: int, code: str, detail: str):
        self.status = status
        self.code = code
        self.detail = detail
        super().__init__(f"[{status}] {code}: {detail}" if detail else f"[{status}] {code}")


class InvalidRequest(LabDevicesError):
    """400 — invalid request body or query parameter."""


class DeviceNotFound(LabDevicesError):
    """404 — the requested device id is not in the registry."""


class DeviceBusy(LabDevicesError):
    """409 — another caller currently holds the device's mutex."""


class DiscoveryInProgress(LabDevicesError):
    """409 — a discovery pass is already running."""


class DiscoveryFailed(LabDevicesError):
    """500 — the service could not enumerate ports."""


class DeviceUnreachable(LabDevicesError):
    """503 — the service could not re-open the device's serial port."""


class DeviceIOFailed(LabDevicesError):
    """503 — generic device I/O failure that the server could not recover from."""


class DeviceIdentityChanged(LabDevicesError):
    """503 — the device's identity changed on the wire; it has been removed from the registry."""


class TransportError(LabDevicesError):
    """Network-level failure (connection refused, timeout, malformed response).

    `status` is 0 because no HTTP response was completed. `code` is one of
    "connection error", "read timeout", "invalid response".
    """
