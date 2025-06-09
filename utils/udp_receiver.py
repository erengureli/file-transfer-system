import socket
import select
import os
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.backends import default_backend
import struct

def udp_receive(folderpath: str, port: int, valid_username: str, valid_password: str):
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

    # Create UDP Socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    # UDP buffer optimizations
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2*1024*1024)  # 2MB send buffer
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 2*1024*1024)  # 2MB receive buffer
    
    try:
        # Bind to port
        server_socket.bind(("0.0.0.0", port))
        print(f"UDP Sunucu localhost:{port} adresinde dinleniyor...")
        
        while True:
            try:
                ready, _, _ = select.select([server_socket], [], [], 1.0)
                
                if not ready: continue

                # Receive initial connection request
                data, client_address = server_socket.recvfrom(1024)
                if data == b"CONNECT":
                    print(f"\nBağlantı talebi alındı: {client_address}")
                    
                    # Send public key to client
                    chunks = [public_pem[i:i+1024] for i in range(0, len(public_pem), 1024)]
                    server_socket.sendto(struct.pack('!I', len(chunks)), client_address)
                    
                    for i, chunk in enumerate(chunks):
                        server_socket.sendto(struct.pack('!I', i) + chunk, client_address)
                    
                    # Wait for ACK
                    ack_data, _ = server_socket.recvfrom(1024)
                    if ack_data != b"KEY_RECEIVED":
                        continue
                
                # Client authentication
                auth_data, _ = server_socket.recvfrom(2048)
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
                        server_socket.sendto(b"AUTH_FAILED", client_address)
                        continue
                    else:
                        print("Kimlik doğrulama başarılı!")
                        server_socket.sendto(b"AUTH_SUCCESS", client_address)
                except Exception as e:
                    print(f"Kimlik doğrulama hatası: {e}")
                    server_socket.sendto(b"AUTH_FAILED", client_address)
                    continue
                
                # Receive encrypted AES key
                encrypted_aes_key, _ = server_socket.recvfrom(2048)
                aes_key = private_key.decrypt(
                    encrypted_aes_key,
                    padding.OAEP(
                        mgf=padding.MGF1(algorithm=hashes.SHA256()),
                        algorithm=hashes.SHA256(),
                        label=None
                    )
                )
                
                # Send ACK for AES key
                server_socket.sendto(b"AES_KEY_RECEIVED", client_address)
                
                # Receive IV
                iv_data, _ = server_socket.recvfrom(1024)
                iv = iv_data
                
                # Send ACK for IV
                server_socket.sendto(b"IV_RECEIVED", client_address)
                
                # Get file data
                file_info, _ = server_socket.recvfrom(2048)
                data_str = file_info.decode('utf-8').rstrip('a')  # Remove padding
                filename, filesize, fragment, checksum, *_ = data_str.split('|')
                filesize = int(filesize)
                fragment = int(fragment)

                print(f"Alınacak dosya: {filename}")
                print(f"Dosya boyutu: {filesize} bytes")
                print(f"Dosya parça boyutu: {fragment} bytes")
                print(f"Beklenen SHA-256 checksum: {checksum}")
                
                # Send ACK for file info
                server_socket.sendto(b"FILE_INFO_RECEIVED", client_address)
                
                # Setup AES decryption
                cipher = Cipher(algorithms.AES(aes_key), modes.CBC(iv), backend=default_backend())
                decryptor = cipher.decryptor()
                
                # Prepare for file reception with packet ordering
                total_encrypted_size = filesize + (16 - filesize % 16) if filesize % 16 != 0 else filesize
                max_packet_size = 65507  # Max UDP payload size
                expected_packets = (total_encrypted_size + max_packet_size - 1) // max_packet_size
                received_packets = {}
                
                print(f"Beklenen paket sayısı: {expected_packets}")
                
                # Receive file data packets
                bytes_received = 0
                while len(received_packets) < expected_packets:
                    try:
                        server_socket.settimeout(5.0)  # 5 second timeout
                        packet_data, addr = server_socket.recvfrom(max_packet_size + 100)
                        
                        if addr != client_address:
                            continue
                        
                        # Extract packet number and data
                        packet_num = struct.unpack('!I', packet_data[:4])[0]
                        encrypted_chunk = packet_data[4:]
                        
                        received_packets[packet_num] = encrypted_chunk
                        bytes_received += len(encrypted_chunk)
                        
                        # Send ACK for this packet
                        server_socket.sendto(struct.pack('!I', packet_num), client_address)
                        
                        # Update progress
                        progress = (len(received_packets) / expected_packets) * 100
                        print(f"\rPaket alındı: {len(received_packets)}/{expected_packets} ({progress:.1f}%)", end='', flush=True)
                        
                    except socket.timeout:
                        print(f"\nTimeout! Alınan paket: {len(received_packets)}/{expected_packets}")
                        # Request missing packets
                        missing = [i for i in range(expected_packets) if i not in received_packets]
                        if missing:
                            for miss in missing[:10]:  # Request first 10 missing packets
                                server_socket.sendto(b"RESEND:" + struct.pack('!I', miss), client_address)
                        continue
                
                server_socket.settimeout(None)  # Remove timeout
                
                # Save file and calculate checksum - decrypt in order
                file_hash = hashlib.sha256()
                
                with open(folderpath + filename, 'wb') as file:
                    receive_buffer = b""
                    
                    for packet_num in sorted(received_packets.keys()):
                        encrypted_data = received_packets[packet_num]
                        receive_buffer += encrypted_data
                        
                        # Process complete 16-byte blocks
                        while len(receive_buffer) >= 16:
                            block_to_decrypt = receive_buffer[:16]
                            receive_buffer = receive_buffer[16:]
                            
                            # Decrypt block
                            decrypted_block = decryptor.update(block_to_decrypt)
                            file.write(decrypted_block)
                            file_hash.update(decrypted_block)
                    
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
                    server_socket.sendto(b"FILE_SUCCESS", client_address)
                else:
                    print(f"\rHATA: Dosya bozuk! Beklenen: {checksum}, Alınan: {received_checksum}")
                    os.remove(folderpath + filename)
                    print(f"Bozuk dosya silindi: {filename}")
                    server_socket.sendto(b"FILE_FAILED", client_address)
                    
            except KeyboardInterrupt:
                print("Sunucu kapatılıyor...")
                break
            except Exception as e:
                print(f"HATA: {e}")
                    
    except Exception as e:
        print(f"HATA: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    udp_receive("output/", 12345, "admin", "admin123")