import subprocess
from icmplib import ping
import time
import queue
from dataclasses import dataclass

import state

_CANARY_DEAD = '"17"=inactive'
_CANARY_ALIVE = '"17"=active'

_PING_TIMEOUT = 0.6
_DELAY = 0.1
_SWITCH_IPS = [
    "172.16.38.71",
]
_SWITCH_IPS_REAL = [
    "172.16.40.101",
    "172.16.40.102",
    "172.16.40.103",
    "172.16.40.104",
    "172.16.40.105",
]

@dataclass
class Inputs:
    canary_healthy: bool
    switches_healthy: bool




# @dataclass
# class State:
#     name: str
#     suspend_sent: bool = False
#     same_input_ticks: int = 0


def _read_signal_canary():

    try:
        result = subprocess.run(
        ["gpioget", "-c", "0", "17"], 
        capture_output=True, 
        text=True, 
        timeout=1)
        output = result.stdout.strip()
        
        if output == _CANARY_ALIVE:
            return True
        elif output == _CANARY_DEAD:
            return False
        else:
            # logging.warning(f"Unexpected GPIO output: {output}")
            return True
            
    except subprocess.TimeoutExpired:
        # logging.warning("GPIO read timed out")
        return True
    except FileNotFoundError:
        # logging.error("gpioget not installed")
        return True
    except Exception as e:
        # logging.error(f"GPIO error: {e}")
        return True

def _ping_single(ip):
    try:
        return ping(ip, count=1, timeout=_PING_TIMEOUT).is_alive
    except Exception:
        return False

def _read_signal_ping():
    for ip in _SWITCH_IPS:
        if _ping_single(ip):
            return True
    return False

def poller_switches_deprecated(injected_queue):

    last_state = None
    
    while True:

        signal_to_emit = None
        current_readings = _read_signal_ping()

        if current_readings != last_state:
            last_state = current_readings
            signal_to_emit = current_readings


        try:
            injected_queue.put_nowait(signal_to_emit)      # Replace if full
        except queue.Full:
            injected_queue.get_nowait()
            injected_queue.put_nowait(signal_to_emit)

        time.sleep(_DELAY)

def poller_switches(injected_queue):

    last_emitted = None
    last_bool_emitted = None
    
    while True:

        signal_to_emit = None
        current_readings = _read_signal_ping()

        if current_readings != last_bool_emitted:
            signal_to_emit = current_readings


        try:
            injected_queue.put_nowait(signal_to_emit)

            last_emitted = signal_to_emit
            if signal_to_emit is not None:
                last_bool_emitted = signal_to_emit
        except queue.Full:

            if signal_to_emit is not None:
                if signal_to_emit != last_bool_emitted:
                    injected_queue.get_nowait()
                    injected_queue.put_nowait(signal_to_emit)

                    last_emitted = signal_to_emit
                    if signal_to_emit is not None:
                        last_bool_emitted = signal_to_emit

        time.sleep(_DELAY)

def poller_canary_debounced_deprecated(injected_queue):

    stable_value = None
    next_probable_state = None

    TRIGGER_CYCLES_COUNT = 30
    consequtive_opposite_values_counter = 0

    while True:

        canary_current_status = _read_signal_canary()
        if stable_value != canary_current_status:
            consequtive_opposite_values_counter += 1
            next_probable_state = canary_current_status
        else:
            consequtive_opposite_values_counter = 0
            next_probable_state = None


        if consequtive_opposite_values_counter >= (TRIGGER_CYCLES_COUNT):           
 
            stable_value = next_probable_state
            next_probable_state = None
            consequtive_opposite_values_counter = 0

            try:
                injected_queue.put_nowait(stable_value)      # Replace if full
            except queue.Full:
                injected_queue.get_nowait()
                injected_queue.put_nowait(stable_value)

        time.sleep(_DELAY)

def poller_canary_debounced_deprecated2(injected_queue):

    stable_value = None
    next_probable_state = None

    TRIGGER_CYCLES_COUNT = 30
    consequtive_opposite_values_counter = 0

    while True:

        # 1 collect proof 
        canary_current_status = _read_signal_canary()
        if stable_value != canary_current_status:
            consequtive_opposite_values_counter += 1
            next_probable_state = canary_current_status
        else:
            consequtive_opposite_values_counter = 0
            next_probable_state = None

        # 2 decide what to do with collected
        signal_to_emit = None
        if consequtive_opposite_values_counter >= (TRIGGER_CYCLES_COUNT):           
            stable_value = next_probable_state
            signal_to_emit = next_probable_state
            next_probable_state = None
            consequtive_opposite_values_counter = 0

        # 999 emit at ANY cause
        try:
            injected_queue.put_nowait(signal_to_emit)      # Replace if full
        except queue.Full:
            injected_queue.get_nowait()
            injected_queue.put_nowait(signal_to_emit)

        time.sleep(_DELAY)

