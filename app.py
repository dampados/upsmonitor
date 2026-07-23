#!/usr/bin/env python3
import time
import threading
import queue
from dataclasses import replace

import repository
from models import PowerState, Inputs, HostState, HostsHealthStatusWrapper, PowerStateViewModel
from helper_functions import load_config, print_dashboard
from actionbox import ActionBoxReal
import http_server



def main():

    #0 READ config: credentials AND inventory. READ ONLY!
    CREDS_FILENAME = "creds.json"
    INVENTORY_FILENAME = "inventory.json"

    try:
        # no nested scope here!
        CREDS, INVENTORY = load_config(CREDS_FILENAME, INVENTORY_FILENAME)
    except FileNotFoundError as e:
        print(f"Config file not found! : {e.filename}")
        return 1

    #0 Template for the pinger: just the list of hostnames it needs to ping
    # HOSTNAMES = [host["name"] for host in INVENTORY["hosts"]]
    HOST_TO_IP_MAP = {host["name"]: host["ip"] for host in INVENTORY["hosts"]}
    AC_CANARIES = INVENTORY.get("ac_canaries", [])

    #0.5 spawn QUEUEs (like channels in golang)
    queue_canary = queue.Queue(maxsize=1)
    queue_ac_switches = queue.Queue(maxsize=1)
    queue_hosts_status = queue.Queue(maxsize=1)

#--------------START sensors routines!------------------#
    #1 START canary sensor 
    thread_cannary = threading.Thread(
        target=repository.poller_canary_debounced,
        args=(queue_canary,)
    )
    thread_cannary.daemon = True
    thread_cannary.start()

    #2 START ac switches sensor
    thread_switches = threading.Thread(
        target = repository.poller_switches,
        args=(queue_ac_switches, AC_CANARIES)
    )
    thread_switches.daemon = True
    thread_switches.start()

    #3 START hosts health sensor
    thread_hosts_health = threading.Thread(
        target = repository.poller_hosts_health,
        args=(queue_hosts_status, HOST_TO_IP_MAP)
    )
    thread_hosts_health.daemon = True
    thread_hosts_health.start()


#---------------------main_loop-------------------------#

    #999 main cycle: react to changes in signals (WIP)
    current_inputs = Inputs()

    # current_power_state_model = PowerState() # must be READ ONLY FOR EVERYONE AND PRVATE
    # current_power_state_viewmodel = PowerStateViewModel(current_power_state_model) # BEHAVIOR ABSTRACTION

    current_power_state_viewmodel = PowerStateViewModel(PowerState()) # liek this mb?

    current_hosts_health_status = HostsHealthStatusWrapper(
        {host["name"]: HostState.UNKNOWN for host in INVENTORY["hosts"]}
    )


    # DELETEME 
    # action_box = ActionBoxMock()
    # DELETEME 

    action_box = ActionBoxReal(
        current_hosts_health_status,
        CREDS,
        INVENTORY,
    )

    # http_server.start_dashboard_server(current_power_state_model, current_hosts_health_status)
    http_server.start_dashboard_server(current_power_state_viewmodel, current_hosts_health_status)

    # action_box.start_suspending_routine()   # should print and run for 5s
    # time.sleep(2)
    # action_box.start_restoring_routine() 

    thread_keyboard = threading.Thread(target=repository.keyboard_listener, daemon=True)
    thread_keyboard.start()

    while True:
        try:
            canary_reading = queue_canary.get_nowait()
            # print(f"Canary STATUS: {canary_reading}")
            current_inputs = replace(current_inputs, canary_healthy = canary_reading)
            # current_power_state_model = repository.react(current_power_state_model, current_inputs, action_box)
            updated_state = repository.react_experimantal(current_power_state_viewmodel.get(), current_inputs, action_box)
            current_power_state_viewmodel.update(updated_state)
        except queue.Empty:
            pass

        try:
            ac_switches_reading = queue_ac_switches.get_nowait()
            # print(f"Switches STATUS: {ac_switches_reading}")
            current_inputs = replace(current_inputs, switches_healthy = ac_switches_reading)
            # current_power_state_model = repository.react(current_power_state_model, current_inputs, action_box)
            # updated_state = repository.react(current_power_state_viewmodel.get(), current_inputs, action_box)
            updated_state = repository.react_experimantal(current_power_state_viewmodel.get(), current_inputs, action_box)
            current_power_state_viewmodel.update(updated_state)
        except queue.Empty:
            pass

        try:
            hosts_health_reading = queue_hosts_status.get_nowait()
            current_hosts_health_status.update(hosts_health_reading)  # MUTEXED UPDATE BC SHARED 

        except queue.Empty:
            pass
            
        # print_dashboard(current_power_state_model, current_hosts_health_status)
 

        time.sleep(repository.GLOBAL_DELAY)
    # BLOCKING MAIN LOOP DONT PUT ANYTHING AFTER


if __name__ == "__main__":
    main()