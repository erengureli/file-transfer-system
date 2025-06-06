import socket
import os

def tcp_send(filename: str, ip: str, port: int, fragment: int):
    # File check
    if not os.path.exists(filename) and not os.path.isfile(filename):
        print(f"Hata: {filename} dosyası bulunamadı!")
        return
    
    # Get file data
    filesize = os.path.getsize(filename)

    # Create Socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Sonnect Server
        client_socket.connect((ip, port))
        print(f"Sunucuya bağlandı: {ip}:{port}")
        
        # Send file data
        info = f"{filename}|{filesize}|{fragment}|"
        info_bytes = info.encode('utf-8')
        length = len(info_bytes)

        if length < 1024:
            padding = 1024 - length
            info_padded = info_bytes + b'a' * padding
        else:
            info_padded = info_bytes[:1024]

        client_socket.send(info_padded)
        
        print(f"Gönderilen dosya: {filename}")
        print(f"Dosya boyutu: {filesize} bytes")
        print(f"Dosya parça boyutu: {fragment} bytes")
        
        # Send File
        with open(filename, 'rb') as file:
            bytes_sent = 0
            while bytes_sent < filesize:
                data = file.read(fragment)
                if not data:
                    break
                client_socket.send(data)
                bytes_sent += len(data)
                
                progress = (bytes_sent / filesize) * 100
                print(f"\rİlerleme: {progress:.1f}%", end='', flush=True)
        
        print(f"\nDosya başarıyla gönderildi!")
    except Exception as e:
        print(f"Hata: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    tcp_send("test.txt", "localhost", 12345, 1024)