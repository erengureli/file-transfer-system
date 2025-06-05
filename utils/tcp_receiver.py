import socket
import os

def tcp_receive(foldername: str, ip: str, port: int):

    # Klasör kontrolü
    if not os.path.exists(foldername) and not os.path.isdir(foldername):
        print(f"Hata: {foldername} klasör bulunamadı!")
        return

    # Socket oluştur
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # Bağlantıyı dinle
        server_socket.bind((ip, port))
        server_socket.listen(1)
        print(f"Sunucu {ip}:{port} adresinde dinleniyor...")
        
        # Bağlantı kabul et
        client_socket, address = server_socket.accept()
        print(f"Bağlantı kabul edildi: {address}")
        
        # Dosya bilgilerini al
        data = client_socket.recv(1024).decode('utf-8')
        filename, filesize, fragment, *_ = data.split('|')
        filesize = int(filesize)
        fragment = int(fragment)

        print(f"Alınacak dosya: {filename}")
        print(f"Dosya boyutu: {filesize} bytes")
        print(f"Dosya parça boyutu: {fragment} bytes")
        
        # Dosyayı kaydet
        with open(foldername + filename, 'wb') as file:
            bytes_received = 0
            while bytes_received < filesize:
                data = client_socket.recv(1024)
                if not data:
                    break
                file.write(data)
                bytes_received += len(data)
                
                # İlerleme göster
                progress = (bytes_received / filesize) * 100
                print(f"\rİlerleme: {progress:.1f}%", end='', flush=True)
        
        print(f"\nDosya başarıyla alındı: {filename}")
    except Exception as e:
        print(f"Hata: {e}")
    finally:
        client_socket.close()
        server_socket.close()

if __name__ == "__main__":
    tcp_receive("data/", "localhost", 12345)