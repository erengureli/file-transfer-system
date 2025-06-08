import socket
import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import secrets

def tcp_send(filepath: str, ip: str, port: int, fragment: int, username: str, password: str):
    # File check
    if not os.path.exists(filepath) and not os.path.isfile(filepath):
        print(f"HATA: {filepath} dosyası bulunamadı!")
        return
    
    if not os.access(filepath, os.R_OK):
        print(f"HATA: {filepath} dosyası okunamıyor!")
        return

    # Get file data and calculate checksum (SHA-256)
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)
    
    # Calculate file checksum using SHA-256
    file_hash = hashlib.sha256()
    with open(filepath, 'rb') as file:
        for chunk in iter(lambda: file.read(4096), b""):
            file_hash.update(chunk)
    checksum = file_hash.hexdigest()

    # Create Socket with optimized settings
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    # TCP optimizations
    client_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)  # Disable Nagle's algorithm
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024*1024)  # 1MB send buffer
    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024*1024)  # 1MB receive buffer
    
    try:
        # Connect Server
        client_socket.connect((ip, port))
        print(f"Sunucuya bağlandı: {ip}:{port}")
        
        # Receive server's public key
        public_key_pem = client_socket.recv(1024)
        public_key = serialization.load_pem_public_key(public_key_pem, backend=default_backend())
        
        # Send authentication credentials (encrypted with RSA)
        auth_data = f"{username}|{password}".encode('utf-8')
        encrypted_auth = public_key.encrypt(
            auth_data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        client_socket.send(encrypted_auth)
        
        # Wait for authentication response
        auth_response = client_socket.recv(1024)
        if auth_response != b"AUTH_SUCCESS":
            print("HATA: Kimlik doğrulama başarısız!")
            return
        else:
            print("Kimlik doğrulama başarılı!")
        
        # Generate AES key and IV
        aes_key = secrets.token_bytes(32)  # 256-bit key
        iv = secrets.token_bytes(16)       # 128-bit IV
        
        # Encrypt AES key with RSA and send
        encrypted_aes_key = public_key.encrypt(
            aes_key,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        client_socket.send(encrypted_aes_key)
        
        # Send IV
        client_socket.send(iv)
        
        # Send file data with checksum
        info = f"{filename}|{filesize}|{fragment}|{checksum}|"
        info_bytes = info.encode('utf-8')
        length = len(info_bytes)

        if length < 1024:
            padding_len = 1024 - length
            info_padded = info_bytes + b'a' * padding_len
        else:
            info_padded = info_bytes[:1024]

        client_socket.send(info_padded)
        
        print(f"Gönderilen dosya: {filename}")
        print(f"Dosya boyutu: {filesize} bytes")
        print(f"Dosya parça boyutu: {fragment} bytes")
        print(f"Dosya SHA-256 checksum: {checksum}")
        
        # Setup AES encryption
        cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Send file in optimized chunks (larger buffer for better performance)
        buffer_size = max(fragment, 65536)  # At least 64KB chunks
        with open(filepath, 'rb') as file:
            bytes_sent = 0
            encrypted_buffer = b""
            
            while bytes_sent < filesize:
                # Read larger chunk from file
                data = file.read(buffer_size)
                if not data:
                    break
                
                # Apply PKCS7 padding only to the last chunk
                if bytes_sent + len(data) >= filesize:
                    padding_length = 16 - (len(data) % 16)
                    if padding_length != 16:
                        data += bytes([padding_length] * padding_length)
                else:
                    # Ensure chunk is multiple of 16 for AES CBC
                    if len(data) % 16 != 0:
                        padding_needed = 16 - (len(data) % 16)
                        data += b'\x00' * padding_needed
                
                # Encrypt chunk
                encrypted_chunk = encryptor.update(data)
                encrypted_buffer += encrypted_chunk
                
                # Send when buffer is large enough or at the end
                while len(encrypted_buffer) >= 65536 or (bytes_sent + len(data) >= filesize and encrypted_buffer):
                    send_chunk = encrypted_buffer[:65536] if len(encrypted_buffer) >= 65536 else encrypted_buffer
                    client_socket.sendall(send_chunk)  # sendall ensures all data is sent
                    encrypted_buffer = encrypted_buffer[len(send_chunk):]
                
                bytes_sent += len(data) if bytes_sent + len(data) <= filesize else filesize - bytes_sent
                
                # Update progress less frequently for better performance
                if bytes_sent % (buffer_size * 10) == 0 or bytes_sent >= filesize:
                    progress = (bytes_sent / filesize) * 100
                    print(f"\rİlerleme: {progress:.1f}%", end='', flush=True)
            
            # Finalize encryption and send any remaining data
            final_chunk = encryptor.finalize()
            if final_chunk:
                client_socket.sendall(final_chunk)
        
        print(f"\rDosya başarıyla gönderildi!")
    except Exception as e:
        print(f"HATA: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    tcp_send("input/test.txt", "localhost", 12345, 1024, "admin", "admin123")