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
    <title>Syslog Viewer</title>
    <style>
        :root { --bg-color: #1a1a1a; --text-color: #e0e0e0; --border-color: #444; --header-bg: #2c2c2c; --search-bg: #333; --search-text: #fff; --row-hover: #2a2a2a; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background-color: var(--bg-color); color: var(--text-color); font-size: 14px; }
        .container { display: flex; flex-direction: column; height: 100vh; }
        .header { background-color: var(--header-bg); padding: 12px 20px; border-bottom: 1px solid var(--border-color); display: flex; align-items: center; }
        .header h1 { margin: 0; font-size: 1.2em; }
        .search-box { margin-left: auto; }
        #searchInput { background-color: var(--search-bg); color: var(--search-text); border: 1px solid var(--border-color); border-radius: 5px; padding: 8px 12px; width: 300px; }
        .log-container { flex-grow: 1; overflow-y: auto; padding: 0; }
        table { border-collapse: collapse; width: 100%; }
        th, td { text-align: left; padding: 10px 20px; border-bottom: 1px solid var(--border-color); white-space: pre-wrap; word-break: break-all; }
        thead { position: sticky; top: 0; background-color: var(--header-bg); }
        tbody tr:hover { background-color: var(--row-hover); }
        .col-timestamp { width: 160px; } .col-source { width: 180px; } .col-port {width: 100px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Syslog Viewer</h1>
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search logs...">
            </div>
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
                </thead>
                <tbody id="logTableBody"></tbody>
            </table>
        </div>
    </div>
    <script>
        const logTableBody = document.getElementById('logTableBody');
        const searchInput = document.getElementById('searchInput');
        let lastLogCount = 0;

        async function fetchLogs() {
            try {
                const response = await fetch('/logs');
                const logs = await response.json();

                if (logs.length !== lastLogCount) {
                    updateTable(logs);
                    lastLogCount = logs.length;
                }
            } catch (error) {
                console.error('Error fetching logs:', error);
            }
        }

        function updateTable(logs) {
            const searchTerm = searchInput.value.toLowerCase();
            let tableHtml = '';

            for (const log of logs) {
                const logMessage = log.message.toLowerCase();
                const sourceIp = log.source_ip.toLowerCase();
                if (logMessage.includes(searchTerm) || sourceIp.includes(searchTerm)) {
                    tableHtml += `
                        <tr>
                            <td>${log.timestamp}</td>
                            <td>${log.source_ip}:${log.source_port}</td>
                            <td>${log.destination_port}</td>
                            <td>${escapeHtml(log.message)}</td>
                        </tr>
                    `;
                }
            }
            logTableBody.innerHTML = tableHtml;
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

        searchInput.addEventListener('input', fetchLogs);
        setInterval(fetchLogs, 3000); // Refresh every 3 seconds
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

