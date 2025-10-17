# Pylog

Simple Syslog Server with Web UI

A lightweight, single-file syslog server written in Python that provides a clean, modern web interface for viewing, searching, and filtering syslog messages in real-time. This tool is designed for easy deployment and immediate use, requiring no external dependencies.

The web interface showing live log data.

# Features

UDP Syslog Listener: Listens on a configurable UDP port (default 514) for incoming syslog messages.

Real-time Web UI: A built-in web server provides a user-friendly interface to view logs as they arrive.

Live Search & Filtering: Instantly search through all collected logs directly from your browser.

Auto-Refresh: The log view automatically updates to show the latest entries.

Zero Dependencies: Runs using only the Python standard library. No pip install required.

Self-Contained: The entire application—server and web UI—is contained in a single Python file.

In-Memory Storage: Logs are stored in a capped, in-memory list for simplicity and speed.

# Requirements

Python 3.x

# How to Use

# Download the File:
Save the pylog.py script to your local machine.

# Run the Server:
Open your terminal, navigate to the directory where you saved the file, and execute the script:

python3 pylog.py


Note on Permissions: The standard syslog port 514 is a privileged port. On most systems, you will need administrator/root rights to use it. You have two options:

Run with sudo (Recommended for standard port):

sudo python3 syslog_server.py


Change the Port: Edit syslog_server.py and change the SYSLOG_PORT variable to a number greater than 1024 (e.g., 5140).

# Access the Web Interface:
Open your web browser and navigate to:
http://localhost:8000

# Configure Log Sources:
Configure your network devices (routers, switches, firewalls), servers, or applications to send their syslog messages to the IP address of the computer running the script, using the configured UDP port.

# Configuration

You can easily change the server settings by editing the following variables at the top of the syslog_server.py script:

WEB_HOST: The host address for the web UI (default: "0.0.0.0").

WEB_PORT: The port for the web UI (default: 8000).

SYSLOG_HOST: The host address for the syslog listener (default: "0.0.0.0").

SYSLOG_PORT: The UDP port for the syslog listener (default: 514).

MAX_LOGS: The maximum number of log entries to keep in memory (default: 2000).

# How It Works

The script operates by running two server components concurrently in separate threads:

Syslog UDP Server: A socketserver.UDPServer continuously listens for incoming data on the specified syslog port. When a message is received, it's decoded, timestamped, and added to a thread-safe global list.

Web HTTP Server: A http.server.HTTPServer serves the web interface.

Requests to the root path (/) return the self-contained HTML, CSS, and JavaScript for the user interface.

Requests to the /logs path return the current list of stored logs as a JSON object, which the web UI fetches to update the display.

This multi-threaded approach ensures that log collection is not interrupted by web requests, and vice-versa.

License

This project is licensed under the MIT License. See the LICENSE file for details.
