import socket
import select
import os
import hashlib

def tcp_receive(folderpath: str, port: int):
    # Dir check
    if not os.path.exists(folderpath):
        os.makedirs(folderpath)
        print(f"Klasör oluşturuldu: {folderpath}")
    elif not os.path.isdir(folderpath):
        print(f"HATA: {folderpath} bir klasör değil!")
        return  

    # Create Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        # Listen Connection
        server_socket.bind(("0.0.0.0", port))
        server_socket.listen(1)
        print(f"Sunucu localhost:{port} adresinde dinleniyor...")
        
        while True:
            try:
                ready, _, _ = select.select([server_socket], [], [], 1.0)
                
                if not ready:
                    continue

                # Accept Connection
                client_socket, address = server_socket.accept()
                print(f"\nBağlantı kabul edildi: {address}")
                
                # Get file data
                data = client_socket.recv(1024).decode('utf-8')
                filename, filesize, fragment, checksum, *_ = data.split('|')
                filesize = int(filesize)
                fragment = int(fragment)

                print(f"Alınacak dosya: {filename}")
                print(f"Dosya boyutu: {filesize} bytes")
                print(f"Dosya parça boyutu: {fragment} bytes")
                print(f"Beklenen checksum: {checksum}")
                
                # Save file and calculate checksum
                file_hash = hashlib.md5()
                with open(folderpath + filename, 'wb') as file:
                    bytes_received = 0
                    while bytes_received < filesize:
                        data = client_socket.recv(1024)
                        if not data:
                            break
                        file.write(data)
                        file_hash.update(data)
                        bytes_received += len(data)
                        
                        progress = (bytes_received / filesize) * 100
                        print(f"\rİlerleme: {progress:.1f}%", end='', flush=True)
                
                # Verify file integrity
                received_checksum = file_hash.hexdigest()
                if received_checksum == checksum:
                    print(f"\rDosya başarıyla alındı ve doğrulandı: {filename}")
                else:
                    print(f"\rHATA: Dosya bozuk! Beklenen: {checksum}, Alınan: {received_checksum}")
                    os.remove(folderpath + filename)
                    print(f"Bozuk dosya silindi: {filename}")
                    
            except KeyboardInterrupt:
                print("Sunucu kapatılıyor...")
                break
            except Exception as e:
                print(f"HATA: {e}")
            finally:
                if 'client_socket' in locals():
                    client_socket.close()
                    
    except Exception as e:
        print(f"HATA: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    tcp_receive("output/", 12345)