def poller_canary_debounced_deprecated3(injected_queue):

    last_emitted = None
    stable_value = None
    next_probable_state = None

    TRIGGER_CYCLES_COUNT = 30
    consequtive_opposite_values_counter = 0

    while True:

        # 1 collect proof 
        canary_current_status = _read_signal_canary()
        if stable_value != canary_current_status:
            consequtive_opposite_values_counter += 1
            next_probable_state = canary_current_status
        else:
            consequtive_opposite_values_counter = 0
            next_probable_state = None

        # 2 decide what to do with collected
        signal_to_emit = None
        if consequtive_opposite_values_counter >= (TRIGGER_CYCLES_COUNT):           
            stable_value = next_probable_state
            signal_to_emit = next_probable_state
            next_probable_state = None
            consequtive_opposite_values_counter = 0

        # 999 emit at ANY cause
        try: # IF EMPTY --> just PUSH
            injected_queue.put_nowait(signal_to_emit)
            last_emitted = signal_to_emit

        except queue.Full: # IF FULL --> careful

            if last_emitted is not None:
                if signal_to_emit is not last_emitted:
                    injected_queue.get_nowait()
                    injected_queue.put_nowait(signal_to_emit)
                    last_emitted = signal_to_emit
            else:
                injected_queue.get_nowait()
                injected_queue.put_nowait(signal_to_emit)
                last_emitted = signal_to_emit


        #9999 wait a little
        time.sleep(_DELAY)

def poller_canary_debounced(injected_queue):

    last_emitted = None
    last_bool_emitted = None
    stable_value = None
    next_probable_state = None

    TRIGGER_CYCLES_COUNT = 30
    consequtive_opposite_values_counter = 0

    while True:

        # 1 collect proof 
        canary_current_status = _read_signal_canary()
        if stable_value != canary_current_status:
            consequtive_opposite_values_counter += 1
            next_probable_state = canary_current_status
        else:
            consequtive_opposite_values_counter = 0
            next_probable_state = None

        # 2 decide what to do with collected
        signal_to_emit = None
        if consequtive_opposite_values_counter >= (TRIGGER_CYCLES_COUNT):           
            stable_value = next_probable_state
            signal_to_emit = next_probable_state
            next_probable_state = None
            consequtive_opposite_values_counter = 0


        # 999 emit if different
        try: # IF EMPTY --> just PUSH
            injected_queue.put_nowait(signal_to_emit)
            last_emitted = signal_to_emit

        except queue.Full: # IF FULL --> careful

            if signal_to_emit is not None:
                if signal_to_emit != last_emitted:
                    injected_queue.get_nowait()
                    injected_queue.put_nowait(signal_to_emit)
                    last_emitted = signal_to_emit

        #9999 wait a little
        time.sleep(_DELAY)

#---------------------------------------------------------#

# def decide_and_apply(inputs: Inputs, side_effects_box: SideEffects) -> str:

#     if canary_healthy and switches_healthy:
#         status = "OK Returned back to normal (AC). Waking servers up . . ."
#         # side_effects_box.full_log("Returned back to AC")
#         side_effects_box.start_servers_waking_routine()
#         return status

#     elif canary_healthy and not switches_healthy:
#         status = "OK Generator started. Waking servers up . . ."
#         side_effects_box.start_servers_waking_routine()
#         return status

#     elif not canary_healthy and switches_healthy:
#         status = "BAD Check canary signal_to_emit. Fallback to old rules . . ."
#         side_effects_box.start_servers_waking_routine()
#         return status

#     elif not canary_healthy and not switches_healthy:
#         status = "BAD No power, no generator. Suspending soon . . ."
#         side_effects_box.start_servers_suspending_routine()
#         return status

# def transform(inp: Inputs) -> PowerStateName:
#     if inp.canary_healthy and inp.switches_healthy:
#         return PowerStateName.OK_HEALTHY
#     elif inp.canary_healthy and not inp.switches_healthy:
#         return PowerStateName.OK_GENERATOR
#     elif not inp.canary_healthy and not inp.switches_healthy:
#         return PowerStateName.BAD_ON_BBU
#     else:
#         return PowerStateName.BAD_CANARY_DEAD

def react(old_state, inputs, routine_manager):

        