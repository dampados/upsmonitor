import json
import os

from models import PowerState, HostState

def load_config(creds_file, inventory_file):
    with open(creds_file) as f:
        creds = json.load(f)
    with open(inventory_file) as f:
        inventory = json.load(f)
    return creds, inventory

#DEBUG ONLY OUTPUT vvvvvv

def clear_screen():
    os.system('clear')  # or 'cls' for Windows

def print_dashboard(power_state: PowerState, hosts_status: dict[str, HostState]):
    clear_screen()
    print("=" * 60)
    print(f"  POWER STATE: {power_state.status.name}")
    print("=" * 60)
    print(f"  Canary:     {power_state.canary_latest_bool}")
    print(f"  Switches:   {power_state.switches_latest_bool}")
    print(f"  Ticks:      {power_state.ticks_counter}")
    print("=" * 60)
    print("  HOSTS HEALTH:")
    for name, state in hosts_status.items():
        state_str = state.name
        print(f"    {name:20} : {state_str}")
    print("=" * 60)