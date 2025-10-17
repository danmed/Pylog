import http.server
import socketserver
import json
import threading
from datetime import datetime
import os
import glob
from collections import deque

# --- Configuration ---
WEB_HOST = "0.0.0.0"
WEB_PORT = 8000
SYSLOG_HOST = "0.0.0.0"
SYSLOG_PORTS = [514, 1514] # Add your desired UDP ports here
LOG_DIRECTORY = "syslog_logs" # Directory to store log files
MAX_LOGS_PER_FILE_IN_UI = 1000 # Max logs to read from each file for the UI display

# --- Thread-safe lock for file writing ---
# Although each thread writes to its own file, a lock is good practice
# if you ever consolidate logging. For now, it's less critical.
log_lock = threading.Lock()

# --- Syslog UDP Handler ---
def create_syslog_handler(port):
    """Factory function to create a handler class that knows its port."""

    class SyslogUDPHandler(socketserver.BaseRequestHandler):
        """
        Handles incoming syslog messages and writes them to a file
        named after the port it's serving.
        """
        def handle(self):
            try:
                data = self.request[0]
                socket = self.request[1]
                message = data.decode('utf-8', errors='ignore')

                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "source_ip": self.client_address[0],
                    "source_port": self.client_address[1],
                    "destination_port": port,
                    "message": message.strip()
                }

                # Define the log file path
                log_file_path = os.path.join(LOG_DIRECTORY, f"{port}.log")

                # Write to the specific log file for this port
                with log_lock:
                    with open(log_file_path, 'a') as f:
                        f.write(json.dumps(log_entry) + '\n')

            except Exception as e:
                print(f"Error handling syslog message on port {port}: {e}")

    return SyslogUDPHandler

