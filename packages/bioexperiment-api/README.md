# Bioexperiment API

FastAPI REST API for bioexperiment-tools devices including pumps and spectrophotometers.

## Features

- Stateless REST API with device registry
- Asynchronous job execution for long-running operations
- Device hotplug support with manual and on-startup scanning
- Thread-safe device access with per-device locking
- WebSocket support for job status updates

## Installation

```bash
cd packages/bioexperiment-api
poetry install
```

## Usage

### Development Server

```bash
poetry run uvicorn bioexperiment_api.app:app --reload --host 0.0.0.0 --port 8000
```

### Environment Variables

- `EMULATE_DEVICES`: Set to "true" to use virtual devices
- `N_VIRTUAL_PUMPS`: Number of virtual pumps (default: 0)
- `N_VIRTUAL_SPECTROPHOTOMETERS`: Number of virtual spectrophotometers (default: 0)
- `LOG_LEVEL`: Logging level (default: "INFO")
- `RESCAN_INTERVAL_SEC`: Device rescan interval in seconds (default: 0, disabled). Set to 0 to disable automatic rescanning. Use `POST /devices:rescan` for manual rescanning.
- `JOB_RETENTION_SEC`: Job retention time in seconds (default: 3600)
- `MAX_WORKERS`: Maximum worker threads (default: 4)

### API Endpoints

#### Health & Discovery
- `GET /healthz` - Health check
- `GET /devices` - List all devices
- `GET /devices/{device_id}` - Get device details
- `POST /devices:rescan` - Rescan for devices

#### Pump Operations
- `POST /devices/{device_id}/pump/set-default-flow` - Set default flow rate
- `POST /devices/{device_id}/pump/pour-volume` - Pour specific volume
- `POST /devices/{device_id}/pump/start` - Start continuous rotation
- `POST /devices/{device_id}/pump/stop` - Stop pump

#### Spectrophotometer Operations
- `GET /devices/{device_id}/spectro/temperature` - Get temperature
- `POST /devices/{device_id}/spectro/measure` - Measure optical density (async)

#### Job Management
- `GET /jobs/{job_id}` - Get job status
- `DELETE /jobs/{job_id}` - Delete job
- `GET /jobs` - List jobs
- `WS /ws/jobs/{job_id}` - WebSocket job updates

## License

MIT
