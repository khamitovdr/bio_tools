"""Device command definitions with type safety."""

from dataclasses import dataclass
from typing import Any

from ..core.types import Direction, FlowRate, Volume
from ..utils.serial_utils import int_to_bytes


@dataclass(frozen=True)
class DeviceCommand:
    """Base class for device commands."""
    
    data: list[int]
    response_length: int = 0
    description: str = ""
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.description}): {self.data}"


@dataclass(frozen=True)
class PumpCommand(DeviceCommand):
    """Command for pump devices."""
    
    @classmethod
    def identification(cls) -> "PumpCommand":
        """Create pump identification command."""
        return cls(
            data=[1, 2, 3, 4, 181],
            response_length=4,
            description="Pump identification"
        )
    
    @classmethod
    def set_flow_rate(cls, flow_rate: FlowRate) -> "PumpCommand":
        """Create set flow rate command."""
        speed_param = int(29 / flow_rate) if flow_rate > 0 else 29
        return cls(
            data=[10, 0, 1, speed_param, 0],
            response_length=0,
            description=f"Set flow rate to {flow_rate} mL/min"
        )
    
    @classmethod
    def pour_volume(cls, volume: Volume, direction: Direction, calibration_volume: float) -> "PumpCommand":
        """Create pour volume command."""
        direction_byte = 16 if direction == Direction.LEFT else 17
        step_volume = int((volume * 10**4) / calibration_volume)
        step_volume_bytes = int_to_bytes(step_volume, 4)
        
        return cls(
            data=[direction_byte] + step_volume_bytes,
            response_length=0,
            description=f"Pour {volume} mL {direction.value}"
        )
    
    @classmethod
    def start_continuous_rotation(cls, flow_rate: FlowRate, direction: Direction) -> "PumpCommand":
        """Create continuous rotation command."""
        direction_byte = 11 if direction == Direction.LEFT else 12
        speed_param = int(29 / flow_rate) if flow_rate > 0 else 29
        
        return cls(
            data=[direction_byte, 111, 1, speed_param, 0],
            response_length=0,
            description=f"Start continuous rotation {direction.value} at {flow_rate} mL/min"
        )
    
    @classmethod
    def stop_rotation(cls) -> "PumpCommand":
        """Create stop rotation command."""
        # Stop by pouring 0 volume
        return cls.pour_volume(0.0, Direction.LEFT, 1.0)


@dataclass(frozen=True) 
class SpectrophotometerCommand(DeviceCommand):
    """Command for spectrophotometer devices."""
    
    @classmethod
    def identification(cls) -> "SpectrophotometerCommand":
        """Create spectrophotometer identification command."""
        return cls(
            data=[1, 2, 3, 4, 0],
            response_length=4,
            description="Spectrophotometer identification"
        )
    
    @classmethod
    def get_temperature(cls) -> "SpectrophotometerCommand":
        """Create get temperature command."""
        return cls(
            data=[76, 0, 0, 0, 0],
            response_length=4,
            description="Get temperature"
        )
    
    @classmethod
    def start_measurement(cls) -> "SpectrophotometerCommand":
        """Create start measurement command."""
        return cls(
            data=[78, 4, 0, 0, 0],
            response_length=0,
            description="Start optical density measurement"
        )
    
    @classmethod
    def get_measurement_result(cls) -> "SpectrophotometerCommand":
        """Create get measurement result command."""
        return cls(
            data=[79, 4, 0, 0, 0],
            response_length=4,
            description="Get measurement result"
        )