# --- Web Server ---
class WebServerHandler(http.server.SimpleHTTPRequestHandler):
    """
    Handles web requests to serve the UI and the log data.
    """
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(self._get_html_content().encode('utf-8'))
        elif self.path == '/logs':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            logs = self._get_logs_from_files()
            self.wfile.write(json.dumps(logs).encode('utf-8'))
        else:
            super().do_GET()

    def _get_logs_from_files(self):
        """
        Reads the latest logs from all .log files, combines, sorts, and returns them.
        """
        all_logs = []
        log_files = glob.glob(os.path.join(LOG_DIRECTORY, '*.log'))

        for file_path in log_files:
            try:
                with open(file_path, 'r') as f:
                    # Use deque for an efficient way to get the last N lines
                    last_lines = deque(f, MAX_LOGS_PER_FILE_IN_UI)
                    for line in last_lines:
                        try:
                            all_logs.append(json.loads(line))
                        except json.JSONDecodeError:
                            # Handle cases where a line is not valid JSON
                            print(f"Warning: Could not parse line in {file_path}: {line.strip()}")
            except Exception as e:
                print(f"Error reading log file {file_path}: {e}")

        # Sort all collected logs by timestamp in descending order (newest first)
        all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return all_logs

    def _get_html_content(self):
        """Returns the full HTML for the web interface."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Syslog Viewer Pro</title>
    <style>
        :root {
            --bg-color: #1e1e2e; --base-color: #cdd6f4; --surface-color: #313244;
            --overlay-color: #45475a; --header-bg: #181825; --border-color: #585b70;
            --green: #a6e3a1; --mauve: #cba6f7; --red: #f38ba8; --peach: #fab387;
        }
        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0; background-color: var(--bg-color); color: var(--base-color);
            font-size: 14px; line-height: 1.6;
        }
        .container { display: flex; flex-direction: column; height: 100vh; }
        .header {
            background-color: var(--header-bg); padding: 16px 24px;
            border-bottom: 1px solid var(--border-color); display: flex; align-items: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.2); z-index: 10;
        }
        .header h1 { margin: 0; font-size: 1.5em; color: var(--mauve); letter-spacing: 1px;}
        .log-container { flex-grow: 1; overflow: auto; }
        table { border-collapse: collapse; width: 100%; }
        th, td {
            text-align: left; padding: 12px 24px;
            border-bottom: 1px solid var(--surface-color);
            white-space: pre-wrap; word-break: break-word;
        }
        thead { position: sticky; top: 0; z-index: 5; }
        thead tr:first-child th {
             background-color: var(--header-bg);
             font-size: 0.9em; text-transform: uppercase; letter-spacing: 0.5px;
        }
        thead tr:last-child th { background-color: var(--surface-color); padding: 8px 16px; }
        tbody tr { transition: background-color 0.2s ease; }
        tbody tr:hover { background-color: var(--overlay-color); }
        .col-timestamp { width: 180px; color: var(--green); }
        .col-source { width: 200px; color: var(--peach); }
        .col-port { width: 120px; color: var(--red); }
        .column-filter {
            width: 100%; box-sizing: border-box; background-color: var(--overlay-color);
            color: var(--base-color); border: 1px solid var(--border-color);
            border-radius: 5px; padding: 8px 10px; font-size: 13px;
        }
        .column-filter::placeholder { color: #7f849c; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Log Stream</h1>
        </div>
        <div class="log-container">
            <table>
                <thead>
                    <tr>
                        <th class="col-timestamp">Timestamp</th>
                        <th class="col-source">Source</th>
                        <th class="col-port">Dest Port</th>
                        <th class="col-message">Message</th>
                    </tr>
                    <tr>
                        <th><input type="text" class="column-filter" id="filterTimestamp" placeholder="Filter timestamp..."></th>
                        <th><input type="text" class="column-filter" id="filterSource" placeholder="Filter source..."></th>
                        <th><input type="text" class="column-filter" id="filterPort" placeholder="Filter port..."></th>
                        <th><input type="text" class="column-filter" id="filterMessage" placeholder="Filter message..."></th>
                    </tr>
                </thead>
                <tbody id="logTableBody"></tbody>
            </table>
        </div>
    </div>
    <script>
        const logTableBody = document.getElementById('logTableBody');
        const filterInputs = document.querySelectorAll('.column-filter');
        const filterTimestamp = document.getElementById('filterTimestamp');
        const filterSource = document.getElementById('filterSource');
        const filterPort = document.getElementById('filterPort');
        const filterMessage = document.getElementById('filterMessage');
        let logsCache = [];
        let viewNeedsUpdate = true;

        async function fetchLogs() {
            try {
                const response = await fetch('/logs');
                const newLogs = await response.json();

                if (JSON.stringify(newLogs) !== JSON.stringify(logsCache)) {
                    logsCache = newLogs;
                    viewNeedsUpdate = true;
                    updateTable();
                }
            } catch (error) {
                console.error('Error fetching logs:', error);
            }
        }

        function updateTable() {
            const timestampFilter = filterTimestamp.value.toLowerCase();
            const sourceFilter = filterSource.value.toLowerCase();
            const portFilter = filterPort.value.toLowerCase();
            const messageFilter = filterMessage.value.toLowerCase();

            let tableHtml = '';
            for (const log of logsCache) {
                const logTimestamp = log.timestamp.toLowerCase();
                const logSource = `${log.source_ip}:${log.source_port}`.toLowerCase();
                const logPort = String(log.destination_port).toLowerCase();
                const logMessage = log.message.toLowerCase();

                if (
                    logTimestamp.includes(timestampFilter) &&
                    logSource.includes(sourceFilter) &&
                    logPort.includes(portFilter) &&
                    logMessage.includes(messageFilter)
                ) {
                    tableHtml += `
                        <tr>
                            <td class="col-timestamp">${log.timestamp}</td>
                            <td class="col-source">${log.source_ip}:${log.source_port}</td>
                            <td class="col-port">${log.destination_port}</td>
                            <td>${escapeHtml(log.message)}</td>
                        </tr>
                    `;
                }
            }
            logTableBody.innerHTML = tableHtml;
            viewNeedsUpdate = false;
        }

        function escapeHtml(unsafe) {
            if (!unsafe) return '';
            return unsafe
                 .replace(/&/g, "&amp;")
                 .replace(/</g, "&lt;")
                 .replace(/>/g, "&gt;")
                 .replace(/"/g, "&quot;")
                 .replace(/'/g, "&#039;");
        }

        filterInputs.forEach(input => {
            input.addEventListener('input', updateTable);
        });

        setInterval(fetchLogs, 3000); // Refresh data every 3 seconds
        fetchLogs(); // Initial fetch
    </script>
</body>
</html>
        """;

def run_web_server():
    """Starts the HTTP web server in a thread."""
    try:
        with socketserver.TCPServer((WEB_HOST, WEB_PORT), WebServerHandler) as httpd:
            print(f"Web interface available at http://{WEB_HOST}:{WEB_PORT}")
            httpd.serve_forever()
    except Exception as e:
        print(f"Failed to start web server: {e}")

if __name__ == "__main__":
    # Create the log directory if it doesn't exist
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)
        print(f"Created log directory: {LOG_DIRECTORY}")

    # --- Start a thread for each syslog port ---
    for port in SYSLOG_PORTS:
        handler_class = create_syslog_handler(port)
        server = socketserver.UDPServer((SYSLOG_HOST, port), handler_class)

        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()
        print(f"Syslog server listening on UDP {SYSLOG_HOST}:{port}")

    # --- Start the web server in the main thread ---
    print(f"Web interface starting on http://localhost:{WEB_PORT}")
    run_web_server()

