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
        self._thread_suspending = None          # ref to a routine specific thread
        self._thread_restoring = None           # ref to a routine specific thread
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
                # NO! now we ONLY exit the routine via STOP EVENT!!!
                # break # EXIT + THREAD DEATH
                continue
            
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
                # subprocess.run(cmd, timeout=15, capture_output=False)
                try:
                    subprocess.run(cmd, timeout=15, capture_output=False)
                    print(f"suspend issued for {host['name']}")
                except Exception as e:
                    print(f"suspend failed for {host['name']}: {e}")
                # print("suspend issued")
                print(f"suspend issued for {host['name']}")

            # Suspend Windows hosts (hibernate)
            for host in alive_windows:
                if self._stop_event.is_set():
                    break

                # cmd = [
                #     "sshpass",
                #     "-p", host["password"],
                #     "ssh",
                #     "-o", "StrictHostKeyChecking=no",
                #     "-o", "ConnectTimeout=10",
                #     f"{host['user']}@{host['ip']}",
                #     "shutdown", "/h", "/f", "/t", "0"
                # ]
                cmd = [
                    "sshpass",
                    "-p", host["password"],
                    "ssh",
                    "-o", "StrictHostKeyChecking=no",
                    "-o", "ConnectTimeout=10",
                    f"{host['user']}@{host['ip']}",
                    "shutdown", "/h", "/f"
                ]
                # subprocess.run(cmd, timeout=15, capture_output=False)
                try:
                    subprocess.run(cmd, timeout=15, capture_output=False)
                except subprocess.TimeoutExpired:
                    print(f"hibernate issued for {host['name']} (SSH timed out, host likely hibernated)")
                except Exception as e:
                    print(f"hibernate failed for {host['name']}: {e}")
                # print("hibernate issued")
                print(f"hibernate issued for {host['name']}")
                
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
                # NO! now we ONLY exit the routine via STOP EVENT!!!
                # break # EXIT + THREAD DEATH
                continue

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
                    # print("restoring issued")
                    print(f"restoring issued for {host['name']} ({mac})")

                time.sleep(1)

            if self._stop_event.is_set():
                break
            time.sleep(10)

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

    def _stop_all_threads_experimental(self):
        if self._thread_restoring and self._thread_restoring.is_alive():
            self._stop_event.set()
            self._thread_restoring.join() # TODO DEBUG BLOCKING

        if self._thread_suspending and self._thread_suspending.is_alive():
            self._stop_event.set()
            self._thread_suspending.join() # TODO DEBUG BLOCKING


# ----- public  ----- $

    def start_suspending_routine(self):
        if self._thread_suspending and self._thread_suspending.is_alive():
            return
        self._stop_all_threads_experimental()
        self._stop_event = threading.Event()
        
        self._thread_suspending = threading.Thread(target=self._suspending_routine)
        self._thread_suspending.daemon = True
        self._thread_suspending.start()

    def start_restoring_routine(self):
        if self._thread_restoring and self._thread_restoring.is_alive():
            return
        self._stop_all_threads_experimental()
        self._stop_event = threading.Event()
        
        self._thread_restoring = threading.Thread(target=self._restoring_routine)
        self._thread_restoring.daemon = True
        self._thread_restoring.start()
