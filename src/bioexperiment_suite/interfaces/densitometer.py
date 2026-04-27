"""Densitometer device class — composes a LabDevicesClient."""
from __future__ import annotations

from time import sleep
from typing import TYPE_CHECKING

from bioexperiment_suite.loader import device_interfaces, logger

if TYPE_CHECKING:
    from .lab_devices_client import LabDevicesClient


_MEASUREMENT_DELAY_SEC = 3


class Densitometer:
    """High-level optical density / temperature reader."""

    def __init__(self, client: "LabDevicesClient", device_id: str, port: str):
        self.client = client
        self.device_id = device_id
        self.port = port
        self.interface = device_interfaces.densitometer

    def get_temperature(self) -> float:
        logger.debug(f"{self.device_id}: getting temperature")
        response = self.client.send_command(
            self.device_id,
            list(self.interface.commands.get_temperature.request),
            wait_for_response=True,
            expected_response_bytes=int(self.interface.commands.get_temperature.response_len),
        )
        integer, fractional = response[2:4]
        temperature = integer + fractional / 100
        logger.debug(f"{self.device_id}: temperature {temperature:.2f}")
        return temperature

    def _send_start_measurement_command(self) -> None:
        logger.debug(f"{self.device_id}: start measurement")
        self.client.send_command(
            self.device_id,
            list(self.interface.commands.start_measurement.request),
            wait_for_response=False,
        )

    def _get_optical_density(self) -> float | None:
        response = self.client.send_command(
            self.device_id,
            list(self.interface.commands.get_measurement_result.request),
            wait_for_response=True,
            expected_response_bytes=int(self.interface.commands.get_measurement_result.response_len),
        )
        if not response:
            return None
        integer, fractional = response[2:4]
        return integer + fractional / 100

    def measure_optical_density(self) -> float:
        logger.debug(f"{self.device_id}: measuring optical density")
        self._send_start_measurement_command()
        sleep(_MEASUREMENT_DELAY_SEC)
        optical_density = self._get_optical_density()
        if optical_density is None:
            logger.error(f"{self.device_id}: optical density could not be measured")
            raise Exception("Optical density could not be measured")
        return optical_density
