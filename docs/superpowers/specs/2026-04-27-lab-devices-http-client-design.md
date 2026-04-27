# Lab Devices HTTP Client — Design

**Status:** approved by user, ready for implementation plan
**Branch strategy:** this design is implemented on a dedicated branch; `main` keeps the existing direct-serial implementation. The two branches diverge — there is no runtime switch between transports.

## 1. Goal

Replace the project's local serial transport with an HTTP client that talks to `lab_devices_client`, a Go service on a lab machine reachable through a chisel reverse tunnel inside a docker-compose network. Discovery, port enumeration, and low-level serial communication move entirely server-side. The high-level `experiment/` package is intentionally untouched.

## 2. Scope

### Removed

- `interfaces/serial_connection.py` — pyserial transport.
- `tools/serial_port.py`, `tools/devices.py` — local discovery and identification. The `tools/` package is removed.
- `gui/` package, `gui.py` shim at the repo root, `[tool.poetry.scripts] run_gui` entry, the `[gui]` poetry extra, and the `ttkbootstrap` dependency.
- `pyserial` and `types-pyserial` dependencies.
- `settings.py`. `EMULATE_DEVICES`, `N_VIRTUAL_PUMPS`, `N_VIRTUAL_SPECTROPHOTOMETERS` and the `Settings` dataclass go with it. Server-side emulation makes client-side emulation unnecessary.

### Kept intact

- `experiment/` — transport-agnostic.
- `device_interfaces.json` — still the byte-level vocabulary for pump and densitometer commands. The server is byte-blind; the client owns the wire vocabulary.
- `loader.py` — same role (load JSON, set up loguru). Only the `spectrophotometer` JSON key changes (see rename).

### Renamed

`Spectrophotometer` → `Densitometer` everywhere: class names, module names, JSON key, examples, the notebook, and any imports. No alias — single canonical name.

### Edited

`device_interfaces.json`:

- Top-level key `"spectrophotometer"` → `"densitometer"`.
- `pump.identification_signal`: `[1, 2, 3, 4, 181]` → `[1, 2, 3, 4, 0]`. The pump replies identically to either probe, but using the universal probe `[1, 2, 3, 4, 0]` keeps a single shared probe across all device types and matches what the server already sent during discovery.

### Added

- `interfaces/lab_devices_client.py` — HTTP client + discovery factory + exception hierarchy.
- `interfaces/pump.py` — rewritten on top of `LabDevicesClient` (composition).
- `interfaces/densitometer.py` — replaces `spectrophotometer.py`.
- `interfaces/valve.py` — placeholder class (no methods); only purpose is being returned by `discover()` so the namespace is in place when the wire protocol is specified.
- `httpx = "^0.28"` dependency.
- `tests/` directory with the test layers described in §10.

## 3. Module layout (after the change)

```
src/bioexperiment_suite/
├── interfaces/
│   ├── __init__.py            # re-exports public API
│   ├── lab_devices_client.py  # LabDevicesClient, DiscoveredDevices, exceptions
│   ├── pump.py                # Pump
│   ├── densitometer.py        # Densitometer
│   └── valve.py               # Valve (placeholder)
├── experiment/                # unchanged
├── device_interfaces.json     # "spectrophotometer" → "densitometer"
└── loader.py                  # unchanged behavior
```

## 4. `LabDevicesClient`

Single class. Owns one `httpx.Client` instance for its lifetime, acts as the discovery factory, and exposes the low-level `send_command` escape hatch.

### 4.1 Constructor

```python
class LabDevicesClient:
    def __init__(
        self,
        port: int,                         # required
        host: str = "chisel",
        request_timeout_sec: float = 5.0,  # httpx connect+read timeout
    ): ...
```

`host` defaults to the docker-compose service name. The client is always run inside the docker-compose network — there is no external-host fallback.

### 4.2 Public methods

```python
def discover(self) -> DiscoveredDevices: ...    # POST /discover (destructive)
def list_devices(self) -> DiscoveredDevices: ... # GET  /devices  (cached)

def send_command(
    self,
    device_id: str,
    command: list[int],
    *,
    wait_for_response: bool,                  # always passed by callers
    expected_response_bytes: int | None = None,
    timeout_ms: int | None = None,            # default unless tuning
    inter_byte_ms: int | None = None,         # default unless tuning
) -> list[int]: ...

def close(self) -> None: ...                  # closes the httpx.Client
def __enter__(self) -> "LabDevicesClient": ...
def __exit__(self, *exc) -> None: ...
```

**Query-parameter policy for `send_command`:**

- `wait_for_response` is always set explicitly by callers (we know per-command).
- `expected_response_bytes` is set explicitly when `wait_for_response=True` and we know the reply length. When `wait_for_response=False`, the parameter is **omitted** from the request — the server ignores it in that mode and we don't send a stub value.
- `timeout_ms` and `inter_byte_ms` are server responsibility; callers pass them only when fine-tuning a specific call.

