from models import ActionBox, HostsHealthStatusWrapper, HostState
import subprocess
import time

class ActionBoxReal(ActionBox):
    def __init__(
            self, 
            hosts_status: HostsHealthStatusWrapper, 
            creds: dict,
            inventory: dict,
            ):
        self._hosts_status = hosts_status
        self._hosts_combined_ram = []
        # self._creds = creds
        # self._inventory_ram = inventory

        for host in inventory["hosts"]:
            cred_set = host["cred_set"]
            creds_for_host = creds["credentials"].get(cred_set, {})
            self._hosts_combined_ram.append({
                "name": host["name"],
                "ip": host["ip"],
                "macs": host["macs"],
                "os_type": host["os_type"],
                "user": creds_for_host.get("user"),
                "password": creds_for_host.get("password"),
            })
    
    def start_suspending_routine(self) -> None:
        # SSH suspend all alive hosts
        pass

    def _suspending_routine(self) -> None:
        while True:
            status = self._hosts_status.get()

            alive_linux = []
            alive_windows = []

            for host in self._hosts_combined_ram:
                if status.get(host["name"]) == HostState.ALIVE:
                    if host["os_type"] == "linux":
                        alive_linux.append(host)
                    elif host["os_type"] == "windows":
                        alive_windows.append(host)

            
            if not alive_linux and not alive_windows:
                break
            
            # Suspend Linux hosts
            for host in alive_linux:
                cmd = ["sshpass", "-p", host["password"], "ssh", ... "systemctl", "suspend"]
                subprocess.run(cmd, timeout=10, capture_output=True)

            # Suspend Windows hosts
            for host in alive_windows:
                # cmd = ["sshpass", "-p", host["password"], "ssh", ... "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"]
                # subprocess.run(cmd, timeout=10, capture_output=True)
                pass
        
            time.sleep(2)



    def start_restoring_routine(self) -> None:
        # WoL all dead hosts
        pass