# LabDevicesClient Username-Based Discovery — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add username-based lab-machine resolution to `LabDevicesClient`, plus `list_registered_users` / `list_active_users` classmethods, while keeping the existing `port=` constructor path working unchanged.

**Architecture:** All new code lives in `src/bioexperiment_suite/interfaces/lab_devices_client.py`. A small `_fetch_roster` helper hits the bridge endpoint and validates the JSON shape. The constructor and both classmethods route through it. A parallel `ClientLookupError` exception hierarchy keeps lookup failures distinct from `LabDevicesError`. Two module-level factory functions (`_build_discovery_client`, `_build_probe_client`) act as test seams that pytest can monkeypatch with `httpx.MockTransport`-backed clients.

**Tech Stack:** Python 3.12, httpx (already a dep), `concurrent.futures.ThreadPoolExecutor` (stdlib), pytest with `monkeypatch`. Integration test uses stdlib `http.server`.

**Spec:** `docs/superpowers/specs/2026-05-04-labdevicesclient-username-discovery-design.md`

---

## File Inventory

- **Modify** `src/bioexperiment_suite/interfaces/lab_devices_client.py` — add hierarchy, helpers, constructor branch, classmethods.
- **Modify** `src/bioexperiment_suite/interfaces/__init__.py` — re-export new exception classes.
- **Create** `tests/test_client_discovery.py` — all unit + integration tests for the new behavior.

The existing `tests/test_lab_devices_client.py` and `tests/test_discovery.py` are not touched.

## Convention

When tasks say "append to `tests/test_client_discovery.py`", treat that as: **new `import` statements go at the top of the file, merged with the existing import block; new fixtures and test functions go at the bottom.** Don't leave imports scattered between functions.

---

## Task 1: Add the `ClientLookupError` hierarchy

**Files:**
- Modify: `src/bioexperiment_suite/interfaces/lab_devices_client.py` (append to existing exception section)
- Test: `tests/test_client_discovery.py` (new file)

- [ ] **Step 1: Write the failing test**

Create `tests/test_client_discovery.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_client_discovery.py -v`
Expected: FAIL — `ImportError: cannot import name 'ClientLookupError'`.

- [ ] **Step 3: Add the exception classes**

Append to `src/bioexperiment_suite/interfaces/lab_devices_client.py` immediately after the existing exception block (after `class TransportError`):

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/test_client_discovery.py -v`
Expected: PASS, both tests green.

- [ ] **Step 5: Commit**

```bash
git add src/bioexperiment_suite/interfaces/lab_devices_client.py tests/test_client_discovery.py
git commit -m "Add ClientLookupError hierarchy for bridge-level discovery failures"
```

---

## Task 2: Add `_fetch_roster` helper and the discovery client factory

**Files:**
- Modify: `src/bioexperiment_suite/interfaces/lab_devices_client.py`
- Test: `tests/test_client_discovery.py`

This task introduces the helper but does **not** wire it into `__init__` yet. Direct unit tests against the helper exercise the wire-shape validation in isolation.

- [ ] **Step 1: Add the test fixtures and a happy-path test**

Append to `tests/test_client_discovery.py`:

```python
from typing import Callable

import httpx
import pytest

from bioexperiment_suite.interfaces import lab_devices_client as ldc_mod


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_client_discovery.py::test_fetch_roster_returns_parsed_body -v`
Expected: FAIL — `AttributeError: module ... has no attribute '_build_discovery_client'`.

- [ ] **Step 3: Add the helpers**

Append to `src/bioexperiment_suite/interfaces/lab_devices_client.py` after the new exception block. Add `import os` near the top of the file (next to other imports) if not already present:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/test_client_discovery.py -v`
Expected: PASS, all tests so far green.

- [ ] **Step 5: Commit**

```bash
git add src/bioexperiment_suite/interfaces/lab_devices_client.py tests/test_client_discovery.py
git commit -m "Add _fetch_roster helper and discovery client factory"
```

---

## Task 3: Add bridge error handling to `_fetch_roster`

