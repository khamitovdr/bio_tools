# Lab Devices HTTP Client — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the project's pyserial transport with an HTTP client that talks to the `lab_devices_client` Go service, on a dedicated branch. Drop the GUI and local discovery; rename `Spectrophotometer` → `Densitometer`; preserve the `experiment/` package.

**Architecture:** A single `LabDevicesClient` owns one `httpx.Client`, performs discovery (`POST /discover`, `GET /devices`), exposes a low-level `send_command(device_id, ...)`, and acts as the factory that constructs `Pump`, `Densitometer`, and `Valve` instances bound to itself. Devices use composition (no transport inheritance). A typed exception hierarchy maps HTTP errors 1:1.

**Tech Stack:** Python 3.12 · `httpx` ^0.28 (sync) · `loguru` · `pytest` · `httpx.MockTransport` for tests · Poetry · existing `munch` for `device_interfaces` access.

**Spec:** `docs/superpowers/specs/2026-04-27-lab-devices-http-client-design.md`

---

## Task 1: Create the feature branch

**Files:** none

- [ ] **Step 1: Confirm we're on `main` and clean (apart from untracked dirs that should stay).**

```bash
cd /Users/khamitovdr/bio_tools
git status
git rev-parse --abbrev-ref HEAD
```
Expected: branch `main`, working tree clean apart from optional untracked `labdevices/` directory (out of scope).

- [ ] **Step 2: Create and switch to the feature branch.**

```bash
git checkout -b lab-devices-http-client
```
Expected: `Switched to a new branch 'lab-devices-http-client'`.

---

## Task 2: Update `pyproject.toml` for the new dependency stack

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Replace `pyproject.toml` with the new content.**

Read the current file first with `Read`, then `Write` the new content below:

```toml
[tool.ruff.lint]
fixable = ["ALL"]
unfixable = ["F401"]

[tool.ruff]
line-length = 120

[tool.poetry]
name = "bioexperiment-suite"
version = "0.5.0"
description = "Python toolbox for managing biological experiment devices via the lab_devices_client HTTP service."
license = "MIT"
authors = ["Denis Khamitov <hamitov.97@mail.ru>"]
readme = "README.md"
repository = "https://github.com/denis240997/bio_tools"
packages = [
    { include = "bioexperiment_suite", from = "src"},
]
include = [
    { path = "src/bioexperiment_suite/device_interfaces.json"},
    { path = "src/bioexperiment_suite/py.typed"},
]

[tool.poetry.dependencies]
python = ">=3.12,<3.13"
loguru = "^0.7.2"
munch = "^4.0.0"
httpx = "^0.28"
python-dotenv = "^1.0.1"

[tool.poetry.group.dev.dependencies]
munch-stubs = "^0.1.2"
ruff = "^0.5.4"
notebook = "^7.3.1"
pyinstaller = "^6.9.0"
nbstripout = "^0.8.1"
pre-commit = "^4.0.1"
ipykernel = "^7.2.0"
pytest = "^8.3"

[tool.poetry.group.docs]
optional = true

[tool.poetry.group.docs.dependencies]
mkdocs-material = "^9.5.30"
mkdocstrings = {extras = ["python"], version = "^0.25.2"}

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

Changes vs. the previous file:
- `version`: `0.4.1` → `0.5.0`.
- `description`: rewritten.
- Removed deps: `pyserial`, `ttkbootstrap`, `types-pyserial`.
- Removed: `[tool.poetry.extras] gui` block, `[tool.poetry.scripts] run_gui` entry.
- Added: `httpx = "^0.28"` (runtime), `pytest = "^8.3"` (dev).

- [ ] **Step 2: Regenerate the lock file.**

```bash
poetry lock
```
Expected: `Resolving dependencies...` followed by `Writing lock file`. No errors.

- [ ] **Step 3: Install.**

```bash
poetry install
```
Expected: installs `httpx` (and its deps `httpcore`, `h11`, `anyio`, `idna`, `sniffio`, `certifi`) and `pytest` (and `pluggy`, `iniconfig`, `packaging`); removes `pyserial`, `ttkbootstrap`, `types-pyserial`, plus their transitive deps. Exit 0.

- [ ] **Step 4: Sanity check that `httpx` imports.**

```bash
poetry run python -c "import httpx; print(httpx.__version__)"
```
Expected: prints a `0.28.x` version.

- [ ] **Step 5: Commit.**

```bash
git add pyproject.toml poetry.lock
git commit -m "Switch deps: drop pyserial/ttkbootstrap, add httpx and pytest"
```

---

## Task 3: Delete the obsolete code

After this task, the package is intentionally broken until later tasks add the new modules. That's fine — we won't run tests until Task 5.

**Files:**
- Delete: `src/bioexperiment_suite/interfaces/serial_connection.py`
- Delete: `src/bioexperiment_suite/interfaces/spectrophotometer.py`
- Delete: `src/bioexperiment_suite/interfaces/pump.py`
- Delete: `src/bioexperiment_suite/settings.py`
- Delete: `src/bioexperiment_suite/tools/` (entire package)
- Delete: `src/bioexperiment_suite/gui/` (entire package)
- Delete: `gui.py` (repo-root shim)
- Modify: `src/bioexperiment_suite/interfaces/__init__.py` — temporarily empty

- [ ] **Step 1: Remove deleted files via git.**

```bash
git rm \
  src/bioexperiment_suite/interfaces/serial_connection.py \
  src/bioexperiment_suite/interfaces/spectrophotometer.py \
  src/bioexperiment_suite/interfaces/pump.py \
  src/bioexperiment_suite/settings.py \
  gui.py
