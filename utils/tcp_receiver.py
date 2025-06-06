import socket
import select
import os

def tcp_receive(foldername: str, port: int):
    # Dir check
    if not os.path.exists(foldername):
        os.makedirs(foldername)
        print(f"Klasör oluşturuldu: {foldername}")
    elif not os.path.isdir(foldername):
        print(f"Hata: {foldername} bir klasör değil!")
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
                print(f"Bağlantı kabul edildi: {address}")
                
                # Get file data
                data = client_socket.recv(1024).decode('utf-8')
                filename, filesize, fragment, *_ = data.split('|')
                filesize = int(filesize)
                fragment = int(fragment)

                print(f"Alınacak dosya: {filename}")
                print(f"Dosya boyutu: {filesize} bytes")
                print(f"Dosya parça boyutu: {fragment} bytes")
                
                # Save file
                with open(foldername + filename, 'wb') as file:
                    bytes_received = 0
                    while bytes_received < filesize:
                        data = client_socket.recv(1024)
                        if not data:
                            break
                        file.write(data)
                        bytes_received += len(data)
                        
                        progress = (bytes_received / filesize) * 100
                        print(f"\rİlerleme: {progress:.1f}%", end='', flush=True)
                
                print(f"\nDosya başarıyla alındı: {filename}")
            except KeyboardInterrupt:
                print("Sunucu kapatılıyor...")
                break
            except Exception as e:
                print(f"Dosya alma hatası: {e}")
            finally:
                if 'client_socket' in locals():
                    client_socket.close()
                    
    except Exception as e:
        print(f"Sunucu hatası: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    tcp_receive("data/", "localhost", 12345)