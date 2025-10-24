# Bioexperiment Tools Async

[![Python Version](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Poetry](https://img.shields.io/badge/dependency%20manager-poetry-blue.svg)](https://python-poetry.org/)
[![Code Style: Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checker: mypy](https://img.shields.io/badge/type%20checker-mypy-blue.svg)](https://mypy.readthedocs.io/)

Modern async-first library for biological experiment devices including pumps and spectrophotometers. Built with proper async/await patterns, comprehensive typing, and robust error handling.

## Features

- **Async-First Design**: Built from the ground up with asyncio for non-blocking device operations
- **Type Safety**: Comprehensive type annotations with protocols and generics
- **Concurrent Operations**: Safe concurrent access to multiple devices with proper locking
- **Smart Device Discovery**: Concurrent device scanning with intelligent caching
- **Robust Error Handling**: Structured exception hierarchy with detailed context
- **Modern Architecture**: Clean separation of concerns with dependency injection
- **Hardware Emulation**: Built-in device emulation for development and testing
- **Comprehensive Testing**: Extensive test suite with mocks and integration tests

## Installation

### Using Poetry (Recommended)

```bash
cd packages/bioexperiment-tools-async
poetry install
```

### Using pip

```bash
pip install bioexperiment-tools-async
```

## Quick Start

### Basic Usage

```python
import asyncio
from bioexperiment_tools_async import discover_devices, Direction

async def main():
    # Discover all connected devices
    pumps, spectrophotometers = await discover_devices()

    print(f"Found {len(pumps)} pumps and {len(spectrophotometers)} spectrophotometers")

    # Use a pump with async context manager
    if pumps:
        async with pumps[0] as pump:
            await pump.set_default_flow_rate(5.0)
            await pump.pour_volume(10.0, direction=Direction.LEFT)
            print("Poured 10 mL to the left")

    # Use a spectrophotometer
    if spectrophotometers:
        async with spectrophotometers[0] as spectro:
            temperature = await spectro.get_temperature()
            optical_density = await spectro.measure_optical_density()
            print(f"Temperature: {temperature:.2f}°C, OD: {optical_density:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Device Discovery with Filtering

```python
import asyncio
from bioexperiment_tools_async import discover_devices, DeviceType

async def main():
    # Discover only pumps
    pumps, _ = await discover_devices(device_type=DeviceType.PUMP)

    # Discover only spectrophotometers with timeout
    _, spectrophotometers = await discover_devices(
        device_type=DeviceType.SPECTROPHOTOMETER,
        timeout=10.0
    )

    print(f"Found {len(pumps)} pumps and {len(spectrophotometers)} spectrophotometers")

asyncio.run(main())
```

### Concurrent Operations

```python
import asyncio
from bioexperiment_tools_async import discover_devices, Direction

async def operate_pump(pump, volume, flow_rate):
    """Operate a pump with specific parameters."""
    async with pump:
        await pump.set_default_flow_rate(flow_rate)
        await pump.pour_volume(volume, direction=Direction.LEFT)
        return f"Pump {pump.device_id} poured {volume} mL"

async def measure_spectro(spectro):
    """Take measurements from a spectrophotometer."""
    async with spectro:
        temperature = await spectro.get_temperature()
        optical_density = await spectro.measure_optical_density()
        return {
            'device_id': spectro.device_id,
            'temperature': temperature,
            'optical_density': optical_density,
        }

async def main():
    # Discover devices
    pumps, spectrophotometers = await discover_devices()

    # Prepare concurrent tasks
    tasks = []

    # Add pump operations
    for i, pump in enumerate(pumps[:3]):  # Use up to 3 pumps
        tasks.append(operate_pump(pump, volume=5.0 + i, flow_rate=3.0 + i))

    # Add spectrophotometer measurements
    for spectro in spectrophotometers:
        tasks.append(measure_spectro(spectro))

    # Execute all operations concurrently
    if tasks:
        results = await asyncio.gather(*tasks)
        for result in results:
            print(result)

asyncio.run(main())
```

## Configuration

### Environment Variables

The library supports configuration via environment variables:

```bash
# Device emulation (useful for development/testing)
export BIOEXPERIMENT_EMULATE_DEVICES=true
export BIOEXPERIMENT_N_VIRTUAL_PUMPS=2
export BIOEXPERIMENT_N_VIRTUAL_SPECTROPHOTOMETERS=1

# Discovery settings
export BIOEXPERIMENT_DISCOVERY_TIMEOUT=30.0
export BIOEXPERIMENT_DISCOVERY_CONCURRENT_LIMIT=10
export BIOEXPERIMENT_DEVICE_CACHE_TTL=60.0

# Connection settings
export BIOEXPERIMENT_CONNECTION__BAUDRATE=9600
export BIOEXPERIMENT_CONNECTION__TIMEOUT=2.0
export BIOEXPERIMENT_CONNECTION__MAX_RETRIES=3

# Logging
export BIOEXPERIMENT_LOG_LEVEL=INFO
```

### Programmatic Configuration

```python
from bioexperiment_tools_async.core.config import get_config

# Get current configuration
config = get_config()
print(f"Emulation mode: {config.emulate_devices}")
print(f"Discovery timeout: {config.discovery_timeout}s")
```

## Advanced Usage

### Custom Connection Configuration

```python
import asyncio
from bioexperiment_tools_async.core.config import ConnectionConfig
from bioexperiment_tools_async.connection import SerialConnection
from bioexperiment_tools_async.devices import AsyncPump

async def main():
    # Custom connection configuration
    config = ConnectionConfig(
        baudrate=115200,
        timeout=5.0,
        max_retries=5,
        retry_delay=1.0,
    )

    # Create pump with custom connection
    connection = SerialConnection("/dev/ttyUSB0", config=config)
    pump = AsyncPump("/dev/ttyUSB0")

    async with pump:
        await pump.set_default_flow_rate(8.0)
        await pump.pour_volume(15.0)

asyncio.run(main())
```

### Device Scanner with Caching

```python
import asyncio
from bioexperiment_tools_async.discovery import DeviceScanner

async def main():
    scanner = DeviceScanner()

    # First scan (hits hardware)
    pumps, spectros = await scanner.discover_devices()
    print(f"First scan: {len(pumps)} pumps, {len(spectros)} spectros")

    # Second scan (uses cache)
    pumps, spectros = await scanner.discover_devices()
    print(f"Cached scan: {len(pumps)} pumps, {len(spectros)} spectros")

    # Get cache statistics
    stats = scanner.get_cache_stats()
    print(f"Cache stats: {stats}")

    # Clear cache and rescan
    scanner.clear_cache()
    pumps, spectros = await scanner.discover_devices()

asyncio.run(main())
```

### Error Handling

```python
import asyncio
from bioexperiment_tools_async import discover_devices, Direction
from bioexperiment_tools_async.core.exceptions import (
    DeviceConnectionError,
    DeviceOperationError,
    InvalidDeviceParameterError,
)

async def main():
    try:
        pumps, _ = await discover_devices(device_type=DeviceType.PUMP, timeout=5.0)

        if not pumps:
            print("No pumps found")
            return

        pump = pumps[0]
        async with pump:
            await pump.set_default_flow_rate(5.0)
            await pump.pour_volume(10.0, direction=Direction.LEFT)

    except DeviceConnectionError as e:
        print(f"Connection failed: {e}")
        print(f"Device: {e.device_id}, Context: {e.context}")

    except InvalidDeviceParameterError as e:
        print(f"Invalid parameter: {e}")
        print(f"Operation: {e.operation}")

    except DeviceOperationError as e:
        print(f"Operation failed: {e}")
        print(f"Device: {e.device_id}, Context: {e.context}")

    except Exception as e:
        print(f"Unexpected error: {e}")

asyncio.run(main())
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/your-repo/bio_tools.git
cd bio_tools/packages/bioexperiment-tools-async

# Install with development dependencies
poetry install

# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=bioexperiment_tools_async --cov-report=html

# Type checking
poetry run mypy src/

# Linting and formatting
poetry run ruff check src/ tests/
poetry run ruff format src/ tests/
```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test categories
poetry run pytest tests/unit/           # Unit tests only
poetry run pytest tests/integration/   # Integration tests only

# Run with device emulation
EMULATE_DEVICES=true poetry run pytest

# Run specific test file
poetry run pytest tests/unit/test_devices.py
```

### Device Emulation for Testing

Enable device emulation to test without physical hardware:

```bash
export BIOEXPERIMENT_EMULATE_DEVICES=true
export BIOEXPERIMENT_N_VIRTUAL_PUMPS=3
export BIOEXPERIMENT_N_VIRTUAL_SPECTROPHOTOMETERS=2

# Now run your scripts or tests
python your_script.py
```

## Architecture

The library is built with modern Python practices and clean architecture:

- **Core**: Type definitions, protocols, exceptions, and configuration
- **Connection**: Async serial communication with retry logic and mocking
- **Protocol**: Device communication protocols with typed commands
- **Devices**: High-level device classes with async context managers
- **Discovery**: Concurrent device scanning with intelligent caching
- **Utils**: Serial port utilities and structured logging

### Key Design Principles

1. **Async-First**: All I/O operations are async to prevent blocking
2. **Type Safety**: Comprehensive typing with protocols and generics
3. **Separation of Concerns**: Clean layered architecture
4. **Error Handling**: Structured exceptions with detailed context
5. **Testability**: Dependency injection and comprehensive mocking
6. **Performance**: Concurrent operations with proper resource management

## API Reference

### Device Classes

- `AsyncPump`: Async pump device with flow control
- `AsyncSpectrophotometer`: Async spectrophotometer for measurements

### Discovery Functions

- `discover_devices()`: Discover and return device instances
- `DeviceScanner`: Advanced device discovery with caching

### Configuration

- `get_config()`: Get global configuration
- `ConnectionConfig`: Connection-specific settings
- `GlobalConfig`: Global application settings

### Exceptions

- `BioexperimentError`: Base exception class
- `DeviceConnectionError`: Connection-related errors
- `DeviceCommunicationError`: Communication failures
- `DeviceOperationError`: Operation failures
- `InvalidDeviceParameterError`: Invalid parameters

For detailed API documentation, see the docstrings in the source code.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Run the test suite (`poetry run pytest`)
5. Run linting (`poetry run ruff check`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](../../LICENSE) file for details.
