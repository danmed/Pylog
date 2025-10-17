# Simple Syslog Server with Web GUI (Multi-port Version)
#
# This script runs multiple servers in parallel:
# 1. A UDP server for EACH port specified in the SYSLOG_PORTS list to collect syslog messages.
# 2. A single TCP server on port 8000 to serve a web interface for viewing all collected logs.
#
# To Run:
# 1. Save this file as `syslog_server.py`.
# 2. Edit the `SYSLOG_PORTS` list below to include all the UDP ports you want to monitor.
# 3. Run from your terminal: `python3 syslog_server.py`
# 4. Open your web browser and navigate to http://localhost:8000
#
# Note: Using ports below 1024 (like the standard 514) might require administrator/root privileges.
# If you get a "Permission denied" error, try running with sudo: `sudo python3 syslog_server.py`

import socketserver
import threading
import json
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, HTTPServer

# --- Configuration ---
WEB_HOST = "0.0.0.0"
WEB_PORT = 8000
SYSLOG_HOST = "0.0.0.0"
# --- MODIFIED: List of UDP ports to listen on for syslog messages ---
SYSLOG_PORTS = [514, 1514, 5140]

# --- In-memory Log Storage ---
# A thread-safe way to store logs from all ports.
LOGS_LOCK = threading.Lock()
LOGS = []
MAX_LOGS = 2000 # Limit the number of logs stored in memory

# --- Web Page Content ---
# A complete, self-contained HTML file with Tailwind CSS and JavaScript for the UI.
HTML_CONTENT = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Simple Syslog Viewer</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        /* Simple dark theme */
        body {
            background-color: #1a202c;
            color: #e2e8f0;
            font-family: 'Inter', sans-serif;
        }
        .table-container {
            max-height: calc(100vh - 150px); /* Adjust based on header/footer height */
            overflow-y: auto;
        }
        /* Custom scrollbar for a better look */
        .table-container::-webkit-scrollbar {
            width: 8px;
        }
        .table-container::-webkit-scrollbar-track {
            background: #2d3748;
        }
        .table-container::-webkit-scrollbar-thumb {
            background: #4a5568;
            border-radius: 4px;
        }
    </style>
    <link rel="preconnect" href="https://rsms.me/">
    <link rel="stylesheet" href="https://rsms.me/inter/inter.css">
