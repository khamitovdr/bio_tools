"""Pump operation routes."""

from typing import Union
from uuid import UUID

from fastapi import APIRouter, HTTPException, Response
from loguru import logger

from ..jobs import JobManager
from ..models import JobResponse, PourVolumeRequest, SetDefaultFlowRequest, StartPumpRequest
from ..registry import DeviceRegistry

router = APIRouter()


@router.post("/devices/{device_id}/pump/set-default-flow")
async def set_default_flow(device_id: str, request: SetDefaultFlowRequest) -> dict[str, str]:
    """Set default flow rate for a pump."""
    try:
        registry = DeviceRegistry()
        device_type, pump = registry.get(device_id)

        if device_type != "pump":
            raise HTTPException(status_code=409, detail=f"Device {device_id} is not a pump")

        # Acquire device lock for synchronous operation
        lock = registry.lock(device_id)
        async with lock:
            pump.set_default_flow_rate(request.flow_rate)

        logger.info(f"Set default flow rate {request.flow_rate} mL/min for pump {device_id}")
        return {"message": f"Default flow rate set to {request.flow_rate} mL/min"}

    except HTTPException:
        raise
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    except AttributeError as e:
        logger.error(f"Device type mismatch for pump operation on {device_id}: {e}")
        raise HTTPException(status_code=409, detail=f"Device {device_id} is not a pump")
    except Exception as e:
        logger.error(f"Error setting default flow for pump {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to set default flow rate")


@router.post("/devices/{device_id}/pump/pour-volume", response_model=Union[JobResponse, dict])
async def pour_volume(device_id: str, request: PourVolumeRequest, response: Response) -> JobResponse | dict:
    """Pour a specific volume with the pump."""
    try:
        registry = DeviceRegistry()
        device_type, pump = registry.get(device_id)

        if device_type != "pump":
            raise HTTPException(status_code=409, detail=f"Device {device_id} is not a pump")

        # Determine if this should be async based on blocking_mode
        # blocking_mode=True forces synchronous execution
        # blocking_mode=False forces asynchronous execution
        use_async = not request.blocking_mode

        if use_async:
            # Submit as async job
            job_manager = JobManager()
            lock = registry.lock(device_id)

            def pour_operation():
                return pump.pour_in_volume(
                    volume=request.volume,
                    flow_rate=request.flow_rate,
                    direction=request.direction,
                    blocking_mode=True,  # Always block in the worker thread
                    info_log_message=f"Pouring {request.volume} mL in direction {request.direction}",
                )

            job_id = job_manager.submit(
                device_id=device_id,
                action="pour_volume",
                fn=pour_operation,
                lock=lock,
                params=request.model_dump(),
                timeout=request.timeout,
            )

            logger.info(f"Submitted async pour volume job {job_id} for pump {device_id}")
            response.status_code = 202
            return JobResponse(job_id=job_id)

        else:
            # Execute synchronously
            lock = registry.lock(device_id)
            async with lock:
                pump.pour_in_volume(
                    volume=request.volume,
                    flow_rate=request.flow_rate,
                    direction=request.direction,
                    blocking_mode=request.blocking_mode,
                    info_log_message=f"Pouring {request.volume} mL in direction {request.direction}",
                )

            logger.info(f"Completed synchronous pour volume for pump {device_id}")
            return {"message": f"Poured {request.volume} mL successfully"}

    except HTTPException:
        raise
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error pouring volume with pump {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to pour volume")


@router.post("/devices/{device_id}/pump/start")
async def start_pump(device_id: str, request: StartPumpRequest) -> dict[str, str]:
    """Start continuous pump rotation."""
    try:
        registry = DeviceRegistry()
        device_type, pump = registry.get(device_id)

        if device_type != "pump":
            raise HTTPException(status_code=409, detail=f"Device {device_id} is not a pump")

        # Acquire device lock for synchronous operation
        lock = registry.lock(device_id)
        async with lock:
            pump.start_continuous_rotation(
                flow_rate=request.flow_rate,
                direction=request.direction,
            )

        flow_rate_msg = f" at {request.flow_rate} mL/min" if request.flow_rate else ""
        logger.info(f"Started continuous rotation for pump {device_id} in direction {request.direction}{flow_rate_msg}")
        return {"message": f"Pump started in {request.direction} direction{flow_rate_msg}"}

    except HTTPException:
        raise
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting pump {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to start pump")


@router.post("/devices/{device_id}/pump/stop")
async def stop_pump(device_id: str) -> dict[str, str]:
    """Stop pump rotation."""
    try:
        registry = DeviceRegistry()
        device_type, pump = registry.get(device_id)

        if device_type != "pump":
            raise HTTPException(status_code=409, detail=f"Device {device_id} is not a pump")

        # Acquire device lock for synchronous operation
        lock = registry.lock(device_id)
        async with lock:
            pump.stop_continuous_rotation()

        logger.info(f"Stopped pump {device_id}")
        return {"message": "Pump stopped"}

    except HTTPException:
        raise
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not found")
    except ValueError as e:
        # Handle flow rate requirement error more gracefully
        if "Flow rate must be set" in str(e):
            # Set a default flow rate for stopping
            lock = registry.lock(device_id)
            async with lock:
                pump.set_default_flow_rate(1.0)  # Set minimal flow rate
                pump.stop_continuous_rotation()
            logger.info(f"Stopped pump {device_id} (set default flow rate)")
            return {"message": "Pump stopped"}
        raise HTTPException(status_code=422, detail=str(e))
    except AttributeError as e:
        logger.error(f"Device type mismatch for pump operation on {device_id}: {e}")
        raise HTTPException(status_code=409, detail=f"Device {device_id} is not a pump")
    except Exception as e:
        logger.error(f"Error stopping pump {device_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to stop pump")
