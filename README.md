# Simple Syslog Server with Web UI (Multi-port)

A lightweight, single-file syslog server written in Python that provides a clean, modern web interface for viewing, searching, and filtering syslog messages in real-time. This tool is designed for easy deployment and can listen on **multiple UDP ports simultaneously**, aggregating all logs into a single view.

*The web interface showing live log data from multiple sources.*

## Features

* **Multi-port UDP Syslog Listener:** Listens on a configurable list of UDP ports (e.g., 514, 1514) for incoming syslog messages.

* **Real-time Web UI:** A built-in web server provides a user-friendly interface to view logs as they arrive.

* **Live Search & Filtering:** Instantly search through all collected logs directly from your browser.

* **Auto-Refresh:** The log view automatically updates to show the latest entries.

* **Zero Dependencies:** Runs using only the Python standard library. No `pip install` required.

* **Self-Contained:** The entire application—server and web UI—is contained in a single Python file.

* **In-Memory Storage:** Logs are stored in a capped, in-memory list for simplicity and speed.

## Requirements

* Python 3.x

## How to Use

1. **Download the File:**
   Save the `syslog_server.py` script to your local machine.

2. **Configure Ports:**
   Open `syslog_server.py` and edit the `SYSLOG_PORTS` list to include all the UDP ports you wish to monitor.



Example configuration

SYSLOG_PORTS = [514, 1514, 5140]


3. **Run the Server:**
Open your terminal, navigate to the directory where you saved the file, and execute the script:



python3 syslog_server.py


**Note on Permissions:** Standard syslog port `514` is privileged. On most systems, you will need administrator/root rights to use ports below 1024. You have two options:

* **Run with `sudo` (Recommended):**

  ```
  sudo python3 syslog_server.py
  
  ```

* **Use High Ports:** Ensure all ports in your `SYSLOG_PORTS` list are greater than 1024.

4. **Access the Web Interface:**
Open your web browser and navigate to:
`http://localhost:8000`

5. **Configure Log Sources:**
Configure your network devices (routers, switches, firewalls), servers, or applications to send their syslog messages to the IP address of the computer running the script, using one of the configured UDP ports.

## Configuration

You can easily change the server settings by editing the following variables at the top of the `syslog_server.py` script:

* `WEB_HOST`: The host address for the web UI (default: `"0.0.0.0"`).

* `WEB_PORT`: The port for the web UI (default: `8000`).

* `SYSLOG_HOST`: The host address for the syslog listener (default: `"0.0.0.0"`).

* `SYSLOG_PORTS`: A Python list of UDP ports for the syslog listeners (e.g., `[514, 1514]`).

* `MAX_LOGS`: The maximum number of log entries to keep in memory (default: `2000`).

## How It Works

The script operates by running multiple server components concurrently in separate threads:

1. **Syslog UDP Servers:** For each port in the `SYSLOG_PORTS` list, a dedicated `socketserver.UDPServer` thread is started. When a message is received on any of these ports, it's decoded, timestamped, and added to a single, shared, thread-safe global list.

2. **Web HTTP Server:** A single `http.server.HTTPServer` thread serves the web interface.

* Requests to the root path (`/`) return the self-contained HTML, CSS, and JavaScript for the user interface.

* Requests to the `/logs` path return the current list of all aggregated logs as a JSON object, which the web UI fetches to update the display.

This multi-threaded approach ensures that log collection from multiple ports is efficient and does not interfere with web requests.

## License

This project is licensed under the MIT License.
