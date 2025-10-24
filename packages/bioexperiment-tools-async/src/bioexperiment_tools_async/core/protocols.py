"""Type protocols for devices and connections."""

from typing import Any, Protocol, runtime_checkable

from .types import DeviceType, Direction, FlowRate, OpticalDensity, PortName, Temperature, Volume


@runtime_checkable
class AsyncConnection(Protocol):
    """Protocol for async connection implementations."""

    @property
    def port(self) -> PortName:
        """The port name this connection is bound to."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether the connection is currently active."""
        ...

    async def connect(self) -> None:
        """Establish the connection."""
        ...

    async def disconnect(self) -> None:
        """Close the connection."""
        ...

    async def write(self, data: list[int]) -> None:
        """Write data to the connection."""
        ...

    async def read(self, num_bytes: int) -> bytes:
        """Read data from the connection."""
        ...

    async def communicate(self, data: list[int], response_bytes: int) -> bytes:
        """Send data and read response in one operation."""
        ...

    async def __aenter__(self) -> "AsyncConnection":
        """Async context manager entry."""
        ...

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        ...


@runtime_checkable
class AsyncDevice(Protocol):
    """Protocol for async device implementations."""

    @property
    def device_type(self) -> DeviceType:
        """The type of this device."""
        ...

    @property
    def port(self) -> PortName:
        """The port this device is connected to."""
        ...

    @property
    def device_id(self) -> str:
        """Unique identifier for this device."""
        ...

    @property
    def is_connected(self) -> bool:
        """Whether the device is currently connected."""
        ...

    async def connect(self) -> None:
        """Connect to the device."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        ...

    async def __aenter__(self) -> "AsyncDevice":
        """Async context manager entry."""
        ...

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        ...


@runtime_checkable
class AsyncPumpProtocol(AsyncDevice, Protocol):
    """Protocol for async pump implementations."""

    @property
    def default_flow_rate(self) -> FlowRate | None:
        """The default flow rate for this pump."""
        ...

    async def set_default_flow_rate(self, flow_rate: FlowRate) -> None:
        """Set the default flow rate."""
        ...

    async def pour_volume(
        self,
        volume: Volume,
        *,
        flow_rate: FlowRate | None = None,
        direction: Direction = Direction.LEFT,
        timeout: float | None = None,
    ) -> None:
        """Pour a specific volume."""
        ...

    async def start_continuous_rotation(
        self,
        *,
        flow_rate: FlowRate | None = None,
        direction: Direction = Direction.LEFT,
    ) -> None:
        """Start continuous rotation."""
        ...

    async def stop_continuous_rotation(self) -> None:
        """Stop continuous rotation."""
        ...


@runtime_checkable
class AsyncSpectrophotometerProtocol(AsyncDevice, Protocol):
    """Protocol for async spectrophotometer implementations."""

    async def get_temperature(self) -> Temperature:
        """Get the current temperature."""
        ...

    async def measure_optical_density(self, *, timeout: float | None = None) -> OpticalDensity:
        """Measure optical density."""
        ...
