"""Device discovery and management routes."""

from fastapi import APIRouter, HTTPException
from loguru import logger

from ..models import Device, HealthResponse, RescanResponse
from ..registry import DeviceRegistry

router = APIRouter()


@router.get("/healthz", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(status="healthy")


@router.get("/devices", response_model=list[Device])
async def list_devices() -> list[Device]:
    """List all connected devices."""
    try:
        registry = DeviceRegistry()

        # Ensure registry is initialized
        if not registry.is_initialized():
            await registry.scan()

        devices = registry.list_devices()
        logger.debug(f"Listed {len(devices)} devices")
        return devices

    except Exception as e:
        logger.error(f"Error listing devices: {e}")
        raise HTTPException(status_code=500, detail="Failed to list devices")


@router.get("/devices/{device_id}", response_model=Device)
async def get_device(device_id: str) -> Device:
    """Get details for a specific device."""
    try:
        registry = DeviceRegistry()
        device = registry.get_device_details(device_id)
        return device

    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    except Exception as e:
        logger.error(f"Error getting device {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get device details")


@router.post("/devices:rescan", response_model=RescanResponse)
async def rescan_devices() -> RescanResponse:
    """Rescan for connected devices."""
    try:
        registry = DeviceRegistry()
        result = await registry.scan()

        logger.info(f"Device rescan completed: {result}")
        return RescanResponse(
            added=result["added"],
            removed=result["removed"],
        )

    except Exception as e:
        logger.error(f"Error during device rescan: {e}")
        raise HTTPException(status_code=500, detail="Failed to rescan devices")
