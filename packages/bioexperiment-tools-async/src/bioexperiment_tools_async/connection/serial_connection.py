"""Async serial connection implementation using pyserial-asyncio."""

import asyncio
from typing import Any

import serial_asyncio
from loguru import logger

from ..core.config import ConnectionConfig, get_config
from ..core.exceptions import DeviceConnectionError, DeviceCommunicationError
from ..core.protocols import AsyncConnection
from ..core.types import PortName


class SerialConnection:
    """Async serial connection implementation."""
    
    def __init__(
        self, 
        port: PortName, 
        *,
        config: ConnectionConfig | None = None,
    ) -> None:
        """Initialize the serial connection.
        
        Args:
            port: The serial port name to connect to
            config: Connection configuration (uses global config if not provided)
        """
        self._port = port
        self._config = config or get_config().connection
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connection_lock = asyncio.Lock()
        self._is_connected = False
        
        logger.debug(f"Created SerialConnection for port {port}")
    
    @property
    def port(self) -> PortName:
        """The port name this connection is bound to."""
        return self._port
    
    @property
    def is_connected(self) -> bool:
        """Whether the connection is currently active."""
        return self._is_connected and self._reader is not None and self._writer is not None
    
    async def connect(self) -> None:
        """Establish the serial connection with retry logic."""
        async with self._connection_lock:
            if self.is_connected:
                logger.debug(f"Already connected to {self._port}")
                return
            
            last_error = None
            for attempt in range(self._config.max_retries):
                try:
                    logger.debug(f"Connecting to {self._port} (attempt {attempt + 1}/{self._config.max_retries})")
                    
                    self._reader, self._writer = await serial_asyncio.open_serial_connection(
                        url=self._port,
                        baudrate=self._config.baudrate,
                        timeout=self._config.timeout,
                    )
                    
                    self._is_connected = True
                    logger.info(f"Successfully connected to {self._port}")
                    
                    # Add connection stabilization delay
                    await asyncio.sleep(0.1)
                    return
                    
                except Exception as e:
                    last_error = e
                    logger.warning(f"Connection attempt {attempt + 1} failed for {self._port}: {e}")
                    
                    if attempt < self._config.max_retries - 1:
                        await asyncio.sleep(self._config.retry_delay)
            
            # All attempts failed
            raise DeviceConnectionError(
                f"Failed to connect to {self._port} after {self._config.max_retries} attempts",
                context={"port": self._port, "last_error": str(last_error)},
            )
    
    async def disconnect(self) -> None:
        """Close the serial connection."""
        async with self._connection_lock:
            if not self.is_connected:
                logger.debug(f"Already disconnected from {self._port}")
                return
            
            try:
                if self._writer:
                    self._writer.close()
                    await self._writer.wait_closed()
                
                self._reader = None
                self._writer = None
                self._is_connected = False
                
                logger.info(f"Disconnected from {self._port}")
                
            except Exception as e:
                logger.warning(f"Error during disconnect from {self._port}: {e}")
                # Still mark as disconnected even if cleanup failed
                self._is_connected = False
                raise DeviceConnectionError(
                    f"Error during disconnect from {self._port}",
                    context={"port": self._port, "error": str(e)},
                )
    
    async def write(self, data: list[int]) -> None:
        """Write data to the serial connection."""
        if not self.is_connected:
            raise DeviceConnectionError(
                f"Cannot write to disconnected port {self._port}",
                context={"port": self._port},
            )
        
        try:
            bytes_data = bytes(data)
            assert self._writer is not None
            self._writer.write(bytes_data)
            await self._writer.drain()
            
            logger.debug(f"Wrote {len(data)} bytes to {self._port}: {data}")
            
        except Exception as e:
            raise DeviceCommunicationError(
                f"Failed to write data to {self._port}",
                context={"port": self._port},
                command=data,
            ) from e
    
    async def read(self, num_bytes: int) -> bytes:
        """Read data from the serial connection."""
        if not self.is_connected:
            raise DeviceConnectionError(
                f"Cannot read from disconnected port {self._port}",
                context={"port": self._port},
            )
        
        try:
            assert self._reader is not None
            data = await asyncio.wait_for(
                self._reader.read(num_bytes),
                timeout=self._config.timeout,
            )
            
            logger.debug(f"Read {len(data)} bytes from {self._port}: {list(data)}")
            return data
            
        except asyncio.TimeoutError as e:
            raise DeviceCommunicationError(
                f"Timeout reading from {self._port}",
                context={"port": self._port, "requested_bytes": num_bytes},
            ) from e
        except Exception as e:
            raise DeviceCommunicationError(
                f"Failed to read data from {self._port}",
                context={"port": self._port, "requested_bytes": num_bytes},
            ) from e
    
    async def communicate(self, data: list[int], response_bytes: int) -> bytes:
        """Send data and read response in one operation."""
        await self.write(data)
        return await self.read(response_bytes)
    
    async def __aenter__(self) -> "SerialConnection":
        """Async context manager entry."""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
