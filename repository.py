import subprocess
from icmplib import ping
import time

_CANARY_DEAD = '"17"=inactive'
_CANARY_ALIVE = '"17"=active'

_PING_TIMEOUT = 0.6
_SWITCH_IPS = [
    "172.16.40.101",
    "172.16.40.102",
    "172.16.40.103",
    "172.16.40.104",
    "172.16.40.105",
]

DELAY = 0.1

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

def poller_switches(queue):

    last_state = None

    while True:

        current_readings = _read_signal_ping()
        if current_readings != last_state:
            last_state = current_readings

            try:

                queue.put_nowait(current_readings)      # Replace if full
            except queue.Full:
                queue.get_nowait()
                queue.put_nowait(current_readings)

        time.sleep(DELAY)
        time.sleep(DELAY)
        time.sleep(DELAY)
        time.sleep(DELAY)
        time.sleep(DELAY)







def poller_canary_debounced(queue):

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
                queue.put_nowait(stable_value)      # Replace if full
            except queue.Full:
                queue.get_nowait()
                queue.put_nowait(stable_value)

        time.sleep(DELAY)