**Files:**
- Modify: `src/bioexperiment_suite/interfaces/lab_devices_client.py` (no impl changes — code from Task 2 already covers this)
- Test: `tests/test_client_discovery.py`

This task adds tests that lock in the bridge error semantics that Task 2's code already implements. Each test should pass on the first run; if any fails, fix the helper before committing.

- [ ] **Step 1: Add the bridge-failure tests**

Append to `tests/test_client_discovery.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `poetry run pytest tests/test_client_discovery.py -v`
Expected: PASS, all tests green.

If any test fails, the issue is in `_fetch_roster` from Task 2 — fix it there, then re-run.

- [ ] **Step 3: Commit**

```bash
git add tests/test_client_discovery.py
git commit -m "Pin _fetch_roster bridge error semantics with tests"
```

---

## Task 4: Add `_resolve_discovery_url` and env-var precedence

**Files:**
- Modify: `src/bioexperiment_suite/interfaces/lab_devices_client.py`
- Test: `tests/test_client_discovery.py`

- [ ] **Step 1: Add the resolution tests**

Append to `tests/test_client_discovery.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_client_discovery.py::test_default_discovery_url_constant -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'DEFAULT_DISCOVERY_URL'`.

- [ ] **Step 3: Add the constants and resolver**

At the top of `src/bioexperiment_suite/interfaces/lab_devices_client.py`, add `import os` to the imports if not already present.

Insert these constants right above the `_build_discovery_client` definition added in Task 2:

```python
DEFAULT_DISCOVERY_URL = "http://siteapp:8000/api/clients/"
DISCOVERY_URL_ENV_VAR = "LAB_DEVICES_DISCOVERY_URL"


def _resolve_discovery_url(explicit: str | None) -> str:
    """Resolve the discovery URL. Precedence: explicit arg > env var > default."""
    if explicit is not None:
        return explicit
    return os.environ.get(DISCOVERY_URL_ENV_VAR, DEFAULT_DISCOVERY_URL)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_client_discovery.py -v`
Expected: PASS, all tests green.

- [ ] **Step 5: Commit**

```bash
git add src/bioexperiment_suite/interfaces/lab_devices_client.py tests/test_client_discovery.py
git commit -m "Add _resolve_discovery_url with env var fallback"
```

---

## Task 5: Make `LabDevicesClient.__init__` keyword-only and add the `user=` path

**Files:**
- Modify: `src/bioexperiment_suite/interfaces/lab_devices_client.py` (the `__init__` method)
- Test: `tests/test_client_discovery.py`

- [ ] **Step 1: Add the constructor happy-path test**

Append to `tests/test_client_discovery.py`:

```python
from bioexperiment_suite.interfaces.lab_devices_client import LabDevicesClient


def test_constructor_with_user_resolves_via_bridge(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "khamit_desktop": {"host": "chisel", "port": 8089},
                "another_lab": {"host": "chisel", "port": 8090},
            },
        )

    mock_discovery(handler)

    client = LabDevicesClient(user="khamit_desktop")
    try:
        assert client.host == "chisel"
        assert client.port == 8089
        assert str(client._http.base_url) == "http://chisel:8089"
    finally:
        client.close()


def test_constructor_with_user_passes_explicit_discovery_url(mock_discovery):
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json={"x": {"host": "chisel", "port": 1}})

    mock_discovery(handler)

    LabDevicesClient(
        user="x", discovery_url="http://custom.example/api/clients/"
    ).close()
    assert seen_urls == ["http://custom.example/api/clients/"]


def test_constructor_with_user_unknown_raises(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"another_lab": {"host": "chisel", "port": 8090}},
        )

    mock_discovery(handler)

    with pytest.raises(UnknownLabClient) as info:
        LabDevicesClient(user="khamit_desktp")
    assert info.value.name == "khamit_desktp"
    assert info.value.available == ["another_lab"]


