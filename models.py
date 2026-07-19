# models.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod


# === ENUMS ===
class PowerStateName(Enum):
    UNKNOWN = auto()
    OK_HEALTHY = auto()
    OK_GENERATOR = auto()
    BAD_ON_BBU = auto()
    BAD_CANARY_DEAD = auto()

class Routine(Enum):
    """Tracks which routine was launched (for testing)."""
    SUSPEND = auto()
    RESTORE = auto()


# === DATA CLASSES ===
@dataclass
class PowerState:
    status: PowerStateName = PowerStateName.UNKNOWN
    canary_latest_bool: Optional[bool] = None
    switches_latest_bool: Optional[bool] = None
    ticks_counter: int = 0


@dataclass
class Inputs:
    canary_healthy: Optional[bool] = None
    switches_healthy: Optional[bool] = None


# === ABSTRACT BASE CLASS (Interface) ===
class ActionBox(ABC):
    @abstractmethod
    def start_suspending_routine(self) -> None:
        pass
    
    @abstractmethod
    def start_restoring_routine(self) -> None:
        pass


# === MOCK IMPLEMENTATIONS ===
class ActionBoxMock(ActionBox):
    """Mock implementation of ActionBox for testing."""
    
    def __init__(self):
        self.current_routine = None
    
    def start_suspending_routine(self) -> None:
        self.current_routine = Routine.SUSPEND
    
    def start_restoring_routine(self) -> None:
        self.current_routine = Routine.RESTORE

