import socket
import time
import struct

def ping_send(ip: str, port: int, count: int):
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
                    print(f"Ping {i+1}: RTT = {rtt:.2f} ms")
                else:
                    print(f"Ping {i+1}: HATA (Veri alınamadı)")
        except Exception as e:
            print(f"Ping {i+1}: HATA ({e})")
        
        if i < count - 1: # Wait before other ping
            time.sleep(1)

def ping_send_return(ip: str, port: int, count: int):
    rtt_times = []  # RTT değerlerini saklamak için liste
    
    for i in range(count):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: # Opening socket
                s.settimeout(5.0)

                start = time.time()     # Start time
                s.connect((ip, port))   # Connecting
                s.sendall(b'ping')      # Sending data
                data = s.recv(1024)     # Receiving data
                end = time.time()       # End time

                if data:
                    rtt = (end - start) * 1000  # Calculating time
                    rtt_times.append(rtt)  # RTT değerini listeye ekle
                    print(f"Ping {i+1}: RTT = {rtt:.2f} ms")
                else:
                    print(f"Ping {i+1}: HATA (Veri alınamadı)")
        except Exception as e:
            print(f"Ping {i+1}: HATA ({e})")
        
        if i < count - 1: # Wait before other ping
            time.sleep(1)
    
    # Ortalama hesaplama
    if rtt_times:
        avg_rtt = sum(rtt_times) / len(rtt_times)
        print(f"Ortalama RTT: {avg_rtt:.2f} ms")
        
        # Ortalamayı receivera gönder
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5.0)
                s.connect((ip, port))
                avg_message = f"AVG:{avg_rtt:.2f}".encode()
                s.sendall(avg_message)
                print("Ortalama değer receivera gönderildi.")
        except Exception as e:
            print(f"Ortalama gönderilirken hata: {e}")
        
        return avg_rtt
    else:
        print("Hiç başarılı ping olmadı, ortalama hesaplanamadı.")
        return 0.0

if __name__ == "__main__":
    ping_send("localhost", 12345, 5)
