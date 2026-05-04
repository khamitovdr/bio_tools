"""HTTP client for the lab_devices_client Go service."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx

from bioexperiment_suite.loader import logger


# --- exception hierarchy ---

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


# --- bridge-level discovery errors (parallel hierarchy) ---


class ClientLookupError(Exception):
    """Bridge-level discovery failure.

    Distinct from LabDevicesError (which models HTTP errors from the
    lab_devices_client service itself). Lookup errors come from the
    lab-bridge roster endpoint, a different system.
    """


class ClientLookupEndpointUnreachable(ClientLookupError):
    """Bridge endpoint refused the connection or timed out.

    Typical cause: the caller is not on the docker `labnet` network.
    Surfaced as a configuration error, not a generic ConnectionError.
    """


class ClientLookupEndpointError(ClientLookupError):
    """Bridge returned 5xx, or the response body was missing/non-JSON/wrong shape."""


class UnknownLabClient(ClientLookupError):
    """Requested user name is not in the bridge roster."""

    def __init__(self, name: str, available: list[str]):
        self.name = name
        self.available = available
        super().__init__(f"unknown lab client {name!r}; available: {available}")


# --- discovery helpers ---


def _build_discovery_client(timeout: float) -> httpx.Client:
    """Factory for the short-lived client used to fetch the bridge roster.

    Module-level so tests can monkeypatch it to inject a MockTransport.
    """
    return httpx.Client(timeout=timeout)


def _fetch_roster(discovery_url: str, request_timeout_sec: float) -> dict[str, dict[str, Any]]:
    """GET the bridge endpoint and return the parsed roster.

    Raises ClientLookupEndpointUnreachable / ClientLookupEndpointError.
    Does NOT raise UnknownLabClient — caller decides whether a missing
    user is fatal (constructor) or just absent (listing).
    """
    with _build_discovery_client(request_timeout_sec) as client:
        try:
            response = client.get(discovery_url)
        except (
            httpx.ConnectError,
            httpx.ConnectTimeout,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ) as exc:
            raise ClientLookupEndpointUnreachable(
                f"discovery endpoint unreachable at {discovery_url}: {exc}"
            ) from exc

    if response.status_code != 200:
        body_excerpt = response.text[:200]
        raise ClientLookupEndpointError(
            f"discovery endpoint at {discovery_url} returned status "
            f"{response.status_code}: {body_excerpt}"
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise ClientLookupEndpointError(
            f"discovery endpoint at {discovery_url} returned invalid JSON: {exc}"
        ) from exc

    if not isinstance(body, dict):
        raise ClientLookupEndpointError(
            f"discovery endpoint at {discovery_url} returned non-object body: "
            f"{type(body).__name__}"
        )

    for name, entry in body.items():
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("host"), str)
            or not isinstance(entry.get("port"), int)
        ):
            raise ClientLookupEndpointError(
                f"discovery endpoint at {discovery_url} returned malformed entry "
                f"for {name!r}: {entry!r}"
            )

    return body


# --- error mapping ---

_ERROR_CODE_TO_EXCEPTION: dict[tuple[int, str], type[LabDevicesError]] = {
    (400, "invalid request body"): InvalidRequest,
    (400, "invalid query param"): InvalidRequest,
    (404, "device not found"): DeviceNotFound,
    (409, "device busy"): DeviceBusy,
    (409, "discovery in progress"): DiscoveryInProgress,
    (500, "discovery failed"): DiscoveryFailed,
    (503, "device unreachable"): DeviceUnreachable,
    (503, "device i/o failed"): DeviceIOFailed,
    (503, "device identity changed"): DeviceIdentityChanged,
}


# --- client ---

class LabDevicesClient:
    """HTTP client for the lab_devices_client service.

    The constructor opens a single httpx.Client kept alive for the object's
    lifetime. Use as a context manager, or call close() explicitly.
    """

    def __init__(
        self,
        port: int,
        host: str = "chisel",
        request_timeout_sec: float = 5.0,
    ):
        self.host = host
        self.port = port
        self._http = httpx.Client(
            base_url=f"http://{host}:{port}",
            timeout=request_timeout_sec,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "LabDevicesClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def send_command(
        self,
        device_id: str,
        command: list[int],
        *,
        wait_for_response: bool,
        expected_response_bytes: int | None = None,
        timeout_ms: int | None = None,
        inter_byte_ms: int | None = None,
    ) -> list[int]:
        """Send a byte sequence to a discovered device and return its response bytes.

        Query-parameter policy:
          * `wait_for_response` is always sent (callers always pass it).
          * `expected_response_bytes` is sent only when `wait_for_response=True`
            and the caller passed a value.
          * `timeout_ms` and `inter_byte_ms` are sent only when explicitly passed
            (otherwise the server's context-dependent defaults apply).
        """
        params: dict[str, str] = {"wait_for_response": "true" if wait_for_response else "false"}
        if wait_for_response and expected_response_bytes is not None:
            params["expected_response_bytes"] = str(expected_response_bytes)
        if timeout_ms is not None:
            params["timeout_ms"] = str(timeout_ms)
        if inter_byte_ms is not None:
            params["inter_byte_ms"] = str(inter_byte_ms)

        path = f"/devices/{device_id}/command"
        body = {"command": command}
        data = self._request("POST", path, json=body, params=params)
        response = data.get("response", [])
        return list(response)

    def discover(self) -> "DiscoveredDevices":
        data = self._request("POST", "/discover")
        return self._build_devices(data)

    def list_devices(self) -> "DiscoveredDevices":
        data = self._request("GET", "/devices")
        return self._build_devices(data)

    def _build_devices(self, data: dict) -> "DiscoveredDevices":
        # Local imports prevent a circular dep with pump/densitometer/valve modules.
        from .pump import Pump
        from .densitometer import Densitometer
        from .valve import Valve

        pumps: list[Pump] = []
        densitometers: list[Densitometer] = []
        valves: list[Valve] = []
        for entry in data.get("devices", []):
            kind = entry.get("type")
            device_id = entry["id"]
            port = entry["port"]
            if kind == "pump":
                pumps.append(Pump(self, device_id, port))
            elif kind == "densitometer":
                densitometers.append(Densitometer(self, device_id, port))
            elif kind == "valve":
                valves.append(Valve(self, device_id, port))
            else:
                logger.warning(f"Unknown device type from server: {kind!r} (id={device_id})")
        return DiscoveredDevices(
            pumps=pumps,
            densitometers=densitometers,
            valves=valves,
            discovered_at=_parse_iso(data.get("discovered_at")),
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Issue an HTTP request and return the parsed JSON body, raising on error."""
        logger.debug(f"{method} {path} params={params} body={json}")
        try:
            response = self._http.request(method, path, json=json, params=params)
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise TransportError(status=0, code="connection error", detail=str(exc)) from exc
        except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
            raise TransportError(status=0, code="read timeout", detail=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise TransportError(status=0, code="connection error", detail=str(exc)) from exc

        if response.status_code >= 400:
            self._raise_for_error_response(response)

        try:
            data = response.json()
        except ValueError as exc:
            raise TransportError(status=0, code="invalid response", detail=str(exc)) from exc
        logger.debug(f"{method} {path} -> {response.status_code} {data}")
        return data

    def _raise_for_error_response(self, response: httpx.Response) -> None:
        try:
            body = response.json()
        except ValueError:
            raise LabDevicesError(
                status=response.status_code,
                code="invalid response",
                detail=response.text,
            )
        code = body.get("error", "")
        detail = body.get("detail", "")
        exc_cls = _ERROR_CODE_TO_EXCEPTION.get((response.status_code, code), LabDevicesError)
        raise exc_cls(status=response.status_code, code=code, detail=detail)


@dataclass
class DiscoveredDevices:
    pumps: list["Pump"]
    densitometers: list["Densitometer"]
    valves: list["Valve"]
    discovered_at: datetime | None


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)
