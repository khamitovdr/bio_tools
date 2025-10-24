"""FastAPI application factory and configuration."""

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .jobs import JobManager
from .registry import DeviceRegistry
from .routes import devices, jobs, pump, spectro
from .settings import get_settings


async def periodic_rescan():
    """Periodic device rescan background task."""
    settings = get_settings()
    registry = DeviceRegistry()

    while True:
        try:
            await asyncio.sleep(settings.RESCAN_INTERVAL_SEC)
            result = await registry.scan()
            if result["added"] or result["removed"]:
                logger.info(f"Periodic rescan found changes: {result}")
        except asyncio.CancelledError:
            logger.info("Periodic rescan task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic rescan: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager."""
    settings = get_settings()

    # Configure logging
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        level=settings.LOG_LEVEL,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    )

    logger.info("Starting bioexperiment API...")

    # Initialize device registry
    registry = DeviceRegistry()
    await registry.scan()
    logger.info(f"Initial device scan found {len(registry.list_devices())} devices")

    # Start job manager cleanup task
    job_manager = JobManager()
    await job_manager.start_cleanup_task()

    # Start periodic rescan task
    rescan_task = None
    if settings.RESCAN_INTERVAL_SEC > 0:
        rescan_task = asyncio.create_task(periodic_rescan())
        logger.info(f"Started periodic device rescan (interval: {settings.RESCAN_INTERVAL_SEC}s)")

    logger.info("Bioexperiment API startup complete")

    yield

    # Shutdown
    logger.info("Shutting down bioexperiment API...")

    # Cancel periodic rescan
    if rescan_task:
        rescan_task.cancel()
        try:
            await rescan_task
        except asyncio.CancelledError:
            pass

    # Shutdown job manager
    await job_manager.shutdown()

    # Shutdown device registry
    await registry.shutdown()

    logger.info("Bioexperiment API shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Bioexperiment API",
        description="REST API for bioexperiment-tools devices including pumps and spectrophotometers",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Add API key authentication middleware if configured
    if settings.API_KEY:

        @app.middleware("http")
        async def api_key_middleware(request: Request, call_next):
            # Skip auth for health check
            if request.url.path == "/healthz":
                return await call_next(request)

            api_key = request.headers.get("X-API-Key")
            if api_key != settings.API_KEY:
                from fastapi import HTTPException

                raise HTTPException(status_code=401, detail="Invalid API key")

            return await call_next(request)

    # Include routers
    app.include_router(devices.router, tags=["devices"])
    app.include_router(pump.router, tags=["pump"])
    app.include_router(spectro.router, tags=["spectrophotometer"])
    app.include_router(jobs.router, tags=["jobs"])

    return app


# Create the app instance
app = create_app()