git rm -r src/bioexperiment_suite/tools src/bioexperiment_suite/gui
```
Expected: each `rm` echoes the deleted file/directory.

- [ ] **Step 2: Replace `src/bioexperiment_suite/interfaces/__init__.py` with an empty placeholder.**

Use `Write` with this content:

```python
# Module contents added in later tasks.
```

- [ ] **Step 3: Confirm the package still imports `experiment` (the part we kept).**

```bash
poetry run python -c "from bioexperiment_suite.experiment import Experiment, Condition; print('ok')"
```
Expected: prints `ok`.

- [ ] **Step 4: Commit.**

```bash
git add -A
git commit -m "Remove serial transport, GUI, local discovery, and Settings"
```

---

## Task 4: Update `device_interfaces.json`

**Files:**
- Modify: `src/bioexperiment_suite/device_interfaces.json`

- [ ] **Step 1: Read the file with `Read`, then apply two edits with `Edit`.**

Edit A — change the pump's identification probe to the universal probe `[1, 2, 3, 4, 0]`:

```
old_string:
    "pump": {
        "type": "pump",
        "identification_signal": [
            1,
            2,
            3,
            4,
            181
        ],

new_string:
    "pump": {
        "type": "pump",
        "identification_signal": [
            1,
            2,
            3,
            4,
            0
        ],
```

Edit B — rename the top-level key `spectrophotometer` to `densitometer`:

```
old_string:
    "spectrophotometer": {
        "type": "cell density detector",

new_string:
    "densitometer": {
        "type": "densitometer",
```

(The `"type"` field also changes from `"cell density detector"` to `"densitometer"` so consumer log lines read correctly.)

- [ ] **Step 2: Verify the JSON is still valid.**

```bash
poetry run python -c "import json; json.load(open('src/bioexperiment_suite/device_interfaces.json')); print('ok')"
```
Expected: `ok`.

- [ ] **Step 3: Verify the `device_interfaces` munch object exposes both keys correctly.**

```bash
poetry run python -c "from bioexperiment_suite.loader import device_interfaces; print(list(device_interfaces.keys())); print(device_interfaces.pump.identification_signal); print(device_interfaces.densitometer.commands.get_temperature.request)"
```
Expected output:
```
['pump', 'densitometer']
[1, 2, 3, 4, 0]
[76, 0, 0, 0, 0]
```

- [ ] **Step 4: Commit.**

```bash
git add src/bioexperiment_suite/device_interfaces.json
git commit -m "Rename spectrophotometer → densitometer in device_interfaces.json; align pump probe with universal probe"
```

---

## Task 5: Set up the `tests/` directory

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Modify: `pyproject.toml` (add `[tool.pytest.ini_options]`)

- [ ] **Step 1: Create `tests/__init__.py` empty.**

Use `Write` with content `""` (empty file is fine).

- [ ] **Step 2: Create `tests/conftest.py`.**

```python
"""Shared pytest fixtures."""
import pytest
```

(Empty for now; later tasks add fixtures here.)

- [ ] **Step 3: Add a pytest config block to `pyproject.toml`.**

`Edit` `pyproject.toml`:

```
old_string:
[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

new_string:
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 4: Confirm pytest collects (zero tests is OK).**

```bash
poetry run pytest --collect-only
```
Expected: `collected 0 items`, exit 0.

- [ ] **Step 5: Commit.**

```bash
git add tests/__init__.py tests/conftest.py pyproject.toml
git commit -m "Add tests/ scaffolding and pytest config"
```

---

## Task 6: Implement the exception hierarchy (TDD)

**Files:**
- Create: `tests/test_exceptions.py`
- Create: `src/bioexperiment_suite/interfaces/lab_devices_client.py`

- [ ] **Step 1: Write the failing test.**

`Write` `tests/test_exceptions.py`:

```python
"""Exception hierarchy for the lab_devices HTTP client."""
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
```

- [ ] **Step 2: Run the test — must fail with import error.**

```bash
poetry run pytest tests/test_exceptions.py -v
```
Expected: `ImportError` / `ModuleNotFoundError` for `lab_devices_client`.

- [ ] **Step 3: Implement the minimal exception module.**

`Write` `src/bioexperiment_suite/interfaces/lab_devices_client.py`:

```python
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
```

- [ ] **Step 4: Run the test again.**

```bash
poetry run pytest tests/test_exceptions.py -v
```
Expected: 11 passed (9 parametrized + 2 individual).

- [ ] **Step 5: Commit.**

```bash
git add tests/test_exceptions.py src/bioexperiment_suite/interfaces/lab_devices_client.py
git commit -m "Add LabDevicesError hierarchy"
```

---

## Task 7: Implement `LabDevicesClient.send_command` (TDD with httpx.MockTransport)

This task adds the constructor, lifecycle, and the central `send_command` method. Discovery comes in Task 8.

**Files:**
- Create: `tests/test_lab_devices_client.py`
- Modify: `src/bioexperiment_suite/interfaces/lab_devices_client.py`

- [ ] **Step 1: Write failing tests.**

`Write` `tests/test_lab_devices_client.py`:

```python
"""LabDevicesClient HTTP behaviour, exercised through httpx.MockTransport."""
from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import parse_qsl

import httpx
import pytest

from bioexperiment_suite.interfaces.lab_devices_client import (
    LabDevicesClient,
    DeviceBusy,
    DeviceIOFailed,
    DeviceIdentityChanged,
    DeviceNotFound,
    DeviceUnreachable,
    DiscoveryFailed,
    DiscoveryInProgress,
    InvalidRequest,
    TransportError,
)


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> LabDevicesClient:
    """Build a LabDevicesClient whose transport is an in-memory MockTransport."""
    client = LabDevicesClient(port=9001)
    client._http.close()
    client._http = httpx.Client(
        base_url="http://chisel:9001",
        timeout=5.0,
        transport=httpx.MockTransport(handler),
    )
    return client


def test_constructor_uses_chisel_default_host():
    client = LabDevicesClient(port=9001)
    assert str(client._http.base_url) == "http://chisel:9001"
    client.close()


def test_constructor_overrides_host():
    client = LabDevicesClient(host="localhost", port=8080)
    assert str(client._http.base_url) == "http://localhost:8080"
    client.close()


def test_context_manager_closes_http_client():
    with LabDevicesClient(port=9001) as client:
        assert client._http.is_closed is False
    assert client._http.is_closed is True


def test_send_command_happy_path_and_query_omits_optional_params():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        captured["query"] = dict(parse_qsl(request.url.query.decode()))
        return httpx.Response(200, json={"response": [10, 1, 2, 3]})

    with _make_client(handler) as client:
        result = client.send_command(
            "pump_1",
            command=[1, 2, 3, 4, 0],
            wait_for_response=True,
            expected_response_bytes=4,
        )

    assert result == [10, 1, 2, 3]
    assert "/devices/pump_1/command" in captured["url"]
    assert captured["body"] == {"command": [1, 2, 3, 4, 0]}
    assert captured["query"] == {"wait_for_response": "true", "expected_response_bytes": "4"}


def test_send_command_omits_expected_response_bytes_when_no_wait():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(parse_qsl(request.url.query.decode()))
        return httpx.Response(200, json={"response": []})

    with _make_client(handler) as client:
        result = client.send_command("pump_1", command=[16, 0, 0, 1, 0], wait_for_response=False)

    assert result == []
    assert captured["query"] == {"wait_for_response": "false"}
    assert "expected_response_bytes" not in captured["query"]


def test_send_command_passes_optional_timeout_overrides():
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["query"] = dict(parse_qsl(request.url.query.decode()))
        return httpx.Response(200, json={"response": [10, 0, 0, 0]})

    with _make_client(handler) as client:
        client.send_command(
            "pump_1",
            command=[1, 2, 3, 4, 0],
            wait_for_response=True,
            expected_response_bytes=4,
            timeout_ms=2000,
            inter_byte_ms=75,
        )

    assert captured["query"]["timeout_ms"] == "2000"
    assert captured["query"]["inter_byte_ms"] == "75"


@pytest.mark.parametrize(
    "status, code, exc_cls",
    [
        (400, "invalid request body", InvalidRequest),
        (400, "invalid query param", InvalidRequest),
        (404, "device not found", DeviceNotFound),
        (409, "device busy", DeviceBusy),
        (409, "discovery in progress", DiscoveryInProgress),
        (500, "discovery failed", DiscoveryFailed),
        (503, "device unreachable", DeviceUnreachable),
        (503, "device i/o failed", DeviceIOFailed),
        (503, "device identity changed", DeviceIdentityChanged),
    ],
)
def test_send_command_maps_http_errors_to_exceptions(status, code, exc_cls):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json={"error": code, "detail": "details here"})

    with _make_client(handler) as client:
        with pytest.raises(exc_cls) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.status == status
    assert exc_info.value.code == code
    assert exc_info.value.detail == "details here"


def test_send_command_translates_connect_error_to_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused")

    with _make_client(handler) as client:
        with pytest.raises(TransportError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.status == 0
    assert exc_info.value.code == "connection error"


def test_send_command_translates_read_timeout_to_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("read timed out")

    with _make_client(handler) as client:
        with pytest.raises(TransportError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.code == "read timeout"


def test_send_command_translates_invalid_json_to_transport_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not json at all")

    with _make_client(handler) as client:
        with pytest.raises(TransportError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.code == "invalid response"


def test_unknown_error_status_raises_lab_devices_error():
    """A status the server shouldn't ever return still raises a typed error."""
    from bioexperiment_suite.interfaces.lab_devices_client import LabDevicesError

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(418, json={"error": "i'm a teapot", "detail": ""})

    with _make_client(handler) as client:
        with pytest.raises(LabDevicesError) as exc_info:
            client.send_command("pump_1", command=[1, 2, 3, 4, 0], wait_for_response=False)

    assert exc_info.value.status == 418
```

- [ ] **Step 2: Run tests, expect failures (no client implementation yet).**

```bash
poetry run pytest tests/test_lab_devices_client.py -v
```
Expected: every test fails (import / attribute errors).

- [ ] **Step 3: Implement the client.**

`Edit` `src/bioexperiment_suite/interfaces/lab_devices_client.py` — append the following at the end of the file (after the last exception class):

```python
import json
from typing import Any

import httpx

from bioexperiment_suite.loader import logger


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
        logger.debug(f"POST {path} params={params} body={body}")
        data = self._request("POST", path, json=body, params=params)
        response = data.get("response", [])
        logger.debug(f"POST {path} response={response}")
        return list(response)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Issue an HTTP request and return the parsed JSON body, raising on error."""
        try:
            response = self._http.request(method, path, json=json, params=params)
        except httpx.ConnectError as exc:
            raise TransportError(status=0, code="connection error", detail=str(exc)) from exc
        except (httpx.ReadTimeout, httpx.TimeoutException) as exc:
            raise TransportError(status=0, code="read timeout", detail=str(exc)) from exc
        except httpx.HTTPError as exc:
            raise TransportError(status=0, code="connection error", detail=str(exc)) from exc

        if response.status_code >= 400:
            self._raise_for_error_response(response)

        try:
            return response.json()
        except ValueError as exc:
            raise TransportError(status=0, code="invalid response", detail=str(exc)) from exc

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
```

(Note: place the `import json`, `from typing import Any`, `import httpx`, and `from bioexperiment_suite.loader import logger` lines at the top of the file with the other imports — combine them with the existing `from __future__ import annotations` line. The structure when finished should be: future-import → stdlib/third-party imports → exception hierarchy → mapping table → `LabDevicesClient`.)

- [ ] **Step 4: Run tests.**

```bash
poetry run pytest tests/test_lab_devices_client.py -v
```
Expected: all tests pass (count varies with parametrization; all green).

- [ ] **Step 5: Run the full suite.**

```bash
poetry run pytest -v
```
Expected: all green, no errors.

- [ ] **Step 6: Commit.**

```bash
git add tests/test_lab_devices_client.py src/bioexperiment_suite/interfaces/lab_devices_client.py
git commit -m "Implement LabDevicesClient.send_command with typed error mapping"
```

---

## Task 8: Implement `discover()` and `list_devices()` (TDD)

This task introduces the `DiscoveredDevices` dataclass and the discovery factory. To avoid an order-of-construction problem (the factory needs to instantiate `Pump`/`Densitometer`/`Valve`, which don't exist yet), this task uses **temporary local stub classes** inside `lab_devices_client.py`. Tasks 9–11 replace them with real classes in their own modules.

**Files:**
- Modify: `src/bioexperiment_suite/interfaces/lab_devices_client.py`
- Create: `tests/test_discovery.py`

- [ ] **Step 1: Write failing tests.**

`Write` `tests/test_discovery.py`:

```python
"""Discovery factory: POST /discover and GET /devices."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import httpx
import pytest

from bioexperiment_suite.interfaces.lab_devices_client import (
    LabDevicesClient,
    DiscoveredDevices,
    DiscoveryInProgress,
    DiscoveryFailed,
)


_DEVICES_RESPONSE = {
    "devices": [
        {"id": "pump_1", "type": "pump", "type_code": 10, "port": "COM3"},
        {"id": "valve_1", "type": "valve", "type_code": 30, "port": "COM4"},
        {"id": "densitometer_1", "type": "densitometer", "type_code": 70, "port": "COM7"},
    ],
    "discovered_at": "2026-04-26T12:34:56Z",
}


def _make_client(handler: Callable[[httpx.Request], httpx.Response]) -> LabDevicesClient:
    client = LabDevicesClient(port=9001)
    client._http.close()
    client._http = httpx.Client(
        base_url="http://chisel:9001",
        transport=httpx.MockTransport(handler),
        timeout=5.0,
    )
    return client


def _discovery_handler(devices_response: dict, command_response: dict) -> Callable:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path in ("/discover", "/devices"):
            return httpx.Response(200, json=devices_response)
        if path.endswith("/command"):
            return httpx.Response(200, json=command_response)
        return httpx.Response(404, json={"error": "not found", "detail": ""})

    return handler


def test_discover_returns_categorized_devices_and_parses_timestamp():
    handler = _discovery_handler(_DEVICES_RESPONSE, {"response": [10, 0, 0, 100]})
    with _make_client(handler) as client:
        result = client.discover()

    assert isinstance(result, DiscoveredDevices)
    assert len(result.pumps) == 1
    assert len(result.densitometers) == 1
    assert len(result.valves) == 1
    assert result.pumps[0].device_id == "pump_1"
    assert result.pumps[0].port == "COM3"
    assert result.densitometers[0].device_id == "densitometer_1"
    assert result.valves[0].device_id == "valve_1"
    assert result.discovered_at == datetime(2026, 4, 26, 12, 34, 56, tzinfo=timezone.utc)


def test_list_devices_handles_null_discovered_at():
    handler = _discovery_handler(
        {"devices": [], "discovered_at": None},
        {"response": []},
    )
    with _make_client(handler) as client:
        result = client.list_devices()

    assert result.pumps == []
    assert result.densitometers == []
    assert result.valves == []
    assert result.discovered_at is None


def test_unknown_device_type_is_logged_and_skipped(caplog):
    response = {
        "devices": [
            {"id": "pump_1", "type": "pump", "type_code": 10, "port": "COM3"},
            {"id": "thing_1", "type": "thing", "type_code": 99, "port": "COM9"},
        ],
        "discovered_at": "2026-04-26T12:34:56Z",
    }
    handler = _discovery_handler(response, {"response": [10, 0, 0, 100]})
    with _make_client(handler) as client:
        result = client.discover()

    assert len(result.pumps) == 1
    assert len(result.densitometers) == 0
    assert len(result.valves) == 0


def test_discover_raises_discovery_in_progress():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json={"error": "discovery in progress", "detail": ""})

    with _make_client(handler) as client:
        with pytest.raises(DiscoveryInProgress):
            client.discover()


def test_discover_raises_discovery_failed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "discovery failed", "detail": "USB enum error"})

    with _make_client(handler) as client:
        with pytest.raises(DiscoveryFailed) as exc_info:
            client.discover()

    assert exc_info.value.detail == "USB enum error"
```

(The `test_discover_returns_categorized_devices_and_parses_timestamp` test exercises the calibration round-trip too: each pump under construction will issue `POST /devices/{id}/command`. The handler responds with `[10, 0, 0, 100]`, which decodes to a `_calibration_volume` of `100 / 1e5 = 0.001`.)

- [ ] **Step 2: Run tests, expect failures.**

```bash
poetry run pytest tests/test_discovery.py -v
```
Expected: import errors for `DiscoveredDevices` plus the helpers.

- [ ] **Step 3: Add `DiscoveredDevices`, `discover()`, `list_devices()`, and stub device classes.**

`Edit` `src/bioexperiment_suite/interfaces/lab_devices_client.py`. At the top of the file, change `from __future__ import annotations` to remain the first line, then add these imports near the others:

```python
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
```

Append at the bottom of the file (after the `LabDevicesClient` class):

```python
@dataclass
class DiscoveredDevices:
    pumps: list["Pump"]
    densitometers: list["Densitometer"]
    valves: list["Valve"]
    discovered_at: datetime | None


def _parse_iso(value: str | None) -> datetime | None:
    if value is None:
        return None
    # The server emits "...Z" suffixes; datetime.fromisoformat handles them in 3.12.
    return datetime.fromisoformat(value)
```

Inside the `LabDevicesClient` class, add two methods (place them between `send_command` and `_request`):

```python
    def discover(self) -> "DiscoveredDevices":
        data = self._request("POST", "/discover")
        return self._build_devices(data)

    def list_devices(self) -> "DiscoveredDevices":
        data = self._request("GET", "/devices")
        return self._build_devices(data)

    def _build_devices(self, data: dict) -> "DiscoveredDevices":
        # Imports kept local to avoid a circular import once Pump/Densitometer/Valve
        # move into their own modules in the next tasks.
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
```

To avoid breakage between this task and the next, **also create three minimal stub modules** so the imports above resolve:

`Write` `src/bioexperiment_suite/interfaces/pump.py`:

```python
"""Pump device — temporary stub. Real implementation in Task 10."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lab_devices_client import LabDevicesClient


class Pump:
    def __init__(self, client: "LabDevicesClient", device_id: str, port: str):
        self.client = client
        self.device_id = device_id
        self.port = port
        # Calibration probe: matches the spec; real Pump in Task 10 will store the result.
        client.send_command(
            device_id,
            [1, 2, 3, 4, 0],
            wait_for_response=True,
            expected_response_bytes=4,
        )
```

`Write` `src/bioexperiment_suite/interfaces/densitometer.py`:

```python
"""Densitometer device — temporary stub. Real implementation in Task 11."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lab_devices_client import LabDevicesClient


class Densitometer:
    def __init__(self, client: "LabDevicesClient", device_id: str, port: str):
        self.client = client
        self.device_id = device_id
        self.port = port
```

`Write` `src/bioexperiment_suite/interfaces/valve.py`:

```python
"""Valve placeholder — wire protocol not yet specified."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lab_devices_client import LabDevicesClient


class Valve:
    def __init__(self, client: "LabDevicesClient", device_id: str, port: str):
        self.client = client
        self.device_id = device_id
        self.port = port
```

- [ ] **Step 4: Run the discovery tests.**

```bash
poetry run pytest tests/test_discovery.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Run full suite.**

```bash
poetry run pytest -v
```
Expected: all green.

- [ ] **Step 6: Commit.**

```bash
git add tests/test_discovery.py \
    src/bioexperiment_suite/interfaces/lab_devices_client.py \
    src/bioexperiment_suite/interfaces/pump.py \
    src/bioexperiment_suite/interfaces/densitometer.py \
    src/bioexperiment_suite/interfaces/valve.py
git commit -m "Implement discover()/list_devices() with stub device classes"
```

---

## Task 9: Add a fake-client test fixture and helper

Lays the groundwork for Tasks 10 and 11. The fake records `send_command` calls and serves canned responses.

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Replace `tests/conftest.py`.**

`Write`:

```python
"""Shared pytest fixtures."""
from __future__ import annotations

from dataclasses import dataclass, field

import pytest


@dataclass
class RecordedCall:
    device_id: str
    command: list[int]
    wait_for_response: bool
    expected_response_bytes: int | None
    timeout_ms: int | None
    inter_byte_ms: int | None


class FakeLabDevicesClient:
    """Stand-in for LabDevicesClient in device-class unit tests.

    Records every send_command call. Responses are dispensed from a queue:
    each entry is a list[int] (the bytes the server would have returned).
    """

    def __init__(self, responses: list[list[int]] | None = None):
        self.calls: list[RecordedCall] = []
        self._responses: list[list[int]] = list(responses or [])

    def queue(self, response: list[int]) -> None:
        self._responses.append(response)

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
        self.calls.append(
            RecordedCall(
                device_id=device_id,
                command=list(command),
                wait_for_response=wait_for_response,
                expected_response_bytes=expected_response_bytes,
                timeout_ms=timeout_ms,
                inter_byte_ms=inter_byte_ms,
            )
        )
        if not self._responses:
            return []
        return self._responses.pop(0)


@pytest.fixture
def fake_client() -> FakeLabDevicesClient:
    return FakeLabDevicesClient()
```

- [ ] **Step 2: Run full test suite to confirm conftest is valid Python and nothing regresses.**

```bash
poetry run pytest -v
```
Expected: all green.

- [ ] **Step 3: Commit.**

```bash
git add tests/conftest.py
git commit -m "Add FakeLabDevicesClient fixture for device-class tests"
```

---

## Task 10: Implement the real `Pump` (TDD)

**Files:**
- Create: `tests/test_pump.py`
- Modify: `src/bioexperiment_suite/interfaces/pump.py`

- [ ] **Step 1: Write failing tests.**

`Write` `tests/test_pump.py`:

```python
"""Pump device behaviour."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from bioexperiment_suite.interfaces.pump import Pump
from tests.conftest import FakeLabDevicesClient


def _make_pump(calibration_response: list[int] | None = None) -> tuple[Pump, FakeLabDevicesClient]:
    """Construct a Pump bound to a FakeLabDevicesClient.

    The FakeLabDevicesClient is pre-loaded with the calibration probe response
    that Pump.__init__ will consume.
    """
    client = FakeLabDevicesClient(responses=[calibration_response or [10, 0, 0, 100]])
    pump = Pump(client, "pump_1", "COM3")
    return pump, client


def test_init_runs_calibration_probe_and_stores_volume():
    pump, client = _make_pump(calibration_response=[10, 0, 0, 100])

    assert pump.device_id == "pump_1"
    assert pump.port == "COM3"
    assert pump._calibration_volume == pytest.approx(100 / 10**5)

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call.device_id == "pump_1"
    assert call.command == [1, 2, 3, 4, 0]
    assert call.wait_for_response is True
    assert call.expected_response_bytes == 4


def test_set_default_flow_rate_does_not_call_server():
    pump, client = _make_pump()
    initial = len(client.calls)

    pump.set_default_flow_rate(3.0)

    assert pump.default_flow_rate == 3.0
    assert len(client.calls) == initial  # no extra send_command


def test_pour_in_volume_left_emits_correct_command_and_does_not_wait_for_response():
    pump, client = _make_pump(calibration_response=[10, 0, 0, 100])
    pump.set_default_flow_rate(60.0)  # to make the post-pour sleep negligible
    client.calls.clear()

    with patch("bioexperiment_suite.interfaces.pump.sleep") as fake_sleep:
        pump.pour_in_volume(volume=0.0, direction="left")

    # Two send_command calls expected: _set_flow_rate, then the volume write.
    assert len(client.calls) == 2
    set_speed_call, volume_call = client.calls

    assert set_speed_call.command[0] == 10           # set-speed prefix
    assert set_speed_call.wait_for_response is False
    assert set_speed_call.expected_response_bytes is None

    assert volume_call.command[0] == 16              # left direction byte
    assert volume_call.wait_for_response is False
    assert volume_call.expected_response_bytes is None
    fake_sleep.assert_called_once()                  # blocking-mode wait happened


def test_pour_in_volume_right_uses_direction_byte_17():
    pump, client = _make_pump()
    pump.set_default_flow_rate(60.0)
    client.calls.clear()

    with patch("bioexperiment_suite.interfaces.pump.sleep"):
        pump.pour_in_volume(volume=0.0, direction="right")

    _, volume_call = client.calls
    assert volume_call.command[0] == 17


def test_pour_in_volume_requires_flow_rate():
    pump, _ = _make_pump()
    with pytest.raises(ValueError):
        pump.pour_in_volume(volume=1.0)


def test_start_continuous_rotation_left():
    pump, client = _make_pump()
    client.calls.clear()

    pump.start_continuous_rotation(flow_rate=3.0, direction="left")

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call.command[0] == 11
    assert call.wait_for_response is False
    assert call.expected_response_bytes is None


def test_start_continuous_rotation_right_uses_direction_byte_12():
    pump, client = _make_pump()
    client.calls.clear()

    pump.start_continuous_rotation(flow_rate=3.0, direction="right")

    assert client.calls[0].command[0] == 12


def test_stop_continuous_rotation_delegates_to_pour_in_volume_zero():
    pump, client = _make_pump()
    pump.set_default_flow_rate(60.0)
    client.calls.clear()

    with patch("bioexperiment_suite.interfaces.pump.sleep"):
        pump.stop_continuous_rotation()

    # Same shape as pour_in_volume(0): set-speed + direction byte.
    assert len(client.calls) == 2
    assert client.calls[0].command[0] == 10
    assert client.calls[1].command[0] == 16  # default direction is "left"
```

- [ ] **Step 2: Run tests, expect failures.**

```bash
poetry run pytest tests/test_pump.py -v
```
Expected: failures (the stub Pump from Task 8 doesn't have these methods).

- [ ] **Step 3: Replace `src/bioexperiment_suite/interfaces/pump.py` with the real implementation.**

`Write`:

```python
"""Pump device class — composes a LabDevicesClient."""
from __future__ import annotations

from time import sleep
from typing import TYPE_CHECKING

from bioexperiment_suite.loader import device_interfaces, logger

if TYPE_CHECKING:
    from .lab_devices_client import LabDevicesClient


UNACCOUNTED_FOR_TIME_SEC = 1


def _bytes_to_int(values: list[int]) -> int:
    return int.from_bytes(bytes(values), byteorder="big")


def _int_to_bytes(value: int, n_bytes: int) -> list[int]:
    return list(value.to_bytes(n_bytes, byteorder="big"))


class Pump:
    """High-level peristaltic pump driver, served over the lab_devices HTTP API."""

    def __init__(self, client: "LabDevicesClient", device_id: str, port: str):
        self.client = client
        self.device_id = device_id
        self.port = port
        self.interface = device_interfaces.pump
        self.default_flow_rate: float | None = None
        self._calibration_volume: float = self._compute_calibration_volume()

    def _compute_calibration_volume(self) -> float:
        response = self.client.send_command(
            self.device_id,
            list(self.interface.identification_signal),
            wait_for_response=True,
            expected_response_bytes=4,
        )
        calibration_volume = _bytes_to_int(response[1:]) / 10**5
        logger.debug(f"{self.device_id}: calibration volume {calibration_volume:.5f}")
        return calibration_volume

    def _compute_speed_param_from_flow(self, flow: float) -> int:
        return int(29 / flow)

    def _compute_step_volume_bytes(self, volume: float) -> list[int]:
        step_volume = int((volume * 10**4) / self._calibration_volume)
        return _int_to_bytes(step_volume, 4)

    def set_default_flow_rate(self, flow_rate: float) -> None:
        self.default_flow_rate = flow_rate

    def _set_flow_rate(self, flow_rate: float) -> None:
        logger.debug(f"{self.device_id}: setting flow rate to {flow_rate:.3f} mL/min")
        speed_param = self._compute_speed_param_from_flow(flow_rate)
        self.client.send_command(
            self.device_id,
            [10, 0, 1, speed_param, 0],
            wait_for_response=False,
        )

    def pour_in_volume(
        self,
        volume: float,
        flow_rate: float | None = None,
        direction: str = "left",
        blocking_mode: bool = True,
        info_log_message: str | None = None,
        info_log_level: str = "INFO",
    ) -> None:
        if direction not in ("left", "right"):
            raise ValueError("Invalid direction. Must be either 'left' or 'right'")
        direction_byte = 16 if direction == "left" else 17

        flow_rate = flow_rate if flow_rate is not None else self.default_flow_rate
        if flow_rate is None:
            raise ValueError("Flow rate must be set before pouring in volume or passed as an argument")

        self._set_flow_rate(flow_rate)

        logger.debug(f"{self.device_id}: pouring {volume:.3f} mL at {flow_rate:.3f} mL/min ({direction})")
        if info_log_message:
            logger.log(info_log_level, info_log_message)

        command = [direction_byte] + self._compute_step_volume_bytes(volume)
        self.client.send_command(self.device_id, command, wait_for_response=False)

        if blocking_mode:
            sleep_time = (volume / flow_rate) * 60
            sleep(sleep_time + UNACCOUNTED_FOR_TIME_SEC)

    def start_continuous_rotation(
        self,
        flow_rate: float | None = None,
        direction: str = "left",
    ) -> None:
        if direction not in ("left", "right"):
            raise ValueError("Invalid direction. Must be either 'left' or 'right'")
        direction_byte = 11 if direction == "left" else 12

        flow_rate = flow_rate if flow_rate is not None else self.default_flow_rate
        if flow_rate is None:
            raise ValueError(
                "Flow rate must be set before starting continuous rotation or passed as an argument"
            )

        logger.debug(
            f"{self.device_id}: starting continuous rotation at {flow_rate:.3f} mL/min ({direction})"
        )
        speed_param = self._compute_speed_param_from_flow(flow_rate)
        self.client.send_command(
            self.device_id,
            [direction_byte, 111, 1, speed_param, 0],
            wait_for_response=False,
        )

    def stop_continuous_rotation(self) -> None:
        logger.debug(f"{self.device_id}: stopping continuous rotation")
        self.pour_in_volume(0)
```

- [ ] **Step 4: Run pump tests.**

```bash
poetry run pytest tests/test_pump.py -v
```
Expected: all tests pass.

- [ ] **Step 5: Run full suite.**

```bash
poetry run pytest -v
```
Expected: all green.

- [ ] **Step 6: Commit.**

```bash
git add tests/test_pump.py src/bioexperiment_suite/interfaces/pump.py
git commit -m "Implement Pump on top of LabDevicesClient"
```

---

## Task 11: Implement the real `Densitometer` (TDD)

**Files:**
- Create: `tests/test_densitometer.py`
- Modify: `src/bioexperiment_suite/interfaces/densitometer.py`

- [ ] **Step 1: Write failing tests.**

`Write` `tests/test_densitometer.py`:

```python
"""Densitometer device behaviour."""
from __future__ import annotations

from unittest.mock import patch

from bioexperiment_suite.interfaces.densitometer import Densitometer
from tests.conftest import FakeLabDevicesClient


def test_init_does_not_call_server():
    client = FakeLabDevicesClient()
    densitometer = Densitometer(client, "densitometer_1", "COM7")

    assert densitometer.device_id == "densitometer_1"
    assert densitometer.port == "COM7"
    assert client.calls == []


def test_get_temperature_decodes_two_byte_payload():
    # Temperature payload format from device_interfaces.json: [_, _, integer, fractional]
    client = FakeLabDevicesClient(responses=[[0, 0, 25, 30]])
    densitometer = Densitometer(client, "densitometer_1", "COM7")

    temperature = densitometer.get_temperature()

    assert temperature == 25 + 30 / 100
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call.device_id == "densitometer_1"
    assert call.command == [76, 0, 0, 0, 0]
    assert call.wait_for_response is True
    assert call.expected_response_bytes == 4


def test_measure_optical_density_starts_then_reads_after_sleep():
    client = FakeLabDevicesClient(
        responses=[
            [],                  # response to start_measurement (wait_for_response=False)
            [0, 0, 0, 42],       # response to get_measurement_result
        ]
    )
    densitometer = Densitometer(client, "densitometer_1", "COM7")

    with patch("bioexperiment_suite.interfaces.densitometer.sleep") as fake_sleep:
        optical_density = densitometer.measure_optical_density()

    assert optical_density == 0 + 42 / 100
    fake_sleep.assert_called_once_with(3)

    assert len(client.calls) == 2
    start_call, read_call = client.calls
    assert start_call.command == [78, 4, 0, 0, 0]
    assert start_call.wait_for_response is False
    assert start_call.expected_response_bytes is None
    assert read_call.command == [79, 4, 0, 0, 0]
    assert read_call.wait_for_response is True
    assert read_call.expected_response_bytes == 4


def test_measure_optical_density_raises_on_empty_read():
    import pytest

    client = FakeLabDevicesClient(responses=[[], []])
    densitometer = Densitometer(client, "densitometer_1", "COM7")

    with patch("bioexperiment_suite.interfaces.densitometer.sleep"):
        with pytest.raises(Exception):
            densitometer.measure_optical_density()
```

- [ ] **Step 2: Run tests, expect failures.**

```bash
poetry run pytest tests/test_densitometer.py -v
```
Expected: failures (stub Densitometer has no methods).

- [ ] **Step 3: Replace `src/bioexperiment_suite/interfaces/densitometer.py` with the real implementation.**

`Write`:

```python
"""Densitometer device class — composes a LabDevicesClient."""
from __future__ import annotations

from time import sleep
from typing import TYPE_CHECKING

from bioexperiment_suite.loader import device_interfaces, logger

if TYPE_CHECKING:
    from .lab_devices_client import LabDevicesClient


_MEASUREMENT_DELAY_SEC = 3


class Densitometer:
    """High-level optical density / temperature reader."""

    def __init__(self, client: "LabDevicesClient", device_id: str, port: str):
        self.client = client
        self.device_id = device_id
        self.port = port
        self.interface = device_interfaces.densitometer

    def get_temperature(self) -> float:
        logger.debug(f"{self.device_id}: getting temperature")
        response = self.client.send_command(
            self.device_id,
            list(self.interface.commands.get_temperature.request),
            wait_for_response=True,
            expected_response_bytes=int(self.interface.commands.get_temperature.response_len),
        )
        integer, fractional = response[2:4]
        temperature = integer + fractional / 100
        logger.debug(f"{self.device_id}: temperature {temperature:.2f}")
        return temperature

    def _send_start_measurement_command(self) -> None:
        logger.debug(f"{self.device_id}: start measurement")
        self.client.send_command(
            self.device_id,
            list(self.interface.commands.start_measurement.request),
            wait_for_response=False,
        )

    def _get_optical_density(self) -> float | None:
        response = self.client.send_command(
            self.device_id,
            list(self.interface.commands.get_measurement_result.request),
            wait_for_response=True,
            expected_response_bytes=int(self.interface.commands.get_measurement_result.response_len),
        )
        if not response:
            return None
        integer, fractional = response[2:4]
        return integer + fractional / 100

    def measure_optical_density(self) -> float:
        logger.debug(f"{self.device_id}: measuring optical density")
        self._send_start_measurement_command()
        sleep(_MEASUREMENT_DELAY_SEC)
        optical_density = self._get_optical_density()
        if optical_density is None:
            logger.error(f"{self.device_id}: optical density could not be measured")
            raise Exception("Optical density could not be measured")
        return optical_density
```

- [ ] **Step 4: Run densitometer tests.**

```bash
poetry run pytest tests/test_densitometer.py -v
```
Expected: all pass.

- [ ] **Step 5: Run full suite.**

```bash
poetry run pytest -v
```
Expected: all green.

- [ ] **Step 6: Commit.**

```bash
git add tests/test_densitometer.py src/bioexperiment_suite/interfaces/densitometer.py
git commit -m "Implement Densitometer on top of LabDevicesClient"
```

---

## Task 12: Lock down `Valve` and finalize `interfaces/__init__.py`

**Files:**
- Create: `tests/test_valve.py`
- Modify: `src/bioexperiment_suite/interfaces/valve.py` (no behavior change; just confirm shape)
- Modify: `src/bioexperiment_suite/interfaces/__init__.py`

- [ ] **Step 1: Write a test that pins down the Valve placeholder shape.**

`Write` `tests/test_valve.py`:

```python
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
```

- [ ] **Step 2: Run the valve test.**

```bash
poetry run pytest tests/test_valve.py -v
```
Expected: both tests pass against the stub from Task 8.

- [ ] **Step 3: Update `interfaces/__init__.py` with the public API.**

`Write` `src/bioexperiment_suite/interfaces/__init__.py`:

```python
"""Public API for the lab_devices HTTP transport."""
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
    "LabDevicesClient",
    "DiscoveredDevices",
    "LabDevicesError",
    "InvalidRequest",
    "DeviceNotFound",
    "DeviceBusy",
    "DiscoveryInProgress",
    "DiscoveryFailed",
    "DeviceUnreachable",
    "DeviceIOFailed",
    "DeviceIdentityChanged",
    "TransportError",
    "Pump",
    "Densitometer",
    "Valve",
]
```

- [ ] **Step 4: Verify the public API imports.**

```bash
poetry run python -c "from bioexperiment_suite.interfaces import LabDevicesClient, Pump, Densitometer, Valve, DiscoveredDevices, LabDevicesError; print('ok')"
```
Expected: `ok`.

- [ ] **Step 5: Run full suite.**

```bash
poetry run pytest -v
```
Expected: all green.

- [ ] **Step 6: Commit.**

```bash
git add tests/test_valve.py src/bioexperiment_suite/interfaces/__init__.py
git commit -m "Pin Valve placeholder shape and finalize interfaces/__init__.py"
```

---

## Task 13: Update `examples/experiment_example.py`

**Files:**
- Modify: `examples/experiment_example.py`

- [ ] **Step 1: Replace the file.**

`Write`:

```python
from bioexperiment_suite.experiment import Experiment  # Import the Experiment class
from bioexperiment_suite.interfaces import LabDevicesClient

# Define the experiment parameters
TOTAL_EXPERIMENT_DURATION_HOURS = 24  # Total duration of the experiment in hours
SOLUTION_REFRESH_INTERVAL_MIN = 60  # Interval for refreshing the solution in minutes

MEASUREMENT_INTERVAL_MINUTES = 5  # Interval for taking measurements in minutes
POURED_OUT_VOLUME_ML = 2  # Volume of solution poured out in mL
INFUSED_VOLUME_ML = 1  # Volume of solution infused in mL
FLOW_RATE_ML_PER_MINUTE = 3  # Flow rate of the pump in mL/min

LAB_DEVICES_PORT = 9001  # Per-lab-machine chisel-tunnel port

# Ensure intervals are valid
assert (
    SOLUTION_REFRESH_INTERVAL_MIN % MEASUREMENT_INTERVAL_MINUTES == 0
), "Solution refresh interval should be a multiple of measurement interval"
assert (
    TOTAL_EXPERIMENT_DURATION_HOURS * 60
) % SOLUTION_REFRESH_INTERVAL_MIN == 0, "Total experiment duration should be a multiple of solution refresh interval"

# Calculate the number of solution refreshes and measurements per refresh
n_solution_refreshes = (
    TOTAL_EXPERIMENT_DURATION_HOURS * 60 // SOLUTION_REFRESH_INTERVAL_MIN
)
n_measurements_per_solution_refresh = (
    SOLUTION_REFRESH_INTERVAL_MIN // MEASUREMENT_INTERVAL_MINUTES
)

# Connect to the lab devices service and discover devices
client = LabDevicesClient(port=LAB_DEVICES_PORT)
devices = client.discover()

# Unpack discovered devices
(pump1, pump2) = devices.pumps  # Suppose we have two pumps
(densitometer,) = devices.densitometers  # Suppose we have one densitometer

# Initialize the experiment
experiment = Experiment()

# Configure the experiment with measurements and actions
for i in range(n_solution_refreshes):
    for j in range(n_measurements_per_solution_refresh):
        experiment.add_measurement(
            densitometer.get_temperature, measurement_name="Temperature (C)"
        )
        experiment.add_measurement(
            densitometer.measure_optical_density, measurement_name="Optical density"
        )
        experiment.add_wait(MEASUREMENT_INTERVAL_MINUTES * 60)

    experiment.add_action(
        pump2.pour_in_volume, volume=POURED_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction="left"
    )
    experiment.add_action(
        pump1.pour_in_volume, volume=INFUSED_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction="right"
    )
    experiment.add_wait(MEASUREMENT_INTERVAL_MINUTES * 60)

# Run the experiment
experiment.start()

# After the experiment is complete, the results can be accessed from the experiment object by assigned names
print(experiment.measurements["Temperature (C)"])
print(experiment.measurements["Optical density"])
```

- [ ] **Step 2: Confirm the file at least parses (we won't run it — there's no live server).**

```bash
poetry run python -m py_compile examples/experiment_example.py
```
Expected: no output, exit 0.

- [ ] **Step 3: Commit.**

```bash
git add examples/experiment_example.py
git commit -m "Update experiment_example.py to use LabDevicesClient"
```

---

## Task 14: Update `examples/three_pumps_experiment.py`

**Files:**
- Modify: `examples/three_pumps_experiment.py`

- [ ] **Step 1: Replace the file.**

`Write`:

```python
#!/usr/bin/env python
# coding: utf-8

from bioexperiment_suite.experiment.collections import Relation, Statistic
from bioexperiment_suite.experiment import Experiment, Condition
from bioexperiment_suite.interfaces import LabDevicesClient


# Define the experiment parameters
TOTAL_EXPERIMENT_DURATION_HOURS = 24  # Total duration of the experiment in hours
SOLUTION_REFRESH_INTERVAL_MIN = 60  # Interval for refreshing the solution in minutes
INWARDS_PUMP_DELAY_SEC = 10  # Delay before "food" or "drug" pump strts working

MEASUREMENT_INTERVAL_MINUTES = 5  # Interval for taking measurements in minutes

FLOW_RATE_ML_PER_MINUTE = 3  # Flow rate of the pumps in mL/min

PUMP_OUT_VOLUME_ML = 5
PUMP_FOOD_VOLUME_ML = 2
PUMP_DRUG_VOLUME_ML = 2

OPTICAL_DENSITY_THRESHOLD = 0.5

LAB_DEVICES_PORT = 9001  # Per-lab-machine chisel-tunnel port

# Define measurements
OPTICAL_DENSITY = "optical_density"
TEMPERATURE = "temperature"

# Define pump rotation directions
IN = "right"
OUT = "left"


# Ensure intervals are valid
assert (
    SOLUTION_REFRESH_INTERVAL_MIN % MEASUREMENT_INTERVAL_MINUTES == 0
), "Solution refresh interval should be a multiple of measurement interval"
assert (
    TOTAL_EXPERIMENT_DURATION_HOURS * 60
) % SOLUTION_REFRESH_INTERVAL_MIN == 0, "Total experiment duration should be a multiple of solution refresh interval"

# Calculate the number of solution refreshes and measurements per refresh
n_solution_refreshes = (
    TOTAL_EXPERIMENT_DURATION_HOURS * 60 // SOLUTION_REFRESH_INTERVAL_MIN
)
n_measurements_per_solution_refresh = (
    SOLUTION_REFRESH_INTERVAL_MIN // MEASUREMENT_INTERVAL_MINUTES
)
delay_time = (PUMP_OUT_VOLUME_ML / FLOW_RATE_ML_PER_MINUTE) * 60 + 1 + INWARDS_PUMP_DELAY_SEC


# Connect to the lab devices service and discover devices
client = LabDevicesClient(port=LAB_DEVICES_PORT)
devices = client.discover()

(densitometer,) = devices.densitometers  # Suppose we have one densitometer
pumps = devices.pumps


# Comparison of found pumps
assert len(pumps) == 3, f"{len(pumps)} pumps found! Exactly 3 pumps is needed for this experiment"
print("""
Please choose the role of currently rotating pump:

1. Pump for removing waste
2. Pump for feeding the bacteria
3. Pump for adding the drug
""")
for pump in pumps:
    pump.set_default_flow_rate(1)
    pump.start_continuous_rotation(0.1)

    role = input("Enter the number and press Enter: ")
    if role == "1":
        pump_out = pump
    elif role == "2":
        pump_food = pump
    elif role == "3":
        pump_drug = pump
    else:
        print("Invalid input. Please enter a number between 1 and 3")

    pump.stop_continuous_rotation()


for name in ["pump_out", "pump_food", "pump_drug"]:
    assert name in locals(), f"Please assign a pump to the variable {name}"


# Initialize the experiment
experiment = Experiment(
    output_dir=".",
)

# Define the metrics
optical_density_last_value = experiment.create_metric(
    measurement_name=OPTICAL_DENSITY,
    statistic=Statistic.LAST(),
)

# Define the conditions
od_exceeded_threshold = Condition(
    metric=optical_density_last_value,
    relation=Relation.GREATER_THAN(OPTICAL_DENSITY_THRESHOLD),
)
od_not_exceeded_threshold = od_exceeded_threshold.negation


# Add the initial actions to pour out the excessive solution and pour in the food
experiment.add_action(
    pump_out.pour_in_volume, volume=PUMP_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=OUT
)
experiment.add_wait(delay_time)
experiment.add_action(
    pump_food.pour_in_volume, volume=PUMP_FOOD_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=IN
)

# Add the main experiment loop
for _ in range(n_solution_refreshes):
    for i in range(n_measurements_per_solution_refresh):
        wait_time = (
            MEASUREMENT_INTERVAL_MINUTES * 60 - delay_time
            if i == 0 else MEASUREMENT_INTERVAL_MINUTES * 60
        )
        experiment.add_wait(wait_time)

        experiment.add_measurement(densitometer.measure_optical_density, measurement_name=OPTICAL_DENSITY)
        experiment.add_measurement(densitometer.get_temperature, measurement_name=TEMPERATURE)

    experiment.add_action(
        pump_out.pour_in_volume, volume=PUMP_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=OUT
    )
    experiment.add_wait(delay_time)

    experiment.add_action(
        pump_drug.pour_in_volume,
        volume=PUMP_DRUG_VOLUME_ML,
        flow_rate=FLOW_RATE_ML_PER_MINUTE,
        direction=IN,
        condition=od_exceeded_threshold,
        info_log_message="Drug added",
    )
    experiment.add_action(
        pump_food.pour_in_volume,
        volume=PUMP_FOOD_VOLUME_ML,
        flow_rate=FLOW_RATE_ML_PER_MINUTE,
        direction=IN,
        condition=od_not_exceeded_threshold,
        info_log_message="Food added",
    )


experiment.start(start_in_background=False)
```

- [ ] **Step 2: Compile-check.**

```bash
poetry run python -m py_compile examples/three_pumps_experiment.py
```
Expected: no output, exit 0.

- [ ] **Step 3: Commit.**

```bash
git add examples/three_pumps_experiment.py
git commit -m "Update three_pumps_experiment.py to use LabDevicesClient"
```

---

## Task 15: Update `examples/experiment_example.ipynb`

**Files:**
- Modify: `examples/experiment_example.ipynb` (cells `cell-0`, `cell-3`, `cell-4`)

The notebook has 9 cells (`cell-0` through `cell-8`). Three need editing.

- [ ] **Step 1: Edit cell-0 (imports) — replace the `tools` import.**

```python
NotebookEdit:
  notebook_path: /Users/khamitovdr/bio_tools/examples/experiment_example.ipynb
  cell_id: cell-0
  edit_mode: replace
  new_source: |
    from bioexperiment_suite.experiment.collections import Relation, Statistic
    from bioexperiment_suite.experiment import Experiment, Condition
    from bioexperiment_suite.interfaces import LabDevicesClient

    LAB_DEVICES_PORT = 9001  # Per-lab-machine chisel-tunnel port
```

- [ ] **Step 2: Edit cell-3 (device discovery) — replace `get_connected_devices` with the new client.**

```python
NotebookEdit:
  notebook_path: /Users/khamitovdr/bio_tools/examples/experiment_example.ipynb
  cell_id: cell-3
  edit_mode: replace
  new_source: |
    # Connect to the lab devices service and discover devices
    client = LabDevicesClient(port=LAB_DEVICES_PORT)
    devices = client.discover()

    pumps = devices.pumps
    (densitometer,) = devices.densitometers  # Suppose we have one densitometer
```

- [ ] **Step 3: Edit cell-6 (experiment loop) — rename `spectrophotometer` references to `densitometer`.**

```python
NotebookEdit:
  notebook_path: /Users/khamitovdr/bio_tools/examples/experiment_example.ipynb
  cell_id: cell-6
  edit_mode: replace
  new_source: |
    # Add the initial actions to pour out the excessive solution and pour in the food
    experiment.add_action(
        pump_out.pour_in_volume, volume=PUMP_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=OUT
    )
    experiment.add_action(
        pump_food.pour_in_volume, volume=PUMP_FOOD_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=IN
    )

    # Add the main experiment loop
    for _ in range(n_solution_refreshes):  # Loop over the number of solution refreshes
        for _ in range(n_measurements_per_solution_refresh):  # Loop over the number of measurements per refresh
            experiment.add_measurement(densitometer.measure_optical_density, measurement_name=OPTICAL_DENSITY)
            experiment.add_measurement(densitometer.get_temperature, measurement_name=TEMPERATURE)

            experiment.add_wait(MEASUREMENT_INTERVAL_MINUTES * 60)  # Wait for the measurement interval

        experiment.add_action(
            pump_out.pour_in_volume, volume=PUMP_OUT_VOLUME_ML, flow_rate=FLOW_RATE_ML_PER_MINUTE, direction=OUT
        )

        # Add the actions to pour in the drug or food based on the condition
        experiment.add_action(
            pump_drug.pour_in_volume,
            volume=PUMP_DRUG_VOLUME_ML,
            flow_rate=FLOW_RATE_ML_PER_MINUTE,
            direction=IN,
            condition=od_exceeded_threshold, # Only add the drug if the OD exceeded the threshold
            info_log_message="Drug added",
        )
        experiment.add_action(
            pump_food.pour_in_volume,
            volume=PUMP_FOOD_VOLUME_ML,
            flow_rate=FLOW_RATE_ML_PER_MINUTE,
            direction=IN,
            condition=od_not_exceeded_threshold, # Only add the food if the OD did not exceed the threshold
            info_log_message="Food added",
        )
```

- [ ] **Step 4: Validate the notebook is still parseable JSON.**

```bash
poetry run python -c "import json; nb = json.load(open('examples/experiment_example.ipynb')); print(f\"{len(nb['cells'])} cells, format {nb['nbformat']}.{nb['nbformat_minor']}\")"
```
Expected: prints something like `9 cells, format 4.5`.

- [ ] **Step 5: Confirm no leftover `spectrophotometer` references in the notebook.**

```bash
! grep -i "spectrophotometer\|get_connected_devices" examples/experiment_example.ipynb || echo "no matches"
```
Expected: `no matches`.

- [ ] **Step 6: Commit.**

```bash
git add examples/experiment_example.ipynb
git commit -m "Update experiment_example.ipynb to use LabDevicesClient"
```

---

## Task 16: Final verification pass

**Files:** none (read-only)

- [ ] **Step 1: Confirm `poetry check` is happy.**

```bash
poetry check
```
Expected: `All set!` (or equivalent success message).

- [ ] **Step 2: Confirm the public API imports cleanly.**

```bash
poetry run python -c "
from bioexperiment_suite.interfaces import (
    LabDevicesClient, DiscoveredDevices, Pump, Densitometer, Valve,
    LabDevicesError, InvalidRequest, DeviceNotFound, DeviceBusy,
    DiscoveryInProgress, DiscoveryFailed, DeviceUnreachable,
    DeviceIOFailed, DeviceIdentityChanged, TransportError,
)
from bioexperiment_suite.experiment import Experiment, Condition
print('public API OK')
"
```
Expected: `public API OK`.

- [ ] **Step 3: Confirm no stray references to removed modules remain in the package.**

```bash
! grep -rn "SerialConnection\|EMULATE_DEVICES\|get_connected_devices\|N_VIRTUAL\|pyserial\|ttkbootstrap\|run_gui\|tools.serial_port\|tools.devices\|bioexperiment_suite.gui\|bioexperiment_suite.tools\|bioexperiment_suite.settings" \
    src/ examples/ tests/ pyproject.toml \
    || echo "no matches"
```
Expected: `no matches`. (References inside the design spec under `docs/` are allowed and are not searched.)

- [ ] **Step 4: Run the full test suite one last time.**

```bash
poetry run pytest -v
```
Expected: all green; the test counts roughly:
- `test_exceptions.py`: ~11
- `test_lab_devices_client.py`: ~14 (parametrized cases included)
- `test_discovery.py`: ~5
- `test_pump.py`: ~8
- `test_densitometer.py`: ~4
- `test_valve.py`: 2

- [ ] **Step 5: Print a one-line branch summary.**

```bash
git log --oneline main..HEAD
```
Expected: ~16 commits, one per task.

- [ ] **Step 6: No commit needed for this task.**

---

## Notes

- **No automatic retry.** `409 device busy` and `503 device unreachable` propagate. Callers (or experiment-script logic) decide whether to retry.
- **Calibration cost.** Each `discover()` / `list_devices()` pays one HTTP round-trip per pump. With N pumps, N sequential calls. Sub-second for realistic lab loads.
- **Forward compatibility.** Unknown device types in the discovery response are logged at WARNING and skipped, not raised. This lets the server add new types without breaking older clients.
- **Async path.** Sync `httpx.Client` is used. Choosing `httpx` (not `requests`) leaves the door open to an `AsyncLabDevicesClient` later without dragging in another dependency.
- **Branch hygiene.** This branch diverges from `main`; there is no runtime switch between transports.
