"""Application settings."""

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Settings:
    """Application settings."""
    # Device emulation (inherited from bioexperiment-tools)
    EMULATE_DEVICES: bool = False
    N_VIRTUAL_PUMPS: int = 0
    N_VIRTUAL_SPECTROPHOTOMETERS: int = 0
    
    # API settings
    LOG_LEVEL: str = "INFO"
    RESCAN_INTERVAL_SEC: int = 60
    JOB_RETENTION_SEC: int = 3600
    MAX_WORKERS: int = 4
    
    # Security
    API_KEY: str = ""
    CORS_ORIGINS: list[str] = None
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    """Get application settings."""
    cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
    
    return Settings(
        EMULATE_DEVICES=os.getenv("EMULATE_DEVICES", "False").lower() == "true",
        N_VIRTUAL_PUMPS=int(os.getenv("N_VIRTUAL_PUMPS", "0")),
        N_VIRTUAL_SPECTROPHOTOMETERS=int(os.getenv("N_VIRTUAL_SPECTROPHOTOMETERS", "0")),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        RESCAN_INTERVAL_SEC=int(os.getenv("RESCAN_INTERVAL_SEC", "60")),
        JOB_RETENTION_SEC=int(os.getenv("JOB_RETENTION_SEC", "3600")),
        MAX_WORKERS=int(os.getenv("MAX_WORKERS", "4")),
        API_KEY=os.getenv("API_KEY", ""),
        CORS_ORIGINS=cors_origins,
        HOST=os.getenv("HOST", "0.0.0.0"),
        PORT=int(os.getenv("PORT", "8000")),
    )
