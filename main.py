import argparse

def main():
    parser = argparse.ArgumentParser(description="Simple file transfer system.")

    parser.add_argument("path", help="Path of the file or directory to send or receive.", nargs="?")
    
    # Protocol selection
    protocol_group = parser.add_mutually_exclusive_group(required=True)
    protocol_group.add_argument("--tcp", action="store_true", help="Use TCP protocol for file transfer.")
    protocol_group.add_argument("--udp", action="store_true", help="Use UDP protocol for file transfer.")
    protocol_group.add_argument("--ping", action="store_true", help="Use ping protocol for RTT.")
    protocol_group.add_argument("--bandwidth", action="store_true", help="Use iperf to test bandwidth.")
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=False)
    mode_group.add_argument("-s", "--send", action="store_true", help="Send file or directory.")
    mode_group.add_argument("-r", "--receive", action="store_true", help="Receive file or directory.")
    
    # Params
    parser.add_argument("-i", "--ip", help="IP address for sending file.", type=str, default="localhost")
    parser.add_argument("-p", "--port", help="Port for sending or receiving files.", type=int, default=12345)
    parser.add_argument("-f", "--fragment", help="Fragment size for sending files.", type=int, default=1024)
    parser.add_argument("-c", "--count", help="Packet count for ping.", type=int, default=5)
    parser.add_argument("-U", "--username", help="Username for authentication.", type=str, default="admin")
    parser.add_argument("-P", "--password", help="Password for authentication.", type=str, default="admin123")

    # iperf Params
    parser.add_argument("--iserver", help="Password for authentication.", type=str, default="speedtest.serverius.net")
    parser.add_argument("--iport", help="Password for authentication.", type=int, default=5002)
    parser.add_argument("--iduration", help="Password for authentication.", type=int, default=15)
    parser.add_argument("--ipath", help="Password for authentication.", type=str, default="input\\iperf3.exe")
    parser.add_argument("--iinter", help="Password for authentication.", type=str, default=None)
    parser.add_argument("--iexport", help="Password for authentication.", type=str, default="bandwidth_test.json")

    args = parser.parse_args()

    if args.tcp == True:
        if args.send == True:
            from utils.tcp_sender import tcp_send
            tcp_send(args.path, args.ip, args.port, args.fragment, args.username, args.password)
        else:
            from utils.tcp_receiver import tcp_receive
            tcp_receive(args.path, args.port, args.username, args.password)
    elif args.udp == True:
        if args.send == True:
            from utils.udp_sender import udp_send
            udp_send(args.path, args.ip, args.port, args.fragment, args.username, args.password)
        else:
            from utils.udp_receiver import udp_receive
            udp_receive(args.path, args.port, args.username, args.password)
    elif args.ping == True:
        if args.send == True:
            from utils.ping_sender import ping_send
            ping_send(args.ip, args.port, args.count, args.username, args.password)
        else:
            from utils.ping_receiver import ping_receive
            ping_receive(args.port, args.username, args.password)
    elif args.bandwidth == True:
        from utils.bandwidth_test import measure_bandwidth
        measure_bandwidth(args.iserver, args.iport, args.iduration, args.ipath, args.iinter, args.iexport)


if __name__ == "__main__":
    main()
