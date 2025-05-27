# type: ignore
from scapy.all import *
import hashlib
import threading

received_fragments = {}
file_transfer_done = threading.Event()

def checksum(data):
    return hashlib.sha256(data).hexdigest()

def handle_packet(packet, server_port):
    if TCP in packet and packet[TCP].dport == server_port:
        payload = bytes(packet[TCP].payload)
        if not payload:
            return
        
        # Special END packet
        if payload == b"END":
            print("[+] End of file transfer signal received.")
            file_transfer_done.set()
            return
        
        # Extracting fragment
        fragment_id = int.from_bytes(payload[0:4], 'big')
        recv_checksum = payload[4:68].decode()
        data = payload[68:]

        calc_checksum = checksum(data)
        if recv_checksum == calc_checksum:
            received_fragments[fragment_id] = data
            print(f"[+] Received valid fragment {fragment_id}")
        else:
            print(f"[-] Checksum mismatch on fragment {fragment_id}")

def tcp_receiv(output_file: str, server_port: int):
    print(f"[+] Listening on {server_port}...")

    sniff_thread = threading.Thread(target=lambda: sniff(
        filter=f"tcp port {server_port}",
        prn=lambda pkt: handle_packet(pkt, server_port),
        stop_filter=lambda x: file_transfer_done.is_set()
    ))
    sniff_thread.start()

    sniff_thread.join()

    with open(output_file, "wb") as f:
        for i in sorted(received_fragments.keys()):
            f.write(received_fragments[i])
    print(f"[+] File reassembled and saved as {output_file}")

if __name__ == "__main__":
    tcp_receiv(output_file="output_file.txt", server_port=12345)
