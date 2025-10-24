"""Connection implementations for device communication."""

from .mock_connection import MockConnection
from .serial_connection import SerialConnection

__all__ = [
    "SerialConnection",
    "MockConnection",
]
