import socket
import os
import hashlib

def tcp_send(filepath: str, ip: str, port: int, fragment: int):
    # File check
    if not os.path.exists(filepath) and not os.path.isfile(filepath):
        print(f"HATA: {filepath} dosyası bulunamadı!")
        return
    
    if not os.access(filepath, os.R_OK):
        print(f"HATA: {filepath} dosyası okunamıyor!")
        return

    # Get file data and calculate checksum
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)
    
    # Calculate file checksum
    file_hash = hashlib.md5()
    with open(filepath, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b""):
            file_hash.update(chunk)
    checksum = file_hash.hexdigest()

    # Create Socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        # Connect Server
        client_socket.connect((ip, port))
        print(f"Sunucuya bağlandı: {ip}:{port}")
        
        # Send file data with checksum
        info = f"{filename}|{filesize}|{fragment}|{checksum}|"
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
        print(f"Dosya checksum: {checksum}")
        
        # Send File
        with open(filepath, 'rb') as file:
            bytes_sent = 0
            while bytes_sent < filesize:
                data = file.read(fragment)
                if not data:
                    break
                client_socket.send(data)
                bytes_sent += len(data)
                
                progress = (bytes_sent / filesize) * 100
                print(f"\rİlerleme: {progress:.1f}%", end='', flush=True)
        
        print(f"\rDosya başarıyla gönderildi!")
    except Exception as e:
        print(f"HATA: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    tcp_send("input/test.txt", "localhost", 12345, 1024)