"""Pydantic models for the bioexperiment API."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DeviceType(str, Enum):
    """Device type enumeration."""
    PUMP = "pump"
    SPECTROPHOTOMETER = "spectrophotometer"


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Device(BaseModel):
    """Device model."""
    device_id: str
    type: DeviceType
    port: str
    is_available: bool


class Job(BaseModel):
    """Job model."""
    job_id: UUID
    status: JobStatus
    submitted_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    device_id: str
    action: str
    params: dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"


class RescanResponse(BaseModel):
    """Device rescan response."""
    added: list[str]
    removed: list[str]


class JobResponse(BaseModel):
    """Job creation response."""
    job_id: UUID


# Pump operation models
class SetDefaultFlowRequest(BaseModel):
    """Set default flow rate request."""
    flow_rate: float = Field(gt=0, description="Flow rate in mL/min")


class PourVolumeRequest(BaseModel):
    """Pour volume request."""
    volume: float = Field(gt=0, description="Volume to pour in mL")
    flow_rate: Optional[float] = Field(None, gt=0, description="Flow rate in mL/min")
    direction: str = Field("left", pattern="^(left|right)$", description="Pump direction")
    blocking_mode: bool = Field(True, description="Whether to wait for completion")
    timeout: Optional[float] = Field(None, gt=0, description="Timeout in seconds")


class StartPumpRequest(BaseModel):
    """Start continuous pump rotation request."""
    flow_rate: Optional[float] = Field(None, gt=0, description="Flow rate in mL/min")
    direction: str = Field("left", pattern="^(left|right)$", description="Pump direction")


# Spectrophotometer operation models
class TemperatureResponse(BaseModel):
    """Temperature response."""
    temperature: float = Field(description="Temperature in degrees Celsius")


class MeasureRequest(BaseModel):
    """Measure optical density request."""
    timeout: Optional[float] = Field(None, gt=0, description="Timeout in seconds")
