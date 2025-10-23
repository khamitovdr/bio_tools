import os

from dataclasses import dataclass
from functools import lru_cache


@dataclass
class Settings:
    EMULATE_DEVICES: bool = False
    N_VIRTUAL_PUMPS: int = 0
    N_VIRTUAL_SPECTROPHOTOMETERS: int = 0


@lru_cache
def get_settings():
    return Settings(
        EMULATE_DEVICES=os.getenv("EMULATE_DEVICES", "False").lower() == "true",
        N_VIRTUAL_PUMPS=int(os.getenv("N_VIRTUAL_PUMPS", "0")),
        N_VIRTUAL_SPECTROPHOTOMETERS=int(os.getenv("N_VIRTUAL_SPECTROPHOTOMETERS", "0"))
    )
