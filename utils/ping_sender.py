import socket
import time

def ping_send(ip: str, port: int, count: int):
    ping = []

    for i in range(count):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Opening socket
                s.settimeout(5.0)

                start = time.time()     # Start time
                s.connect((ip, port))   # Connecting
                s.sendall(b'ping')      # Sendin data
                data = s.recv(1024)     # Receiving data
                end = time.time()       # End time

                if data:
                    rtt = (end - start) * 1000  # Calculating time
                    ping.append(rtt)
                    print(f"Ping {i+1}: RTT = {rtt:.2f} ms")
                else:
                    print(f"Ping {i+1}: HATA (Veri alınamadı)")
                    ping.append(None)
        except Exception as e:
            print(f"Ping {i+1}: HATA ({e})")
            ping.append(None)
        
        if i < count - 1: # Wait before other ping
            time.sleep(1)
    
    successful_pings = [p for p in ping if p is not None]    
    return sum(successful_pings) / len(successful_pings)

if __name__ == "__main__":
    ping_send("localhost", 12345, 5)
