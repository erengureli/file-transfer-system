import tkinter as tk
from tkinter import ttk, filedialog
import threading
from contextlib import redirect_stdout, redirect_stderr

# Ping limit for auto protocol selection
PING_LIMIT = 50  # milliseconds - adjust this value as needed

class TerminalRedirector:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        
    def write(self, text):
        # Handle carriage return by replacing current line
        if '\r' in text and not text.endswith('\n'):
            # Find the last complete line in the text widget
            lines = text.split('\r')
            
            # Get current cursor position
            try:
                current_line_start = self.text_widget.index("end-1c linestart")
                current_line_end = self.text_widget.index("end-1c lineend")
                
                # Delete current line content after last newline
                if current_line_start != current_line_end:
                    self.text_widget.delete(current_line_start, current_line_end)
                
                # Insert the last part (what should be on the current line)
                self.text_widget.insert(current_line_start, lines[-1])
            except tk.TclError:
                # Fallback: just insert the text
                self.text_widget.insert(tk.END, lines[-1])
        else:
            # Normal text - insert as is
            self.text_widget.insert(tk.END, text)
        
        self.text_widget.see(tk.END)
        self.text_widget.update()
        
    def flush(self):
        # Simple flush - just update the display
        self.text_widget.update()

class FileTransferGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("File Transfer System")
        self.root.geometry("800x700")
        
        # Main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Tab structure
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Tabs
        self.tcp_udp_frame = ttk.Frame(self.notebook)
        self.ping_frame = ttk.Frame(self.notebook)
        self.bandwidth_frame = ttk.Frame(self.notebook)
        
        self.notebook.add(self.tcp_udp_frame, text="TCP/UDP")
        self.notebook.add(self.ping_frame, text="Ping")
        self.notebook.add(self.bandwidth_frame, text="Bandwidth")
        
        # Terminal
        terminal_label = ttk.Label(main_frame, text="Terminal Output:")
        terminal_label.grid(row=1, column=0, sticky=tk.W, pady=(10, 5))
        
        terminal_frame = ttk.Frame(main_frame)
        terminal_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.terminal_text = tk.Text(terminal_frame, height=12, bg="black", fg="white", font=("Consolas", 9))
        terminal_scrollbar = ttk.Scrollbar(terminal_frame, orient="vertical", command=self.terminal_text.yview)
        self.terminal_text.configure(yscrollcommand=terminal_scrollbar.set)
        
        self.terminal_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        terminal_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Clear terminal button
        clear_btn = ttk.Button(main_frame, text="Clear Terminal", command=self.clear_terminal)
        clear_btn.grid(row=3, column=0, pady=5, sticky=tk.W)
        
        # Grid configuration
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        terminal_frame.columnconfigure(0, weight=1)
        terminal_frame.rowconfigure(0, weight=1)
        
        # Setup UI for tabs
        self.setup_tcp_udp_tab()
        self.setup_ping_tab()
        self.setup_bandwidth_tab()
        
        # Terminal redirection
        self.terminal_redirector = TerminalRedirector(self.terminal_text)
        
    def setup_tcp_udp_tab(self):
        # TCP/UDP tab
        frame = self.tcp_udp_frame
        
        # Center all content in a container frame
        container = ttk.Frame(frame)
        container.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Protocol selection
        protocol_frame = ttk.LabelFrame(container, text="Protocol", padding="15")
        protocol_frame.pack(fill='x', pady=(0, 15))
        
        protocol_inner = ttk.Frame(protocol_frame)
        protocol_inner.pack(expand=True)
        
        self.protocol_var = tk.StringVar(value="tcp")
        ttk.Radiobutton(protocol_inner, text="TCP", variable=self.protocol_var, value="tcp").pack(side='left', padx=20)
        ttk.Radiobutton(protocol_inner, text="UDP", variable=self.protocol_var, value="udp").pack(side='left', padx=20)
        ttk.Radiobutton(protocol_inner, text="Auto", variable=self.protocol_var, value="auto").pack(side='left', padx=20)
        
        # Mode selection
        mode_frame = ttk.LabelFrame(container, text="Mode", padding="15")
        mode_frame.pack(fill='x', pady=(0, 15))
        
        mode_inner = ttk.Frame(mode_frame)
        mode_inner.pack(expand=True)
        
        self.mode_var = tk.StringVar(value="send")
        self.mode_var.trace('w', self.on_mode_change)  # Add trace for mode changes
        ttk.Radiobutton(mode_inner, text="Send", variable=self.mode_var, value="send").pack(side='left', padx=20)
        ttk.Radiobutton(mode_inner, text="Receive", variable=self.mode_var, value="receive").pack(side='left', padx=20)
        
        # File/Directory selection
        path_frame = ttk.LabelFrame(container, text="File/Directory Path", padding="15")
        path_frame.pack(fill='x', pady=(0, 15))
        
        path_inner = ttk.Frame(path_frame)
        path_inner.pack(expand=True, fill='x')
        
        self.path_var = tk.StringVar(value="input/test.txt")  # Default for send mode
        path_entry = ttk.Entry(path_inner, textvariable=self.path_var, width=50)
        path_entry.pack(side='left', padx=(0, 10), fill='x', expand=True)
        
        ttk.Button(path_inner, text="Browse", command=self.browse_path).pack(side='right')
        
        # Parameters
        params_frame = ttk.LabelFrame(container, text="Parameters", padding="15")
        params_frame.pack(fill='x', pady=(0, 15))
        
        # Create grid layout for parameters
        params_grid = ttk.Frame(params_frame)
        params_grid.pack(expand=True)
        
        # Row 1: IP and Port
        ttk.Label(params_grid, text="IP Address:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.ip_var = tk.StringVar(value="localhost")
        ttk.Entry(params_grid, textvariable=self.ip_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(params_grid, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        self.port_var = tk.StringVar(value="12345")
        ttk.Entry(params_grid, textvariable=self.port_var, width=10).grid(row=0, column=3, padx=5, pady=5)
        
        # Row 2: Fragment Size and Username
        ttk.Label(params_grid, text="Fragment Size:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.fragment_var = tk.StringVar(value="1024")
        ttk.Entry(params_grid, textvariable=self.fragment_var, width=10).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(params_grid, text="Username:").grid(row=1, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        self.username_var = tk.StringVar(value="admin")
        ttk.Entry(params_grid, textvariable=self.username_var, width=15).grid(row=1, column=3, padx=5, pady=5)
        
        # Row 3: Password and Ping Count (for auto mode)
        ttk.Label(params_grid, text="Password:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.password_var = tk.StringVar(value="admin123")
        ttk.Entry(params_grid, textvariable=self.password_var, width=15, show="*").grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(params_grid, text="Ping Count (Auto):").grid(row=2, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        self.auto_ping_count_var = tk.StringVar(value="5")
        ttk.Entry(params_grid, textvariable=self.auto_ping_count_var, width=10).grid(row=2, column=3, padx=5, pady=5)
        
        # Center the parameters grid
        params_grid.pack(expand=True)
        
        # Start button
        button_frame = ttk.Frame(container)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Start Transfer", command=self.start_tcp_udp_transfer).pack()
        
    def setup_ping_tab(self):
        # Ping tab
        frame = self.ping_frame
        
        # Center all content in a container frame
        container = ttk.Frame(frame)
        container.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Mode selection
        ping_mode_frame = ttk.LabelFrame(container, text="Mode", padding="15")
        ping_mode_frame.pack(fill='x', pady=(0, 15))
        
        mode_inner = ttk.Frame(ping_mode_frame)
        mode_inner.pack(expand=True)
        
        self.ping_mode_var = tk.StringVar(value="send")
        ttk.Radiobutton(mode_inner, text="Send Ping", variable=self.ping_mode_var, value="send").pack(side='left', padx=20)
        ttk.Radiobutton(mode_inner, text="Receive Ping", variable=self.ping_mode_var, value="receive").pack(side='left', padx=20)
        
        # Parameters
        ping_params_frame = ttk.LabelFrame(container, text="Parameters", padding="15")
        ping_params_frame.pack(fill='x', pady=(0, 15))
        
        # Create grid layout for parameters
        params_grid = ttk.Frame(ping_params_frame)
        params_grid.pack(expand=True)
        
        # Row 1: IP and Port
        ttk.Label(params_grid, text="IP Address:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=10)
        self.ping_ip_var = tk.StringVar(value="localhost")
        ttk.Entry(params_grid, textvariable=self.ping_ip_var, width=20).grid(row=0, column=1, padx=10, pady=10)
        
        ttk.Label(params_grid, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5), pady=10)
        self.ping_port_var = tk.StringVar(value="12345")
        ttk.Entry(params_grid, textvariable=self.ping_port_var, width=10).grid(row=0, column=3, padx=10, pady=10)
        
        # Row 2: Packet Count (centered)
        ttk.Label(params_grid, text="Packet Count:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=10)
        self.ping_count_var = tk.StringVar(value="5")
        ttk.Entry(params_grid, textvariable=self.ping_count_var, width=10).grid(row=1, column=1, padx=10, pady=10)
        
        # Center the parameters grid
        params_grid.pack(expand=True)
        
        # Start button
        button_frame = ttk.Frame(container)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Start Ping", command=self.start_ping).pack()
        
    def setup_bandwidth_tab(self):
        # Bandwidth tab
        frame = self.bandwidth_frame
        
        # Center all content in a container frame
        container = ttk.Frame(frame)
        container.pack(expand=True, fill='both', padx=20, pady=20)
        
        # Parameters
        bandwidth_params_frame = ttk.LabelFrame(container, text="iperf Parameters", padding="15")
        bandwidth_params_frame.pack(fill='x', pady=(0, 15))
        
        # Create grid layout for parameters
        params_grid = ttk.Frame(bandwidth_params_frame)
        params_grid.pack(expand=True, fill='x')
        
        # Row 1: Server and Port
        ttk.Label(params_grid, text="Server:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.iserver_var = tk.StringVar(value="speedtest.serverius.net")
        ttk.Entry(params_grid, textvariable=self.iserver_var, width=30).grid(row=0, column=1, padx=10, pady=5, sticky='w')
        
        ttk.Label(params_grid, text="Port:").grid(row=0, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        self.iport_var = tk.StringVar(value="5002")
        ttk.Entry(params_grid, textvariable=self.iport_var, width=10).grid(row=0, column=3, padx=10, pady=5)
        
        # Row 2: Duration and Interface
        ttk.Label(params_grid, text="Duration (sec):").grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.iduration_var = tk.StringVar(value="15")
        ttk.Entry(params_grid, textvariable=self.iduration_var, width=10).grid(row=1, column=1, padx=10, pady=5, sticky='w')
        
        ttk.Label(params_grid, text="Interface:").grid(row=1, column=2, sticky=tk.W, padx=(20, 5), pady=5)
        self.iinter_var = tk.StringVar()
        ttk.Entry(params_grid, textvariable=self.iinter_var, width=15).grid(row=1, column=3, padx=10, pady=5)
        
        # Row 3: iperf3 Path
        ttk.Label(params_grid, text="iperf3 Path:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.ipath_var = tk.StringVar(value="input\\iperf3.exe")
        path_frame = ttk.Frame(params_grid)
        path_frame.grid(row=2, column=1, columnspan=2, sticky='ew', padx=10, pady=5)
        ttk.Entry(path_frame, textvariable=self.ipath_var, width=35).pack(side='left', fill='x', expand=True)
        ttk.Button(path_frame, text="Browse", command=self.browse_iperf_path).pack(side='right', padx=(5, 0))
        
        # Row 4: Export File
        ttk.Label(params_grid, text="Export File:").grid(row=3, column=0, sticky=tk.W, padx=(0, 5), pady=5)
        self.iexport_var = tk.StringVar(value="bandwidth_test.json")
        ttk.Entry(params_grid, textvariable=self.iexport_var, width=25).grid(row=3, column=1, padx=10, pady=5, sticky='w')
        
        # Configure grid columns
        params_grid.columnconfigure(1, weight=1)
        
        # Start button
        button_frame = ttk.Frame(container)
        button_frame.pack(pady=20)
        ttk.Button(button_frame, text="Start Bandwidth Test", command=self.start_bandwidth_test).pack()
    
    def on_mode_change(self, *args):
        """Update path default when mode changes"""
        if self.mode_var.get() == "send":
            self.path_var.set("input/test.txt")
        else:  # receive
            self.path_var.set("output/")
    
    def browse_path(self):
        if self.mode_var.get() == "send":
            path = filedialog.askopenfilename()
        else:
            path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
    
    def browse_iperf_path(self):
        path = filedialog.askopenfilename(title="Select iperf3 executable")
        if path:
            self.ipath_var.set(path)
    
    def clear_terminal(self):
        self.terminal_text.delete(1.0, tk.END)
    
    def run_in_thread(self, func):
        """Run function in separate thread and redirect output to terminal"""
        def wrapper():
            try:
                with redirect_stdout(self.terminal_redirector), redirect_stderr(self.terminal_redirector):
                    func()
                # Flush any remaining content
                self.terminal_redirector.flush()
            except Exception as e:
                self.terminal_text.insert(tk.END, f"Error: {str(e)}\n")
                self.terminal_text.see(tk.END)
        
        thread = threading.Thread(target=wrapper)
        thread.daemon = True
        thread.start()
    
    def start_tcp_udp_transfer(self):
        """Start TCP/UDP transfer"""
        def transfer():
            protocol = self.protocol_var.get()
            mode = self.mode_var.get()
            path = self.path_var.get()
            ip = self.ip_var.get()
            port = int(self.port_var.get())
            fragment = int(self.fragment_var.get())
            username = self.username_var.get()
            password = self.password_var.get()
            
            if protocol == "auto":
                print(f"Starting AUTO protocol selection...")
                print(f"Path: {path}")
                print(f"IP: {ip}, Port: {port}")
                print(f"Fragment size: {fragment}")
                print(f"Username: {username}")
                print(f"Ping limit: {PING_LIMIT}ms")
                print("-" * 50)
                
                try:
                    ping_count = int(self.auto_ping_count_var.get())
                    
                    if mode == "send":
                        from utils.ping_sender import ping_send_return
                        ping_result = ping_send_return(ip, port, ping_count)
                        if ping_result < PING_LIMIT:
                            print(f"\nPing {PING_LIMIT}'den küçük olduğu için TCP protokolü seçildi.\n")
                            from utils.tcp_sender import tcp_send
                            tcp_send(path, ip, port, fragment, username, password)
                        else:
                            print(f"\nPing {PING_LIMIT}'den büyük olduğu için UDP protokolü seçildi.\n")
                            from utils.udp_sender import udp_send
                            udp_send(path, ip, port, fragment, username, password)
                    else:  # receive mode
                        from utils.ping_receiver import ping_receive_return
                        ping_result = ping_receive_return(port)
                        if ping_result < PING_LIMIT:
                            print(f"\nPing {PING_LIMIT}'den küçük olduğu için TCP protokolü seçildi.\n")
                            from utils.tcp_receiver import tcp_receive
                            tcp_receive(path, port, username, password)
                        else:
                            print(f"\nPing {PING_LIMIT}'den büyük olduğu için UDP protokolü seçildi.\n")
                            from utils.udp_receiver import udp_receive
                            udp_receive(path, port, username, password)
                            
                except ImportError as e:
                    print(f"Module import error: {e}")
                    print("Make sure the utils modules are available in the correct path.")
                except Exception as e:
                    print(f"Auto protocol selection error: {e}")
            else:
                # Manual protocol selection (existing code)
                print(f"Starting {protocol.upper()} {mode}...")
                print(f"Path: {path}")
                print(f"IP: {ip}, Port: {port}")
                print(f"Fragment size: {fragment}")
                print(f"Username: {username}")
                print("-" * 50)
                
                try:
                    if protocol == "tcp":
                        if mode == "send":
                            from utils.tcp_sender import tcp_send
                            tcp_send(path, ip, port, fragment, username, password)
                        else:
                            from utils.tcp_receiver import tcp_receive
                            tcp_receive(path, port, username, password)
                    elif protocol == "udp":
                        if mode == "send":
                            from utils.udp_sender import udp_send
                            udp_send(path, ip, port, fragment, username, password)
                        else:
                            from utils.udp_receiver import udp_receive
                            udp_receive(path, port, username, password)
                except ImportError as e:
                    print(f"Module import error: {e}")
                    print("Make sure the utils modules are available in the correct path.")
                except Exception as e:
                    print(f"Transfer error: {e}")
        
        self.run_in_thread(transfer)
    
    def start_ping(self):
        """Start ping operation"""
        def ping():
            mode = self.ping_mode_var.get()
            ip = self.ping_ip_var.get()
            port = int(self.ping_port_var.get())
            count = int(self.ping_count_var.get())
            
            print(f"Starting ping {mode}...")
            print(f"IP: {ip}, Port: {port}")
            print(f"Packet count: {count}")
            print("-" * 50)
            
            try:
                if mode == "send":
                    from utils.ping_sender import ping_send
                    ping_send(ip, port, count)
                else:
                    from utils.ping_receiver import ping_receive
                    print("aaa")
                    ping_receive(port)
            except ImportError as e:
                print(f"Module import error: {e}")
                print("Make sure the utils modules are available in the correct path.")
            except Exception as e:
                print(f"Ping error: {e}")
        
        self.run_in_thread(ping)
    
    def start_bandwidth_test(self):
        """Start bandwidth test"""
        def bandwidth():
            server = self.iserver_var.get()
            port = int(self.iport_var.get())
            duration = int(self.iduration_var.get())
            path = self.ipath_var.get()
            interface = self.iinter_var.get() if self.iinter_var.get() else None
            export = self.iexport_var.get()
            
            print(f"Starting bandwidth test...")
            print(f"Server: {server}, Port: {port}")
            print(f"Duration: {duration} seconds")
            print(f"iperf3 path: {path}")
            print(f"Interface: {interface}")
            print(f"Export file: {export}")
            print("-" * 50)
            
            try:
                from utils.bandwidth_test import measure_bandwidth
                measure_bandwidth(server, port, duration, path, interface, export)
            except ImportError as e:
                print(f"Module import error: {e}")
                print("Make sure the utils modules are available in the correct path.")
            except Exception as e:
                print(f"Bandwidth test error: {e}")
        
        self.run_in_thread(bandwidth)

def main():
    root = tk.Tk()
    app = FileTransferGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()