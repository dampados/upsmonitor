# UPSmonitor

**UPSMonitor** watches AC/Generator status and handles the full power-loss lifecycle — graceful cluster shutdown before batteries fail, and full auto-restore when AC or generator power comes back. No USB type B and Windows XP software.

![Scheme](/upsmonitor-scheme.png)

## How to use

### Hardware
- Any Linux SBC with GPIO support (RPi 2/3/4/5, Orange Pi, etc.)
- Python + `gpiod` GPIO
- Feed **3.3V** into **GPIO 17** --> that detects generator/AC directly.
  
### Inventory & Credentials
- See inventory.json inside the "app/" catalog: fill your own inventory (ac_canaries are optional, if AC only, u can use a fake one)
- See creds.json inside the "app/" catalog: fill with your own credentials for each server type.

### Installation & Deployment
- Clone repo to a local PC
- See "env_example.txt" inside root, fill credentials for the upsmonitor target node
- chmod +x *.sh
- run ./install.sh to deploy and create systemd service
- run ./purge.sh to uninstall everything from the target node.