def test_constructor_with_port_path_unaffected():
    """The original construction path keeps working without touching the bridge."""
    client = LabDevicesClient(port=9001)
    try:
        assert client.host == "chisel"
        assert client.port == 9001
        assert str(client._http.base_url) == "http://chisel:9001"
    finally:
        client.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_client_discovery.py::test_constructor_with_user_resolves_via_bridge -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'user'`.

- [ ] **Step 3: Replace the `__init__` method**

In `src/bioexperiment_suite/interfaces/lab_devices_client.py`, replace the existing `__init__` method (currently lines ~116–127) with:

```python
    def __init__(
        self,
        *,
        port: int | None = None,
        host: str | None = None,
        user: str | None = None,
        discovery_url: str | None = None,
        request_timeout_sec: float = 5.0,
    ):
        if user is not None and port is not None:
            raise TypeError("user= and port= are mutually exclusive")
        if user is None and port is None:
            raise TypeError("either user= or port= must be provided")
        if user is not None and host is not None:
            raise TypeError("host= cannot be combined with user=")
        if port is not None and discovery_url is not None:
            raise TypeError("discovery_url= cannot be combined with port=")

        if user is not None:
            url = _resolve_discovery_url(discovery_url)
            roster = _fetch_roster(url, request_timeout_sec)
            if user not in roster:
                raise UnknownLabClient(name=user, available=sorted(roster.keys()))
            entry = roster[user]
            host = entry["host"]
            port = entry["port"]
        else:
            if host is None:
                host = "chisel"

        self.host = host
        self.port = port
        self._http = httpx.Client(
            base_url=f"http://{host}:{port}",
            timeout=request_timeout_sec,
        )
```

- [ ] **Step 4: Run all tests to verify**

Run: `poetry run pytest -v`
Expected: PASS — both the new `test_client_discovery.py` tests and all existing tests in `test_lab_devices_client.py`, `test_discovery.py`, `test_pump.py`, `test_densitometer.py`, `test_valve.py` (which already use kwargs).

If any existing test fails because it relied on positional args, that test should be updated to use kwargs — but a quick grep confirmed all current callers already use kwargs.

- [ ] **Step 5: Commit**

```bash
git add src/bioexperiment_suite/interfaces/lab_devices_client.py tests/test_client_discovery.py
git commit -m "Add user= constructor path and keyword-only signature"
```

---

## Task 6: Lock in `__init__` argument-validation tests

**Files:**
- Test: `tests/test_client_discovery.py`

The validation logic was added in Task 5. This task adds dedicated tests for each forbidden combination so a future refactor can't quietly relax the rules.

- [ ] **Step 1: Add the validation tests**

Append to `tests/test_client_discovery.py`:

```python
def test_constructor_user_and_port_are_mutually_exclusive():
    with pytest.raises(TypeError, match="mutually exclusive"):
        LabDevicesClient(user="x", port=9001)


def test_constructor_requires_user_or_port():
    with pytest.raises(TypeError, match="either user= or port="):
        LabDevicesClient()


def test_constructor_host_cannot_combine_with_user():
    with pytest.raises(TypeError, match="host= cannot be combined with user="):
        LabDevicesClient(user="x", host="other")


def test_constructor_discovery_url_cannot_combine_with_port():
    with pytest.raises(TypeError, match="discovery_url= cannot be combined with port="):
        LabDevicesClient(port=9001, discovery_url="http://example/")


def test_constructor_rejects_positional_port():
    """The signature is keyword-only; positional args should be rejected."""
    with pytest.raises(TypeError):
        LabDevicesClient(9001)  # type: ignore[misc]
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `poetry run pytest tests/test_client_discovery.py -v`
Expected: PASS, all tests green.

- [ ] **Step 3: Commit**

```bash
git add tests/test_client_discovery.py
git commit -m "Pin LabDevicesClient argument-validation rules with tests"
```

---

## Task 7: Implement `list_registered_users`

**Files:**
- Modify: `src/bioexperiment_suite/interfaces/lab_devices_client.py`
- Test: `tests/test_client_discovery.py`

- [ ] **Step 1: Add the test**

