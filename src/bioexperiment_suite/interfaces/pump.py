"""Pump device — temporary stub. Real implementation in Task 10."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .lab_devices_client import LabDevicesClient


class Pump:
    def __init__(self, client: "LabDevicesClient", device_id: str, port: str):
        self.client = client
        self.device_id = device_id
        self.port = port
        # Calibration probe: matches the spec; the real Pump in Task 10 will store the result.
        client.send_command(
            device_id,
            [1, 2, 3, 4, 0],
            wait_for_response=True,
            expected_response_bytes=4,
        )
