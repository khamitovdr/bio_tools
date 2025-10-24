"""Job management routes."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from loguru import logger

from ..jobs import JobManager
from ..models import Job

router = APIRouter()


@router.get("/jobs/{job_id}", response_model=Job)
async def get_job(job_id: UUID) -> Job:
    """Get job status and details."""
    try:
        job_manager = JobManager()
        job = job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return job

    except HTTPException:
        raise
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Invalid job ID format: {job_id}")
    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get job")


@router.delete("/jobs/{job_id}")
async def delete_job(job_id: UUID) -> dict[str, str]:
    """Delete a completed job."""
    try:
        job_manager = JobManager()

        if not job_manager.get_job(job_id):
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        success = job_manager.delete_job(job_id)

        if not success:
            raise HTTPException(status_code=409, detail="Cannot delete running job")

        logger.info(f"Deleted job {job_id}")
        return {"message": f"Job {job_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete job")


@router.get("/jobs", response_model=list[Job])
async def list_jobs(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of jobs to return"),
    offset: int = Query(0, ge=0, description="Number of jobs to skip"),
) -> list[Job]:
    """List jobs with pagination."""
    try:
        job_manager = JobManager()
        jobs = job_manager.list_jobs(limit=limit, offset=offset)

        logger.debug(f"Listed {len(jobs)} jobs (limit={limit}, offset={offset})")
        return jobs

    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to list jobs")


@router.websocket("/ws/jobs/{job_id}")
async def job_websocket(websocket: WebSocket, job_id: UUID):
    """WebSocket endpoint for real-time job updates."""
    await websocket.accept()

    job_manager = JobManager()

    try:
        # Check if job exists
        job = job_manager.get_job(job_id)
        if not job:
            await websocket.send_json({"error": f"Job {job_id} not found"})
            await websocket.close(code=1000)
            return

        logger.info(f"WebSocket connected for job {job_id}")

        # Send initial job status
        await websocket.send_json(job.model_dump(mode="json"))

        # Poll for updates until job is complete or connection closes
        while True:
            try:
                # Wait for any message from client (keep-alive)
                await websocket.receive_text()
            except WebSocketDisconnect:
                break

            # Get updated job status
            updated_job = job_manager.get_job(job_id)
            if not updated_job:
                await websocket.send_json({"error": f"Job {job_id} no longer exists"})
                break

            # Send updated status
            await websocket.send_json(updated_job.model_dump(mode="json"))

            # If job is complete, close connection
            if updated_job.status in ["succeeded", "failed"]:
                break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass
    finally:
        try:
            await websocket.close()
        except:
            pass
