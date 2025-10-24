"""Type definitions and enums for the bioexperiment tools."""

from enum import Enum
from typing import Literal, TypeAlias


# Device types
class DeviceType(str, Enum):
    """Supported device types."""

    PUMP = "pump"
    SPECTROPHOTOMETER = "spectrophotometer"


# Direction for pump operations
class Direction(str, Enum):
    """Pump direction options."""

    LEFT = "left"
    RIGHT = "right"


# Type aliases for better readability
PortName: TypeAlias = str
DeviceId: TypeAlias = str
FlowRate: TypeAlias = float  # mL/min
Volume: TypeAlias = float  # mL
Temperature: TypeAlias = float  # Celsius
OpticalDensity: TypeAlias = float

# Literal types for specific values
DirectionLiteral = Literal["left", "right"]
