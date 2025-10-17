# Pylog - Simple Syslog Server with Web UI (Multi-port)

A lightweight, single-file syslog server written in Python that provides a clean, modern web interface for viewing, searching, and filtering syslog messages in real-time. This tool is designed for easy deployment and can listen on **multiple UDP ports simultaneously**.

All incoming logs are stored persistently in **flat files**, with a separate file for each listening port (e.g., `514.log`, `1514.log`).

## Screenshot
<img width="1613" height="454" alt="image" src="https://github.com/user-attachments/assets/60d56236-a71c-4da8-ac69-269f770d8fd6" />


## Features

* **Multi-port UDP Syslog Listener:** Listens on a configurable list of UDP ports for incoming syslog messages.

* **Persistent File-Based Storage:** Logs are saved to disk in `.log` files, one for each port, ensuring data survives restarts.

* **Real-time Web UI:** A built-in web server provides a user-friendly interface to view logs as they arrive.

* **Live Search & Filtering:** Instantly search through all collected logs directly from your browser.

* **Auto-Refresh:** The log view automatically updates to show the latest entries.

* **Zero Dependencies:** Runs using only the Python standard library. No `pip install` required.

* **Self-Contained:** The entire application—server and web UI—is contained in a single Python file.

## Requirements

* Python 3.x

## How to Use

1. **Download the File:**
   Save the `pylog.py` script to your local machine.

2. **Configure Ports & Log Directory:**
   Open `pylog.py` and edit the configuration variables at the top of the file.


Example configuration

`SYSLOG_PORTS = [514, 1514, 5140]`

`LOG_DIRECTORY = "syslog_logs"`

3. **Run the Server:**
Open your terminal, navigate to the directory where you saved the file, and execute the script:

`python3 pylog.py`

The script will automatically create the log directory if it doesn't exist.

**Note on Permissions:** To use privileged ports (below 1024), you must run the script with administrator/root rights.

**sudo python3 syslog_server.py**

4. **Access the Web Interface:**
Open your web browser and navigate to:
**`http://localhost:8000`**

5. **Configure Log Sources:**
Configure your devices to send syslog messages to the IP address of the computer running the script, using one of the configured UDP ports.

## Configuration

You can easily change the server settings by editing the following variables at the top of the `syslog_server.py` script:

* `WEB_HOST`: The host address for the web UI (default: `"0.0.0.0"`).

* `WEB_PORT`: The port for the web UI (default: `8000`).

* `SYSLOG_HOST`: The host address for the syslog listener (default: `"0.0.0.0"`).

* `SYSLOG_PORTS`: A Python list of UDP ports for the syslog listeners (e.g., `[514, 1514]`).

* `LOG_DIRECTORY`: The folder where log files will be stored (default: `"syslog_logs"`).

* `MAX_LOGS_PER_FILE_IN_UI`: The maximum number of recent logs to read from *each file* for display in the web UI.

## How It Works

1. **Syslog UDP Servers:** For each port in the `SYSLOG_PORTS` list, a dedicated `socketserver.UDPServer` thread is started. When a message is received, the handler writes it as a JSON object to a corresponding log file (e.g., messages on port 514 go to `syslog_logs/514.log`).

2. **Web HTTP Server:** A single `http.server.HTTPServer` thread serves the web interface.

* Requests to `/` return the UI's HTML, CSS, and JavaScript.

* Requests to `/logs` trigger a function that reads the last `N` lines from every `.log` file in the `LOG_DIRECTORY`, combines them, sorts them by timestamp, and returns the result as a JSON object. The UI then fetches and displays this data.

This design ensures logs are stored permanently on disk while the web interface remains fast and responsive by only reading the most recent entries.

## License

This project is licensed under the MIT License
