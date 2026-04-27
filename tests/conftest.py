"""Shared pytest fixtures."""
from __future__ import annotations

from dataclasses import dataclass

import pytest


@dataclass
class RecordedCall:
    device_id: str
    command: list[int]
    wait_for_response: bool
    expected_response_bytes: int | None
    timeout_ms: int | None
    inter_byte_ms: int | None


class FakeLabDevicesClient:
    """Stand-in for LabDevicesClient in device-class unit tests.

    Records every send_command call. Responses are dispensed from a queue:
    each entry is a list[int] (the bytes the server would have returned).
    """

    def __init__(self, responses: list[list[int]] | None = None):
        self.calls: list[RecordedCall] = []
        self._responses: list[list[int]] = list(responses or [])

    def queue(self, response: list[int]) -> None:
        self._responses.append(response)

    def send_command(
        self,
        device_id: str,
        command: list[int],
        *,
        wait_for_response: bool,
        expected_response_bytes: int | None = None,
        timeout_ms: int | None = None,
        inter_byte_ms: int | None = None,
    ) -> list[int]:
        self.calls.append(
            RecordedCall(
                device_id=device_id,
                command=list(command),
                wait_for_response=wait_for_response,
                expected_response_bytes=expected_response_bytes,
                timeout_ms=timeout_ms,
                inter_byte_ms=inter_byte_ms,
            )
        )
        if not self._responses:
            return []
        return self._responses.pop(0)


@pytest.fixture
def fake_client() -> FakeLabDevicesClient:
    return FakeLabDevicesClient()
