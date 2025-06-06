import socket
import time

def ping_send(ip: str, port: int, count: int):
    ping = []

    for i in range(count):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                start = time.time()
                s.connect((ip, port))
                s.sendall(b'ping')
                data = s.recv(1024)
                end = time.time()

                rtt = (end - start) * 1000
                ping.append(rtt)
                print(f"Ping {i+1}: RTT = {rtt:.2f} ms")
        except Exception as e:
            print(f"Ping {i+1}: FAILED ({e})")
        time.sleep(1)
    return ping

if __name__ == "__main__":
    ping_send("localhost", 12345, 4)
