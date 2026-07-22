# models.py
from enum import Enum, auto
from dataclasses import dataclass
from typing import Optional
from abc import ABC, abstractmethod
import threading

# === ENUMS ===
class PowerStateName(Enum):
    UNKNOWN = auto()
    OK_HEALTHY = auto()
    OK_GENERATOR = auto()
    BAD_ON_BBU = auto()
    BAD_CANARY_DEAD = auto()

class HostState(Enum):
    UNKNOWN = auto()
    ALIVE = auto()
    DEAD = auto()

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

# === MUTEX WRAPPERS ===
# viewmodel for the PowerState !!!!!!! a.k.a. android viewmodel OR a.k.a. mutex wrapper 
class PowerStateViewModel:
    def __init__(self, initial: PowerState):
        self._state = initial
        self._lock = threading.Lock()
    
    def update(self, new_state: PowerState) -> None:
        with self._lock:
            self._state = new_state
    
    def get(self) -> PowerState:
        with self._lock:
            return self._state

# we dont need dataclass bc our model is a dictionary! but still a viewmodel/mutex-wrapper
class HostsHealthStatusWrapper:
    def __init__(self, initial_status: dict = None):
        self._status = initial_status if initial_status is not None else {}
        self._lock = threading.Lock()
    
    def update(self, new_status):
        with self._lock:
            self._status = new_status
    
    def get(self):
        with self._lock:
            return self._status.copy()





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

# # === REAL CLASSES ===
# class ActionBoxReal(ActionBox):
#     """REAL ONE finally"""

#     def __init__(
#         self, 
#         hosts_health_status_wrapper_obj, 
#         suspending_routine,
#         restoring_routine,
#     ):

#     def __init__(self, initial_status: dict = None):
#         self._status = initial_status if initial_status is not None else {}
#         self._lock = threading.Lock()