Append to `tests/test_client_discovery.py`:

```python
def test_list_registered_users_returns_sorted_keys(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "zeta_lab": {"host": "chisel", "port": 8091},
                "alpha_lab": {"host": "chisel", "port": 8089},
                "mid_lab": {"host": "chisel", "port": 8090},
            },
        )

    mock_discovery(handler)

    assert LabDevicesClient.list_registered_users() == ["alpha_lab", "mid_lab", "zeta_lab"]


def test_list_registered_users_empty_roster(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    mock_discovery(handler)

    assert LabDevicesClient.list_registered_users() == []


def test_list_registered_users_propagates_bridge_unreachable(mock_discovery):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    mock_discovery(handler)

    with pytest.raises(ClientLookupEndpointUnreachable):
        LabDevicesClient.list_registered_users()


def test_list_registered_users_uses_explicit_discovery_url(mock_discovery):
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        return httpx.Response(200, json={})

    mock_discovery(handler)

    LabDevicesClient.list_registered_users(discovery_url="http://custom.example/api/")
    assert seen_urls == ["http://custom.example/api/"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_client_discovery.py::test_list_registered_users_returns_sorted_keys -v`
Expected: FAIL — `AttributeError: type object 'LabDevicesClient' has no attribute 'list_registered_users'`.

- [ ] **Step 3: Add the classmethod**

In `src/bioexperiment_suite/interfaces/lab_devices_client.py`, inside the `LabDevicesClient` class, add this method just below `__exit__`:

```python
    @classmethod
    def list_registered_users(
        cls,
        *,
        discovery_url: str | None = None,
        request_timeout_sec: float = 5.0,
    ) -> list[str]:
        """Return sorted names from the bridge roster — registered, regardless of connectivity.

        Raises ClientLookupEndpointUnreachable / ClientLookupEndpointError on
        bridge-level failures.
        """
        url = _resolve_discovery_url(discovery_url)
        roster = _fetch_roster(url, request_timeout_sec)
        return sorted(roster.keys())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_client_discovery.py -v`
Expected: PASS, all tests green.

- [ ] **Step 5: Commit**

```bash
git add src/bioexperiment_suite/interfaces/lab_devices_client.py tests/test_client_discovery.py
git commit -m "Add LabDevicesClient.list_registered_users classmethod"
```

---

## Task 8: Implement `list_active_users`

**Files:**
- Modify: `src/bioexperiment_suite/interfaces/lab_devices_client.py`
- Test: `tests/test_client_discovery.py`

- [ ] **Step 1: Add the probe-mock fixture and tests**

Append to `tests/test_client_discovery.py`:

