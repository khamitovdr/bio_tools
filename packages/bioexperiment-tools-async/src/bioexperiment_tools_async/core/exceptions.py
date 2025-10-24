"""Custom exception hierarchy for bioexperiment tools."""

from typing import Any


class BioexperimentError(Exception):
    """Base exception for all bioexperiment tools errors."""
    
    def __init__(self, message: str, *, device_id: str | None = None, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.device_id = device_id
        self.context = context or {}
    
    def __str__(self) -> str:
        base_msg = super().__str__()
        if self.device_id:
            base_msg = f"[Device: {self.device_id}] {base_msg}"
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            base_msg = f"{base_msg} (Context: {context_str})"
        return base_msg


class DeviceConnectionError(BioexperimentError):
    """Raised when device connection fails or is lost."""
    pass


class DeviceCommunicationError(BioexperimentError):
    """Raised when communication with device fails."""
    
    def __init__(
        self, 
        message: str, 
        *, 
        device_id: str | None = None, 
        context: dict[str, Any] | None = None,
        command: list[int] | None = None,
        response: bytes | None = None,
    ) -> None:
        super().__init__(message, device_id=device_id, context=context)
        self.command = command
        self.response = response


class DeviceNotFoundError(BioexperimentError):
    """Raised when a requested device cannot be found."""
    pass


class DeviceOperationError(BioexperimentError):
    """Raised when a device operation fails."""
    
    def __init__(
        self, 
        message: str, 
        *, 
        device_id: str | None = None, 
        context: dict[str, Any] | None = None,
        operation: str | None = None,
    ) -> None:
        super().__init__(message, device_id=device_id, context=context)
        self.operation = operation


class DeviceTimeoutError(DeviceOperationError):
    """Raised when a device operation times out."""
    pass


class InvalidDeviceParameterError(DeviceOperationError):
    """Raised when invalid parameters are provided to device operations."""
    pass
