import socket
import select
import struct

def ping_receive(port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:    # Opening socket
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        s.listen()
        print(f"Sunucu localhost:{port} adresinde dinleniyor...")

        while True:
            try:
                ready, _, _ = select.select([s], [], [], 1.0)   # Non-blocking design
                if not ready: continue
                
                conn, addr = s.accept() # Acceptin connection
                with conn:
                    print(f"Bağlantı kabul edildi: {addr}")
                    data = conn.recv(1024)
                    if data: conn.sendall(data) # Sendin data
            except KeyboardInterrupt:
                print("Sunucu kapatılıyor...")
                break
            except Exception as e:
                print(f"Hata oluştu: {e}")
                continue

def ping_receive_return(port: int):
    received_average = 0.0
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:    # Opening socket
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        s.listen()
        print(f"Sunucu localhost:{port} adresinde dinleniyor...")

        while True:
            try:
                ready, _, _ = select.select([s], [], [], 1.0)   # Non-blocking design
                if not ready: continue

                conn, addr = s.accept() # Accepting connection
                with conn:
                    print(f"Bağlantı kabul edildi: {addr}")
                    data = conn.recv(1024)
                    if data:
                        message = data.decode()
                        
                        # Ortalama mesajı kontrolü
                        if message.startswith("AVG:"):
                            avg_value = float(message.split(":")[1])
                            received_average = avg_value
                            print(f"Ortalama RTT alındı: {avg_value:.2f} ms")
                            
                            conn.sendall(b"AVG_RECEIVED")  # Onay mesajı gönder
                            break
                        else:
                            conn.sendall(data)  # Normal ping mesajı için echo
                                
            except KeyboardInterrupt:
                print("Sunucu kapatılıyor...")
                return received_average
            except Exception as e:
                print(f"Hata oluştu: {e}")
                continue
            
    return received_average

if __name__ == "__main__":
    ping_receive(12345)