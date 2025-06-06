# server.py
import socket

def ping_receive(port: int):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", port))
        s.listen()
        print(f"Sunucu localhost:{port} adresinde dinleniyor...")

        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Bağlantı kabul edildi: {addr}")
                data = conn.recv(1024)
                if data:
                    conn.sendall(data)

if __name__ == "__main__":
    ping_receive(12345)