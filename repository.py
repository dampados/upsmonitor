import subprocess
from icmplib import ping
import time
import queue
from dataclasses import replace

from models import PowerStateName, PowerState, Inputs, ActionBox, ActionBoxMock

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
        # logging.warning````("GPIO read timed out")
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

def react_deprecated(old_state: PowerState, i: Inputs) -> PowerState:
    if i.canary_healthy is None and i.switches_healthy is None:

        inremented = old_state.ticks_counter + 1

        if (old_state.canary_latest_bool == False 
        and old_state.switches_latest_bool == False
        and old_state.ticks_counter >= 60): #five minutes timeout

            #cancel all tasks and nulify the counter
            #replace routine in the thread to suspending one
            print("New state is BAD_ON_BBU")
            return replace(old_state, ticks_counter = 0, status = PowerStateName.BAD_ON_BBU)

        elif (old_state.canary_latest_bool == False 
        and old_state.switches_latest_bool == True
        and old_state.ticks_counter >= 60): #6 seconds timout

            #cancel all tasks and nulify the counter
            #replace routine in the thread to restoring one (FALLBACK)
            print("New state is BAD_CANARY_DEAD")
            return replace(old_state, ticks_counter = 0, status = PowerStateName.BAD_CANARY_DEAD)


        elif (old_state.canary_latest_bool == True 
        and old_state.switches_latest_bool == True
        and old_state.ticks_counter >= 60): #6 seconds timout

            #cancel all tasks and nulify the counter
            #replace routine in the thread to restoring one (FALLBACK)
            print("New state is OK_HEALTHY")
            return replace(old_state, ticks_counter = 0, status = PowerStateName.OK_HEALTHY)

        elif (old_state.canary_latest_bool == True 
        and old_state.switches_latest_bool == False
        and old_state.ticks_counter >= 60): #6 seconds timout

            #cancel all tasks and nulify the counter
            #replace routine in the thread to restoring one (FALLBACK)
            print("New state is OK_GENERATOR")
            return replace(old_state, ticks_counter = 0, status = PowerStateName.OK_GENERATOR)

        return replace(old_state, ticks_counter = inremented)

    else: # anything but None annywhere

        if i.canary_healthy and i.switches_healthy:
            #cancel all tasks and nulify the counter
            #replace routine in the thread to restoring one
            # print("New state is OK_HEALTHY")
            return replace(old_state, 
                            ticks_counter = 0, 
                            # status = PowerStateName.OK_HEALTHY,
                             canary_latest_bool = i.canary_healthy,
                            switches_latest_bool = i.switches_healthy,
                        )
        elif i.canary_healthy and not i.switches_healthy:
            #cancel all tasks and nulify the counter
            #replace routine in the thread to restoring one
            # print("New state is OK_GENERATOR")
            return replace(old_state, 
                            ticks_counter = 0, 
                            # status = PowerStateName.OK_GENERATOR,
                            canary_latest_bool = i.canary_healthy,
                            switches_latest_bool = i.switches_healthy,                            
                        )
        elif not i.canary_healthy and not i.switches_healthy:
            return replace(old_state, 
                            ticks_counter = 0, 
                            # status = PowerStateName.BAD_ON_BBU,
                            canary_latest_bool = i.canary_healthy,
                            switches_latest_bool = i.switches_healthy,
                        )
        elif not i.canary_healthy and i.switches_healthy:
            return replace(old_state, 
                            ticks_counter = 0, 
                            # status = PowerStateName.BAD_CANARY_DEAD,
                            canary_latest_bool = i.canary_healthy,
                            switches_latest_bool = i.switches_healthy,
                        )


# current inputs are the KEY to THIS mapping dict --> solves elif hell
STATE_MAPPING = {
    (False, False): PowerStateName.BAD_ON_BBU,
    (False, True):  PowerStateName.BAD_CANARY_DEAD,
    (True, True):   PowerStateName.OK_HEALTHY,
    (True, False):  PowerStateName.OK_GENERATOR,
}

# router 
def react(old_state: PowerState, i: Inputs, a: ActionBox) -> PowerState:
    if i.canary_healthy is None and i.switches_healthy is None:

        STATE_CHANGE_DEBOUNCING_PERIOD = 60 # each tick is 0.1 delay
        incremented = old_state.ticks_counter + 1

        if old_state.ticks_counter >= STATE_CHANGE_DEBOUNCING_PERIOD: # ALERT: state is stable


            current_readings_key = (old_state.canary_latest_bool, old_state.switches_latest_bool) #fetch the key
            power_state_name = STATE_MAPPING.get(current_readings_key) #challege dict by key

            # start the assigned in STATE MAPPING routine here!!!
            if power_state_name != old_state.status:
                if power_state_name != PowerStateName.BAD_ON_BBU:
                    a.start_restoring_routine()
                else:
                    a.start_suspending_routine()

                return replace(
                    old_state,
                    ticks_counter = 0,
                    status = power_state_name
                )
            else: 
                return replace(old_state, ticks_counter = 0)

        else: # keep ticking
            return replace(
                old_state,
                ticks_counter = incremented,
            )

    else:
        return replace(
            old_state,
            ticks_counter = 0,
            canary_latest_bool = ( i.canary_healthy 
                if i.canary_healthy is not None
                else old_state.canary_latest_bool ),
            switches_latest_bool = ( i.switches_healthy
                if i.switches_healthy is not None
                else old_state.switches_latest_bool),
        )
                
        
