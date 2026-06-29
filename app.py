#!/usr/bin/env python3
import time
import threading
import queue

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


    stable_state_canary = None
    stable_state_pingie = None

    #999 main cycle: react to changes in signals (WIP)
    while True:
        try:
            queue_read_value_canary = queue_canary.get_nowait()
            print(f"Canary STATUS: {queue_read_value_canary}")
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