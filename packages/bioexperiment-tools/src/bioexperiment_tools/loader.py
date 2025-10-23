import json
import sys
from importlib import resources as impresources

from loguru import logger
from munch import DefaultMunch

import bioexperiment_tools

logger.remove(0)
logger.add(
    sys.stderr,
    level="INFO",
)

device_interfaces_file = impresources.files(bioexperiment_tools) / "device_interfaces.json"
with device_interfaces_file.open(encoding="utf8") as file:
    device_interfaces = DefaultMunch.fromDict(json.load(file))
