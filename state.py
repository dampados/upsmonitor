# models.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional

class PowerStateName(Enum):
    OK_HEALTHY = auto()
    OK_GENERATOR = auto()
    BAD_ON_BBU = auto()
    BAD_CANARY_DEAD = auto()

class PowerState:
    def __init__(self):
        self.status = PowerStateName.BAD_ON_BBU
        self.canary_latest_bool = None
        self.switches_latest_bool = None
        self.ticks_counter = 0

@dataclass
class Inputs:
    canary_healthy: Optional[bool] = None
    switches_healthy: Optional[bool] = None