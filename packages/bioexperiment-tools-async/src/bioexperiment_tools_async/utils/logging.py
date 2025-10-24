"""Structured logging setup with async support."""

import sys
from typing import Any

from loguru import logger

from ..core.config import get_config


def setup_logging() -> None:
    """Configure structured logging for the application."""
    config = get_config()

    # Remove default handler
    logger.remove()

    # Add custom handler with structured format
    logger.add(
        sys.stderr,
        level=config.log_level,
        format=config.log_format,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )


def get_logger(name: str) -> Any:
    """Get a logger instance with the given name."""
    return logger.bind(name=name)
