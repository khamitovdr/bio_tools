"""Job manager for handling asynchronous device operations."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any, Callable, ClassVar, Optional
from uuid import UUID, uuid4

import anyio
from loguru import logger

from .models import Job, JobStatus
from .settings import get_settings


class JobManager:
    """Singleton job manager for handling asynchronous operations."""
    
    _instance: ClassVar["JobManager | None"] = None
    
    def __new__(cls) -> "JobManager":
        """Create or return singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self) -> None:
        """Initialize the job manager."""
        settings = get_settings()
        self._jobs: dict[UUID, Job] = {}
        self._executor = ThreadPoolExecutor(max_workers=settings.MAX_WORKERS)
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start_cleanup_task(self) -> None:
        """Start the periodic cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
    
    async def stop_cleanup_task(self) -> None:
        """Stop the periodic cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
    
    async def _periodic_cleanup(self) -> None:
        """Periodically clean up old completed jobs."""
        settings = get_settings()
        
        while True:
            try:
                await asyncio.sleep(settings.JOB_RETENTION_SEC // 4)  # Check every quarter of retention time
                await self._cleanup_old_jobs()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in job cleanup task: {e}")
    
    async def _cleanup_old_jobs(self) -> None:
        """Clean up jobs older than retention time."""
        settings = get_settings()
        cutoff_time = datetime.now(timezone.utc).timestamp() - settings.JOB_RETENTION_SEC
        
        jobs_to_remove = []
        for job_id, job in self._jobs.items():
            # Only clean up completed jobs (succeeded or failed)
            if job.status in [JobStatus.SUCCEEDED, JobStatus.FAILED]:
                finished_time = job.finished_at or job.submitted_at
                if finished_time.timestamp() < cutoff_time:
                    jobs_to_remove.append(job_id)
        
        for job_id in jobs_to_remove:
            del self._jobs[job_id]
        
        if jobs_to_remove:
            logger.debug(f"Cleaned up {len(jobs_to_remove)} old jobs")
    
    def submit(
        self,
        device_id: str,
        action: str,
        fn: Callable[[], Any],
        lock: asyncio.Lock,
        params: Optional[dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> UUID:
        """Submit a job for execution.
        
        Args:
            device_id: ID of the device to operate on
            action: Action being performed
            fn: Function to execute in thread
            lock: Device lock to acquire
            params: Job parameters
            timeout: Execution timeout in seconds
            
        Returns:
            Job ID
        """
        job_id = uuid4()
        now = datetime.now(timezone.utc)
        
        job = Job(
            job_id=job_id,
            status=JobStatus.PENDING,
            submitted_at=now,
            device_id=device_id,
            action=action,
            params=params or {},
        )
        
        self._jobs[job_id] = job
        
        # Start the job execution
        asyncio.create_task(self._execute_job(job_id, fn, lock, timeout))
        
        logger.info(f"Job {job_id} submitted for device {device_id}, action {action}")
        return job_id
    
    async def _execute_job(
        self,
        job_id: UUID,
        fn: Callable[[], Any],
        lock: asyncio.Lock,
        timeout: Optional[float] = None,
    ) -> None:
        """Execute a job with proper error handling and status updates.
        
        Args:
            job_id: Job ID
            fn: Function to execute
            lock: Device lock to acquire
            timeout: Execution timeout in seconds
        """
        job = self._jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found during execution")
            return
        
        try:
            # Acquire device lock
            async with lock:
                # Update job status to running
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now(timezone.utc)
                
                logger.debug(f"Job {job_id} started execution")
                
                # Execute function in thread pool with timeout
                if timeout:
                    async with anyio.fail_after(timeout):
                        result = await anyio.to_thread.run_sync(fn)
                else:
                    result = await anyio.to_thread.run_sync(fn)
                
                # Update job with success
                job.status = JobStatus.SUCCEEDED
                job.finished_at = datetime.now(timezone.utc)
                job.result = result
                
                logger.info(f"Job {job_id} completed successfully")
                
        except asyncio.TimeoutError:
            job.status = JobStatus.FAILED
            job.finished_at = datetime.now(timezone.utc)
            job.error = f"Job timed out after {timeout} seconds"
            logger.warning(f"Job {job_id} timed out")
            
        except Exception as e:
            job.status = JobStatus.FAILED
            job.finished_at = datetime.now(timezone.utc)
            job.error = str(e)
            logger.error(f"Job {job_id} failed with error: {e}")
    
    def get_job(self, job_id: UUID) -> Optional[Job]:
        """Get job by ID.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job if found, None otherwise
        """
        return self._jobs.get(job_id)
    
    def list_jobs(self, limit: int = 100, offset: int = 0) -> list[Job]:
        """List jobs with pagination.
        
        Args:
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip
            
        Returns:
            List of jobs
        """
        jobs = list(self._jobs.values())
        # Sort by submission time, newest first
        jobs.sort(key=lambda j: j.submitted_at, reverse=True)
        return jobs[offset:offset + limit]
    
    def delete_job(self, job_id: UUID) -> bool:
        """Delete a job.
        
        Args:
            job_id: Job ID
            
        Returns:
            True if job was deleted, False if not found
        """
        if job_id in self._jobs:
            job = self._jobs[job_id]
            # Only allow deletion of completed jobs
            if job.status in [JobStatus.SUCCEEDED, JobStatus.FAILED]:
                del self._jobs[job_id]
                logger.debug(f"Job {job_id} deleted")
                return True
            else:
                logger.warning(f"Cannot delete running job {job_id}")
                return False
        return False
    
    async def shutdown(self) -> None:
        """Shutdown job manager and cleanup resources."""
        logger.info("Shutting down job manager...")
        
        # Stop cleanup task
        await self.stop_cleanup_task()
        
        # Shutdown executor
        self._executor.shutdown(wait=True)
        
        # Clear jobs
        self._jobs.clear()
        
        logger.info("Job manager shutdown complete")
