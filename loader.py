import json
import sys

from loguru import logger
from munch import DefaultMunch

DEVICE_INTERFACES_PATH = "./device_interfaces.json"


logger.remove(0)
logger.add(
    sys.stderr,
    level="INFO",
)

with open(DEVICE_INTERFACES_PATH, encoding="utf8") as file:
    device_interfaces = DefaultMunch.fromDict(json.load(file))