</head>
<body class="antialiased">
    <div class="container mx-auto p-4 md:p-6">
        <header class="mb-4">
            <h1 class="text-3xl font-bold text-white">Simple Syslog Viewer</h1>
            <p class="text-gray-400">Live log messages from your syslog clients.</p>
        </header>

        <!-- Filter and Search Controls -->
        <div class="flex flex-wrap items-center gap-4 p-4 bg-gray-900/50 rounded-lg shadow-md mb-4">
            <div class="relative flex-grow">
                <input type="text" id="searchInput" placeholder="Search logs..."
                       class="w-full bg-gray-700 text-white placeholder-gray-400 rounded-md py-2 px-4 focus:outline-none focus:ring-2 focus:ring-blue-500">
                <svg class="absolute right-3 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd" />
                </svg>
            </div>
            <button id="clearButton" class="bg-red-600 hover:bg-red-700 text-white font-bold py-2 px-4 rounded-md transition-colors">
                Clear Search
            </button>
            <div class="flex items-center space-x-2 text-sm text-gray-300">
                <label for="autoRefreshToggle">Auto-refresh:</label>
                <input type="checkbox" id="autoRefreshToggle" class="form-checkbox h-5 w-5 text-blue-500 bg-gray-700 border-gray-600 rounded focus:ring-blue-500" checked>
            </div>
             <div id="logCount" class="text-sm text-gray-400"></div>
        </div>

        <!-- Log Display Table -->
        <div class="bg-gray-800 rounded-lg shadow-xl table-container">
            <table class="w-full text-left">
                <thead class="sticky top-0 bg-gray-900">
                    <tr>
                        <th class="p-4 text-sm font-semibold text-gray-300 w-1/5">Timestamp</th>
                        <th class="p-4 text-sm font-semibold text-gray-300 w-1/5">Source</th>
                        <th class="p-4 text-sm font-semibold text-gray-300 w-3/5">Message</th>
                    </tr>
                </thead>
                <tbody id="logTableBody" class="divide-y divide-gray-700">
                    <!-- Log entries will be inserted here by JavaScript -->
                </tbody>
            </table>
            <div id="loadingIndicator" class="text-center p-8 text-gray-500">Loading logs...</div>
        </div>

    </div>

    <script>
        const logTableBody = document.getElementById('logTableBody');
        const searchInput = document.getElementById('searchInput');
        const clearButton = document.getElementById('clearButton');
        const autoRefreshToggle = document.getElementById('autoRefreshToggle');
        const logCountElement = document.getElementById('logCount');
        const loadingIndicator = document.getElementById('loadingIndicator');

        let allLogs = [];
        let autoRefreshInterval;

        // Function to fetch logs from the server
        async function fetchLogs() {
            try {
                const response = await fetch('/logs');
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                allLogs = await response.json();
                renderLogs();
            } catch (error) {
                console.error('Failed to fetch logs:', error);
                logTableBody.innerHTML = '<tr><td colspan="3" class="text-center p-4 text-red-400">Error loading logs. Is the server running?</td></tr>';
            } finally {
                loadingIndicator.style.display = 'none';
            }
        }

        // Function to render logs based on the current filter
        function renderLogs() {
            const searchTerm = searchInput.value.toLowerCase();
            const filteredLogs = allLogs.filter(log =>
                log.message.toLowerCase().includes(searchTerm) ||
                log.source.toLowerCase().includes(searchTerm)
            );

            // Reverse the logs to show the newest first
            const logsToRender = filteredLogs.slice().reverse();

            logTableBody.innerHTML = ''; // Clear existing logs

            if (logsToRender.length === 0 && allLogs.length > 0) {
                const row = document.createElement('tr');
                row.innerHTML = `<td colspan="3" class="text-center p-4 text-gray-500">No logs match your search.</td>`;
                logTableBody.appendChild(row);
            } else {
                 logsToRender.forEach(log => {
                    const row = document.createElement('tr');
                    row.className = 'hover:bg-gray-700/50';

                    // Sanitize content to prevent HTML injection
                    const escapeHtml = (unsafe) => {
                        return unsafe
                             .replace(/&/g, "&amp;")
                             .replace(/</g, "&lt;")
                             .replace(/>/g, "&gt;")
                             .replace(/"/g, "&quot;")
                             .replace(/'/g, "&#039;");
                    }

                    row.innerHTML = `
                        <td class="p-3 text-sm text-gray-400 whitespace-nowrap">${escapeHtml(log.timestamp)}</td>
                        <td class="p-3 text-sm text-gray-300 whitespace-nowrap">${escapeHtml(log.source)}</td>
                        <td class="p-3 text-sm text-white font-mono" style="word-break: break-all;">${escapeHtml(log.message)}</td>
                    `;
                    logTableBody.appendChild(row);
                });
            }
            logCountElement.textContent = `Displaying ${logsToRender.length} of ${allLogs.length} logs.`;
        }

        // --- Event Listeners and Initializers ---
        searchInput.addEventListener('keyup', renderLogs);
        
        clearButton.addEventListener('click', () => {
            searchInput.value = '';
            renderLogs();
        });

        function setupAutoRefresh() {
             if (autoRefreshToggle.checked) {
                autoRefreshInterval = setInterval(fetchLogs, 3000);
            } else {
                clearInterval(autoRefreshInterval);
            }
        }
        
        autoRefreshToggle.addEventListener('change', setupAutoRefresh);

        // Initial fetch and setup
        document.addEventListener('DOMContentLoaded', () => {
            fetchLogs();
            setupAutoRefresh();
        });
    </script>
</body>
</html>
"""

# --- Syslog Server Implementation ---
class SyslogUDPHandler(socketserver.BaseRequestHandler):
    """
    Handles incoming syslog messages. This handler is used by all syslog servers.
    """
    def handle(self):
        try:
            data = self.request[0].strip()
            # Decode message, trying multiple encodings for robustness
            message = ""
            for encoding in ['utf-8', 'latin-1', 'ascii']:
                try:
                    message = data.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            
            if not message:
                print(f"Could not decode message from {self.client_address[0]}")
                return

            source = self.client_address[0]
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            log_entry = {
                "timestamp": timestamp,
                "source": source,
                "message": message
            }

            with LOGS_LOCK:
                LOGS.append(log_entry)
                # Trim the log buffer if it exceeds the max size
                if len(LOGS) > MAX_LOGS:
                    del LOGS[0]
        except Exception as e:
            print(f"Error handling syslog message: {e}")


# --- Web Server Implementation ---
class WebUIHandler(SimpleHTTPRequestHandler):
    """
    Handles HTTP requests for the web UI.
    """
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_CONTENT.encode('utf-8'))
        elif self.path == '/logs':
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            with LOGS_LOCK:
                self.wfile.write(json.dumps(LOGS).encode('utf-8'))
        else:
            # Fallback for other requests (e.g., favicon.ico)
            self.send_response(404)
            self.end_headers()


def run_web_server():
    """Starts the web interface HTTP server."""
    try:
        server = HTTPServer((WEB_HOST, WEB_PORT), WebUIHandler)
        print(f"Web interface available at http://{WEB_HOST}:{WEB_PORT}")
        server.serve_forever()
    except Exception as e:
        print(f"Failed to start web server: {e}")


# --- MODIFIED: Main execution block to handle multiple ports ---
if __name__ == "__main__":
    # --- Start a thread for each syslog port ---
    syslog_threads = []
    print("Starting syslog listeners...")
    for port in SYSLOG_PORTS:
        # We need a function scope to properly capture the 'port' variable for the thread
        def start_server_for_port(p=port):
            try:
                server = socketserver.UDPServer((SYSLOG_HOST, p), SyslogUDPHandler)
                print(f"-> Syslog server listening on UDP {SYSLOG_HOST}:{p}")
                server.serve_forever(poll_interval=0.5)
            except PermissionError:
                print(f"[ERROR] Permission denied to bind to port {p}. Try running with 'sudo'.")
            except Exception as e:
                print(f"[ERROR] Failed to start syslog server on port {p}: {e}")

        thread = threading.Thread(target=start_server_for_port)
        thread.daemon = True
        thread.start()
        syslog_threads.append(thread)

    # --- Start the web server in its own thread ---
    web_thread = threading.Thread(target=run_web_server)
    web_thread.daemon = True
    web_thread.start()

    print("\nAll servers started. Press Ctrl+C to exit.")
    
    # Keep the main thread alive to handle Ctrl+C
    try:
        # This is a simple way to wait for the web_thread, or any other long-running thread
        web_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down servers...")