```python
@pytest.fixture
def mock_probes(monkeypatch):
    """Patch _build_probe_client to use httpx.MockTransport per (host, port).

    Returns a setter: call set_handler(host, port, callable) to install a
    handler for that target. Unregistered targets behave as connection-refused.
    """
    handlers: dict[tuple[str, int], Callable[[httpx.Request], httpx.Response]] = {}

    def factory(host: str, port: int, timeout: float) -> httpx.Client:
        handler = handlers.get((host, port))
        if handler is None:
            def refused(_req: httpx.Request) -> httpx.Response:
                raise httpx.ConnectError("refused")
            handler = refused
        return httpx.Client(
            base_url=f"http://{host}:{port}",
            transport=httpx.MockTransport(handler),
            timeout=timeout,
        )

    monkeypatch.setattr(ldc_mod, "_build_probe_client", factory)

    def set_handler(host: str, port: int, handler: Callable[[httpx.Request], httpx.Response]) -> None:
        handlers[(host, port)] = handler

    return set_handler


def _devices_ok_handler(request: httpx.Request) -> httpx.Response:
    assert request.url.path == "/devices"
    return httpx.Response(200, json={"devices": [], "discovered_at": None})


def test_list_active_users_returns_only_responsive(mock_discovery, mock_probes):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "alive_lab": {"host": "chisel", "port": 8089},
                "refused_lab": {"host": "chisel", "port": 8090},
                "timeout_lab": {"host": "chisel", "port": 8091},
            },
        )

    mock_discovery(discovery_handler)
    mock_probes("chisel", 8089, _devices_ok_handler)
    # 8090 and 8091 are unregistered → default connection-refused behavior.
    # For timeout, override explicitly to make the intent obvious.

    def timeout_handler(_req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("connect timed out")

    mock_probes("chisel", 8091, timeout_handler)

    active = LabDevicesClient.list_active_users()
    assert active == ["alive_lab"]


def test_list_active_users_treats_5xx_response_as_active(mock_discovery, mock_probes):
    """Any HTTP response (even 500) means the service is up."""

    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"unhappy_lab": {"host": "chisel", "port": 8089}}
        )

    def probe_500(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    mock_discovery(discovery_handler)
    mock_probes("chisel", 8089, probe_500)

    assert LabDevicesClient.list_active_users() == ["unhappy_lab"]


def test_list_active_users_treats_4xx_response_as_active(mock_discovery, mock_probes):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"weird_lab": {"host": "chisel", "port": 8089}}
        )

    def probe_404(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    mock_discovery(discovery_handler)
    mock_probes("chisel", 8089, probe_404)

    assert LabDevicesClient.list_active_users() == ["weird_lab"]


def test_list_active_users_returns_sorted(mock_discovery, mock_probes):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "zeta_lab": {"host": "chisel", "port": 8091},
                "alpha_lab": {"host": "chisel", "port": 8089},
            },
        )

    mock_discovery(discovery_handler)
    mock_probes("chisel", 8089, _devices_ok_handler)
    mock_probes("chisel", 8091, _devices_ok_handler)

    assert LabDevicesClient.list_active_users() == ["alpha_lab", "zeta_lab"]


def test_list_active_users_empty_roster(mock_discovery):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    mock_discovery(discovery_handler)
    assert LabDevicesClient.list_active_users() == []


def test_list_active_users_propagates_bridge_unreachable(mock_discovery):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    mock_discovery(discovery_handler)
    with pytest.raises(ClientLookupEndpointUnreachable):
        LabDevicesClient.list_active_users()


def test_list_active_users_propagates_bridge_500(mock_discovery):
    def discovery_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="boom")

    mock_discovery(discovery_handler)
    with pytest.raises(ClientLookupEndpointError):
        LabDevicesClient.list_active_users()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `poetry run pytest tests/test_client_discovery.py::test_list_active_users_returns_only_responsive -v`
Expected: FAIL — `AttributeError: type object 'LabDevicesClient' has no attribute 'list_active_users'`.

- [ ] **Step 3: Add `_build_probe_client` and `list_active_users`**

In `src/bioexperiment_suite/interfaces/lab_devices_client.py`, add this import near the top (with the other imports):

```python
from concurrent.futures import ThreadPoolExecutor
```

Add this factory below `_build_discovery_client`:

```python
def _build_probe_client(host: str, port: int, timeout: float) -> httpx.Client:
    """Factory for per-machine probe clients used by list_active_users.

    Module-level so tests can monkeypatch it to inject a MockTransport.
    """
    return httpx.Client(base_url=f"http://{host}:{port}", timeout=timeout)
