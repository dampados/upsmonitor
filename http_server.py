from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from models import HostsHealthStatusWrapper, HostState, PowerStateViewModel

class DashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._power_state_viewmodel = kwargs.pop('power_state_viewmodel', None)
        self._hosts_status = kwargs.pop('hosts_status', None)
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path != '/':
            self.send_response(404)
            self.end_headers()
            return

        status = self._hosts_status.get()
        power = self._power_state_viewmodel.get()

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta http-equiv="refresh" content="2">
    <title>Canary Monitor</title>
    <style>
        body {{ font-family: monospace; background: #111; color: #0f0; padding: 20px; }}
        .state {{ font-size: 2em; }}
        .ok {{ color: #0f0; }}
        .bad {{ color: #f00; }}
        .unknown {{ color: #ff0; }}
        table {{ border-collapse: collapse; margin-top: 20px; }}
        td, th {{ padding: 8px 16px; border: 1px solid #333; }}
        .alive {{ color: #0f0; }}
        .dead {{ color: #f00; }}
        .unknown-state {{ color: #ff0; }}
    </style>
</head>
<body>
    <div class="state {power.status.name.lower()}">
        POWER STATE: {power.status.name}
    </div>
    <div>Canary: {power.canary_latest_bool}</div>
    <div>Switches: {power.switches_latest_bool}</div>
    <div>Ticks: {power.ticks_counter}</div>
    <table>
        <tr><th>Host</th><th>Status</th></tr>
"""

        for name, state in status.items():
            state_class = state.name.lower()
            html += f"<tr><td>{name}</td><td class='{state_class}'>{state.name}</td></tr>"

        html += """
    </table>
</body>
</html>
"""

        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.end_headers()
        self.wfile.write(html.encode())


class ReusableHTTPServer(HTTPServer):
    allow_reuse_address = True


def start_dashboard_server(power_state_viewmodel: PowerStateViewModel, hosts_status: HostsHealthStatusWrapper, port: int = 80):
    def handler(*args, **kwargs):
        return DashboardHandler(*args, power_state_viewmodel=power_state_viewmodel, hosts_status=hosts_status, **kwargs)

    server = ReusableHTTPServer(('0.0.0.0', port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server