# File Transfer System

A simple and versatile file transfer application that supports multiple protocols (TCP, UDP, Auto-selection) with built-in network testing capabilities.

## Features

- **Multiple Protocols**: TCP, UDP, and automatic protocol selection based on network conditions
- **File & Directory Transfer**: Send and receive both individual files and entire directories
- **Network Testing**: Built-in ping functionality and bandwidth testing with iperf
- **Authentication**: Username/password authentication for secure transfers
- **GUI Interface**: User-friendly graphical interface alongside command-line operation
- **Real-time Monitoring**: Terminal output for monitoring transfer progress

## Requirements

Install the required dependencies:

```bash
pip install -r requirements.txt
```

Required packages:
- cffi==1.17.1
- cryptography==45.0.3
- psutil==7.0.0
- pycparser==2.22

## Installation

1. Clone or download the project files
2. Install dependencies: `pip install -r requirements.txt`
3. Ensure you have the required directory structure:
   ```
   project/
   ├── main.py
   ├── gui.py
   ├── requirements.txt
   ├── utils/
   │   ├── tcp_sender.py
   │   ├── tcp_receiver.py
   │   ├── udp_sender.py
   │   ├── udp_receiver.py
   │   ├── ping_sender.py
   │   ├── ping_receiver.py
   │   └── bandwidth_test.py
   └── input/
       └── iperf3.exe
   ```

## Usage

### GUI Mode (Recommended)

Launch the graphical interface:

```bash
python main.py --gui
```

The GUI provides three main tabs:
- **TCP/UDP**: File transfer operations
- **Ping**: Network latency testing
- **Bandwidth**: Network speed testing

### Command Line Mode

#### Basic File Transfer

**Send a file using TCP:**
```bash
python main.py --tcp --send path/to/file.txt --ip 192.168.1.100 --port 12345
```

**Receive files using TCP:**
```bash
python main.py --tcp --receive output/ --port 12345
```

**Send using UDP:**
```bash
python main.py --udp --send path/to/file.txt --ip 192.168.1.100 --port 12345
```

**Auto protocol selection (recommended):**
```bash
python main.py --auto --send path/to/file.txt --ip 192.168.1.100 --port 12345
```

#### Network Testing

**Ping test:**
```bash
# Send ping
python main.py --ping --send --ip 192.168.1.100 --port 12345 --count 10

# Receive ping
python main.py --ping --receive --port 12345
```

**Bandwidth test:**
```bash
python main.py --bandwidth --iserver speedtest.serverius.net --iport 5002 --iduration 30
```

## Command Line Parameters

### General Options
- `--tcp`: Use TCP protocol
- `--udp`: Use UDP protocol  
- `--auto`: Automatic protocol selection based on ping results
- `--ping`: Ping functionality
- `--bandwidth`: Bandwidth testing
- `--gui`: Launch graphical interface

### Transfer Options
- `-s, --send`: Send mode
- `-r, --receive`: Receive mode
- `path`: File or directory path

### Network Parameters
- `-i, --ip`: Target IP address (default: localhost)
- `-p, --port`: Port number (default: 12345)
- `-f, --fragment`: Fragment size in bytes (default: 1024)
- `-c, --count`: Ping packet count (default: 5)

### Authentication
- `-U, --username`: Username (default: admin)
- `-P, --password`: Password (default: admin123)

### Bandwidth Test Parameters
- `--iserver`: iperf server (default: speedtest.serverius.net)
- `--iport`: iperf port (default: 5002)
- `--iduration`: Test duration in seconds (default: 15)
- `--ipath`: Path to iperf3.exe (default: input/iperf3.exe)
- `--iinter`: Network interface
- `--iexport`: Export file for results (default: bandwidth_test.json)

## Usage Examples

### Example 1: Simple File Transfer

**Sender (Computer A):**
```bash
python main.py --tcp --send document.pdf --ip 192.168.1.50 --port 8080
```

**Receiver (Computer B):**
```bash
python main.py --tcp --receive downloads/ --port 8080
```

### Example 2: Auto Protocol Selection

**Sender:**
```bash
python main.py --auto --send backup.zip --ip 192.168.1.100 --count 3
```

**Receiver:**
```bash
python main.py --auto --receive received_files/ --port 12345
```

### Example 3: Network Testing

**Ping test:**
```bash
python main.py --ping --send --ip google.com --port 80 --count 5
```

**Bandwidth test:**
```bash
python main.py --bandwidth --iduration 60 --iexport speed_test_results.json
```

## How Auto Protocol Selection Works

The auto mode automatically chooses between TCP and UDP based on network conditions:

1. Performs a ping test to measure network latency
2. If ping < 50ms: Uses **TCP** (reliable, good for stable connections)
3. If ping ≥ 50ms: Uses **UDP** (faster, good for high-latency connections)
