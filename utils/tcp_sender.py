# type: ignore
from scapy.all import *
import hashlib
import time

def checksum(data):
    return hashlib.sha256(data).hexdigest()

def tcp_send(input_file: str, server_ip: str, server_port: int, fragment_size: int):
    with open(input_file, "rb") as f:
        file_data = f.read()
    
    fragments = [file_data[i:i+fragment_size] for i in range(0, len(file_data), fragment_size)]
    
    for idx, fragment in enumerate(fragments):
        frag_id_bytes = idx.to_bytes(4, 'big')
        frag_checksum = checksum(fragment).encode()
        payload = frag_id_bytes + frag_checksum + fragment
        
        packet = IP(dst=server_ip)/TCP(dport=server_port, sport=RandShort(), flags='PA')/payload
        send(packet, verbose=False)
        print(f"[+] Sent fragment {idx}")
        time.sleep(0.05)

    # After all fragments, send END packet
    end_packet = IP(dst=server_ip)/TCP(dport=server_port, sport=RandShort(), flags='PA')/b"END"
    send(end_packet, verbose=False)
    print("[+] End of file transfer sent.")

if __name__ == "__main__":
    tcp_send(input_file="data.txt", server_ip="192.168.0.1", server_port=12345, fragment_size=1024)