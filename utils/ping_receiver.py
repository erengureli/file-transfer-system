import socket
import select

def ping_receive(port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:    # Opening socket
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        s.listen()
        print(f"Sunucu localhost:{port} adresinde dinleniyor...")

        while True:
            try:
                ready, _, _ = select.select([s], [], [], 1.0)   # Non-blocking design
                if ready:
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

if __name__ == "__main__":
    ping_receive(12345)