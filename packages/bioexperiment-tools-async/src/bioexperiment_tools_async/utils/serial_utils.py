"""Serial port utility functions."""

import asyncio
import glob
import sys
from typing import Any

import serial
from loguru import logger

from ..core.config import get_config


def bytes_to_int(data: bytes) -> int:
    """Convert bytes to integer using big-endian byte order."""
    return int.from_bytes(data, byteorder="big")


def int_to_bytes(value: int, num_bytes: int | None = None) -> list[int]:
    """Convert integer to list of bytes using big-endian byte order."""
    if num_bytes is None:
        num_bytes = (value.bit_length() + 7) // 8 or 1
    
    byte_representation = value.to_bytes(num_bytes, byteorder="big")
    return list(byte_representation)


async def get_available_ports() -> list[str]:
    """Get list of available serial ports on the system."""
    config = get_config()
    
    if config.emulate_devices:
        logger.info("Using emulated device ports")
        pump_ports = [f"COM{i * 2}" for i in range(config.n_virtual_pumps)]
        spectro_ports = [f"COM{i * 2 + 1}" for i in range(config.n_virtual_spectrophotometers)]
        ports = sorted(pump_ports + spectro_ports)
        logger.debug(f"Emulated ports: {ports} (pumps: {config.n_virtual_pumps}, spectros: {config.n_virtual_spectrophotometers})")
        return ports
    
    # Run port detection in thread pool since it's blocking
    return await asyncio.get_event_loop().run_in_executor(None, _get_system_ports)


def _get_system_ports() -> list[str]:
    """Get actual system serial ports (blocking operation)."""
    if sys.platform.startswith("win"):
        logger.debug("Detecting Windows serial ports")
        ports = [f"COM{i + 1}" for i in range(256)]
    elif sys.platform.startswith("linux") or sys.platform.startswith("cygwin"):
        logger.debug("Detecting Linux serial ports")
        ports = glob.glob("/dev/tty[A-Za-z]*")
    elif sys.platform.startswith("darwin"):
        logger.debug("Detecting macOS serial ports")
        ports = glob.glob("/dev/tty.*")
    else:
        logger.error(f"Unsupported platform: {sys.platform}")
        raise OSError(f"Unsupported platform: {sys.platform}")
    
    # Test which ports are actually available
    available_ports = []
    for port in ports:
        try:
            with serial.Serial(port, timeout=0.1):
                available_ports.append(port)
        except (OSError, serial.SerialException):
            continue
    
    logger.debug(f"Found {len(available_ports)} available serial ports")
    return available_ports
