"""Valve placeholder — wire protocol not yet specified."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lab_devices_client import LabDevicesClient


class Valve:
    def __init__(self, client: "LabDevicesClient", device_id: str, port: str):
        self.client = client
        self.device_id = device_id
        self.port = port
