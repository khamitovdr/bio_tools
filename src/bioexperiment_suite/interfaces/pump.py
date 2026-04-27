"""Pump device class — composes a LabDevicesClient."""
from __future__ import annotations

from time import sleep
from typing import TYPE_CHECKING

from bioexperiment_suite.loader import device_interfaces, logger

if TYPE_CHECKING:
    from .lab_devices_client import LabDevicesClient


UNACCOUNTED_FOR_TIME_SEC = 1


def _bytes_to_int(values: list[int]) -> int:
    return int.from_bytes(bytes(values), byteorder="big")


def _int_to_bytes(value: int, n_bytes: int) -> list[int]:
    return list(value.to_bytes(n_bytes, byteorder="big"))


class Pump:
    """High-level peristaltic pump driver, served over the lab_devices HTTP API."""

    def __init__(self, client: "LabDevicesClient", device_id: str, port: str):
        self.client = client
        self.device_id = device_id
        self.port = port
        self.interface = device_interfaces.pump
        self.default_flow_rate: float | None = None
        self._calibration_volume: float = self._compute_calibration_volume()

    def _compute_calibration_volume(self) -> float:
        response = self.client.send_command(
            self.device_id,
            list(self.interface.identification_signal),
            wait_for_response=True,
            expected_response_bytes=4,
        )
        calibration_volume = _bytes_to_int(response[1:]) / 10**5
        if calibration_volume <= 0:
            raise ValueError(
                f"{self.device_id}: invalid calibration volume {calibration_volume} "
                f"from probe response {response!r}"
            )
        logger.debug(f"{self.device_id}: calibration volume {calibration_volume:.5f}")
        return calibration_volume

    def _compute_speed_param_from_flow(self, flow: float) -> int:
        return int(29 / flow)

    def _compute_step_volume_bytes(self, volume: float) -> list[int]:
        step_volume = int((volume * 10**4) / self._calibration_volume)
        return _int_to_bytes(step_volume, 4)

    def set_default_flow_rate(self, flow_rate: float) -> None:
        self.default_flow_rate = flow_rate

    def _set_flow_rate(self, flow_rate: float) -> None:
        logger.debug(f"{self.device_id}: setting flow rate to {flow_rate:.3f} mL/min")
        speed_param = self._compute_speed_param_from_flow(flow_rate)
        self.client.send_command(
            self.device_id,
            [10, 0, 1, speed_param, 0],
            wait_for_response=False,
        )

    def pour_in_volume(
        self,
        volume: float,
        flow_rate: float | None = None,
        direction: str = "left",
        blocking_mode: bool = True,
        info_log_message: str | None = None,
        info_log_level: str = "INFO",
    ) -> None:
        if direction not in ("left", "right"):
            raise ValueError("Invalid direction. Must be either 'left' or 'right'")
        direction_byte = 16 if direction == "left" else 17

        flow_rate = flow_rate if flow_rate is not None else self.default_flow_rate
        if flow_rate is None:
            raise ValueError("Flow rate must be set before pouring in volume or passed as an argument")

        self._set_flow_rate(flow_rate)

        logger.debug(f"{self.device_id}: pouring {volume:.3f} mL at {flow_rate:.3f} mL/min ({direction})")
        if info_log_message:
            logger.log(info_log_level, info_log_message)

        command = [direction_byte] + self._compute_step_volume_bytes(volume)
        self.client.send_command(self.device_id, command, wait_for_response=False)

        if blocking_mode:
            sleep_time = (volume / flow_rate) * 60
            sleep(sleep_time + UNACCOUNTED_FOR_TIME_SEC)

    def start_continuous_rotation(
        self,
        flow_rate: float | None = None,
        direction: str = "left",
    ) -> None:
        if direction not in ("left", "right"):
            raise ValueError("Invalid direction. Must be either 'left' or 'right'")
        direction_byte = 11 if direction == "left" else 12

        flow_rate = flow_rate if flow_rate is not None else self.default_flow_rate
        if flow_rate is None:
            raise ValueError(
                "Flow rate must be set before starting continuous rotation or passed as an argument"
            )

        logger.debug(
            f"{self.device_id}: starting continuous rotation at {flow_rate:.3f} mL/min ({direction})"
        )
        speed_param = self._compute_speed_param_from_flow(flow_rate)
        self.client.send_command(
            self.device_id,
            [direction_byte, 111, 1, speed_param, 0],
            wait_for_response=False,
        )

    def stop_continuous_rotation(self) -> None:
        logger.debug(f"{self.device_id}: stopping continuous rotation")
        self.pour_in_volume(0)