```

Inside the `LabDevicesClient` class, add this classmethod just below `list_registered_users`:

```python
    @classmethod
    def list_active_users(
        cls,
        *,
        discovery_url: str | None = None,
        request_timeout_sec: float = 5.0,
        probe_timeout_sec: float = 2.0,
        max_workers: int = 8,
    ) -> list[str]:
        """Return sorted names whose lab_devices_client endpoint currently answers.

        Probes ``GET /devices`` against each registered machine in parallel
        threads. Any HTTP response (2xx/4xx/5xx) counts as active; only
        network-level failures count as inactive.

        Bridge-level errors (ClientLookupEndpointUnreachable /
        ClientLookupEndpointError) propagate to the caller. Per-probe
        errors are swallowed.
        """
        url = _resolve_discovery_url(discovery_url)
        roster = _fetch_roster(url, request_timeout_sec)
        if not roster:
            return []

        def probe(item: tuple[str, dict[str, Any]]) -> str | None:
            name, entry = item
            try:
                with _build_probe_client(
                    entry["host"], entry["port"], probe_timeout_sec
                ) as client:
                    client.get("/devices")
                return name
            except (
                httpx.ConnectError,
                httpx.ConnectTimeout,
                httpx.ReadTimeout,
                httpx.WriteTimeout,
                httpx.PoolTimeout,
            ):
                return None
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    f"probe to {name} ({entry['host']}:{entry['port']}) raised "
                    f"unexpected error: {exc!r}"
                )
                return None

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            results = list(ex.map(probe, roster.items()))

        return sorted(name for name in results if name is not None)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest tests/test_client_discovery.py -v`
Expected: PASS, all tests green.

- [ ] **Step 5: Commit**

```bash
git add src/bioexperiment_suite/interfaces/lab_devices_client.py tests/test_client_discovery.py
git commit -m "Add LabDevicesClient.list_active_users classmethod"
```

---

## Task 9: Re-export new exceptions from `interfaces/__init__.py`

**Files:**
- Modify: `src/bioexperiment_suite/interfaces/__init__.py`
- Test: `tests/test_client_discovery.py`

- [ ] **Step 1: Add the re-export test**

Append to `tests/test_client_discovery.py`:

```python
def test_new_exceptions_are_re_exported_from_interfaces():
    from bioexperiment_suite.interfaces import (
        ClientLookupEndpointError,
        ClientLookupEndpointUnreachable,
        ClientLookupError,
        UnknownLabClient,
    )

    assert ClientLookupError is ldc_mod.ClientLookupError
    assert ClientLookupEndpointUnreachable is ldc_mod.ClientLookupEndpointUnreachable
    assert ClientLookupEndpointError is ldc_mod.ClientLookupEndpointError
    assert UnknownLabClient is ldc_mod.UnknownLabClient
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_client_discovery.py::test_new_exceptions_are_re_exported_from_interfaces -v`
Expected: FAIL — `ImportError: cannot import name 'ClientLookupError' from 'bioexperiment_suite.interfaces'`.

- [ ] **Step 3: Update `__init__.py`**

Replace the import block at the top of `src/bioexperiment_suite/interfaces/__init__.py` (currently lines 1–15) with:

```python
"""Public API for the lab_devices HTTP transport."""
from .lab_devices_client import (
    ClientLookupEndpointError,
    ClientLookupEndpointUnreachable,
    ClientLookupError,
    DeviceBusy,
    DeviceIOFailed,
    DeviceIdentityChanged,
    DeviceNotFound,
    DeviceUnreachable,
    DiscoveredDevices,
    DiscoveryFailed,
    DiscoveryInProgress,
    InvalidRequest,
    LabDevicesClient,
    LabDevicesError,
    TransportError,
    UnknownLabClient,
)
from .pump import Pump
from .densitometer import Densitometer
from .valve import Valve

__all__ = [
    "ClientLookupEndpointError",
    "ClientLookupEndpointUnreachable",
    "ClientLookupError",
    "Densitometer",
    "DeviceBusy",
    "DeviceIOFailed",
    "DeviceIdentityChanged",
    "DeviceNotFound",
    "DeviceUnreachable",
    "DiscoveredDevices",
    "DiscoveryFailed",
    "DiscoveryInProgress",
    "InvalidRequest",
    "LabDevicesClient",
    "LabDevicesError",
    "Pump",
    "TransportError",
    "UnknownLabClient",
    "Valve",
]
```

- [ ] **Step 4: Run all tests to verify**

Run: `poetry run pytest -v`
Expected: PASS, every test in the suite green.

- [ ] **Step 5: Commit**

```bash
git add src/bioexperiment_suite/interfaces/__init__.py tests/test_client_discovery.py
git commit -m "Re-export ClientLookupError hierarchy from interfaces package"
```

---

## Task 10: Integration smoke tests with stdlib `http.server`

**Files:**
- Test: `tests/test_client_discovery.py`

These tests stand up real HTTP listeners — no monkeypatching — to verify the wiring end-to-end with the actual httpx network stack.

- [ ] **Step 1: Add the integration tests**

Append to `tests/test_client_discovery.py`:

```python
import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Iterator
from urllib.parse import urlparse


