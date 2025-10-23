import sys

from loguru import logger

try:
    logger.remove(0)
except ValueError:
    pass  # Handler 0 may not exist in some environments
logger.add(
    sys.stderr,
    level="INFO",
)
