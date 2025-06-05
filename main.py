import argparse
import time

def main(file: str, protocol: bool, mode: bool, recursive: bool, server_ip: str, server_port: int, fragment_size: int):
    '''
    Arguments:
    - protocol:
        False -> UDP
        True  -> TCP
    - mode:
        False -> Receiver
        True  -> Sender
    - recursive:
        False -> Single file receive
        True  -> Recursive directory receive
    - server_ip: ip address of receiver
    - server_port: port of receiver
    - fragment_size: fragment size
    '''
    print(f"[+] Protocol: {"TCP" if protocol else "UDP"}, Mode: {"Sender" if mode else "Receiver"}, Recursive: {recursive}")

    if(protocol):
        if(mode):
            from utils.tcp_sender import tcp_send
            tcp_send(filename=file, ip=server_ip, port=server_port, fragment=fragment_size)
        else:
            from utils.tcp_receiver import tcp_receive
            if(recursive):
                while(True):
                    tcp_receive(foldername=file, ip=server_ip, port=server_port)
                    time.sleep(0.05)
            else:
                tcp_receive(foldername=file, ip=server_ip, port=server_port)
    else:
        if(mode):
            print("send")
        else:
            print("rec")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple file transfer system.")
    
    parser.add_argument("file", help="Path of the file or directory to send or receive.")
    
    # Protocol selection
    protocol_group = parser.add_mutually_exclusive_group(required=True)
    protocol_group.add_argument("-t", "--tcp", action="store_true", help="Use TCP protocol for file transfer.")
    protocol_group.add_argument("-u", "--udp", action="store_true", help="Use UDP protocol for file transfer.")
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("-s", "--sender", action="store_true", help="Send file or directory.")
    mode_group.add_argument("-r", "--receiver", action="store_true", help="Receive file or directory.")
    
    # IP address
    parser.add_argument("-i", "--ip", help="IP address for sending file.", type=str, default="192.168.0.1")

    # Port
    parser.add_argument("-p", "--port", help="Port for sending or receiving files.", type=int, default=12345)

    # Fragment size
    parser.add_argument("-f", "--fragment", help="Fragment size for sending files.", type=int, default=1024)

    # Optional recursive flag
    parser.add_argument("-c", "--recursive", action="store_true", help="Recursively receive files.")

    args = parser.parse_args()

    # Call main with parsed arguments
    main(file=args.file, protocol=args.tcp, mode=args.sender, server_ip=args.ip, server_port=args.port,
         fragment_size=args.fragment, recursive=args.recursive,)