### 4.3 `DiscoveredDevices`

```python
@dataclass
class DiscoveredDevices:
    pumps: list[Pump]
    densitometers: list[Densitometer]
    valves: list[Valve]
    discovered_at: datetime | None  # None when /devices has never been probed server-side
```

`discover()` and `list_devices()` both return this dataclass. Devices come back already constructed and bound to the client. Callers do not instantiate `Pump`, `Densitometer`, or `Valve` directly.

### 4.4 Discovery internals

```python
def _build_devices(self, response: dict) -> DiscoveredDevices:
    pumps, densitometers, valves = [], [], []
    for entry in response["devices"]:
        match entry["type"]:
            case "pump":
                pumps.append(Pump(self, entry["id"], entry["port"]))   # __init__ runs calibration
            case "densitometer":
                densitometers.append(Densitometer(self, entry["id"], entry["port"]))
            case "valve":
                valves.append(Valve(self, entry["id"], entry["port"]))
            case other:
                logger.warning(f"Unknown device type from server: {other!r} (id={entry['id']})")
    return DiscoveredDevices(
        pumps=pumps,
        densitometers=densitometers,
        valves=valves,
        discovered_at=_parse_iso(response["discovered_at"]),
    )
```

Unknown device types are logged and skipped, not raised. Forward compatibility: when the server gains a new type, old clients keep working.

**Calibration cost:** every `discover()` and `list_devices()` call triggers one calibration HTTP round-trip per pump (see §5.1). For N pumps, N sequential round-trips — sub-second total under realistic lab loads.

## 5. Device classes

All three follow the same composition pattern. No transport inheritance.

### 5.1 `Pump`

```python
class Pump:
    def __init__(self, client: LabDevicesClient, device_id: str, port: str):
        self.client = client
        self.device_id = device_id            # e.g. "pump_1"
        self.port = port                      # e.g. "COM3" — informational
        self.interface = device_interfaces.pump
        self.default_flow_rate: float | None = None
        self._calibration_volume: float = self._compute_calibration_volume()

    def _compute_calibration_volume(self) -> float:
        # The universal probe [1, 2, 3, 4, 0] doubles as the calibration probe:
        # the pump replies with [type_code=10, a, b, c]; calibration_volume = int(a,b,c) / 1e5.
        response = self.client.send_command(
            self.device_id,
            self.interface.identification_signal,
            wait_for_response=True,
            expected_response_bytes=4,
        )
        return _bytes_to_int(response[1:]) / 10**5
        # _bytes_to_int / _int_to_bytes are module-level helpers in lab_devices_client.py
        # (lifted from today's SerialConnection methods, no behavior change).
```

Public API matches today's `Pump`:

| Method                         | wait_for_response | expected_response_bytes |
|---|---|---|
| `_compute_calibration_volume`  | `True`            | `4`                     |
| `_set_flow_rate`               | `False`           | omitted                 |
| `pour_in_volume`               | `False`           | omitted                 |
| `start_continuous_rotation`    | `False`           | omitted                 |
| `stop_continuous_rotation`     | (delegates to `pour_in_volume(0)`) | |

The blocking sleep inside `pour_in_volume` is preserved (`(volume / flow_rate) * 60 + UNACCOUNTED_FOR_TIME_SEC`).

### 5.2 `Densitometer`

```python
class Densitometer:
    def __init__(self, client, device_id, port):
        self.client = client
        self.device_id = device_id            # "densitometer_1"
        self.port = port
        self.interface = device_interfaces.densitometer

    def get_temperature(self) -> float: ...                  # wait=True, expected=4
    def measure_optical_density(self) -> float: ...          # internally:
                                                              # _send_start_measurement_command (wait=False, no expected)
                                                              # time.sleep(3)
                                                              # _get_optical_density (wait=True, expected=4)
```

Same return semantics as today's `Spectrophotometer`. The 3-second wait between start and read remains a client-side `time.sleep(3)`; the server is not involved.

### 5.3 `Valve`

```python
class Valve:
    """Placeholder. Wire protocol not yet specified."""
    def __init__(self, client: LabDevicesClient, device_id: str, port: str):
        self.client = client
        self.device_id = device_id            # "valve_1"
        self.port = port
        # No `interface` attribute — device_interfaces.json has no "valve" entry yet.
```

No methods. Until the protocol is documented, callers who need to drive a valve drop down to `client.send_command(valve.device_id, ...)` directly.

## 6. Exception hierarchy

