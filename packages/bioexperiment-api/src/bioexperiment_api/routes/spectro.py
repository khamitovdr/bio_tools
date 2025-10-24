"""Spectrophotometer operation routes."""

from fastapi import APIRouter, HTTPException, Response
from loguru import logger

from ..jobs import JobManager
from ..models import JobResponse, MeasureRequest, TemperatureResponse
from ..registry import DeviceRegistry

router = APIRouter()


@router.get("/devices/{device_id}/spectro/temperature", response_model=TemperatureResponse)
async def get_temperature(device_id: str) -> TemperatureResponse:
    """Get temperature from spectrophotometer."""
    try:
        registry = DeviceRegistry()
        device_type, spectro = registry.get(device_id)

        if device_type != "spectrophotometer":
            raise HTTPException(status_code=409, detail=f"Device {device_id} is not a spectrophotometer")

        # Acquire device lock for synchronous operation
        lock = registry.lock(device_id)
        async with lock:
            temperature = spectro.get_temperature()

        logger.info(f"Got temperature {temperature:.2f}°C from spectrophotometer {device_id}")
        return TemperatureResponse(temperature=temperature)

    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    except AttributeError as e:
        logger.error(f"Device type mismatch for spectro operation on {device_id}: {e}")
        raise HTTPException(status_code=409, detail=f"Device {device_id} is not a spectrophotometer")
    except Exception as e:
        logger.error(f"Error getting temperature from spectrophotometer {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get temperature")


@router.post("/devices/{device_id}/spectro/measure", response_model=JobResponse)
async def measure_optical_density(device_id: str, request: MeasureRequest, response: Response) -> JobResponse:
    """Measure optical density with spectrophotometer (async operation)."""
    try:
        registry = DeviceRegistry()
        device_type, spectro = registry.get(device_id)

        if device_type != "spectrophotometer":
            raise HTTPException(status_code=409, detail=f"Device {device_id} is not a spectrophotometer")

        # Submit as async job (measurement takes time)
        job_manager = JobManager()
        lock = registry.lock(device_id)

        def measure_operation():
            return spectro.measure_optical_density()

        job_id = job_manager.submit(
            device_id=device_id,
            action="measure_optical_density",
            fn=measure_operation,
            lock=lock,
            params=request.model_dump(),
            timeout=request.timeout,
        )

        logger.info(f"Submitted async optical density measurement job {job_id} for spectrophotometer {device_id}")
        response.status_code = 202
        return JobResponse(job_id=job_id)

    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    except Exception as e:
        logger.error(f"Error measuring optical density with spectrophotometer {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start optical density measurement")