def _make_handler_class(routes: dict[str, tuple[int, bytes, str]]):
    """Build a BaseHTTPRequestHandler that serves a fixed routing table.

    routes: path -> (status, body, content_type)
    """

    class _Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 — required by stdlib
            entry = routes.get(self.path)
            if entry is None:
                self.send_response(404)
                self.end_headers()
                return
            status, body, content_type = entry
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args, **kwargs) -> None:  # silence test output
            return

    return _Handler


@contextmanager
def _serve(routes: dict[str, tuple[int, bytes, str]]) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _make_handler_class(routes))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2.0)


def _find_closed_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_integration_constructor_resolves_user_against_real_bridge():
    roster = {"khamit_desktop": {"host": "127.0.0.1", "port": 9}}
    bridge_routes = {
        "/api/clients/": (200, json.dumps(roster).encode(), "application/json"),
    }

    with _serve(bridge_routes) as bridge_url:
        client = LabDevicesClient(
            user="khamit_desktop", discovery_url=f"{bridge_url}/api/clients/"
        )
        try:
            assert client.host == "127.0.0.1"
            assert client.port == 9
        finally:
            client.close()


def test_integration_list_active_users_against_real_servers():
    devices_response = json.dumps({"devices": [], "discovered_at": None}).encode()
    devices_routes = {"/devices": (200, devices_response, "application/json")}

    closed_port = _find_closed_port()

    with _serve(devices_routes) as alive_url:
        alive = urlparse(alive_url)
        assert alive.hostname is not None and alive.port is not None

        roster = {
            "alive_machine": {"host": alive.hostname, "port": alive.port},
            "dead_machine": {"host": "127.0.0.1", "port": closed_port},
        }
        bridge_routes = {
            "/api/clients/": (200, json.dumps(roster).encode(), "application/json"),
        }

        with _serve(bridge_routes) as bridge_url:
            active = LabDevicesClient.list_active_users(
                discovery_url=f"{bridge_url}/api/clients/",
                probe_timeout_sec=2.0,
            )

    assert active == ["alive_machine"]


def test_integration_bridge_unreachable_raises_unreachable():
    closed_port = _find_closed_port()
    discovery_url = f"http://127.0.0.1:{closed_port}/api/clients/"

    with pytest.raises(ClientLookupEndpointUnreachable):
        LabDevicesClient(user="x", discovery_url=discovery_url, request_timeout_sec=2.0)
```

- [ ] **Step 2: Run integration tests**

Run: `poetry run pytest tests/test_client_discovery.py -v -k integration`
Expected: PASS, all three integration tests green.

- [ ] **Step 3: Run the full test suite as a final check**

Run: `poetry run pytest -v`
Expected: PASS, every test in the project green. Confirm `test_client_discovery.py` reports the full set of unit + integration tests added across this plan.

- [ ] **Step 4: Commit**

```bash
git add tests/test_client_discovery.py
git commit -m "Add integration smoke tests for username-based discovery"
```

---

## Done

After Task 10:

- The `user=` constructor path resolves a name against the bridge roster.
- `discovery_url` precedence is constructor arg → env var → default.
- `list_registered_users()` and `list_active_users()` are available.
- Bridge failures raise `ClientLookupEndpointUnreachable` / `ClientLookupEndpointError`.
- Unknown user raises `UnknownLabClient` with a helpful message.
- Existing `LabDevicesClient(port=...)` callers (tests, examples, notebook) keep working unchanged.
- All new behavior is covered by unit tests (mocked httpx) and integration smoke tests (real local servers).
