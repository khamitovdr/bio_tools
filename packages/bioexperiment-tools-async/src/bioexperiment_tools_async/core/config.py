"""Pydantic configuration models for devices and global settings."""

from typing import Any

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .types import DeviceType


class DeviceConfig(BaseModel):
    """Configuration for a specific device type."""
    
    device_type: DeviceType = Field(description="The type of device")
    identification_signal: list[int] = Field(description="Signal to send for device identification")
    identification_response_len: int = Field(description="Expected length of identification response")
    first_identification_response_byte: int = Field(description="Expected first byte of identification response")
    commands: dict[str, Any] = Field(default_factory=dict, description="Device command definitions")
    speed_table: dict[str, list[int]] | None = Field(default=None, description="Speed table for pump devices")


class PumpConfig(DeviceConfig):
    """Configuration specific to pump devices."""
    
    device_type: DeviceType = Field(default=DeviceType.PUMP)
    speed_table: dict[str, list[int]] = Field(description="Speed mapping table for pump operations")
    unaccounted_time_sec: float = Field(default=1.0, description="Additional time buffer for operations")


class SpectrophotometerConfig(DeviceConfig):
    """Configuration specific to spectrophotometer devices."""
    
    device_type: DeviceType = Field(default=DeviceType.SPECTROPHOTOMETER)


class ConnectionConfig(BaseModel):
    """Configuration for device connections."""
    
    baudrate: int = Field(default=9600, description="Serial connection baudrate")
    timeout: float = Field(default=1.0, description="Connection timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum connection retry attempts")
    retry_delay: float = Field(default=0.5, description="Delay between retry attempts in seconds")


class GlobalConfig(BaseSettings):
    """Global configuration with environment variable support."""
    
    # Device emulation settings
    emulate_devices: bool = Field(default=False)
    n_virtual_pumps: int = Field(default=0) 
    n_virtual_spectrophotometers: int = Field(default=0)
    
    # Connection settings
    connection: ConnectionConfig = Field(default_factory=ConnectionConfig)
    
    # Discovery settings
    discovery_timeout: float = Field(default=30.0)
    discovery_concurrent_limit: int = Field(default=10)
    device_cache_ttl: float = Field(default=60.0)
    
    # Logging settings
    log_level: str = Field(default="INFO")
    log_format: str = Field(
        default="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}"
    )
    
    model_config = SettingsConfigDict(
        env_prefix="BIOEXPERIMENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Global configuration instance
_global_config: GlobalConfig | None = None


def get_config(*, reload: bool = False) -> GlobalConfig:
    """Get the global configuration instance.
    
    Args:
        reload: Force reload the configuration from environment variables
    """
    global _global_config
    if _global_config is None or reload:
        _global_config = GlobalConfig()
    return _global_config


def clear_config() -> None:
    """Clear the global configuration cache. Useful for testing."""
    global _global_config
    _global_config = None
