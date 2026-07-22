from models import ActionBox, HostsHealthStatusWrapper, HostState
import subprocess
import time
import threading

class ActionBoxReal(ActionBox):
    def __init__(
            self, 
            hosts_status: HostsHealthStatusWrapper, 
            creds: dict,
            inventory: dict,
            ):
        self._thread = None                 # ref to a singular per instance thread
        self._thread_stop_event = threading.Event() # stop event
        self._hosts_status = hosts_status   # alive or dead statuses
        self._hosts_combined_ram = []       # obvious!
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
    
        # thread_cannary = threading.Thread(
        #     target=None,
        #     args=()
        # )
        # thread_cannary.daemon = True
        # thread_cannary.start()

# ----- INIT END ----- $

# ----- private  ----- $

    def _suspending_routine(self) -> None:
        print("suspend started")
        while True:

            if self._stop_event.is_set():
                break

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

                if self._stop_event.is_set():
                    break

                cmd = [
                    "sshpass",
                    "-p", host["password"],
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    f"{host['user']}@{host['ip']}",
                    "systemctl", "suspend"
                ]
                subprocess.run(cmd, timeout=15, capture_output=False)
                print("suspend issued")


            # # Suspend Windows hosts
            # for host in alive_windows:
            #     # cmd = ["sshpass", "-p", host["password"], "ssh", ... "rundll32.exe powrprof.dll,SetSuspendState 0,1,0"]
            #     # subprocess.run(cmd, timeout=10, capture_output=True)
            #     pass

            # Suspend Windows hosts (hibernate)
            for host in alive_windows:
                if self._stop_event.is_set():
                    break

                cmd = [
                    "sshpass",
                    "-p", host["password"],
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    f"{host['user']}@{host['ip']}",
                    "shutdown", "/h", "/f", "/t", "0"
                ]
                subprocess.run(cmd, timeout=15, capture_output=False)
                print("hibernate issued")
                
            if self._stop_event.is_set():
                    break

            time.sleep(2)

    def _restoring_routine(self) -> None:
        print("restoring started")
        while True:
            if self._stop_event.is_set():
                break

            status = self._hosts_status.get()

            dead_hosts = []
            for host in self._hosts_combined_ram:
                if status.get(host["name"]) == HostState.DEAD:
                    dead_hosts.append(host)

            if not dead_hosts:
                break # EXIT + THREAD DEATH

            for host in dead_hosts:
                if self._stop_event.is_set():
                    break

                for mac in host["macs"]:
                    if self._stop_event.is_set():
                        break

                    cmd = [
                        "wakeonlan",
                        mac
                    ]
                    subprocess.run(cmd, timeout=5, capture_output=True)
                    print("restoring issued")

                time.sleep(1)

            if self._stop_event.is_set():
                break
            time.sleep(5)

    def _suspending_routine_mock(self, stop_event) -> None:
        print("🟡 SUSPEND: started")
        for i in range(5):
            if stop_event.is_set():  # ← use the passed event
                print("🟡 SUSPEND: stopped early")
                return
            print(f"🟡 SUSPEND: working... {i+1}/5")
            time.sleep(1)
        print("🟢 SUSPEND: finished")

    def _restoring_routine_mock(self, stop_event) -> None:
        print("🔵 RESTORE: started")
        for i in range(5):
            if stop_event.is_set():  # ← use the passed event
                print("🔵 RESTORE: stopped early")
                return
            print(f"🔵 RESTORE: working... {i+1}/5")
            time.sleep(1)
        print("🟢 RESTORE: finished")

    def _start_routine(self, target):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join() #DEBUG
        
        self._stop_event = threading.Event()
        # self._thread = threading.Thread(target=target, args=(self._stop_event,))
        # self._thread = threading.Thread(target=target, args=())
        self._thread = threading.Thread(target=target)
        self._thread.daemon = True
        self._thread.start()



# ----- public  ----- $

    def start_suspending_routine(self):
        self._start_routine(self._suspending_routine)

    def start_restoring_routine(self):
        self._start_routine(self._restoring_routine)

