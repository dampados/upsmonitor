import subprocess
from icmplib import ping
import time
import queue
from dataclasses import replace

from models import PowerStateName, PowerState, Inputs, ActionBox, ActionBoxMock, HostState

GLOBAL_DELAY = 0.1

_CANARY_DEAD = '"17"=inactive'
_CANARY_ALIVE = '"17"=active'

_PING_TIMEOUT = 0.6
_DELAY_HEALTH_PING = 7
# _SWITCH_IPS = [
#     "172.16.38.244",
# ]
# _SWITCH_IPS_REAL = [
#     "172.16.40.101",
#     "172.16.40.102",
#     "172.16.40.103",
#     "172.16.40.104",
#     "172.16.40.105",
# ]

# DEBUG!!!! TBD
_mock_canary = True

# DEBUG!!!! TBD
def keyboard_listener():
    global _mock_canary
    while True:
        key = input().strip()  # waits for Enter over SSH
        if key == 'j':
            _mock_canary = False
            print("Canary: DEAD")
        elif key == 'k':
            _mock_canary = True
            print("Canary: ALIVE")

# DEBUG!!!! TBD
def _read_signal_canary():
    return _mock_canary

def _read_signal_canary_real():

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

def _read_signal_ac_switches(ac_canary_ips):
    for ip in ac_canary_ips:
        if _ping_single(ip):
            return True
    return False

def poller_switches(injected_queue, ac_canary_ips):

    last_emitted = None
    last_bool_emitted = None
    
    while True:

        signal_to_emit = None
        current_readings = _read_signal_ac_switches(ac_canary_ips)

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

        time.sleep(GLOBAL_DELAY)

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
        time.sleep(GLOBAL_DELAY)

def poller_hosts_health(injected_queue: queue.Queue, hosts_map: dict[str, str]) -> None:

    while(True):

        health_status = {}
        for name, ip in hosts_map.items():
            if _ping_single(ip):
                health_status[name] = HostState.ALIVE
            else: 
                health_status[name] = HostState.DEAD
        
        try:
            injected_queue.put_nowait(health_status)
        except queue.Full:
            injected_queue.get_nowait()
            injected_queue.put_nowait(health_status)
        
        time.sleep(_DELAY_HEALTH_PING)

#---------------------------------------------------------#

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
                
# router 
def react_experimantal(old_state: PowerState, i: Inputs, a: ActionBox) -> PowerState:
    if i.canary_healthy is None and i.switches_healthy is None:

        STATE_CHANGE_DEBOUNCING_PERIOD = 60 # each tick is 0.1 delay
        incremented = old_state.ticks_counter + 1
        formed_new_state = None # reference to the state we return in the end


        if old_state.ticks_counter >= STATE_CHANGE_DEBOUNCING_PERIOD: # ALERT: state is stable

            current_readings_key = (old_state.canary_latest_bool, old_state.switches_latest_bool) #fetch the key
            power_state_name = STATE_MAPPING.get(current_readings_key) #challege dict by key


            # start the assigned in STATE MAPPING routine here!!!
            if power_state_name != old_state.status:
                # if power_state_name != PowerStateName.BAD_ON_BBU:
                #     a.start_restoring_routine()
                # else:
                #     a.start_suspending_routine()


                # return replace(
                #     old_state,
                #     ticks_counter = 0,
                #     status = power_state_name
                # )
                formed_new_state = replace(
                    old_state,
                    ticks_counter = 0,
                    status = power_state_name
                )
            else: 
                # return replace(old_state, ticks_counter = 0)
                formed_new_state = replace(old_state, ticks_counter = 0)

        else: # keep ticking
            # return replace(
            #     old_state,
            #     ticks_counter = incremented,
            # )
            formed_new_state = replace(
                old_state,
                ticks_counter = incremented,
            )

    else:
        # return replace(
        #     old_state,
        #     ticks_counter = 0,
        #     canary_latest_bool = ( i.canary_healthy 
        #         if i.canary_healthy is not None
        #         else old_state.canary_latest_bool ),
        #     switches_latest_bool = ( i.switches_healthy
        #         if i.switches_healthy is not None
        #         else old_state.switches_latest_bool),
        # )
        formed_new_state = replace(
            old_state,
            ticks_counter = 0,
            canary_latest_bool = ( i.canary_healthy 
                if i.canary_healthy is not None
                else old_state.canary_latest_bool ),
            switches_latest_bool = ( i.switches_healthy
                if i.switches_healthy is not None
                else old_state.switches_latest_bool),
        )

    ## META ADDITIONAL LOGIC EXPANSION HERE!!!
    formed_new_final_state = _metareact(old_state, formed_new_state, a)

    return formed_new_final_state


def _metareact(old_state: PowerState, new_state_wip: PowerState, a: ActionBox) -> PowerState:
    """
    Meta-level state reactor.
    Tracks cumulative battery runtime and triggers suspend/restore.
    
    Two counters:
    - cumulative_on_bbu_counter: total ticks spent on BBU since last full charge
    - cumulative_healthy_counter: ticks spent charging since last discharge
    
    Suspend when cumulative BBU time reaches 5 minutes (3000 ticks).
    Reset both counters after 5 hours (180000 ticks) of healthy runtime.
    """

    MAX_BEFORE_SUSPEND_REAL = 3000 # ticks
    NEEDED_HEALTHY_BEFORE_RESET_REAL = 180000 # ticks (about 5 hours, drifts a lot, be ready)
    
    MAX_BEFORE_SUSPEND = 150
    NEEDED_HEALTHY_BEFORE_RESET = 200

    # healthy optimism
    if old_state.status != PowerStateName.BAD_ON_BBU and new_state_wip.status != PowerStateName.BAD_ON_BBU:
        # KEEP IT AT MAX AND WAIT!
        if old_state.cumulative_healthy_counter < NEEDED_HEALTHY_BEFORE_RESET:
            new_state_wip.cumulative_healthy_counter = old_state.cumulative_healthy_counter + 1

    # reset
    if new_state_wip.cumulative_healthy_counter >= NEEDED_HEALTHY_BEFORE_RESET:
        #finally batteries are charged!
        new_state_wip.cumulative_on_bbu_counter = 0
        # keep it clean for later, cooking oven and shit analogy . . .
        # new_state_wip.cumulative_healthy_counter = 0  

    # bad pessimism
    if new_state_wip.status == PowerStateName.BAD_ON_BBU:
        new_state_wip.cumulative_healthy_counter = 0 # WE RESET HEALTHY COUNTER HERE!!! not healthy anymore
        new_state_wip.cumulative_on_bbu_counter = min(
            old_state.cumulative_on_bbu_counter + 1,
            MAX_BEFORE_SUSPEND
        )

    # sideeffects starting logic:
    # if new_state_wip.status != PowerStateName.BAD_ON_BBU:
    #     if old_state.status == PowerStateName.BAD_ON_BBU:
    #         a.start_restoring_routine_experimental()
    if new_state_wip.status != PowerStateName.BAD_ON_BBU:
        a.start_restoring_routine()
    else:
        # spam-safe 
        if new_state_wip.cumulative_on_bbu_counter >= MAX_BEFORE_SUSPEND:
            a.start_suspending_routine()  

    return new_state_wip