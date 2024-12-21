import os

from dataclasses import dataclass
from dotenv import load_dotenv
from functools import lru_cache


@dataclass
class Settings:
    EMULATE_DEVICES: bool = False


@lru_cache
def get_settings():
    load_dotenv()
    return Settings(EMULATE_DEVICES=os.getenv("EMULATE_DEVICES", "False").lower() == "true")


settings = get_settings()
