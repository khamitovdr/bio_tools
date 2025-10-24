<!-- 36d545f4-cf95-459d-b9b7-81fdcc321f07 d6193006-b303-44fd-805a-11667438382a -->
# Bioexperiment Tools Async - Modern Architecture

## Overview

Create a new `bioexperiment-tools-async` package with modern async-first architecture, focusing on clean design principles, comprehensive typing, and extensive testing.

## Improved Architecture Design

### Core Design Principles

- **Separation of Concerns**: Split connection management, protocol handling, and device logic
- **Dependency Injection**: Use protocols and dependency injection for better testability
- **Async Context Managers**: Proper lifecycle management for device connections
- **Type Safety**: Comprehensive typing with protocols and generics
- **Error Handling**: Structured exception hierarchy with detailed error information

### Package Structure

```
packages/bioexperiment-tools-async/
├── src/bioexperiment_tools_async/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── protocols.py           # Type protocols for devices and connections
│   │   ├── exceptions.py          # Custom exception hierarchy
│   │   ├── config.py             # Pydantic configuration models
│   │   └── types.py              # Type definitions and enums
│   ├── connection/
│   │   ├── __init__.py
│   │   ├── serial_connection.py  # Async serial connection implementation
│   │   └── mock_connection.py    # Mock connection for testing
│   ├── protocol/
│   │   ├── __init__.py
│   │   ├── device_protocol.py    # Device communication protocols
│   │   └── commands.py           # Device command definitions
│   ├── devices/
│   │   ├── __init__.py
│   │   ├── base.py              # Abstract base device class
│   │   ├── pump.py              # Async pump implementation
│   │   └── spectrophotometer.py # Async spectrophotometer implementation
│   ├── discovery/
│   │   ├── __init__.py
│   │   ├── scanner.py           # Async device discovery
│   │   └── identifier.py        # Device identification logic
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── serial_utils.py      # Serial port utilities
│   │   └── logging.py           # Structured logging setup
│   ├── device_configs.json      # Device configuration data
│   └── py.typed
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures and configuration
│   ├── unit/
│   │   ├── test_connection.py
│   │   ├── test_devices.py
│   │   ├── test_protocols.py
│   │   └── test_discovery.py
│   ├── integration/
│   │   ├── test_device_operations.py
│   │   └── test_concurrent_access.py
│   └── mocks/
│       ├── mock_devices.py
│       └── mock_serial.py
├── pyproject.toml
├── README.md
└── poetry.lock
```

## Implementation Phases

### Phase 1: Core Foundation & Types

- Create package structure with Poetry and modern dev dependencies
- Define type protocols for devices, connections, and configurations
- Implement custom exception hierarchy with detailed error context
- Create Pydantic configuration models for device settings
- Set up structured logging with proper async support

### Phase 2: Connection Layer

- Implement async serial connection using pyserial-asyncio
- Create proper async context manager for connection lifecycle
- Add connection pooling and retry mechanisms
- Implement mock connection for testing and emulation
- Add comprehensive connection error handling

### Phase 3: Protocol Layer

- Define device communication protocols with typed commands
- Implement message serialization/deserialization
- Add protocol validation and error recovery
- Create command builders with type safety
- Support for device-specific protocol variations

### Phase 4: Device Implementation

- Create abstract base device class with common async patterns
- Implement async pump with proper flow control and timing
- Implement async spectrophotometer with measurement workflows
- Add device-specific error handling and recovery
- Implement async context managers for device operations

### Phase 5: Device Discovery

- Create concurrent device scanner using asyncio.gather()
- Implement smart device identification with caching
- Add discovery filters and device grouping
- Support for hot-plugging and device monitoring
- Graceful handling of discovery failures and timeouts

### Phase 6: Testing & Documentation

- Comprehensive unit test suite with pytest-asyncio
- Mock implementations for hardware-independent testing
- Integration tests for device workflows
- Performance and concurrency testing
- API documentation with examples and best practices

## Key Architectural Improvements

**Protocol-Based Design:**

- Use Python protocols for better typing and loose coupling
- Enable dependency injection for better testability
- Support multiple device implementations

**Async Context Managers:**

```python
async with AsyncPump("/dev/ttyUSB0") as pump:
    await pump.set_flow_rate(5.0)
    await pump.pour_volume(10.0, direction="left")
```

**Structured Configuration:**

- Pydantic models for configuration validation
- Environment-based configuration with sensible defaults
- Device-specific configuration with inheritance

**Error Handling:**

- Custom exception hierarchy with device context
- Async-safe error propagation and recovery
- Detailed error logging with structured data

**Concurrent Operations:**

- Safe concurrent access to multiple devices
- Async locks and resource management
- Efficient device discovery and parallel operations

## Modern Python Practices

- Full type annotations with protocols and generics
- Async/await throughout with proper exception handling
- Pydantic for configuration validation and serialization
- Structured logging with contextual information
- pytest-asyncio for comprehensive async testing
- Modern packaging with Poetry and proper dependency management

### To-dos

- [ ] Create bioexperiment-tools-async package structure with Poetry configuration and dependencies
- [ ] Implement AsyncSerialConnection class using pyserial-asyncio with async I/O methods
- [ ] Create AsyncPump and AsyncSpectrophotometer classes with async device operations
- [ ] Implement async get_connected_devices_async() with concurrent device scanning
- [ ] Modify DeviceRegistry to use async device discovery and remove blocking operations
- [ ] Update API routes to use async device methods and simplify job system
