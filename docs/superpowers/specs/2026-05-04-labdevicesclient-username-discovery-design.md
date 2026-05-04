# `LabDevicesClient` — Username-Based Discovery — Design

**Status:** approved by user, ready for implementation plan
**Related:** [2026-04-27-lab-devices-http-client-design.md](2026-04-27-lab-devices-http-client-design.md)

## 1. Goal

Let notebooks identify a lab machine by name (e.g. `"khamit_desktop"`) instead of a hardcoded chisel-tunnel port. The lab-bridge VPS exposes an internal-only HTTP roster endpoint on the docker `labnet` network that maps lab-machine names to `{host, port}` of their chisel tunnel. `LabDevicesClient` learns to consume that roster.

Existing `port=` / `host=` callers keep working unchanged — the migration is additive.

## 2. Scope

### Added

- New parallel exception hierarchy `ClientLookupError` + three subclasses (see §3). Distinct from `LabDevicesError`; the bridge endpoint is a different system from `lab_devices_client`.
- New constructor keyword arguments `user`, `discovery_url`.
- New environment variable `LAB_DEVICES_DISCOVERY_URL`.
- New classmethods `LabDevicesClient.list_registered_users()` and `LabDevicesClient.list_active_users()`.
- New test file `tests/test_client_discovery.py` covering all of the above.

### Edited

- `LabDevicesClient.__init__` signature: keyword-only, mutually exclusive `user=` vs `port=` paths.

### Out of scope

- Changing notebooks that still pass `port=`. They keep working.
- Discovery by anything other than name (no labels, no tags).
- Retries or fallback to hardcoded ports — discovery failures are fatal.
- Caching the roster across calls — see §6.

## 3. Exception hierarchy

A new hierarchy parallel to `LabDevicesError`. Lookup failures are *not* HTTP errors from `lab_devices_client`; they're failures talking to the bridge. Existing `except LabDevicesError` handlers will not catch them, which is correct: a config/lookup failure is a different class of failure.

```python
class ClientLookupError(Exception):
    """Bridge-level discovery failure."""


class ClientLookupEndpointUnreachable(ClientLookupError):
    """Bridge endpoint refused the connection or timed out.

    Typical cause: the caller is not on the docker `labnet` network
    (e.g. running outside the jupyter container). Surfaced as a
    configuration error, not a generic ConnectionError.
    """


class ClientLookupEndpointError(ClientLookupError):
    """Bridge returned 5xx, or the response body was missing/non-JSON/wrong shape."""


class UnknownLabClient(ClientLookupError):
    """Requested user name is not in the bridge roster.

    Message must include both the bad name and the sorted list of
    available names, so the caller can self-diagnose at a glance.
    """
```

Naming intentionally avoids the word "discovery" — `DiscoveryFailed` already exists in `LabDevicesError` for *device* (USB) enumeration on the lab machine. "Client lookup" disambiguates.

## 4. Constructor

```python
class LabDevicesClient:
    def __init__(
        self,
        *,
        port: int | None = None,
        host: str = "chisel",
        user: str | None = None,
        discovery_url: str | None = None,
        request_timeout_sec: float = 5.0,
    ): ...
```