```python
class LabDevicesError(Exception):
    def __init__(self, status: int, code: str, detail: str):
        self.status = status      # HTTP status
        self.code = code          # server's "error" field, or synthesized for transport errors
        self.detail = detail      # server's "detail" field

class InvalidRequest(LabDevicesError):         # 400 invalid request body / invalid query param
class DeviceNotFound(LabDevicesError):         # 404 device not found
class DeviceBusy(LabDevicesError):             # 409 device busy
class DiscoveryInProgress(LabDevicesError):    # 409 discovery in progress
class DiscoveryFailed(LabDevicesError):        # 500 discovery failed
class DeviceUnreachable(LabDevicesError):      # 503 device unreachable
class DeviceIOFailed(LabDevicesError):         # 503 device i/o failed
class DeviceIdentityChanged(LabDevicesError):  # 503 device identity changed
class TransportError(LabDevicesError):         # connection refused, read timeout,
                                               # malformed response body, etc.
                                               # status=0; code is one of:
                                               #   "connection error"  (httpx.ConnectError)
                                               #   "read timeout"      (httpx.ReadTimeout / TimeoutException)
                                               #   "invalid response"  (non-JSON body / missing fields)
```

`send_command()`, `discover()`, `list_devices()` raise from this hierarchy. **No automatic retry, no silent fallbacks** — the caller (or experiment-script logic) decides what to do. `try/except LabDevicesError` catches everything including transport-layer failures.

## 7. Logging

- `loguru` stays; format unchanged.
- `LabDevicesClient` logs each request/response at `DEBUG`: method, path, body, status, response body.
- Device classes preserve their existing log lines.

## 8. Configuration

There is no `Settings` class on this branch. The `LabDevicesClient` constructor takes `host` and `port` directly. Examples and the notebook hard-code or accept these values from the script's own argument-parsing.

## 9. Examples

Both `experiment_example.py` and `three_pumps_experiment.py`, plus `experiment_example.ipynb`, are rewritten in place:

```python
client = LabDevicesClient(port=9001)            # port supplied per lab machine
devices = client.discover()
pumps = devices.pumps
(densitometer,) = devices.densitometers          # exactly one expected
```

Identifiers in the scripts (`spectrophotometer`, `spectrophotometers`) become `densitometer`, `densitometers`. Variable bindings, log strings, and CSV column names all reflect the new name.

## 10. Tests

New `tests/` directory. Three layers:

1. **`LabDevicesClient` unit tests** using `httpx.MockTransport` (no network). Cover:
   - `discover()` and `list_devices()` parsing happy paths (including `discovered_at=null` from `GET /devices`).
   - Each documented error status → corresponding exception type, with `.status`, `.code`, `.detail` populated.
   - `TransportError` for connection refused, read timeout, malformed JSON.
   - Unknown device types in the response are skipped with a warning, others still constructed.
   - `send_command` query-parameter policy: `expected_response_bytes` omitted when `wait_for_response=False`; `timeout_ms` / `inter_byte_ms` omitted unless explicitly passed.

2. **Device-class unit tests** with a fake `LabDevicesClient` that records calls and returns canned bytes. Verifies:
   - `Pump.__init__` calls `send_command` with `[1,2,3,4,0]`, `wait=True`, `expected=4`, and computes `_calibration_volume` from the response.
   - Each public `Pump` method emits the right byte sequence with the right `wait_for_response` flag.
   - `Densitometer.get_temperature` parses temperature from `[?, ?, integer, fractional]`.
   - `Densitometer.measure_optical_density` issues start, sleeps, then reads (with `time.sleep` patched).

3. **Integration tests** against a real `lab_devices_client` instance: out of CI scope, run manually on a lab machine.

## 11. `pyproject.toml` deltas

- **Add:** `httpx = "^0.28"`.
- **Remove:** `pyserial`, `types-pyserial`, `ttkbootstrap`, the `[tool.poetry.extras] gui` block, the `[tool.poetry.scripts] run_gui` entry.
- **Bump:** `version = "0.5.0"` (breaking change: GUI dropped, serial transport replaced, device renamed).

## 12. Public API surface

`bioexperiment_suite.interfaces.__init__`:

```python
from .lab_devices_client import (
    LabDevicesClient,
    DiscoveredDevices,
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
from .pump import Pump
from .densitometer import Densitometer
from .valve import Valve

__all__ = [
    "LabDevicesClient", "DiscoveredDevices",
    "LabDevicesError", "InvalidRequest", "DeviceNotFound",
    "DeviceBusy", "DiscoveryInProgress", "DiscoveryFailed",
    "DeviceUnreachable", "DeviceIOFailed", "DeviceIdentityChanged", "TransportError",
    "Pump", "Densitometer", "Valve",
]
```

## 13. Non-goals on this branch

- No async API (the sync `httpx.Client` is used; async support is left for a later branch — `httpx` was chosen partly to keep that door open).
- No on-client caching of `/devices` results (the server already caches; an extra layer would be wrong).
- No automatic retry on `409 device busy` or `503 device unreachable` (caller decision).
- No GUI replacement on this branch.
- No valve protocol.
