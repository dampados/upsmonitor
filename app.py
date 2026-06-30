#!/usr/bin/env python3
import time
import threading
import queue
from state import PowerState, PowerStateName, Inputs
from dataclasses import replace

import repository

def main():
    print("Canary Monitor Started")
    
    #0 spawn QUEUEs (like channels in golang)
    queue_canary = queue.Queue(maxsize=1)
    queue_pingie = queue.Queue(maxsize=1)

    #0 START sensors routines 
    thread_cannary = threading.Thread(
        target=repository.poller_canary_debounced,
        args=(queue_canary,)
    )
    thread_cannary.daemon = True
    thread_cannary.start()

    thread_switches = threading.Thread(
        target = repository.poller_switches,
        args=(queue_pingie,)
    )
    thread_switches.daemon = True
    thread_switches.start()


    #999 main cycle: react to changes in signals (WIP)
    current_inputs = Inputs()
    current_state = PowerState()

    while True:
        try:
            canary_reading = queue_canary.get_nowait()
            print(f"Canary STATUS: {canary_reading}")
            current_inputs = replace(current_inputs, canary_healthy = canary_reading)
            current_state = repository.react(current_state, current_inputs)

        except queue.Empty:
            pass

        try:
            queue_read_value_pingie = queue_pingie.get_nowait()
            print(f"Switches STATUS: {queue_read_value_pingie}")
        except queue.Empty:
            pass

        time.sleep(0.5)

if __name__ == "__main__":
    main()