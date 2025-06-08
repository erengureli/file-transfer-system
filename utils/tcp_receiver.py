import socket
import select
import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import secrets

def tcp_receive(folderpath: str, port: int, valid_username: str, valid_password: str):
    # Dir check
    if not os.path.exists(folderpath):
        os.makedirs(folderpath)
        print(f"Klasör oluşturuldu: {folderpath}")
    elif not os.path.isdir(folderpath):
        print(f"HATA: {folderpath} bir klasör değil!")
        return  

    # Generate RSA key pair for this session
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    
    # Serialize public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Create Socket with optimized settings
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # TCP optimizations
    server_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle's algorithm
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB send buffer
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)  # 1MB receive buffer
    
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
                
                # Send public key to client
                client_socket.send(public_pem)
                
                # Client authentication
                auth_data = client_socket.recv(1024)
                try:
                    decrypted_auth = private_key.decrypt(
                        auth_data,
                        padding.OAEP(
                            mgf=padding.MGF1(algorithm=hashes.SHA256()),
                            algorithm=hashes.SHA256(),
                            label=None
                        )
                    )
                    username, password = decrypted_auth.decode('utf-8').split('|')
                    
                    if username != valid_username or password != valid_password:
                        print("HATA: Geçersiz kimlik doğrulama!")
                        client_socket.send(b"AUTH_FAILED")
                        client_socket.close()
                        continue
                    else:
                        print("Kimlik doğrulama başarılı!")
                        client_socket.send(b"AUTH_SUCCESS")
                except Exception as e:
                    print(f"Kimlik doğrulama hatası: {e}")
                    client_socket.send(b"AUTH_FAILED")
                    client_socket.close()
                    continue
                
                # Receive encrypted AES key
                encrypted_aes_key = client_socket.recv(256)
                aes_key = private_key.decrypt(
                    encrypted_aes_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                
                # Receive IV
                iv = client_socket.recv(16)
                
                # Get file data
                data = client_socket.recv(1024).decode('utf-8')
                filename, filesize, fragment, checksum, *_ = data.split('|')
                filesize = int(filesize)
                fragment = int(fragment)

                print(f"Alınacak dosya: {filename}")
                print(f"Dosya boyutu: {filesize} bytes")
                print(f"Dosya parça boyutu: {fragment} bytes")
                print(f"Beklenen SHA-256 checksum: {checksum}")
                
                # Setup AES decryption
                cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
                decryptor = cipher.decryptor()
                
                # Save file and calculate checksum (SHA-256) - optimized streaming
                file_hash = hashlib.sha256()
                receive_buffer = b""
                
                with open(folderpath + filename, 'wb') as file:
                    bytes_received = 0
                    total_encrypted_size = filesize + (16 - filesize % 16) if filesize % 16 != 0 else filesize
                    
                    while bytes_received < total_encrypted_size:
                        # Receive larger chunks for better performance
                        chunk_size = min(65536, total_encrypted_size - bytes_received)
                        encrypted_data = client_socket.recv(chunk_size)
                        
                        if not encrypted_data:
                            break
                        
                        receive_buffer += encrypted_data
                        bytes_received += len(encrypted_data)
                        
                        # Process complete 16-byte blocks
                        while len(receive_buffer) >= 16:
                            block_to_decrypt = receive_buffer[:16]
                            receive_buffer = receive_buffer[16:]
                            
                            # Decrypt block
                            decrypted_block = decryptor.update(block_to_decrypt)
                            file.write(decrypted_block)
                            file_hash.update(decrypted_block)
                        
                        # Update progress less frequently
                        if bytes_received % 65536 == 0 or bytes_received >= total_encrypted_size:
                            progress = (bytes_received / total_encrypted_size) * 100
                            print(f"\rİlerleme: {progress:.1f}%", end='', flush=True)
                    
                    # Process any remaining data
                    if receive_buffer:
                        decrypted_final = decryptor.update(receive_buffer)
                        file.write(decrypted_final)
                        file_hash.update(decrypted_final)
                    
                    # Finalize decryption
                    final_chunk = decryptor.finalize()
                    if final_chunk:
                        file.write(final_chunk)
                        file_hash.update(final_chunk)
                
                # Remove PKCS7 padding by truncating file to original size
                with open(folderpath + filename, 'r+b') as file:
                    file.truncate(filesize)
                
                # Recalculate hash for the actual file content
                file_hash = hashlib.sha256()
                with open(folderpath + filename, 'rb') as file:
                    while True:
                        chunk = file.read(65536)
                        if not chunk:
                            break
                        file_hash.update(chunk)
                
                # Verify file integrity using SHA-256
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
    tcp_receive("output/", 12345, "admin", "admin123")