All arguments become keyword-only. (Today's positional `port` only has one in-tree caller — `tests/test_lab_devices_client.py` — so the cost of the kw-only switch is small and avoids future ambiguity now that there are two construction modes.)

### Argument rules

- Exactly one of `user=` and `port=` must be passed.
  - Both → `TypeError("user= and port= are mutually exclusive")`.
  - Neither → `TypeError("either user= or port= must be provided")`.
- `host=` is meaningful only with `port=`. Passing `host=` together with `user=` → `TypeError("host= cannot be combined with user=")`.
- `discovery_url=` is meaningful only with `user=` (or with the listing classmethods, §5). Passing it with `port=` → `TypeError("discovery_url= cannot be combined with port=")`.
- `request_timeout_sec=` applies in both modes. In `user=` mode it also bounds the bridge GET; this keeps the API surface small and there is no measurable need to tune them separately.

### `discovery_url` resolution

Precedence, highest to lowest:

1. The `discovery_url=` constructor argument.
2. The `LAB_DEVICES_DISCOVERY_URL` environment variable.
3. The default `"http://siteapp:8000/api/clients/"`.

Resolution happens at construction time. There is no module-level constant to monkeypatch.

### `user=` flow

1. Resolve the discovery URL as above.
2. `httpx.get(discovery_url, timeout=request_timeout_sec)`.
   - `httpx.ConnectError` / `ConnectTimeout` / `ReadTimeout` / `WriteTimeout` / `PoolTimeout` → `ClientLookupEndpointUnreachable(discovery_url, str(exc))`.
   - Status `>= 500` → `ClientLookupEndpointError(discovery_url, status, body_excerpt)`.
   - Other non-2xx → `ClientLookupEndpointError` (the bridge contract says this endpoint only returns 200 or 500; anything else is a contract violation).
   - Body not JSON or not `dict[str, dict]` with `host`/`port` keys → `ClientLookupEndpointError`.
3. Look up `roster[user]`.
   - Missing → `UnknownLabClient(name=user, available=sorted(roster.keys()))`. The exception's `str()` must include both the bad name and the available names, e.g. `unknown lab client 'khamit_desktp'; available: ['another_lab', 'khamit_desktop']`.
4. Build the inner `httpx.Client` with `base_url=f"http://{entry['host']}:{entry['port']}"` and `timeout=request_timeout_sec`. Store `host` / `port` on `self` exactly as the existing `port=` path does — downstream code (`self.host`, `self.port`) keeps working.

### `port=` flow

Identical to today's behaviour. Untouched.

## 5. Listing classmethods

```python
@classmethod
def list_registered_users(
    cls,
    *,
    discovery_url: str | None = None,
    request_timeout_sec: float = 5.0,
) -> list[str]: ...

@classmethod
def list_active_users(
    cls,
    *,
    discovery_url: str | None = None,
    request_timeout_sec: float = 5.0,
    probe_timeout_sec: float = 2.0,
    max_workers: int = 8,
) -> list[str]: ...
```

Both use the same `discovery_url` resolution as the constructor (§4).

### `list_registered_users`

Returns `sorted(roster.keys())`. No probing. Bridge-error semantics identical to the constructor.

### `list_active_users`

1. Fetch the roster (same error semantics as the constructor; bridge errors propagate to the caller).
2. For each `(name, entry)`, submit a probe to a `concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)`.
3. Each probe is `httpx.get(f"http://{entry['host']}:{entry['port']}/devices", timeout=probe_timeout_sec)`.
4. Probe outcome:
   - Any HTTP response (2xx / 4xx / 5xx) → **active**.
   - `httpx.ConnectError` / `ConnectTimeout` / `ReadTimeout` / `WriteTimeout` / `PoolTimeout` → **inactive**, swallowed.
   - Any other exception → **inactive**, swallowed but logged at `loguru` `warning` level (so a dependency upgrade doesn't silently turn machines invisible).
5. Return `sorted(name for name in roster if probe_succeeded[name])`.

`max_workers=8` is a soft cap; any reasonable lab roster fits within it. With ThreadPoolExecutor wallclock for `N` machines is `~probe_timeout_sec` regardless of `N` (up to `max_workers`), so the timeout is a per-probe upper bound rather than a summed budget.

`probe_timeout_sec=2.0` default. A healthy chisel hop + cached `GET /devices` should complete well under 1s.

`/devices` is chosen as the probe target over `/discover` because it returns the cached registry without triggering USB enumeration.

#### Why threads, not asyncio

The downstream consumers are Jupyter notebooks. Jupyter runs an IPython kernel with an active event loop, so calling `asyncio.run()` from notebook code raises `RuntimeError: asyncio.run() cannot be called from a running event loop`. `ThreadPoolExecutor` sidesteps that and matches the rest of `lab_devices_client.py`'s sync `httpx.Client` style.

## 6. Caching

The roster is **not cached**. Every `LabDevicesClient(user=...)`, `list_registered_users()`, and `list_active_users()` call re-fetches.

Justification: the bridge endpoint reads its backing file on each request and is on the same docker network as the consumer. There is no measurable latency budget to optimize, and caching would only introduce stale-state bugs when machines come and go.

## 7. Module layout

All new code lives in the existing `src/bioexperiment_suite/interfaces/lab_devices_client.py`. The new pieces are ~50–80 lines and tightly coupled to the constructor; splitting them into a separate module would only add an import dance.

A small private helper handles the bridge fetch and shape validation:

```python
def _fetch_roster(
    discovery_url: str,
    request_timeout_sec: float,
) -> dict[str, dict[str, Any]]:
    """GET the bridge endpoint and return the parsed roster.

    Raises ClientLookupEndpointUnreachable / ClientLookupEndpointError.
    Does NOT raise UnknownLabClient — caller decides whether a missing
    user is fatal (constructor) or just absent (listing).
    """
```

The constructor and both classmethods call `_fetch_roster`.

`__init__.py` re-exports the new exception classes alongside the existing ones.

## 8. Dependencies

No new runtime dependencies. `httpx` already in `pyproject.toml`. `concurrent.futures` and `os` (for env var) are stdlib.

No new test dependencies. Stdlib `http.server` covers the integration smoke test (see §9).

## 9. Tests

New file `tests/test_client_discovery.py`. Existing `tests/test_lab_devices_client.py` and `tests/test_discovery.py` are not modified.

### Helpers

- `_make_roster_handler(roster: dict) -> Callable[[httpx.Request], httpx.Response]` — returns a handler that responds to the discovery URL with `roster` as JSON. For "bridge unreachable" / "bridge 500" cases, return failing handlers directly.
- A small fixture wraps `httpx.MockTransport` to intercept *both* the bridge GET and the per-machine probes. Different hosts in the same `MockTransport` are routed by the request's `url.host` attribute.

### Unit tests

Constructor:

- `LabDevicesClient(user="khamit_desktop")` → resolves to `host="chisel"`, `port=8089` and the inner client's `base_url` matches.
- `LabDevicesClient(user="khamit_desktop", port=9001)` → `TypeError`, message mentions mutual exclusivity.
- `LabDevicesClient()` (neither) → `TypeError`.
- `LabDevicesClient(user="x", host="other")` → `TypeError`.
- `LabDevicesClient(port=9001, discovery_url="http://x")` → `TypeError`.
- Unknown user → `UnknownLabClient`. `str(exc)` contains both the bad name and the sorted available names.
- Bridge raises `httpx.ConnectError` → `ClientLookupEndpointUnreachable`. `str(exc)` mentions the discovery URL.
- Bridge raises `httpx.ConnectTimeout` → `ClientLookupEndpointUnreachable`.
- Bridge returns 500 → `ClientLookupEndpointError`. `str(exc)` mentions status `500`.
- Bridge returns non-JSON body → `ClientLookupEndpointError`.
- Bridge returns JSON of wrong shape (e.g. a list, or entries missing `host`/`port`) → `ClientLookupEndpointError`.

Discovery URL resolution:

- Default URL is used when nothing is passed and env is unset.
- Constructor `discovery_url=` overrides default.
- `LAB_DEVICES_DISCOVERY_URL` env var overrides default (use `monkeypatch.setenv`).
- Constructor `discovery_url=` overrides env var.

Listing:

- `list_registered_users()` returns sorted roster keys.
- `list_registered_users()` propagates bridge errors as the same three exceptions.
- `list_active_users()` against a roster of 3 entries where one is reachable, one refuses connections, one times out → returns sorted list with only the reachable name.
- `list_active_users()` propagates bridge errors as the same three exceptions.
- `list_active_users()` treats a 500 from a probe target as **active** (the lab_devices_client service answered, just unhappily).
- `list_active_users()` treats a 404 from a probe target as **active** (same reason).

### Integration tests

A pytest fixture starts a stdlib `http.server.ThreadingHTTPServer` on `127.0.0.1:0` returning the documented bridge response shape. The test points `discovery_url=` at the fixture's URL.

- Smoke: build `LabDevicesClient(user="x", discovery_url=fixture_url)` end-to-end, then close it. No mocks for the bridge layer.
- Smoke: spin up two more local servers — one returning a `/devices` JSON, one with the port closed. The roster references both. `list_active_users(discovery_url=fixture_url)` returns just the open one.

No real-network test — the bridge endpoint isn't reachable from CI.

## 10. Backwards compatibility

- Every existing caller already passes `port=` (and where applicable `host=`) as a keyword argument — verified by grep across `tests/`, `examples/`, and the notebook. The keyword-only switch is therefore fully transparent to current code.
- The existing `LabDevicesError` hierarchy is untouched. Nothing in the new path raises a `LabDevicesError`; nothing in the existing paths raises a `ClientLookupError`.
- `host` defaults to `"chisel"` as today. Existing tests that assert `base_url == "http://chisel:9001"` keep passing.

## 11. Failure-mode summary

| Situation                                              | Exception                            | Where raised               |
| ------------------------------------------------------ | ------------------------------------ | -------------------------- |
| `user=` + `port=` (or `host=`, `discovery_url=`) both passed | `TypeError`                          | constructor                |
| Neither `user=` nor `port=` passed                     | `TypeError`                          | constructor                |
| Bridge endpoint refuses connection / times out         | `ClientLookupEndpointUnreachable`    | constructor, both listings |
| Bridge returns 500 / non-JSON / wrong shape            | `ClientLookupEndpointError`          | constructor, both listings |
| User name not in roster                                | `UnknownLabClient`                   | constructor only           |
| Probe to a specific machine fails                      | (swallowed; machine omitted from result) | `list_active_users` only |
